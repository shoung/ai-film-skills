"""Loopback-only local dashboard HTTP API."""
import argparse
import hashlib
import http.cookies
import http.client
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from . import project_reader
    from . import creator_views
    from . import project_documents
    from . import storyboard_editor
except ImportError:
    import project_reader
    import creator_views
    import project_documents
    import storyboard_editor

RUNTIME = Path(os.environ.get('LOCALAPPDATA') or tempfile.gettempdir()) / 'film-workbench'
STATIC_ROOT = Path(__file__).resolve().parents[1] / 'assets' / 'dashboard'
CSP = "default-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'"


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, root, token):
        self.root = Path(root).resolve()
        self.token = token
        self.projects = self._discover_projects()
        super().__init__(addr, Handler)

    def _discover_projects(self):
        def metadata(path):
            for name in ('short-drama.json','project.json'):
                try:
                    value=json.loads((path/name).read_text(encoding='utf-8-sig'))
                    if isinstance(value,dict): return value
                except (OSError,ValueError,UnicodeError): pass
            return None
        own=metadata(self.root)
        found={}
        def ident(path, _data):
            # Filesystem identity keeps copied projects with duplicated metadata IDs distinct.
            return hashlib.sha256(str(path).encode('utf-8')).hexdigest()[:20]
        if own is not None:
            found[ident(self.root,own)]=self.root
            return found
        try: children=list(self.root.iterdir())
        except OSError: children=[]
        for child in children:
            if child.is_symlink() or not child.is_dir() or metadata(child) is None: continue
            found[ident(child.resolve(),metadata(child))]=child.resolve()
        if not found:
            found[ident(self.root,{})]=self.root
        return found


