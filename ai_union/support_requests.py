"""Requests record a need; responses never grant tools, money or host access."""
import copy
from .engine import encoded, identifier, now, require, text
from .model_api import reject_saved_secrets


def propose(state, operation, actor, assignment_id, evidence_refs):
    require(actor != 'bootstrap' and assignment_id is not None, '申请需要正式决策任职')
    require(set(operation)=={'op','id','kind','need','reason'},'申请字段不完整或不支持')
    key=identifier(operation['id'])
    require(operation['kind'] in ('resources','tool'),'申请分类不支持')
    text(operation['need'],'申请需求',2000);text(operation['reason'],'申请理由',2000)
    requests=state.setdefault('support_requests',{})
    require(key not in requests,'申请标识已存在')
    requests[key]={'id':key,'kind':operation['kind'],'need':operation['need'],'reason':operation['reason'],
                   'raised_by':actor,'assignment_id':assignment_id,'evidence_refs':copy.deepcopy(evidence_refs),
                   'created_at':now(),'status':'pending','responses':[],'response_count':0}


def view(state,limit=12):
    items=sorted(state.get('support_requests',{}).values(),key=lambda r:(r['created_at'],r['id']),reverse=True)
    projected=[]
    for r in items[:limit]:
        item={k:copy.deepcopy(r[k]) for k in ('id','kind','need','reason','raised_by','assignment_id','created_at','status','response_count')}
        item['evidence_refs']=r['evidence_refs'][:12]
        item['evidence_truncated']=len(r['evidence_refs'])>12
        item['latest_response']=copy.deepcopy(r['responses'][-1]) if r['responses'] else None
        projected.append(item)
    return {'items':projected,'total':len(items),'truncated':len(items)>limit}


def respond(engine,board_key,request_id,status,reason,expected_version):
    identifier(request_id);text(reason,'申请响应依据',2000)
    require(status in ('needs_information','accepted_for_action','declined'),'申请响应状态不支持')
    with engine.transaction() as cx:
        board=engine._board(cx,board_key)
        reject_saved_secrets(cx,reason,extra_secret=board_key)
        s=engine._state(cx)
        require(type(expected_version) is int and expected_version==s['version'],'申请响应版本冲突')
        r=s.get('support_requests',{}).get(request_id)
        require(r is not None and r['status']!='declined','申请不存在或已经关闭')
        response={'status':status,'reason':reason,'board':board,'at':now()}
        r['status']=status;r['responses']=(r['responses']+[response])[-20:];r['response_count']+=1
        s['version']+=1
        engine._event(cx,'support_request_responded',{'request_id':request_id,**response})
        engine._save(cx,s)
    return response
