"""Readers for native Markdown emitted by the film skills."""
import re
import json

SCENE_RE = re.compile(r'^(?:#{2,4}\s*)?(\d+-\d+)\s+(.+?)\s*(?:[／/]\s*|\s+)(\d{3,4}年(?:前後|初|末)?|凌晨|清晨|早晨|上午|中午|下午|傍晚|黃昏|深夜|白天|夜間|日|夜)\s*(?:[／/]\s*|\s+)(內外|內|外)(?:\s*[｜|].*)?$')

def parse_script(text):
    scenes=[]; current=None; in_scene=False; title=''
    for line in (text or '').splitlines():
        s=line.strip()
        m=SCENE_RE.match(s)
        if not m:
            year_scene=re.match(r'^(?:#{2,4}\s*)?(\d+-\d+)\s+(.+?)\s*[／/]\s*(\d{3,4}年[^／/]*?)\s*[／/]\s*(內外|內|外)(?:\s*[｜|].*)?$',s)
            if year_scene:
                current={'id':year_scene.group(1),'space':year_scene.group(4),'place':year_scene.group(2).strip(),'time':year_scene.group(3).strip(),'blocks':[]}
                scenes.append(current); in_scene=True; continue
        if not m:
            loose=re.match(r'^#{2,4}\s+(\d+-\d+)\s+(.+)$',s)
            if loose and re.search(r'\d{2}:\d{2}(?:\.\d+)?\s*[–—-]\s*\d{2}:\d{2}',loose.group(2)):
                tail=re.split(r'\s*U?\d{2}:\d{2}(?:\.\d+)?\s*[–—-]\s*\d{2}:\d{2}',loose.group(2),maxsplit=1)[0].strip()
                space_match=re.search(r'(內外|內景|外景|內|外)',tail)
                time_match=re.search(r'(\d{3,4}年|凌晨|清晨|早晨|上午|中午|下午|傍晚|黃昏|深夜|日|夜)',tail)
                current={'id':loose.group(1),'space':space_match.group(1) if space_match else '', 'place':tail,'time':time_match.group(1) if time_match else '', 'blocks':[]}
                scenes.append(current); in_scene=True; continue
        if m:
            in_scene=True
            current={'id':m.group(1),'space':m.group(4),'place':m.group(2).strip().rstrip('／/ '),'time':m.group(3),'blocks':[]}
            scenes.append(current); continue
        if s.startswith('##') and in_scene: in_scene=False; current=None
        if s.startswith('# ') and not in_scene and not title: title=s[2:].strip()
        if not in_scene or current is None or not s: continue
        if s.startswith('△'):
            current['blocks'].append({'k':'action','text':s.lstrip('△').strip()}); continue
        d=re.match(r'([^（(：:]+)(?:[（(]([^）)]+)[）)])?[：:](.*)',s)
        if d:
            who=d.group(1).strip(); paren=(d.group(2) or '').strip()
            cue=who+' '+paren
            tag='VO' if re.search(r'\bVO\b|旁白|畫外音|画外音',cue,re.I) else ('OS' if re.search(r'\bOS\b|畫外|画外',cue,re.I) else '')
            if who in ('人物','登場人物','CAST'): continue
            who=re.sub(r'\s+(?:VO|OS)$','',who).strip()
            current['blocks'].append({'k':'line','tag':tag,'who':who,'paren':paren,'text':d.group(3).strip()})
        else: current['blocks'].append({'k':'action','text':s})
    if not scenes: raise ValueError('未找到符合格式的場次標題')
    return {'title':title,'scenes':scenes}

def parse_assets(text):
    items=[]; cat=''; parent=None; current=None; prompt=False; form=''; era={'period':'','facets':[]}
    for line in (text or '').splitlines():
        h=re.match(r'^(#{2,4})\s*(.+)',line.strip())
        if h:
            n=len(h.group(1)); title=h.group(2).strip()
            if n==2 and title.endswith('資產'):
                cat={'角色':'人物','場景':'地點','场景':'地點','道具':'道具'}.get(title[:-2],title[:-2]); parent=None; current=None
            elif n in (3,4) and title.startswith('@'):
                name=re.sub(r'\s*[-—–]{2,}\s*$','',title[1:].strip()); current={'cat':cat,'name':name,'fields':{},'desc':[],'locks':[],'lock':None,'designators':[],'overlay':False,'source':{'heading':line.strip()}}; prompt=False
                if n==4 and parent:
                    current['parent']=parent
                    if cat=='人物': current['cat']='造型'
                items.append(current)
                if n==3: parent=name
            else: current=None
            continue
        if current is None:
            if ':' in line or '：' in line:
                k,sep,v=line.partition('：')
                if not sep:k,sep,v=line.partition(':')
                if k.strip() in ('製作形態','制作形态'): form=v.strip()
                if k.strip()=='時代背景':
                    parts=[p.strip() for p in re.split(r'[；;]',v) if p.strip()]
                    if parts:
                        era['period']=parts[0]
                        for part in parts[1:]:
                            key,sep,val=part.partition('：')
                            if not sep:key,sep,val=part.partition(':')
                            if sep:era['facets'].append({'k':key.strip(),'v':val.strip().rstrip('。')})
            continue
        s=line.strip()
        if s.startswith('```'):
            prompt=not prompt
            continue
        if prompt:
            current['fields']['文生圖提示詞']=current['fields'].get('文生圖提示詞','') + ('\n' if current['fields'].get('文生圖提示詞') else '') + line.rstrip()
            continue
        if not s: continue
        if s.startswith('文生圖提示詞'):
            current['fields']['文生圖提示詞']=s.partition('：')[2].strip()
        elif s.startswith('類型：'): current['fields']['類型']=s.partition('：')[2].strip()
        else:
            current['desc'].append(s)
            if ':' in s:
                k,v=s.split(':',1); current['fields'][k.strip()]=v.strip()
    if not items: raise ValueError('未找到原生資產項目')
    return {'form':form,'era':era,'items':items}

