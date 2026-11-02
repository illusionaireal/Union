import base64
import copy
import json
import unittest
from ai_union.engine import Rejected
from ai_union.model_media import payload, project_event, attach_visible_media
from ai_union.model_context import prepare_context
from ai_union.model_protocols import encode_request
from tests import test_model_api as api_tests


def content(data=b'simulated-png',mime='image/png'):
    return json.dumps({'text':'Read supplied media','attachments':[{'name':'input.png','mime':mime,'data':base64.b64encode(data).decode()}]})


class MediaTests(unittest.TestCase):
    def test_projection_hides_encoded_bytes_but_adapter_receives_authorized_media(self):
        raw=content();event={'kind':'model_input','data':{'content':raw}}
        package={'context':{'events':[event]}};before=copy.deepcopy(package)
        projected=project_event(raw)
        self.assertNotIn(base64.b64encode(b'simulated-png').decode(),projected)
        body=attach_visible_media(package,{'model':'gpt-4o','messages':[{'role':'system','content':'authority'},{'role':'user','content':'current task'}]})
        prepared,_=prepare_context({'provider':'openai','model':'gpt-4o','max_output_tokens':512},body)
        for protocol in ('openai_chat_completions','openai_responses','anthropic_messages','google_generate_content'):
            wire,_,_=encode_request(protocol,prepared,'simulated-key')
            self.assertIn(base64.b64encode(b'simulated-png').decode(),json.dumps(wire))
        self.assertEqual(package,before)
        work={'context':{'task':{'id':'work'}}}
        body={'messages':[{'role':'user','content':'only authorized task'}]}
        self.assertEqual(attach_visible_media(work,body),body)

    def test_payload_rejects_paths_urls_invalid_data_and_oversize(self):
        for raw in (content(b'x'*49153), content().replace('input.png','../private.png'), content().replace('image/png','text/html'),json.dumps({'text':'x','attachments':[{'url':'https://other.example'}]})):
            with self.assertRaises(Rejected):payload(raw)


class MediaEventTests(unittest.TestCase):
    setUp=api_tests.ModelAPITests.setUp
    command=api_tests.ModelAPITests.command
    configure=api_tests.ModelAPITests.configure

    def test_encoded_credentials_are_rejected_before_any_event_or_command_is_saved(self):
        self.configure();raw=content(api_tests.SECRET.encode(), 'application/pdf')
        with self.assertRaises(Rejected):self.command('event',{'kind':'model_input','content':raw,'source':'simulated upload','simulated':True})
        self.assertNotIn(base64.b64encode(api_tests.SECRET.encode()),self.e.db.read_bytes())

    def test_media_event_persists_with_explicit_simulation_and_original_bytes(self):
        raw=content()
        receipt=self.command('event',{'kind':'model_input','content':raw,'source':'simulated upload','simulated':True})
        self.assertEqual(receipt['status'],'succeeded')
        event=next(event for event in self.e.events() if event['kind']=='model_input')
        self.assertEqual(event['data']['content'],raw);self.assertTrue(event['data']['simulated'])