class Handler(BaseHTTPRequestHandler):
    server_version = 'FilmWorkbench/1.0'

    def log_message(self, *_args):
        pass

    def _json(self, status, obj, headers=None):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', CSP)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def _err(self, status, message):
        self._json(status, {'error': message})

    def _safe_host(self):
        try:
            parts = urllib.parse.urlsplit('//' + self.headers.get('Host', ''))
            host = parts.hostname
            port = parts.port
        except ValueError:
            return False
        return host in ('127.0.0.1', 'localhost', '::1') and port == self.server.server_port

    def _origin_ok(self):
        origin = self.headers.get('Origin')
        return not origin or origin in (
            'http://127.0.0.1:' + str(self.server.server_port),
            'http://localhost:' + str(self.server.server_port),
        )

    def _authorized(self, cookie=False):
        if not self._safe_host() or not self._origin_ok():
            return False
        try:
            if secrets.compare_digest(self.headers.get('X-Film-Token', ''), self.server.token):
                return True
        except TypeError:
            return False
        if cookie:
            try:
                jar = http.cookies.SimpleCookie(self.headers.get('Cookie', ''))
                morsel = jar.get(self._cookie_name())
                return bool(morsel and secrets.compare_digest(morsel.value, self.server.token))
            except (http.cookies.CookieError, TypeError):
                return False
        return False

    def _cookie_name(self):
        return 'film_session_' + str(self.server.server_port)

    def _project_id(self, root=None):
        root=Path(root or self.server.root).resolve()
        return next((ident for ident,path in self.server.projects.items() if path==root),hashlib.sha256(str(root).encode('utf-8')).hexdigest()[:20])

    def _project_root(self, project_id=None):
        if not project_id:
            if len(self.server.projects)>1: raise ValueError('多專案工作區請指定 project')
            return next(iter(self.server.projects.values()),self.server.root)
        root=self.server.projects.get(str(project_id))
        if root is None: raise ValueError('找不到專案')
        return root

    def _project_title(self, root=None):
        root=Path(root or self.server.root)
        for candidate in ('short-drama.json','project.json','專案設定.json','项目设定.json'):
            try:
                data=json.loads((root/candidate).read_text(encoding='utf-8-sig'))
                if isinstance(data,dict) and isinstance(data.get('title'),str): return data['title']
            except (OSError,ValueError,UnicodeError): pass
        return root.name

    def _metadata(self, root=None):
        root=Path(root or self.server.root)
        for candidate in ('short-drama.json','project.json','專案設定.json','项目设定.json'):
            try:
                data=json.loads((root/candidate).read_text(encoding='utf-8-sig'))
                if isinstance(data,dict): return data
            except (OSError,ValueError,UnicodeError): pass
        return {}

    def _snapshot(self, root=None):
        return project_reader.project_snapshot(root or self.server.root)

    def _episode_ids(self, root=None):
        episodes=self._snapshot(root).get('episodes',[])
        return [str(ep['id']) for ep in episodes if str(ep['id'])!='project' or ep.get('shots') or ep.get('storyboard_sources')]

    def _episode(self, episode_id, root=None):
        root=Path(root or self.server.root)
        snap=self._snapshot(root)
        episode=next((ep for ep in snap.get('episodes',[]) if str(ep['id'])==episode_id),None)
        if episode is None: raise ValueError('找不到分集')
        selected_documents=project_documents.collect(root,episode)
        docs=selected_documents['texts']
        paths=selected_documents['paths']
        review_text=None
        review_entry=next((f for f in snap.get('files',[]) if
            (f.get('episode')==episode_id or re.search(r'(?<![A-Za-z0-9])'+re.escape(episode_id)+r'(?=[-_ .])',Path(f['path']).stem,re.I))
            and ('審查' in f['name'] or '审查' in f['name'] or f['name'].lower().endswith('review.md'))),None)
        if review_entry:
            review_text=project_reader.read_document(root,review_entry['path'])['content']
        result=creator_views.read_episode(episode_id,docs,review_text,
            native_shots=episode.get('shots') or None,
            video_documents=selected_documents['video_documents'] or None,
            image_documents=selected_documents['image_documents'] or None)
        mapped=(result.get('board') or {}).get('shots',[]) if episode.get('shots') else []
        if result.get('board'):
            image_by_id={p.get('id'):p for p in (result.get('imagePrompts') or [])}
            video_by_shot={p.get('shot'):p for p in (result.get('videoPrompts') or []) if p.get('shot')}
            for parsed in result['board'].get('shots',[]):
                if 'fields' in parsed: continue
                image_prompts=[image_by_id.get(img.get('id'),{}).get('prompt','') for img in parsed.get('imgs',[])]
                video=video_by_shot.get(parsed['id'],{})
                projection={'編號':parsed.get('id',''),
                    '畫面描述':'；'.join(v for v in (parsed.get('start',''),parsed.get('action',''),parsed.get('end','')) if v),
                    '攝影機描述':'；'.join(v for v in (parsed.get('framing',''),parsed.get('move','')) if v),
                    '聲音描述':parsed.get('sound',''),'旁白對白':'',
                    '時長':(str(parsed.get('sec'))+'s') if parsed.get('secDeclared') else '',
                    '影片生成方式':video.get('mode',''),'畫面prompt':'\n\n'.join(p for p in image_prompts if p)}
                parsed['fields']=projection
                parsed['field_projection']='只讀對照原版分鏡欄位；無法對應的旁白對白保持空白，原始分鏡資料仍完整保留。'
                parsed['source']=paths.get('分镜.md')
        supplements=[(row, item) for row in mapped for item in row.get('supplement',{}).get('prompts',[])]
        videos=result.get('videoPrompts') or []
        known={(p.get('id'),p.get('shot')) for p in videos}
        covered_shots={shot_id for prompt in videos for shot_id in ([prompt.get('shot')] + list(prompt.get('shot_ids') or [])) if shot_id}
        for row,item in supplements:
            if row['id'] in covered_shots: continue
            if item.get('kind','').lower() in ('video','video_prompt','h3','影片提示詞','视频提示词'):
                prompt={'id':item.get('id') or row['id'],'n':row['n'],'title':item.get('title') or row['id'],
                        'shot':row['id'],'sec':row['sec'],'mode':item.get('kind',''),'chain':'','prompt':item.get('text','')}
                if (prompt['id'],prompt['shot']) not in known and prompt['prompt']:
                    videos.append(prompt); known.add((prompt['id'],prompt['shot']))
        result['videoPrompts']=videos
        if not (result.get('settings') or {}).get('items'):
            cards=[]
            for entry in snap.get('files',[]):
                if entry.get('episode') not in (None,episode_id): continue
                path=Path(entry['path']); match=re.match(r'^([CEP])\d{2}[_-](.+)$',path.stem,re.I)
                if not match or entry.get('kind') not in ('media','grid'): continue
                letter=match.group(1).upper(); category={'C':'人物','E':'地點','P':'道具'}[letter]
                cards.append({'cat':category,'name':match.group(2).replace('_',' ').replace('-',' '),
                    'fields':{},'desc':[],'locks':[],'lock':None,'designators':[],
                    'image':entry['path'],'source':entry['path']})
            if cards:
                result['settings']={'form':'依既有 C／E／P 視覺資產索引顯示','era':{'period':'','facets':[]},'items':cards}
        for item in (result.get('settings') or {}).get('items',[]):
            name=str(item.get('parent') or item.get('name') or '').lstrip('@')
            expected={'人物':'C','造型':'C','地點':'E','地点':'E','道具':'P'}.get(item.get('cat'))
            matches=[]
            for file in episode.get('files',[]):
                path=Path(file['path'])
                if path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'): continue
                stem=re.sub(r'^[CEP]\d+[_-]','',path.stem,flags=re.I).lstrip('@')
                category_match=not expected or path.stem.upper().startswith(expected) or path.stem.startswith('@')
                if category_match and name and (stem==name or stem.startswith(name+'_') or stem.startswith(name+'各')):
                    matches.append(file['path'])
            if len(matches)==1:
                item['image']=matches[0]
                item['imageEvidence']='檔名對應素材候選，不代表實際生成提交紀錄'
        paths['review']=review_entry.get('path') if review_entry else None
        result['docs']=paths
        result['documentSources']={kind:[d['path'] for d in sources] for kind,sources in selected_documents['sources'].items()}
        result['sourceResolution']=episode.get('source_resolution') or {}
        result['hasReviewText']=review_text is not None
        result['qcPackages']=[{'path':package.get('path'),'name':package.get('name'),'kind':package.get('kind'),'episode':package.get('episode')}
            for package in episode.get('packages',[])]
        result['qcIssues']=list(episode.get('issues',[]))
        available={f['path'] for f in snap.get('files',[]) if f.get('kind') in ('media','grid')}
        frames={}
        for shot in (result.get('board') or {}).get('shots',[]):
            for ref in shot.get('refs',[]):
                path=ref.get('path') or ref.get('name')
                if path in available and ref.get('use')=='起始帧': frames[shot['id']]=path
        film=next((p for p in available if p.endswith(('成片.mp4','final.mp4'))),None)
        for row in mapped:
            for item in row.get('supplement',{}).get('media',[]):
                path=item.get('path')
                if path in available and item.get('role') in ('起始帧','起始幀','start_frame','first_frame','frame'):
                    frames.setdefault(row['id'],path)
        clips={}
        for cut in (result.get('cutlist') or {}).get('cuts',[]):
            media=cut.get('media')
            if not isinstance(media,str): continue
            storyboard_path=paths.get('分镜.md')
            base=Path(storyboard_path).parent if storyboard_path else Path(episode_id)
            candidates=(str(base/Path(media)).replace('\\','/'),media,str(Path(episode_id)/media).replace('\\','/'))
            path=next((candidate for candidate in candidates if candidate in available),None)
            if path: clips[cut['id']]=path
        linked_candidates={}
        for shot in (result.get('board') or {}).get('shots',[]):
            for candidate in shot.get('supplement',{}).get('media',[]):
                if candidate.get('kind')=='video' and candidate.get('path'):
                    linked_candidates.setdefault(candidate['path'],set()).add(shot['id'])
        candidate_paths=sorted({file['path'] for file in episode.get('files',[]) if Path(file['path']).suffix.lower() in ('.mp4','.mov','.webm')})
        candidates=[{'path':path,'shot_ids':sorted(linked_candidates.get(path,set())),
                     'kind':'video','role':'video_candidate'}
                    for path in candidate_paths]
        result['media']={'frames':frames,'clips':clips,'film':film,'candidates':candidates}
        result['cuts']=[]
        episode_issues=list(episode.get('issues',[]))
        if result.get('board') and not mapped:
            episode_issues=[issue for issue in episode_issues if '找不到八欄分鏡表' not in issue]
            result['adaptationNotes']=['來源分鏡採原版結構；畫面使用原始欄位只讀呈現，不轉換或改寫來源文件。']
        result['problems']=list(dict.fromkeys(episode_issues+result['problems']))
        return result

    def _series(self, root=None):
        root=Path(root or self.server.root)
        snap=self._snapshot(root); rows=[]; cast=[]; cast_names=set()
        wanted=set(self._episode_ids(root))
        for ep in snap.get('episodes',[]):
            if str(ep['id']) not in wanted: continue
            names={Path(f['path']).name for f in ep.get('files',[])}
            parsed=self._episode(str(ep['id']),root)
            settings=parsed.get('settings') or {}
            for item in settings.get('items',[]):
                if item.get('cat')!='人物' or item.get('name') in cast_names: continue
                cast_names.add(item['name'])
                cast.append({'name':item['name'],'ep':str(ep['id']),'desc':(item.get('desc') or [''])[0],
                    'shots':None if parsed.get('source_format',{}).get('視覺設定.md')=='native' else sum(1 for s in (parsed.get('board') or {}).get('shots',[]) if any(b.get('name')==item['name'] for b in s.get('basis',[])))})
            has_review=bool(parsed.get('hasReviewText'))
            rows.append({'id':str(ep['id']),'title':parsed.get('title') or str(ep.get('name',ep['id'])),'has':{
                'script':bool(parsed.get('script')) or any('劇本' in n or '剧本' in n for n in names),
                'settings':bool(parsed.get('settings')) or any('設定' in n or '设定' in n for n in names),'board':bool((parsed.get('board') or {}).get('shots')),
                'imgp':bool(parsed.get('imagePrompts')) or any('圖片提示詞' in n or '图片提示词' in n for n in names),
                'vidp':bool(parsed.get('videoPrompts')) or any('視頻提示詞' in n or '影片提示詞' in n or '视频提示词' in n for n in names),
                'cut':bool(parsed.get('cutlist')) or any('剪輯單' in n or '剪辑单' in n for n in names),'film':bool((parsed.get('media') or {}).get('film')),
                'review':has_review},
                'legacy':False,'shots':(parsed.get('metrics') or {}).get('shots',0),'seconds':(parsed.get('metrics') or {}).get('seconds',0),
                'cutSeconds':(parsed.get('cutlist') or {}).get('seconds'),'review':creator_views.review_counts(parsed.get('review')),
                'reviewTone':(parsed.get('review') or {}).get('verdictTone') if has_review else None,'reviewLabel':(parsed.get('review') or {}).get('verdict',''),
                'must':[{'id':f['id'],'title':f['title']} for f in (parsed.get('review') or {}).get('findings',[]) if f.get('sev')=='must'],
                'mediaCount':len((parsed.get('media') or {}).get('candidates',[])),
                'problems':len(set(parsed.get('problems',[])))})
        metadata=self._metadata(root)
        return {'title':self._project_title(root),'format':metadata.get('format') or {},'rhythm':metadata.get('rhythm_profile') or None,
                'lifecycle':metadata.get('lifecycle'),'episodes':rows,'cast':cast}

    def _media_info(self, relative, root=None):
        root=Path(root or self.server.root)
        try:
            target=project_reader._safe(root,relative)
            if target.suffix.lower()[1:] not in project_reader.MEDIA or not target.is_file(): return self._err(404,'找不到媒體')
            kind='video' if target.suffix.lower() in ('.mp4','.mov','.webm') else ('audio' if target.suffix.lower() in ('.mp3','.wav','.m4a') else 'image')
            return self._json(200,{'path':relative,'kind':kind,'contentType':_mime(target.suffix),'size':target.stat().st_size,'readOnly':True,'contentUrl':'/api/media/content?'+urllib.parse.urlencode({'project':self._project_id(root),'path':relative}),'status':'ready'})
        except (ValueError,OSError): return self._err(400,'媒體路徑無效')

    def do_POST(self):
        if not self._safe_host() or not self._origin_ok():
            return self._err(403, '拒絕非本機來源')
        if self.path == '/api/session':
            if not self._authorized():
                return self._err(403, '工作階段驗證失敗')
            cookie = self._cookie_name() + '=' + self.server.token + '; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200'
            return self._json(200, {'ok': True, 'apiBase': ''}, {'Set-Cookie': cookie})
        if self.path == '/api/shutdown':
            if not self._authorized():
                return self._err(403, '工作階段驗證失敗')
            self._json(200, {'ok': True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        return self._err(404, '找不到端點')

    def do_GET(self):
        if not self._safe_host() or not self._origin_ok():
            return self._err(403, '拒絕非本機來源')
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == '/' or parsed.path in ('/app.js', '/styles.css', '/tokens.css'):
            return self._static(parsed.path)
        if parsed.path.startswith('/api/') and not self._authorized(cookie=parsed.path in ('/api/media','/api/media/content')):
            return self._err(403, '工作階段驗證失敗')
        if parsed.path == '/api/health':
            return self._json(200, {'ok': True})
        if parsed.path == '/api/media':
            query=urllib.parse.parse_qs(parsed.query)
            try: root=self._project_root(query.get('project',[''])[0] or None)
            except ValueError as exc: return self._err(400,str(exc))
            if 'project' in query: return self._media_info(query.get('path',[''])[0],root)
            return self._media(urllib.parse.parse_qs(parsed.query).get('path', [''])[0],root)
        if parsed.path == '/api/media/content':
            query=urllib.parse.parse_qs(parsed.query)
            try: root=self._project_root(query.get('project',[''])[0] or None)
            except ValueError as exc: return self._err(400,str(exc))
            return self._media(query.get('path', [''])[0],root)
        try:
            query = urllib.parse.parse_qs(parsed.query)
            if parsed.path == '/api/projects':
                projects=[]
                for ident,root in self.server.projects.items():
                    rel=root.relative_to(self.server.root).as_posix() if root != self.server.root else '.'
                    projects.append({'id':ident,'path':rel,'title':self._project_title(root)})
                return self._json(200, {'projects':projects,'warnings':[]})
            selected=self._project_root(query.get('project',[''])[0] or None)
            if parsed.path == '/api/status':
                snap=project_reader.project_snapshot(selected); meta=self._metadata(selected)
                return self._json(200, {'project_id':self._project_id(selected),'title':self._project_title(selected),'ownership':meta.get('ownership',{}),'format':meta.get('format',{}),
                    'language':meta.get('language'),'prompt_language':meta.get('prompt_language'),'video_prompt_language':meta.get('video_prompt_language'),
                    'video_model_profile':meta.get('video_model_profile',{}),'rhythm_profile':meta.get('rhythm_profile',{}),
                    'rhythm_profile_problems':meta.get('rhythm_profile_problems',[]),'profile_notes':meta.get('profile_notes',[]),'project_root':'.',
                    'layout':meta.get('layout',{'mode':'adapted','pinned':False,'roots':{},'nonstandardRoots':[],'unsafeRoots':[]}),
                    'artifacts':meta.get('artifacts',meta.get('artifact_states',{})),
                    'authority':meta.get('authority',meta.get('creator_authority',{})),
                    'lifecycle':meta.get('lifecycle',{'artifact_state':meta.get('artifact_states',{})}),
                    'issues':snap.get('issues',[])})
            if parsed.path == '/api/tree':
                snap=project_reader.project_snapshot(selected)
                tree=[]
                for entry in snap['files']:
                    parts=Path(entry['path']).parts; cursor=tree; parent=''
                    for part in parts[:-1]:
                        parent=parent+'/'+part if parent else part
                        node=next((n for n in cursor if n.get('type')=='directory' and n['name']==part),None)
                        if node is None:
                            node={'type':'directory','name':part,'path':parent,'children':[]}; cursor.append(node)
                        cursor=node['children']
                    try: size=(selected/Path(entry['path'])).stat().st_size
                    except OSError: size=0
                    cursor.append({'type':'text' if entry.get('kind') in ('document','qc','package') else 'media',
                        'name':entry['name'],'path':entry['path'],'kind':entry.get('kind'),'episode':entry.get('episode'),
                        'size':size,'oversize':size>project_reader.MAX_FILE,'editable':entry.get('editable',False)})
                return self._json(200, {'tree':tree,'warnings':snap.get('issues',[])})
            if parsed.path == '/api/series':
                return self._json(200, self._series(selected))
            if parsed.path == '/api/episode':
                return self._json(200, self._episode(query.get('ep',[''])[0],selected))
            if parsed.path == '/api/search':
                ep=query.get('ep',[None])[0]; q=query.get('q',[''])[0]
                rows=[]
                for item in self._episode_ids(selected):
                    if ep is None or item==ep: rows.extend(creator_views.search_entries(self._episode(item,selected)))
                hits=[r for r in rows if q.casefold() in json.dumps(r,ensure_ascii=False).casefold()]
                return self._json(200, {'query':q,'scope':'ep' if ep else 'series','hits':hits,'results':hits})
            if parsed.path == '/api/project':
                snapshot = project_reader.project_snapshot(selected)
                if 'episodes' in query:
                    selected = set(query['episodes'])
                    snapshot['episodes'] = [ep for ep in snapshot['episodes'] if ep['id'] in selected]
                if 'columns' in query:
                    selected = set(query['columns'][0].split(','))
                    snapshot['columns'] = [col for col in snapshot['columns'] if col in selected]
                if 'files' in query:
                    selected = set(query['files'])
                    snapshot['files'] = [entry for entry in snapshot['files'] if entry['path'] in selected]
                return self._json(200, snapshot)
            if parsed.path == '/api/file':
                path = query.get('path', [''])[0]
                result=project_reader.read_document(selected, path)
                result['expectedVersion']=result.get('version')
                result['writable']=result['editable']
                return self._json(200,result)
            if parsed.path == '/api/storyboard-table':
                return self._json(200, storyboard_editor.document(selected, query.get('path', [''])[0]))
            return self._err(404, '找不到端點')
        except PermissionError as exc:
            return self._err(403, str(exc))
        except (ValueError, OSError, UnicodeError) as exc:
            return self._err(400, str(exc))

    def _static(self, url_path):
        relative = 'index.html' if url_path == '/' else url_path.lstrip('/')
        if any(part in ('..', '.') or part.startswith('.') for part in Path(relative).parts):
            return self._err(404, '找不到頁面資源')
        candidate = STATIC_ROOT / relative
        target = candidate.resolve(strict=False)
        if candidate.is_symlink() or STATIC_ROOT.resolve() not in target.parents or not target.is_file():
            return self._err(404, '找不到頁面資源')
        mime = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
                '.css': 'text/css; charset=utf-8'}.get(target.suffix.lower(), 'application/octet-stream')
        try:
            data = target.read_bytes()
        except OSError:
            return self._err(404, '找不到頁面資源')
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', CSP)
        self.end_headers()
        self.wfile.write(data)

    def do_PUT(self):
        if not self._authorized():
            return self._err(403, '工作階段驗證失敗')
        url = urllib.parse.urlsplit(self.path)
        if url.path not in {'/api/file', '/api/storyboard-table'}:
            return self._err(404, '找不到端點')
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 8 * 1024 * 1024:
                self.close_connection = True
                self._json(413, {'error': '文件大小不正確或超過上限'}, {'Connection': 'close'})
                # Drain oversized requests in bounded chunks so clients receive
                # the 413 response cleanly without buffering an untrusted body.
                if 0 < length <= 32 * 1024 * 1024:
                    self.connection.settimeout(3)
                    remaining = length
                    try:
                        while remaining:
                            chunk = self.rfile.read(min(64 * 1024, remaining))
                            if not chunk:
                                break
                            remaining -= len(chunk)
                    except OSError:
                        pass
                return
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            if not isinstance(body, dict):
                return self._err(400, 'JSON 內容必須是物件')
            expected=body.get('expected_version',body.get('expectedVersion'))
            query=urllib.parse.parse_qs(url.query)
            query_path=query.get('path',[None])[0]
            query_project=query.get('project',[None])[0]
            for key, value in (('path',query_path),('project',query_project)):
                if value is not None and key in body and body[key] != value:
                    return self._err(400, '保存目標與網址不一致')
            target_path=body.get('path',query_path)
            target_project=body.get('project',query_project)
            if url.path == '/api/storyboard-table':
                if not all(isinstance(value, str) for value in (target_path, expected)) or not isinstance(body.get('tables'), list):
                    return self._err(400, '缺少分鏡檔路徑、版本或表格')
                result = storyboard_editor.document(self._project_root(target_project), target_path,
                    draft=body['tables'], expected_version=expected)
                return self._json(200, result)
            if not all(isinstance(value, str) for value in (target_path,body.get('content'),expected)):
                return self._err(400, 'path、content、expectedVersion 必須都是字串')
            root=self._project_root(target_project)
            result = project_reader.read_document(root, target_path,
                                                  content=body.get('content'),
                                                  expected_version=expected)
            result['expectedVersion']=result.get('version')
            return self._json(200, result)
        except (json.JSONDecodeError, UnicodeError):
            return self._err(400, 'JSON 或文字編碼格式錯誤')
        except PermissionError as exc:
            return self._err(403, str(exc))
        except ValueError as exc:
            return self._err(409 if '已變更' in str(exc) else 400, str(exc))
        except (OSError, TypeError) as exc:
            return self._err(400, '無法保存文件：' + str(exc))

    def _media(self, relative, root=None):
        root=Path(root or self.server.root)
        try:
            target = project_reader._safe(root, relative)
            if target.suffix.lower()[1:] not in project_reader.MEDIA or not target.is_file():
                return self._err(404, '找不到媒體')
            size = target.stat().st_size
            start, end, status = 0, size - 1, 200
            requested = self.headers.get('Range')
            if requested:
                import re
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested.strip())
                if not match:
                    return self._range_error(size)
                first, last = match.groups()
                if not first and not last:
                    return self._range_error(size)
                if not first:
                    start = max(0, size - int(last))
                else:
                    start = int(first)
                if first and last:
                    end = int(last)
                end = min(end, size - 1)
                if start >= size or end < start:
                    return self._range_error(size)
                status = 206
            self.send_response(status)
            self.send_header('Content-Type', _mime(target.suffix))
            content_length = end - start + 1
            self.send_header('Content-Length', str(content_length))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if status == 206:
                self.send_header('Content-Range', 'bytes ' + str(start) + '-' + str(end) + '/' + str(size))
            self.end_headers()
            remaining = content_length
            with target.open('rb') as handle:
                handle.seek(start)
                while remaining:
                    chunk = handle.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            # Browsers cancel media transfers when changing shots; no second
            # HTTP response can be sent after the stream has been closed.
            return
        except (ValueError, OSError):
            return self._err(400, '媒體路徑無效')

    def _range_error(self, size):
        self.send_response(416)
        self.send_header('Content-Range', 'bytes */' + str(size))
        self.send_header('Content-Length', '0')
        self.end_headers()


