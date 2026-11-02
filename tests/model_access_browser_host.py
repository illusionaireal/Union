"""Private, restartable browser host. Uses a loopback model double only."""
import argparse
import json
import sys
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai_union.console import Console
from ai_union.server import Server
from tests.novel_browser_host import NovelProvider


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);args=parser.parse_args()
    app=Console(args.root,fixture=[]);server=Server(app,0)
    provider=ThreadingHTTPServer(('127.0.0.1',0),NovelProvider);provider.daemon_threads=True
    workers=[threading.Thread(target=s.serve_forever,daemon=True) for s in (server,provider)]
    for worker in workers:worker.start()
    print(json.dumps({'origin':server.origin,'board_url':server.origin+'/#launch='+app.ticket('board',platform_admin=True),'provider_url':f'http://127.0.0.1:{provider.server_port}/v1'}),flush=True)
    try:
        for line in sys.stdin:
            action=json.loads(line)['op']
            if action=='stop':break
            if action=='restart':
                port=server.server_port;server.shutdown();server.server_close();workers[0].join();app.close()
                app=Console(args.root,fixture=[]);server=Server(app,port)
                workers[0]=threading.Thread(target=server.serve_forever,daemon=True);workers[0].start()
                print(json.dumps({'restarted':True}),flush=True)
    finally:
        server.shutdown();server.server_close();provider.shutdown();provider.server_close()
        for worker in workers:worker.join()
        app.close()


if __name__=='__main__':main()
