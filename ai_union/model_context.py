"""Conservative byte-token budgeting; never silently remove authority or live tools."""
import copy
from .catalog import metadata
from .engine import encoded, require


def validate_policy(value):
    require(isinstance(value,dict) and set(value)<={'window','strategy'}, '上下文策略字段无效')
    require(value.get('strategy','trim_history') in ('trim_history','reject'), '上下文策略不支持')
    if 'window' in value: require(type(value['window']) is int and 512<=value['window']<=10000000, '上下文窗口声明无效')


def _modality(part):
    if part.get('type')=='text': return 'text'
    if part.get('type')=='image_url': return 'image'
    if part.get('type')=='file': return 'pdf'
    require(False, '未知多模态内容类型')


def prepare_context(config, body):
    record=metadata(config['model'],config.get('provider'))
    policy=config.get('context_policy') or {}
    validate_policy(policy)
    limits=[v for v in (policy.get('window'), (record or {}).get('context_window')) if v]
    window=min(limits) if limits else None
    messages=copy.deepcopy(body['messages'])
    pending=set()
    for message in messages:
        require(not pending or message['role']=='tool', '工具结果必须紧随对应工具调用')
        for call in message.get('tool_calls',[]):
            require(call['id'] not in pending, '重复的工具调用ID')
            pending.add(call['id'])
        if message['role']=='tool':
            require(message.get('tool_call_id') in pending, '工具结果缺少对应调用')
            pending.remove(message['tool_call_id'])
        content=message.get('content')
        if isinstance(content,list):
            for part in content:
                modality=_modality(part)
                if modality!='text': require(record is not None and modality in record.get('input_modalities',[]), '模型输入能力未确认或不支持：'+modality)
    require(not pending, '工具调用尚无结果，不能发送不完整上下文')
    def size(): return len(encoded(messages).encode('utf-8'))+len(encoded(body.get('tools',[])).encode('utf-8'))+128*len(messages)
    before=size(); removed=0
    reserve=config['max_output_tokens']+256
    if window:
        budget=window-reserve
        require(budget>0, '输出上限已占满上下文窗口，请调整配置')
        while size()>budget:
            require(policy.get('strategy','trim_history')=='trim_history' and len(messages)>3, '当前工作资料超过上下文容量，请缩小任务或更换模型')
            # The host instructions and current work package are always the first
            # two messages. Remove complete old turns, never half a tool pair.
            end=3
            while end<len(messages) and messages[end]['role']=='tool': end+=1
            require(end<len(messages), '最近工具往返超过上下文容量，请缩小任务')
            removed+=end-2; del messages[2:end]
    require(size()<=1000000, '任务会话超出本地上下文容量')
    report={'estimator':'utf8_bytes_upper_bound','window':window,'estimated_input_tokens':size(), 'dropped_messages':removed,'dropped_bytes':before-size(), 'strategy':policy.get('strategy','trim_history')}
    return dict(body,messages=messages), report
