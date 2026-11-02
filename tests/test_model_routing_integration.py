import copy
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from ai_union.agent_protocol import work_result
from ai_union.engine import Rejected
from ai_union.executor import FixtureExecutor, ExecutionFailure
from ai_union.harness import HarnessExecutor
from ai_union.model_api import APIExecutor, bind_connection, configure_connection, resolve_chain, resolve_connection, resolve_roles
from ai_union.runner import run, reserved_calls
from tests import test_model_api as api_tests
from tests.test_runtime_fallback import Double


class RoutingIntegrationTests(unittest.TestCase):
    setUp=api_tests.ModelAPITests.setUp
    command=api_tests.ModelAPITests.command
    configure=api_tests.ModelAPITests.configure

    def secondary(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Double)
        server.daemon_threads=True;server.seen=[];server.status=200;server.model='secondary'
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(thread.join);self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        key=(self.e.root/'board.key').read_text(encoding='utf-8').strip()
        configure_connection(self.e,key,'secondary',dict(self.config,base_url=f'http://127.0.0.1:{server.server_port}/v1',model='secondary'),'secondary double','secondary-key')
        bind_connection(self.e,key,'primary','test default',fallbacks=['secondary'])
        return server,key

    def test_fallback_reserves_an_extra_call_and_survives_restart(self):
        self.configure();server,key=self.secondary();self.provider.code=401
        executor=APIExecutor(self.e.root,resolve_chain(self.e)[0],fallbacks=resolve_chain(self.e)[1])
        package=self.e.begin_connection_test(executor.metadata)
        result,usage=executor.execute(package);self.e.finish_connection_test(package['run_id'],result,usage)
        self.assertEqual(reserved_calls(self.e),2)
        self.assertEqual(len(server.seen),1)
        self.assertEqual(self.e.runs()[-1]['usage']['connection_id'],'secondary')
        with self.assertRaises(Rejected):self.e.reserve_model_attempt(package['run_id'],1,resolve_connection(self.e,'secondary'))

    def test_global_and_per_run_limit_stop_before_secondary_network_call(self):
        self.configure();server,key=self.secondary();self.provider.code=401
        self.e.configure_resources(key,{'max_calls':1,'timeout_seconds':5},'one actual request only')
        primary,chain=resolve_chain(self.e);executor=APIExecutor(self.e.root,primary,fallbacks=chain)
        package=self.e.begin_connection_test(executor.metadata)
        with self.assertRaises(ExecutionFailure):executor.execute(package)
        self.assertEqual(server.seen,[]);self.assertEqual(reserved_calls(self.e),1)

    def test_explicit_target_is_strict_and_unusable_role_does_not_use_default(self):
        self.configure();server,key=self.secondary()
        configure_connection(self.e,key,'disabled',dict(self.config,enabled=False),'disabled double','disabled-key')
        with self.assertRaises(Rejected):resolve_connection(self.e,'disabled')
        bind_connection(self.e,key,'disabled','bind worker',role='worker',fallbacks=[])
        executor=HarnessExecutor(self.e,resolve_connection(self.e),roles=resolve_roles(self.e))
        with self.assertRaises(Rejected):executor.prepare('work')

    def test_role_metadata_is_selected_before_package_reservation(self):
        self.configure();server,key=self.secondary()
        run(self.e,FixtureExecutor(copy.deepcopy(api_tests.FIXTURE)),1)
        bind_connection(self.e,key,'secondary','bind worker',role='worker',fallbacks=[])
        executor=HarnessExecutor(self.e,resolve_connection(self.e),roles=resolve_roles(self.e))
        def execute(package):
            self.assertEqual(package['execution']['connection_id'],'secondary')
            return work_result('Controlled delivery; no model called'),dict(executor.metadata,input_tokens=1,output_tokens=1)
        with patch.object(executor,'execute',side_effect=execute):
            actions=run(self.e,executor,1)
        self.assertEqual(actions[-1]['action'],'work',actions)
        self.assertEqual(self.e.runs()[-1]['package']['execution']['connection_id'],'secondary')
