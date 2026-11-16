"""Eight-column adapter around the upstream creator dashboard parsers.

The bundled MIT parser is deliberately isolated under ``upstream``: the local
dashboard keeps its eight-column source fields while sharing the mature
screenplay, settings, prompt, cut-list and review readers.
"""
import importlib.util
import re
from pathlib import Path


_UPSTREAM = Path(__file__).resolve().parent / 'upstream'
_spec = importlib.util.spec_from_file_location('film_workbench_creator_views', _UPSTREAM / 'creator_views.py')
if _spec is None or _spec.loader is None:
    raise RuntimeError('無法載入創作台結構解析器')
_views = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_views)

for _name in dir(_views):
    if not _name.startswith('_'):
        globals()[_name] = getattr(_views, _name)


def read_episode(episode_id, documents, review=None, native_shots=None, video_documents=None, image_documents=None):
    """Parse creator documents with upstream schemas, accepting traditional aliases."""
    aliases = {
        '剧本.md': ('劇本.md', '剧本.md'),
        '视觉设定.md': ('視覺設定.md', '视觉设定.md', '設定.md', '设定.md'),
        '分镜.md': ('分鏡.md', '分镜.md'),
        '图片提示词.md': ('圖片提示詞.md', '图片提示词.md'),
        '视频提示词.md': ('視頻提示詞.md', '影片提示詞.md', '视频提示词.md'),
        '剪辑单.md': ('剪輯單.md', '剪辑单.md'),
    }
    normalized = dict(documents)
    for target, names in aliases.items():
        if normalized.get(target) is None:
            normalized[target] = next((documents[name] for name in names if documents.get(name) is not None), None)
    from native_views import parse_assets, parse_script, parse_text_prompts, try_parse_text_prompts, parse_asset_prompts
    native_script = None
    raw_script = normalized.get('剧本.md')
    if raw_script and re.search(r'(?m)^(?:#{2,4}\s*)?\d+-\d+\s+', raw_script):
        try: native_script = parse_script(raw_script)
        except (ValueError, TypeError): pass
    native_settings = None
    raw_settings = normalized.get('视觉设定.md')
    if raw_settings and re.search(r'(?m)^#{2}\s*(?:角色|場景|场景|道具)資產\s*$', raw_settings):
        try: native_settings = parse_assets(raw_settings)
        except (ValueError, TypeError): pass
    clean = dict(normalized)
    if native_script is not None: clean['剧本.md'] = None
    if native_settings is not None: clean['视觉设定.md'] = None
    native_video_prompts, native_video = try_parse_text_prompts(video_documents) if video_documents is not None else ([],False)
    native_image_prompts, native_image = try_parse_text_prompts(image_documents, image=True) if image_documents is not None else ([],False)
    if native_shots is not None and len(native_shots)>0: clean['分镜.md'] = None
    if native_video: clean['视频提示词.md'] = None
    if native_image: clean['图片提示词.md'] = None
    ep = _views.read_episode(episode_id, clean, review)
    if native_script is not None: ep['script'] = native_script
    if native_settings is not None: ep['settings'] = native_settings
    if native_settings is not None:
        ep['imagePrompts'] = parse_asset_prompts(native_settings) + (ep.get('imagePrompts') or [])
    if native_shots:
        shots = [map_shot(row) for row in native_shots]
        for shot, row in zip(shots, native_shots):
            match = re.search(r'(?:\[場次\s*[/／]\s*時間\]|【場次\s*[/／]\s*(?:時碼|時間)】)\s*(\d+-\d+)', str(shot['fields'].get('畫面描述','')))
            shot['scene'] = match.group(1) if match else ''
            dur = str(shot['fields'].get('時長','')).strip()
            dm = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(?:秒|s|sec)?',dur,re.I)
            shot['sec'] = float(dm.group(1)) if dm else 0.0
            shot['secDeclared'] = bool(dm)
        ep['board'] = {'shots':shots,'note':'','blocking':[]}
    if native_video:
        ep['videoPrompts'] = native_video_prompts
        ep['videoGroups'] = []
    if native_image:
        ep['imagePrompts'] = (ep.get('imagePrompts') or []) + native_image_prompts
    if ep.get('imagePrompts'):
        unique=[]; seen=set()
        for prompt in ep['imagePrompts']:
            key=(prompt.get('id',''),prompt.get('prompt',''))
            if key in seen: continue
            seen.add(key); unique.append(prompt)
        ep['imagePrompts']=unique
    ep['metrics'] = _views.metrics(ep['script'], ep['board'])
    ep['source_format'] = {'劇本.md':'native' if native_script is not None else 'upstream','視覺設定.md':'native' if native_settings is not None else 'upstream','分鏡.md':'native' if native_shots else 'upstream','視頻提示詞':'native' if native_video else 'upstream','圖片提示詞':'native' if native_image else 'upstream'}
    paths=[d.get('path') for d in (video_documents or [])+(image_documents or []) if d.get('path')]
    ep['source'] = {'path': paths[0] if paths else '', 'paths': paths or list(normalized.keys())}
    return ep


