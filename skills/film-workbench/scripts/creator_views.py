"""Eight-column adapter around the upstream creator dashboard parsers.

The bundled MIT parser is deliberately isolated under ``upstream``: the local
dashboard keeps its eight-column source fields while sharing the mature
screenplay, settings, prompt, cut-list and review readers.
"""
import importlib.util
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


def read_episode(episode_id, documents, review=None):
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
    return _views.read_episode(episode_id, normalized, review)


def map_shot(row):
    """Map a native eight-column row to the dashboard shot model without losing fields."""
    fields = dict(row.get('fields') or {})
    shot_id = str(row.get('id', fields.get('編號', '')))
    import re
    duration = re.search(r'\d+(?:\.\d+)?', str(fields.get('時長', '')))
    seconds = float(duration.group()) if duration else 0.0
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
        'framing': fields.get('畫面描述', ''), 'scale': '', 'close': False,
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
