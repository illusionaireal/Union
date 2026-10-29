"""Compatible AU descriptions. A controller descriptor never changes authority."""
import json
import re
from .engine import encoded, require, text
from .model_api import reject_saved_secrets

KEY = 'au_descriptor_v1'


def validate_descriptor(value):
    require(isinstance(value,dict) and set(value)=={'principal_id','display_name'},'治理描述字段不完整或不支持')
    require(isinstance(value['principal_id'],str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}',value['principal_id']) is not None,'治理主体引用无效')
    text(value['display_name'],'治理主体显示名',200)
    return dict(value)


def configure_descriptor(engine, board_key, value, reason, expected_version):
    ref=validate_descriptor(value)
    text(reason,'治理描述依据',2000)
    with engine.transaction() as cx:
        board=engine._board(cx,board_key)
        reject_saved_secrets(cx, {'controller_ref':ref,'reason':reason},extra_secret=board_key)
        state=engine._state(cx)
        require(type(expected_version) is int and expected_version==state['version'],'治理描述版本冲突')
        cx.execute('INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)',(KEY,encoded({'version':1,'controller_ref':ref})))
        state['version']+=1
        engine._event(cx,'controller_described',{'controller_ref':ref,'reason':reason,'board':board,'authority_source':'legacy_board'})
        engine._save(cx,state)
    return ref


def projection(engine, cx, s, *, actor=None, assignment_id=None):
    row=cx.execute('SELECT value FROM meta WHERE key=?',(KEY,)).fetchone()
    board=cx.execute("SELECT value FROM meta WHERE key='board_name'").fetchone()[0]
    ref={'principal_id':'legacy-board:'+s['id'],'display_name':board}
    if row:
        data=json.loads(row[0])
        require(data.get('version')==1,'治理描述版本不支持')
        ref=validate_descriptor(data['controller_ref'])
    require((actor is None)==(assignment_id is None),'行动身份与任职须同时提供')
    operations=[]
    if actor is not None:
        assignment=s['assignments'].get(assignment_id)
        require(s['phase']=='active' and actor in s['members'] and assignment is not None
                and assignment['active'] and assignment['member_id']==actor, '投影行动身份没有正式有效任职')
        operations=sorted(engine._authorize(s,engine._charter(cx,s['charter_version']),actor,assignment_id))
    return {'contract_version':1,'au':{k:s[k] for k in ('id','name','goal','phase')},
            'versions':{'state':s['version'],'charter':s['charter_version'],'policy':s['policy_version']},
            'governance':{'controller_ref':ref,'authority_source':'legacy_board'},
            'membership_scope':'single_au','member_refs':{k:{'au_id':s['id'],'member_id':k} for k in s['members']},
            'supported_operations':operations,'resource_summary':engine._budget(cx,s)}


def describe_au_v1(engine, *, actor=None, assignment_id=None):
    # Engine is a trusted host handle; network callers must first resolve it
    # through Console.engine/session scope. Never accept actor claims from HTTP.
    with engine.read_transaction() as cx:
        return projection(engine, cx, engine._state(cx), actor=actor, assignment_id=assignment_id)
