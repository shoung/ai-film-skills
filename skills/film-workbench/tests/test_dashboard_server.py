import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
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

    def test_upstream_editor_query_contract_and_conflicting_targets(self):
        h={'X-Film-Token':self.token}
        project=json.load(self.req('GET','/api/projects',headers=h))['projects'][0]
        url='/api/file?'+urllib.parse.urlencode({'project':project['id'],'path':'notes.md'})
        doc=json.load(self.req('GET',url,headers=h))
        self.assertTrue(doc['writable'])
        updated=json.load(self.req('PUT',url,{'content':'query saved','expectedVersion':doc['version']},h))
        self.assertEqual((self.root/'notes.md').read_text(encoding='utf-8'),'query saved')
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.req('PUT',url,{'path':'other.md','content':'bad','expectedVersion':updated['version']},h)
        self.assertEqual(error.exception.code,400)

    def test_storyboard_table_save_preserves_source_boundaries_and_rejects_stale_draft(self):
        headers = {'X-Film-Token': self.token}
        header = '|編號|修改|畫面描述|攝影機描述|聲音描述|旁白對白|時長|影片生成方式|畫面prompt|\r\n'
        separator = '|---|---|---|---|---|---|---|---|---|\r\n'
        prefix = '# 分鏡及說明\r\n\r\n```markdown\r\n' + header + separator + '|假鏡號|例子||||||||\r\n```\r\n\r\n'
        subtotal = '|小計||||||7秒|||\r\n'
        suffix = '\r\n## 說明\r\n表外文字和 | 符號。'
        source = prefix + header + separator + '|**S01**|舊版附註|清晨||||3秒|||\r\n|S02||傍晚||||4秒|||\r\n' + subtotal + suffix
        actual = self.root / 'board.md'
        actual.write_bytes(source.encode('utf-8-sig'))
        alternative = self.root / 'alternate.md'
        alternative.write_bytes(actual.read_bytes())
        url = '/api/storyboard-table?path=board.md'
        doc = json.load(self.req('GET', url, headers=headers))
        self.assertEqual(len(doc['tables']), 1)
        group = doc['tables'][0]['groups'][0]
        first, second = group['rows']
        first['cells'][1] = '第一行\n第二行 | 分隔符\\|'
        new = {'key': None, 'cells': ['S03', '夜景', '', '', '', '', '', '']}
        # Rearrange old rows, add one, and preserve the summary and the example.
        changes = {'expectedVersion': doc['version'], 'tables': [[[second, first, new]]]}
        saved = json.load(self.req('PUT', url, changes, headers))
        self.assertEqual([row['cells'][0] for row in saved['tables'][0]['groups'][0]['rows']], ['S02', 'S01', 'S03'])
        self.assertEqual(saved['tables'][0]['groups'][0]['rows'][1]['cells'][1], first['cells'][1])
        updated = actual.read_bytes()
        self.assertTrue(updated.startswith((prefix + header + separator).encode('utf-8-sig')))
        self.assertTrue(updated.endswith((subtotal + suffix).encode('utf-8')))
        self.assertIn('| **S01** | 舊版附註 |'.encode('utf-8'), updated)
        self.assertEqual(alternative.read_bytes(), source.encode('utf-8-sig'))
        actual.write_bytes(updated + b'\r\nexternal edit')
        delete = {'expectedVersion': saved['version'], 'tables': [[[]]]}
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.req('PUT', url, delete, headers)
        self.assertEqual(error.exception.code, 409)
        self.assertEqual(actual.read_bytes(), updated + b'\r\nexternal edit')
        latest = json.load(self.req('GET', url, headers=headers))
        delete['expectedVersion'] = latest['version']
        self.req('PUT', url, delete, headers).close()
        self.assertEqual(actual.read_bytes(), (prefix + header + separator + subtotal + suffix).encode('utf-8-sig') + b'\r\nexternal edit')

    def test_original_facade_projects_episode_tree_search_and_version_alias(self):
        ep=self.root/'EP001'; ep.mkdir()
        (ep/'board.md').write_text('|編號|畫面描述|攝影機描述|聲音描述|旁白對白|時長|影片生成方式|畫面prompt|\n|---|---|---|---|---|---|---|---|\n|S01|雨夜|慢推|雨聲|無|3秒|T2VA|street|',encoding='utf-8')
        h={'X-Film-Token':self.token}
        self.assertEqual(json.load(self.req('POST','/api/session',{},h))['apiBase'],'')
        project=json.load(self.req('GET','/api/projects',headers=h))['projects'][0]
        self.assertEqual(project['title'],self.root.name)
        self.assertTrue(json.load(self.req('GET','/api/tree?project='+project['id'],headers=h))['tree'])
        episode=json.load(self.req('GET','/api/episode?project='+project['id']+'&ep=EP001',headers=h))
        self.assertEqual(episode['board']['shots'][0]['fields']['畫面描述'],'雨夜')
        self.assertIsNone(episode['cutlist'])
        self.assertEqual(len(json.load(self.req('GET','/api/search?project='+project['id']+'&q=%E9%9B%A8',headers=h))['hits']),1)
        doc=json.load(self.req('GET','/api/file?project='+project['id']+'&path=notes.md',headers=h))
        updated=json.load(self.req('PUT','/api/file',{'project':project['id'],'path':'notes.md','content':'alias','expectedVersion':doc['version']},h))
        self.assertTrue(updated['version'])

    def test_workspace_projects_with_same_episode_id_are_scoped(self):
        roots=[]
        for name,description in (('project-a','甲資料'),('project-b','乙資料')):
            root=self.root/name; ep=root/'EP001'; ep.mkdir(parents=True)
            (root/'short-drama.json').write_text(json.dumps({'project_id':'duplicate-id','title':name}),encoding='utf-8')
            (ep/'board.md').write_text('|編號|畫面描述|攝影機描述|聲音描述|旁白對白|時長|影片生成方式|畫面prompt|\n|---|---|---|---|---|---|---|---|\n|S01|'+description+'|慢推|雨聲|無|3秒|T2VA|street|',encoding='utf-8')
            (root/'still.png').write_bytes(b'png')
            roots.append(name)
        server,token=serve(self.root); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        base='http://127.0.0.1:'+str(server.server_port); headers={'X-Film-Token':token}
        try:
            projects=json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/projects',headers=headers)))['projects']
            self.assertEqual(len(projects),2)
            self.assertEqual(len({p['id'] for p in projects}),2)
            ids={p['title']:p['id'] for p in projects}
            for name,description in (('project-a','甲資料'),('project-b','乙資料')):
                url=base+'/api/episode?'+urllib.parse.urlencode({'project':ids[name],'ep':'EP001'})
                episode=json.load(urllib.request.urlopen(urllib.request.Request(url,headers=headers)))
                self.assertEqual(episode['board']['shots'][0]['fields']['畫面描述'],description)
                info_url=base+'/api/media?'+urllib.parse.urlencode({'project':ids[name],'path':'still.png'})
                info=json.load(urllib.request.urlopen(urllib.request.Request(info_url,headers=headers)))
                self.assertIn('project='+ids[name],info['contentUrl'])
        finally:
            server.shutdown(); server.server_close()

    def test_public_upstream_fixture_api_keeps_structured_content(self):
        fixture=Path(__file__).resolve().parent/'fixtures'/'creator-first'
        server,token=serve(fixture); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        base='http://127.0.0.1:'+str(server.server_port); headers={'X-Film-Token':token}
        try:
            project=json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/projects',headers=headers)))['projects'][0]
            episode=json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/episode?'+urllib.parse.urlencode({'project':project['id'],'ep':'EP001'}),headers=headers)))
            self.assertEqual((len(episode['script']['scenes']),len(episode['settings']['items']),len(episode['board']['shots']),len(episode['imagePrompts']),len(episode['videoPrompts'])),(2,7,22,4,22))
            self.assertEqual(episode['metrics']['seconds'],62.0)
            if (fixture/'剧集'/'EP001'/'剪辑单.md').exists():
                self.assertGreater(len(episode['cutlist']['cuts']),0)
            else:
                self.assertIsNone(episode['cutlist'])
            series=json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/series?project='+project['id'],headers=headers)))
            self.assertEqual(series['title'],'公開範例比對')
            self.assertEqual(series['episodes'][0]['shots'],22)
        finally:
            server.shutdown(); server.server_close()

    def test_real_project_read_only_adapter_exposes_existing_assets(self):
        root=Path(__file__).resolve().parents[4]/'放手，讓你好走'
        if not root.exists(): self.skipTest('本機唯讀驗收專案未提供')
        server,token=serve(root); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        base='http://127.0.0.1:'+str(server.server_port); headers={'X-Film-Token':token}
        try:
            projects=json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/projects',headers=headers)))['projects']
            self.assertEqual(len(projects),1)
            project=projects[0]['id']
            series=json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/series?'+urllib.parse.urlencode({'project':project}),headers=headers)))
            self.assertEqual(len(series['episodes']),1)
            episode_id=series['episodes'][0]['id']
            episode=json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/episode?'+urllib.parse.urlencode({'project':project,'ep':episode_id}),headers=headers)))
            self.assertEqual(episode['metrics']['shots'],54)
            self.assertGreater(sum(bool(shot.get('supplement',{}).get('media')) for shot in episode['board']['shots']),0)
            self.assertGreater(len(episode['videoPrompts']),0)
            self.assertGreater(len(episode['settings']['items']),0)
            self.assertTrue(episode['docs']['分鏡.md'])
        finally:
            server.shutdown(); server.server_close()
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
