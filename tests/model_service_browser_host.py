"""Browser-only account/service double. No real accounts or external model calls."""
import argparse
import json
import sys
import threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai_union.console import Console
from ai_union.server import Server
from tests.support import CHARTER, RESOURCES
from tests.test_model_accounts import Backend
from ai_union import model_service


class BrowserService(Backend):
    def __init__(self): super().__init__(); self.requests={}
    def runtime(self): return {'protocol_version':1,'upstream':'controlled-browser-double'}
    def call(self, method, path, body=None, **kwargs):
        if path == '/v1/accounts': return {'accounts':[{'id':'controlled-account','name':'受控 Go 账号','workspace':'测试工作区','state':'connected'}]}
        if path.endswith('/models'): return {'models':[{'id':'controlled-model','name':'受控工具模型','tools':True,'context':32000,'output':8192}]}
        if path == '/v1/requests' and method == 'POST':
            assert body['id'] not in self.requests
            self.requests[body['id']]=body
            return {'id':body['id'],'state':'queued'}
        return super().call(method,path,body,**kwargs)
    def request(self, rid, au):
        body=self.requests[rid]; assert body['au_id']==au
        tool=next((m for m in reversed(body['messages']) if m['role']=='tool'),None)
        message={'role':'assistant','content':tool['content'] if tool else '受控连接测试'}
        if body['tools'] and not tool:
            message['tool_calls']=[{'id':'echo-1','type':'function','function':{'name':'connection_echo','arguments':'{}'}}]
        return {'id':rid,'au_id':au,'state':'completed','result':{'message':message,'usage':{'input_tokens':10,'output_tokens':5}}}
    def events(self, rid, au, after): return {'events':[{'request_id':rid,'seq':1,'type':'text_delta','payload':{'text':'受控模型流'}}] if after==0 else []}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);args=parser.parse_args()
    backend=BrowserService(); model_service.ModelServiceClient=lambda:backend
    app=Console(args.root,fixture=[])
    admin=app.new_session('board',platform_admin=True)
    receipt=app.command(admin,{'id':'browser-au','kind':'create','organization_id':None,'base_version':None,
      'data':{'name':'受控接入验收组织','goal':'验证页面与模型服务契约；不调用真实模型','board_name':'test','charter':CHARTER,'resources':RESOURCES}})
    server=Server(app,0); server.model_accounts.client=backend
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    print(json.dumps({'origin':server.origin,'board_url':server.origin+'/models#launch='+app.ticket('board',platform_admin=True),'organization_id':receipt['organization_id']}),flush=True)
    try:
        for line in sys.stdin:
            if json.loads(line)['op']=='stop':break
    finally:
        server.shutdown();server.server_close();thread.join();app.close()


if __name__=='__main__':main()
