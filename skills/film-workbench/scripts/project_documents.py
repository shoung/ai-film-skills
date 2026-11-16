"""Find skill output documents within the reader's already validated file index."""
from pathlib import Path

try:
    from . import project_reader
except ImportError:
    import project_reader

ALIASES = {
    '剧本.md': ('劇本.md', '剧本.md', 'screenplay.md'),
    '视觉设定.md': ('視覺設定.md', '视觉设定.md', '設定.md', '设定.md'),
    '分镜.md': ('分鏡.md', '分镜.md', 'storyboard.md', 'board.md'),
    '图片提示词.md': ('圖片提示詞.md', '图片提示词.md'),
    '视频提示词.md': ('影片提示詞.md', '視頻提示詞.md', '视频提示词.md'),
    '剪辑单.md': ('剪輯單.md', '剪辑单.md'),
}
HINTS = {
    '剧本.md': ('劇本', '剧本', 'screenplay'),
    '视觉设定.md': ('視覺資產', '视觉资产', '視覺設定', '视觉设定'),
    '分镜.md': ('分鏡', '分镜', 'storyboard'),
    '图片提示词.md': ('圖片提示詞', '图片提示词', '單幀生圖提示詞', '已採用圖像提示詞'),
    '视频提示词.md': ('影片提示詞', '視頻提示詞', '视频提示词', 'h3', 'seedance'),
    '剪辑单.md': ('剪輯單', '剪辑单', 'cut list'),
}
TRADITIONAL = {'剧本.md':'劇本.md', '视觉设定.md':'視覺設定.md', '分镜.md':'分鏡.md',
               '图片提示词.md':'圖片提示詞.md', '视频提示词.md':'視頻提示詞.md', '剪辑单.md':'剪輯單.md'}


def collect(root, episode):
    entries = [f for f in episode.get('files', []) if Path(f['path']).suffix.lower() in project_reader.TEXT]
    entries = sorted(entries, key=lambda f: f['path'])

    def candidates(kind):
        exact = [f for f in entries if Path(f['path']).name in ALIASES[kind]]
        if kind == '分镜.md' and episode.get('shots'):
            primary = episode['shots'][0]['source']
            selected = next((f for f in entries if f['path'] == primary), None)
            if selected: return [selected] + [f for f in exact if f != selected]
        others=[]
        for f in entries:
            p=Path(f['path']); name=p.name.casefold()
            if any(w in name for w in ('說明','说明','指南','清單','清单','readme','guide')): continue
            if kind == '剧本.md' and any(w in name for w in ('台詞','台词','dialogue')): continue
            values = [name] + ([p.parent.name.casefold()] if kind == '剧本.md' else [])
            if any(h.casefold() in value for h in HINTS[kind] for value in values): others.append(f)
        return exact + [f for f in others if f not in exact]

    cache={}
    def document(entry):
        path=entry['path']
        if path not in cache:
            cache[path]={'path':path, 'content':project_reader.read_document(root,path)['content']}
        return cache[path]

    texts, paths, sources = {}, {}, {}
    for kind in ALIASES:
        found=candidates(kind)
        sources[kind]=[document(f) for f in found]
        if found:
            texts[kind]=document(found[0])['content']
            paths[kind]=found[0]['path']
        else: paths[kind]=None
        paths[TRADITIONAL[kind]]=paths[kind]
    # Asset prompts also contain actual image prompt blocks, unlike a card PNG.
    images=sources['图片提示词.md'][:]
    for doc in sources['视觉设定.md']:
        if doc['path'] not in {d['path'] for d in images}: images.append(doc)
    return {'texts':texts, 'paths':paths, 'video_documents':sources['视频提示词.md'],
            'image_documents':images, 'sources':sources}