def _mime(ext):
    return {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
            '.webp': 'image/webp', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.m4a': 'audio/mp4',
            '.mp4': 'video/mp4', '.mov': 'video/quicktime', '.webm': 'video/webm'}.get(ext.lower(), 'application/octet-stream')


def serve(root, port=0, token=None):
    token = token or secrets.token_urlsafe(32)
    return Server(('127.0.0.1', port), root, token), token


def _state_path(root):
    digest = hashlib.sha256(str(Path(root).resolve()).encode('utf-8')).hexdigest()
    return RUNTIME / (digest + '.json')


def _write_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, path)


def _health(info):
    try:
        parts = urllib.parse.urlsplit(info['url'])
        if parts.scheme != 'http' or parts.hostname not in ('127.0.0.1', 'localhost', '::1') or not parts.port:
            return False
        url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, '/api/health', '', ''))
        request = urllib.request.Request(url, headers={'X-Film-Token': info['token']})
        with urllib.request.urlopen(request, timeout=0.6) as response:
            return response.status == 200
    except (OSError, KeyError, ValueError):
        return False


def _read_state(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _stop(info):
    if not _health(info):
        return False
    url = info['url'].split('#', 1)[0] + '/api/shutdown'
    request = urllib.request.Request(url, data=b'{}', method='POST', headers={
        'Content-Type': 'application/json', 'X-Film-Token': info['token']})
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            if response.status != 200:
                return False
    except OSError:
        return False
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not _health(info):
            return True
        time.sleep(0.1)
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description='本機八欄創作台後端')
    parser.add_argument('project', nargs='?')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--detach', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--stop', action='store_true')
    args = parser.parse_args(argv)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if args.status:
        if args.project:
            root = Path(args.project).resolve(strict=True)
            path = _state_path(root)
            info = _read_state(path)
            running = bool(info and info.get('project') == str(root) and _health(info))
            print(json.dumps({'running': running, 'url': info.get('url') if running else None}, ensure_ascii=False))
        else:
            states = []
            for path in RUNTIME.glob('*.json'):
                info = _read_state(path)
                if info and _health(info):
                    states.append({'project': info['project'], 'url': info['url']})
            print(json.dumps({'running': bool(states), 'servers': states}, ensure_ascii=False))
        return 0
    if args.stop:
        if not args.project:
            parser.error('--stop 需要指定專案路徑')
        root = Path(args.project).resolve(strict=True)
        state_path = _state_path(root)
        info = _read_state(state_path)
        if not info or info.get('project') != str(root) or not _stop(info):
            print('沒有可停止的本專案服務')
            return 1
        deadline = time.monotonic() + 3
        while state_path.exists() and time.monotonic() < deadline:
            try:
                state_path.unlink()
            except PermissionError:
                time.sleep(0.1)
        if state_path.exists():
            print('服務已停止，但系統狀態檔暫時無法刪除')
            return 1
        print('已停止')
        return 0
    if not args.project:
        parser.error('需要指定專案根目錄')
    root = Path(args.project).resolve(strict=True)
    if not root.is_dir():
        parser.error('專案路徑必須是目錄')
    existing = _read_state(_state_path(root))
    if existing and existing.get('project') == str(root) and _health(existing):
        print('創作台網址：' + existing['url'])
        if args.open:
            import webbrowser
            webbrowser.open(existing['url'])
        return 0
    if args.detach:
        state_path = _state_path(root)
        previous = _read_state(state_path)
        if previous and previous.get('project') == str(root) and _health(previous):
            print('創作台網址：' + previous['url'])
            if args.open:
                import webbrowser
                webbrowser.open(previous['url'])
            return 0
        state_path.unlink(missing_ok=True)
        lock_path = state_path.with_suffix('.lock')
        try:
            lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(lock_fd)
        except FileExistsError:
            print('本專案背景服務正在啟動，請稍後查詢 --status')
            return 1
        command = [sys.executable, str(Path(__file__).resolve()), str(root), '--port', str(args.port)]
        log_path = RUNTIME / 'server.log'
        try:
            flags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0) | getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            with log_path.open('ab') as log:
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                           stderr=subprocess.STDOUT, creationflags=flags)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                info = _read_state(state_path)
                if info and info.get('pid') == process.pid and _health(info):
                    print('創作台網址：' + info['url'])
                    if args.open:
                        import webbrowser
                        webbrowser.open(info['url'])
                    return 0
                if process.poll() is not None:
                    break
                time.sleep(0.1)
            print('背景服務未能就緒，請查閱系統暫存目錄中的 server.log')
            return 1
        finally:
            lock_path.unlink(missing_ok=True)
    server, token = serve(root, args.port)
    url = 'http://127.0.0.1:' + str(server.server_port) + '/#token=' + token
    state_path = _state_path(root)
    _write_state(state_path, {'pid': os.getpid(), 'project': str(root), 'url': url, 'token': token})
    print('創作台網址：' + url, flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        current = _read_state(state_path)
        if current and current.get('pid') == os.getpid():
            state_path.unlink(missing_ok=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
