"""Private single-host HTTPS entry for the actual UNION React workspace.
No production NAS proxy/config is modified. No fixture or automatic dispatch.
"""
import http.client
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import os
from pathlib import Path
import ssl
import threading
from ai_union.console import Console
from ai_union.server import Server

root=Path('/private')
os.umask(0o077)
(root/'console').mkdir(exist_ok=True,mode=0o700)
(root/'console').chmod(0o700)
app=Console(root/'console',fixture=None,enable_codex=False,enable_api=True)
server=Server(app,8766)
threading.Thread(target=server.serve_forever,daemon=True).start()
origin='https://192.168.1.29:18766'

class Proxy(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(10)
        self.request=self.server.ssl_context.wrap_socket(self.request,server_side=True)
        super().setup()
    def log_message(self,*args): pass
    def do_GET(self): self.forward(False)
    def do_POST(self): self.forward(True)
    def do_OPTIONS(self): self.send_error(403)
    def forward(self,write):
        if self.headers.get('Host')!='192.168.1.29:18766' or self.headers.get('Origin') not in ((origin,) if write else (None,origin)) or self.headers.get('Sec-Fetch-Site','same-origin') not in ('same-origin','none'):
            self.send_error(403);return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=200000: self.send_error(413);return
            body=self.rfile.read(length) if length else None
            headers={k:v for k,v in self.headers.items() if k.lower() in ('content-type','cookie','x-union-launch','sec-fetch-site')}
            headers['Host']='127.0.0.1:8766'
            if write: headers['Origin']=server.origin
            conn=http.client.HTTPConnection('127.0.0.1',8766,timeout=15)
            conn.request('POST' if write else 'GET',self.path,body,headers)
            result=conn.getresponse();content=result.read()
            self.send_response(result.status)
            for key,value in result.getheaders():
                if key.lower() in ('connection','server','date'): continue
                self.send_header(key,value+'; Secure' if key.lower()=='set-cookie' else value)
            self.end_headers();self.wfile.write(content);conn.close()
        except (OSError,ValueError):
            self.send_error(503)

class SecureServer(ThreadingHTTPServer):
    limiter=threading.BoundedSemaphore(16)
    def process_request(self,request,address):
        if not self.limiter.acquire(blocking=False): request.close();return
        try: super().process_request(request,address)
        except BaseException: self.limiter.release();raise
    def process_request_thread(self,request,address):
        try: super().process_request_thread(request,address)
        finally: self.limiter.release()
proxy=SecureServer(('192.168.1.29',18766),Proxy)
context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.minimum_version=ssl.TLSVersion.TLSv1_2
context.load_cert_chain(root/'tls/cert.pem',root/'tls/key.pem')
proxy.ssl_context=context

def publish_link():
    while not app.closed:
        # Private local file only. Existing browser sessions remain valid for 8h.
        link=origin+'/models#launch='+app.ticket('board',platform_admin=True)
        path=root/'access.json'
        fd=os.open(path,os.O_CREAT|os.O_TRUNC|os.O_WRONLY,0o600)
        with os.fdopen(fd,'w') as file: json.dump({'url':link},file)
        threading.Event().wait(300)
threading.Thread(target=publish_link,daemon=True).start()
proxy.serve_forever()