def map_shot(row):
    """Map a native eight-column row to the dashboard shot model without losing fields."""
    fields = dict(row.get('fields') or {})
    shot_id = str(row.get('id', fields.get('編號', '')))
    import re
    duration = re.search(r'\d+(?:\.\d+)?', str(fields.get('時長', '')))
    seconds = float(duration.group()) if duration else 0.0
    camera = str(fields.get('攝影機描述', ''))
    scale_map = {'大特寫':'大特写','大特写':'大特写','中近景':'中近景','遠景':'远景','远景':'远景','全景':'全景','中景':'中景','近景':'近景','特寫':'特写','特写':'特写','細節':'细节','细节':'细节'}
    scale_re = re.compile('|'.join(re.escape(k) for k in sorted(scale_map, key=len, reverse=True)))
    found = {scale_map[m.group(0)] for m in scale_re.finditer(camera)}
    scale = next(iter(found)) if len(found) == 1 else ''
    supplement = row.get('supplement') or {}
    media = [m for m in supplement.get('media', []) if not m.get('shot_ids') or shot_id in m.get('shot_ids', [])]
    prompts = [p for p in supplement.get('prompts', []) if not p.get('shot_ids') or shot_id in p.get('shot_ids', [])]
    # Supplemental filename/text matches are candidates, not proof that a
    # particular asset was actually fed to a generation call.
    refs = [m for m in supplement.get('media', []) if m.get('role') in ('REF', 'reference_slot') and m.get('evidence') == 'registered_binding']
    number = re.findall(r'\d+', shot_id)
    return {
        'id': shot_id, 'n': int(number[-1]) if number else 0, 'title': shot_id,
        'scene': '', 'sec': seconds, 'secDeclared': bool(duration), 'purpose': '',
        'framing': camera or fields.get('畫面描述', ''), 'scale': scale, 'close': scale in _views.CLOSE_SCALES,
        'move': fields.get('攝影機描述', ''), 'moveKind': fields.get('攝影機描述', ''),
        'start': fields.get('畫面描述', ''), 'action': fields.get('畫面描述', ''), 'end': '',
        'sound': fields.get('聲音描述', ''), 'screenText': fields.get('旁白對白', ''),
        'imgs': [{'id': p.get('id', ''), 'name': p.get('title', ''), 'ctl': p.get('kind', '')} for p in prompts],
        'refs': refs, 'refState': 'bound' if refs else ('pending' if media else 'none'),
        'refLabel': '已登錄參考' if refs else ('素材候選，待確認' if media else '未提供'),
        'basis': [], 'keyframe': '', 'closing_keyframe': '', 'fields': fields,
        'source': row.get('source', ''), 'row_index': row.get('row_index'), 'supplement': supplement,
        'assets': list(row.get('assets') or []), 'generations': list(row.get('generations') or []),
        'reviews': list(row.get('reviews') or []), 'issues': list(row.get('issues') or []),
    }