def try_parse_text_prompts(docs, image=False):
    out=[]; recognized=False; valid=True
    for doc in docs or []:
        text=doc.get('content') or ''; path=doc.get('path','')
        heads=list(re.finditer(r'(?m)^##\s+(.+?)\s*$',text))
        for i,h in enumerate(heads):
            body=text[h.end():heads[i+1].start() if i+1<len(heads) else len(text)]
            title=h.group(1).strip()
            if image:
                if not re.match(r'(?:單幀\s+)?S\d+[A-Z]?(?:_[\w-]+)?$|圖像\s+[ESBCP]\d+(?:_[\w-]+)?',title): continue
            elif not re.match(r'S\d+[A-Z]?(?:\s*.*)?$|G\d+(?:\s*.*)?$',title): continue
            recognized=True
            # Keep one complete fenced body (including JSON), never split on internal headings.
            fence_matches=list(re.finditer(r'```([^\n]*)\n(.*?)```',body,re.S))
            fences=[m.group(2).strip() for m in fence_matches]
            raw=(fences[0] if fences else body.strip())
            if not fence_matches:
                if re.search(r"無需生成|不需生成|无需生成|後製|后製|後期|后期", title) and not re.search(r"integrated_multimodal_description\s*:", body):
                    continue
                substantive=[]
                for row in body.splitlines():
                    clean=re.sub(r'^\s*(?:[-*+]\s+)?','',row).strip()
                    if not clean: continue
                    if re.match(r'^(?:備註|時長|模式|生成模式|生成方式|鏡號|分鏡|素材|群組|輸入資產|分組依據|狀態|後製|剪輯備註|title|duration|mode|shots|shot_ids)\s*[：:]',clean,re.I): continue
                    substantive.append(row)
                raw='\n'.join(substantive).strip()
                # A heading plus production metadata is not a copyable request.
                if not raw: continue
            if not raw:
                valid=False
                continue
            request_id=re.match(r'^(?:單幀\s+)?(S\d+[A-Z]?)',title) if image else re.match(r'^(S\d+[A-Z]?)',title)
            ids=[request_id.group(1)] if request_id else []
            if title.startswith('G') and re.search(r'[|｜·、]',title):
                ids.extend(re.findall(r'(?<![A-Za-z0-9])S\d+[A-Z]?(?![A-Za-z0-9_])',re.split(r'[|｜·、]',title,1)[1]))
            # Explicit metadata and structured JSON fields identify group membership; prose in a prompt does not.
            meta=re.search(r'(?im)^\s*(?:鏡號|shots?|shot_ids)\s*[：:]\s*([^\n]+)',body)
            if meta: ids.extend(re.findall(r'(?<![A-Za-z0-9])S\d+[A-Z]?(?![A-Za-z0-9_])',meta.group(1)))
            for fence_match in fence_matches:
                if fence_match.group(1).strip().lower()=='json':
                    try:
                        data=json.loads(fence_match.group(2)); members=data.get('shot_ids',data.get('shots',[])) if isinstance(data,dict) else []
                        if isinstance(members,list): ids.extend(str(x) for x in members if re.fullmatch(r'S\d+[A-Z]?',str(x)))
                    except (ValueError,TypeError): pass
            ids=list(dict.fromkeys(ids))
            sec_match=re.search(r'(?im)^(?:時長|duration)\s*[：:]\s*(\d+(?:\.\d+)?)\s*(?:秒|s)?\s*$',body) or re.search(r'(\d+(?:\.\d+)?)\s*秒',title)
            mode_match=re.search(r'(?im)^(?:模式|生成方式|生成模式|mode)\s*[：:]\s*(.+)$',body) or re.search(r'\b(T2VA|I2VA|FL2VA|L2VA|Ref2VA)\b',title)
            n=int(re.search(r'\d+',ids[0]).group()) if ids else 0
            mode=mode_match.group(1).strip() if mode_match else ''
            if mode_match and mode_match.lastindex is None: mode=mode_match.group(1)
            records=[(raw,'')]
            if image and len(fence_matches)>1:
                records=[]
                for index,match in enumerate(fence_matches,1):
                    preceding=body[:match.start()]
                    subheads=list(re.finditer(r'(?m)^#{3,6}\s+(.+?)\s*$',preceding))
                    subhead=subheads[-1].group(1).strip() if subheads else f'提示詞 {index}'
                    records.append((match.group(2).strip(),subhead))
            for prompt_text,subhead in records:
                label=f'{title} · {subhead}' if subhead else title
                prompt_id=f'{title}::{subhead}' if subhead else title
                out.append({'id':prompt_id,'n':n,'title':label,'shot':ids[0] if ids else '', 'shot_ids':ids,'sec':float(sec_match.group(1)) if sec_match else 0.0,'mode':mode,'chain':'','prompt':prompt_text,'text':prompt_text,'source':{'path':path,'heading':label}})
    return out,recognized and valid

def parse_text_prompts(docs, image=False):
    return try_parse_text_prompts(docs,image)[0]

def parse_asset_prompts(settings):
    out=[]
    for item in (settings or {}).get('items',[]):
        prompt=item.get('fields',{}).get('文生圖提示詞','').strip()
        if not prompt: continue
        key=item.get('name','')
        out.append({'id':key,'title':key,'use':item.get('cat',''),'ref':'','prompt':prompt,'source':item.get('source',{})})
    return out
