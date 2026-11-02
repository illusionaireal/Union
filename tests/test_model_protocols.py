import json
import unittest
import re
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ai_union.engine import Rejected


class ProtocolTests(unittest.TestCase):
    def body(self):
        return {'model':'model-a','max_tokens':100,'stream':False,'messages':[
            {'role':'system','content':'Host instructions'}, {'role':'user','content':'Do work'},
            {'role':'assistant','content':'','tool_calls':[{'id':'call-1','type':'function','function':{'name':'lookup','arguments':'{"id":1}'}}]},
            {'role':'tool','tool_call_id':'call-1','content':'found'}],
            'tools':[{'type':'function','function':{'name':'lookup','description':'look up','parameters':{'type':'object','properties':{'id':{'type':'integer'}}}}}]}

    def test_anthropic_tool_result_roundtrip(self):
        from ai_union.model_protocols import encode_request, decode_response
        body, suffix, headers=encode_request('anthropic_messages',self.body(),'key')
        self.assertEqual(suffix,'/messages');self.assertEqual(headers['x-api-key'],'key')
        self.assertEqual(body['system'],'Host instructions')
        self.assertEqual(body['messages'][-1]['content'][0]['tool_use_id'],'call-1')
        result=decode_response('anthropic_messages',{'id':'reply','model':'actual','stop_reason':'tool_use','content':[{'type':'tool_use','id':'call-2','name':'lookup','input':{'id':2}}],'usage':{'input_tokens':5,'output_tokens':3}})
        self.assertEqual(json.loads(result['choices'][0]['message']['tool_calls'][0]['function']['arguments']),{'id':2})
        self.assertEqual(result['usage']['prompt_tokens'],5)

    def test_responses_tool_result_roundtrip_and_refusal(self):
        from ai_union.model_protocols import encode_request, decode_response
        body,suffix,headers=encode_request('openai_responses',self.body(),'key')
        self.assertEqual(suffix,'/responses');self.assertFalse(body['store'])
        self.assertEqual(body['input'][-1]['type'],'function_call_output')
        self.assertEqual(body['tools'][0]['name'],'lookup')
        result=decode_response('openai_responses',{'id':'reply','model':'actual','status':'completed','output':[{'type':'function_call','call_id':'call-2','name':'lookup','arguments':'{}'}],'usage':{'input_tokens':5,'output_tokens':3}})
        self.assertEqual(result['choices'][0]['finish_reason'],'tool_calls')
        result=decode_response('openai_responses',{'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'denied'}]}]})
        self.assertTrue(result['choices'][0]['message']['refusal'])

    def test_google_tool_result_roundtrip(self):
        from ai_union.model_protocols import encode_request, decode_response
        body,suffix,headers=encode_request('google_generate_content',self.body(),'key')
        self.assertEqual(suffix,'/models/model-a:generateContent')
        self.assertEqual(headers['x-goog-api-key'],'key')
        self.assertEqual(body['contents'][-1]['parts'][0]['functionResponse']['name'],'lookup')
        result=decode_response('google_generate_content',{'modelVersion':'actual','candidates':[{'finishReason':'STOP','content':{'parts':[{'functionCall':{'name':'lookup','args':{'id':2}}}]}}],'usageMetadata':{'promptTokenCount':5,'candidatesTokenCount':3}})
        self.assertEqual(result['choices'][0]['finish_reason'],'tool_calls')
        self.assertEqual(result['usage']['completion_tokens'],3)

    def test_unknown_protocol_fails_closed(self):
        from ai_union.model_protocols import encode_request
        with self.assertRaises(Rejected): encode_request('invented',self.body(),'key')


class NativeDouble(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.seen.append((self.path,body))
        first=bool(body.get('tools')); match=re.search(r'连接校验码：([A-Za-z0-9_-]+)',json.dumps(body,ensure_ascii=False))
        text='连接校验码：'+match[1] if match else 'tool call'
        if self.path.endswith('/messages'):
            reply={'id':'native-1','model':'native-test','stop_reason':'tool_use' if first else 'end_turn','content':[{'type':'tool_use','id':'echo-1','name':'connection_echo','input':{}}] if first else [{'type':'text','text':text}],'usage':{'input_tokens':12,'output_tokens':4}}
        elif self.path.endswith('/responses'):
            reply={'id':'native-1','model':'native-test','status':'completed','output':[{'type':'function_call','call_id':'echo-1','name':'connection_echo','arguments':'{}'}] if first else [{'type':'message','content':[{'type':'output_text','text':text}]}],'usage':{'input_tokens':12,'output_tokens':4}}
        else:
            reply={'responseId':'native-1','modelVersion':'native-test','candidates':[{'finishReason':'STOP','content':{'parts':[{'functionCall':{'id':'echo-1','name':'connection_echo','args':{}},'thoughtSignature':'simulated-signature'}] if first else [{'text':text}]}}],'usageMetadata':{'promptTokenCount':12,'candidatesTokenCount':4}}
        raw=json.dumps(reply,ensure_ascii=False).encode()
        self.send_response(200); self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)


class NativeHTTPTests(unittest.TestCase):
    def test_each_native_protocol_completes_real_http_tool_roundtrip(self):
        from ai_union.console import Console
        from ai_union.harness import test_tool_connection
        from ai_union.model_api import APIExecutor, configure_connection, resolve_connection
        from tests.support import CHARTER, RESOURCES
        with tempfile.TemporaryDirectory() as directory:
            app=Console(directory)
            server=ThreadingHTTPServer(('127.0.0.1',0),NativeDouble);server.seen=[];server.daemon_threads=True
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                board=app.new_session('board')
                receipt=app.command(board,{'id':'create-native','organization_id':None,'base_version':None,'kind':'create','data':{'name':'native doubles','goal':'tool roundtrip','board_name':'test','charter':CHARTER,'resources':RESOURCES}})
                engine=app.engine(board,receipt['organization_id']);key=(engine.root/'board.key').read_text(encoding='utf-8').strip()
                for index,protocol in enumerate(('anthropic_messages','openai_responses','google_generate_content')):
                    config={'name':protocol,'model':'native-test','base_url':f'http://127.0.0.1:{server.server_port}/v1','max_output_tokens':512,'token_limit_field':'max_tokens','timeout_seconds':5,'enabled':True,'protocol':protocol}
                    configure_connection(engine,key,'native-'+str(index),config,'native double','simulated-api-key')
                    executor=APIExecutor(engine.root,resolve_connection(engine,'native-'+str(index)))
                    outcome=test_tool_connection(engine,executor)
                    self.assertEqual(outcome['status'],'succeeded',outcome)
                    self.assertEqual(engine.runs()[-1]['usage']['protocol'],protocol)
                self.assertEqual(len(server.seen),6)
                self.assertIn('thoughtSignature',json.dumps(server.seen[-1][1]))
            finally:
                server.shutdown();server.server_close();thread.join();app.close()
