"""Explicit wire adapters. The runtime owns authorization, tools and settlement."""
import copy
import base64
import json
import re
from .engine import encoded, require

PROTOCOLS = ('openai_chat_completions', 'openai_responses', 'anthropic_messages', 'google_generate_content')


def _parts(content, protocol):
    if isinstance(content, str): return [{'type':'text','text':content}]
    if content is None: return []
    require(isinstance(content,list), '消息内容格式无效')
    result=[]
    for part in content:
        require(isinstance(part,dict), '消息内容块无效')
        if part.get('type')=='text': result.append({'type':'text','text':part['text']}); continue
        require(part.get('type') in ('image_url','file'), '不支持的输入内容块')
        url=part.get('image_url',{}).get('url') if part['type']=='image_url' else part.get('file',{}).get('file_data')
        match=re.fullmatch(r'data:([\w.+/-]+);base64,([A-Za-z0-9+/=]+)',url or '')
        require(match is not None, '多模态输入必须为内嵌base64资料，不自动读取外部URL')
        mime,data=match.groups()
        require(mime in ('image/png','image/jpeg','image/webp','image/gif','application/pdf'), '输入资料格式不支持')
        require((part['type']=='file') == (mime=='application/pdf'), '资料类型与MIME不一致')
        decoded=base64.b64decode(data,validate=True)
        require(0<len(decoded)<=262144, '单份输入资料须为1至262144字节')
        if protocol=='anthropic_messages':
            result.append({'type':'document' if mime=='application/pdf' else 'image','source':{'type':'base64','media_type':mime,'data':data}})
        elif protocol=='google_generate_content': result.append({'inlineData':{'mimeType':mime,'data':data}})
        elif protocol=='openai_responses':
            result.append({'type':'input_file','filename':part.get('file',{}).get('filename','document.pdf'),'file_data':url} if mime=='application/pdf' else {'type':'input_image','image_url':url})
        else: result.append(copy.deepcopy(part))
    return result


def encode_request(protocol, body, key):
    require(protocol in PROTOCOLS, '模型协议不支持')
    headers={'Authorization':'Bearer '+key} if key else {}
    if protocol=='openai_chat_completions':
        for message in body['messages']:
            if isinstance(message.get('content'),list): _parts(message['content'],protocol)
        return copy.deepcopy(body), '/chat/completions', headers
    model=body['model']; limit=body.get('max_completion_tokens',body.get('max_tokens',8192))
    tools=[t['function'] for t in body.get('tools',[])]
    systems=[m.get('content','') for m in body['messages'] if m['role']=='system']
    require(all(isinstance(s,str) for s in systems), '系统消息必须是文本')
    messages=[m for m in body['messages'] if m['role']!='system']
    if protocol=='anthropic_messages':
        converted=[]
        for message in messages:
            if message['role']=='tool':
                value={'role':'user','content':[{'type':'tool_result','tool_use_id':message['tool_call_id'],'content':message['content']}]}
            else:
                content=_parts(message.get('content'),protocol)
                content += [{'type':'tool_use','id':c['id'],'name':c['function']['name'],'input':json.loads(c['function']['arguments'])} for c in message.get('tool_calls',[])]
                value={'role':message['role'],'content':content or [{'type':'text','text':' '}]}
            if converted and converted[-1]['role']==value['role']: converted[-1]['content'].extend(value['content'])
            else: converted.append(value)
        result={'model':model,'max_tokens':limit,'system':'\n\n'.join(systems),'messages':converted,'stream':False}
        if tools: result['tools']=[{'name':t['name'],'description':t.get('description',''),'input_schema':t['parameters']} for t in tools]
        return result, '/messages', {'x-api-key':key,'anthropic-version':'2023-06-01'}
    if protocol=='openai_responses':
        inputs=[]
        for message in messages:
            if message['role']=='tool': inputs.append({'type':'function_call_output','call_id':message['tool_call_id'],'output':message['content']}); continue
            if message.get('content'):
                content=_parts(message['content'],protocol)
                for part in content:
                    if part.get('type')=='text': part['type']='output_text' if message['role']=='assistant' else 'input_text'
                inputs.append({'role':message['role'],'content':content})
            inputs.extend({'type':'function_call','call_id':c['id'],'name':c['function']['name'],'arguments':c['function']['arguments']} for c in message.get('tool_calls',[]))
        result={'model':model,'input':inputs,'instructions':'\n\n'.join(systems),'max_output_tokens':limit,'store':False,'stream':False}
        if tools: result['tools']=[dict(type='function',**t) for t in tools]
        return result, '/responses', headers
    converted=[]; names={}
    for message in messages:
        if message['role']=='tool':
            require(message['tool_call_id'] in names, '工具结果缺少对应调用')
            parts=[{'functionResponse':{'name':names[message['tool_call_id']],'id':message['tool_call_id'],'response':{'result':message['content']}}}]
            role='user'
        else:
            role='model' if message['role']=='assistant' else 'user'
            parts=_parts(message.get('content'),protocol)
            parts=[{'text':p['text']} if p.get('type')=='text' else p for p in parts]
            calls=message.get('tool_calls',[])
            for call in calls: names[call['id']]=call['function']['name']
            parts += message.get('_provider_parts') or [{'functionCall':{'name':c['function']['name'],'id':c['id'],'args':json.loads(c['function']['arguments'])}} for c in calls]
        if parts: converted.append({'role':role,'parts':parts})
    result={'contents':converted,'generationConfig':{'maxOutputTokens':limit}}
    if systems: result['systemInstruction']={'parts':[{'text':'\n\n'.join(systems)}]}
    if tools: result['tools']=[{'functionDeclarations':tools}]
    require(re.fullmatch(r'[A-Za-z0-9_.:/-]+',model), 'Gemini模型标识无效')
    return result, '/models/'+model.removeprefix('models/')+':generateContent', {'x-goog-api-key':key}


