import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from dashboard_server import serve

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent); self.root=Path(self.tmp.name)
        (self.root/'notes.md').write_text('hello',encoding='utf-8'); (self.root/'pic.png').write_bytes(b'0123456789')
        (self.root/'long.mp4').write_bytes(bytes(range(256))*600)
        (self.root/'qc.json').write_text('{"reviews":[]}',encoding='utf-8')
        self.server,self.token=serve(self.root); self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.base='http://127.0.0.1:'+str(self.server.server_port)
    def tearDown(self): self.server.shutdown(); self.server.server_close(); self.tmp.cleanup()
    def req(self,method,path,body=None,headers=None):
        data=json.dumps(body).encode() if body is not None else None
        req=urllib.request.Request(self.base+path,data=data,method=method,headers=headers or {})
        return urllib.request.urlopen(req)
    def test_static_root_is_served_when_frontend_exists(self):
        assets=Path(__file__).resolve().parents[1]/'assets'/'dashboard'
        for filename in ('index.html','tokens.css','styles.css','app.js'):
            if not (assets/filename).exists(): self.skipTest('前端尚未交付')
            response=urllib.request.urlopen(self.base+'/'+filename if filename!='index.html' else self.base+'/')
            self.assertEqual(response.status,200)
            self.assertTrue(response.read())
            if filename == 'index.html':
                policy=response.headers['Content-Security-Policy']
                self.assertIn("default-src 'self'",policy)
                self.assertIn("img-src 'self' data:",policy)
                self.assertIn("object-src 'none'",policy)
                self.assertNotIn("script-src *",policy)
    def test_auth_file_edit_and_conflict(self):
        h={'X-Film-Token':self.token}
        with self.assertRaises(urllib.error.HTTPError) as e: self.req('GET','/api/project')
        self.assertEqual(e.exception.code,403)
        doc=json.load(self.req('GET','/api/file?path=notes.md',headers=h))
        qc=json.load(self.req('GET','/api/file?path=qc.json',headers=h))
        self.assertFalse(qc['editable'])
        with self.assertRaises(urllib.error.HTTPError) as e: self.req('GET','/api/project',headers={'X-Film-Token':self.token,'Origin':'https://evil.example'})
        self.assertEqual(e.exception.code,403)
        updated=json.load(self.req('PUT','/api/file',{'path':'notes.md','content':'changed','expected_version':doc['version']},h))
        self.assertTrue(updated['version'])
        with self.assertRaises(urllib.error.HTTPError) as e: self.req('PUT','/api/file',{'path':'notes.md','content':'x','expected_version':doc['version']},h)
        self.assertEqual(e.exception.code,409)
        for body in ({'path':'notes.md','expected_version':doc['version']},
                     {'path':'notes.md','content':None,'expected_version':doc['version']},
                     {'path':'notes.md','content':'x','expected_version':1}):
            with self.assertRaises(urllib.error.HTTPError) as e: self.req('PUT','/api/file',body,h)
            self.assertEqual(e.exception.code,400)
        huge={'path':'notes.md','content':'x'*(8*1024*1024),'expected_version':doc['version']}
        with self.assertRaises(urllib.error.HTTPError) as e: self.req('PUT','/api/file',huge,h)
        self.assertEqual(e.exception.code,413)
        self.assertEqual(e.exception.headers.get('Connection'),'close')
    def test_session_cookie_range_and_path_traversal(self):
        opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        opener.open(urllib.request.Request(self.base+'/api/session',method='POST',headers={'X-Film-Token':self.token})).read()
        r=opener.open(urllib.request.Request(self.base+'/api/media?path=pic.png',headers={'Range':'bytes=2-5'}))
        self.assertEqual(r.status,206); self.assertEqual(r.read(),b'2345'); self.assertEqual(r.headers['Content-Range'],'bytes 2-5/10')
        full=opener.open(self.base+'/api/media?path=long.mp4')
        self.assertEqual(int(full.headers['Content-Length']),256*600)
        self.assertEqual(len(full.read()),256*600)
        with self.assertRaises(urllib.error.HTTPError) as e: opener.open(self.base+'/api/media?path=..%2Fsecrets')
        self.assertEqual(e.exception.code,400)

    def test_two_projects_keep_media_sessions_in_one_cookie_jar(self):
        other_tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        other_root=Path(other_tmp.name)
        (other_root/'pic.png').write_bytes(b'project-b')
        server_b,token_b=serve(other_root)
        thread_b=threading.Thread(target=server_b.serve_forever,daemon=True)
        thread_b.start()
        base_b='http://127.0.0.1:'+str(server_b.server_port)
        opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        try:
            opener.open(urllib.request.Request(self.base+'/api/session',method='POST',headers={'X-Film-Token':self.token})).read()
            self.assertEqual(opener.open(self.base+'/api/media?path=pic.png').read(),b'0123456789')
            opener.open(urllib.request.Request(base_b+'/api/session',method='POST',headers={'X-Film-Token':token_b})).read()
            self.assertEqual(opener.open(base_b+'/api/media?path=pic.png').read(),b'project-b')
            self.assertEqual(opener.open(self.base+'/api/media?path=pic.png').read(),b'0123456789')
        finally:
            server_b.shutdown(); server_b.server_close(); other_tmp.cleanup()

if __name__=='__main__': unittest.main()