def decode_response(protocol, data):
    require(isinstance(data,dict), '模型响应必须是对象')
    if protocol=='openai_chat_completions': return data
    message={'role':'assistant','content':''}; calls=[]; texts=[]; finish='stop'
    usage=data.get('usage') or {}; response_id=data.get('id'); actual=data.get('model')
    if protocol=='anthropic_messages':
        blocks=data.get('content',[])
        for block in blocks:
            if block.get('type')=='text': texts.append(block['text'])
            elif block.get('type')=='tool_use': calls.append({'id':block['id'],'type':'function','function':{'name':block['name'],'arguments':encoded(block['input'])}})
        stop=data.get('stop_reason')
        finish='length' if stop=='max_tokens' else 'stop' if stop in ('end_turn','stop_sequence','tool_use') else 'content_filter'
        usage={'prompt_tokens':usage.get('input_tokens'),'completion_tokens':usage.get('output_tokens'), 'prompt_tokens_details':{'cached_tokens':usage.get('cache_read_input_tokens')}}
    elif protocol=='openai_responses':
        for block in data.get('output',[]):
            if block.get('type')=='function_call': calls.append({'id':block['call_id'],'type':'function','function':{'name':block['name'],'arguments':block['arguments']}})
            elif block.get('type')=='message':
                for part in block.get('content',[]):
                    if part.get('type')=='output_text': texts.append(part['text'])
                    elif part.get('type')=='refusal': message['refusal']=part.get('refusal') or 'refused'
        finish='length' if data.get('status')=='incomplete' else 'stop' if data.get('status')=='completed' else 'content_filter'
        usage={'prompt_tokens':usage.get('input_tokens'),'completion_tokens':usage.get('output_tokens'), 'prompt_tokens_details':usage.get('input_tokens_details',{})}
    else:
        require(protocol=='google_generate_content', '模型协议不支持')
        candidates=data.get('candidates',[])
        require(len(candidates)==1, 'Gemini必须返回一个候选')
        parts=candidates[0].get('content',{}).get('parts',[])
        provider_parts=[]
        for index,part in enumerate(parts):
            if 'text' in part and not part.get('thought'): texts.append(part['text'])
            if 'functionCall' in part:
                call=part['functionCall']; call_id=call.get('id') or f'gemini-call-{index}'
                calls.append({'id':call_id,'type':'function','function':{'name':call['name'],'arguments':encoded(call.get('args',{}))}})
                provider_parts.append(copy.deepcopy(part))
        if provider_parts: message['_provider_parts']=provider_parts
        stop=candidates[0].get('finishReason')
        finish='length' if stop=='MAX_TOKENS' else 'stop' if stop=='STOP' else 'content_filter'
        raw=data.get('usageMetadata') or {}
        usage={'prompt_tokens':raw.get('promptTokenCount'),'completion_tokens':raw.get('candidatesTokenCount'),'prompt_tokens_details':{'cached_tokens':raw.get('cachedContentTokenCount')}}
        response_id=data.get('responseId'); actual=data.get('modelVersion')
    message['content']='\n'.join(texts)
    if calls:
        message['tool_calls']=calls
        if finish=='stop': finish='tool_calls'
    return {'id':response_id,'model':actual,'choices':[{'finish_reason':finish,'message':message}],'usage':usage}
