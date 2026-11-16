"""Read-only adapter for legacy film-workbench files."""
import re
from pathlib import Path


SHOT_TOKEN = re.compile(r'(?<![A-Za-z0-9])S(\d{1,3}[A-Z]?)(?![A-Za-z0-9])', re.I)
RANGE = re.compile(r'(?<![A-Za-z0-9])(S\d{1,3}[A-Z]?)\s*[-–至~]\s*(S?\d{1,3}[A-Z]?)(?![A-Za-z0-9])', re.I)


def _shot_ids(value):
    ids = []
    for short in re.finditer(r'(?<![A-Za-z0-9])S(\d{1,3})([A-Z])((?:/[A-Z])+)(?![A-Za-z0-9])', value, re.I):
        ids.extend('S' + short.group(1) + suffix.upper() for suffix in [short.group(2), *short.group(3).split('/')[1:]])
    for match in RANGE.finditer(value):
        left, right = match.groups()
        if not right.upper().startswith('S'): right = 'S' + right
        left_match = re.fullmatch(r'S(\d{1,3})([A-Z]?)', left, re.I)
        right_match = re.fullmatch(r'S(\d{1,3})([A-Z]?)', right, re.I)
        if left_match and right_match and (left_match.group(2) or right_match.group(2)):
            ids.extend((left.upper(), right.upper()))
        elif left_match and right_match:
            start, end = int(left_match.group(1)), int(right_match.group(1))
            if end >= start and end - start <= 100:
                ids.extend('S%02d' % n for n in range(start, end + 1))
    masked = RANGE.sub(' ', value)
    ids.extend('S' + m.group(1).upper() for m in SHOT_TOKEN.finditer(masked))
    return list(dict.fromkeys(ids))


def _id_key(value):
    match = re.fullmatch(r'S(\d+)([A-Z]?)', str(value), re.I)
    return ('S' + str(int(match.group(1))) + match.group(2).upper()) if match else str(value).upper()


def _kind(path):
    ext = path.suffix.lower().lstrip('.')
    return {'png': 'image', 'jpg': 'image', 'jpeg': 'image', 'webp': 'image',
            'mp4': 'video', 'mov': 'video', 'webm': 'video'}.get(ext, 'media')


def _role(path):
    name = path.stem
    if re.search(r'(?i)(?:^|[_ .-])start(?:$|[_ .-])', name): return 'first_frame'
    if re.search(r'(?i)(?:^|[_ .-])end(?:$|[_ .-])', name): return 'last_frame'
    if '宮格' in name or 'storyboard' in name.lower() or 'grid' in name.lower(): return 'grid'
    if re.match(r'^[CEP]\d{2}', name, re.I): return 'reference_asset'
    if _kind(path) == 'video': return 'video_candidate'
    return 'image_candidate'


def _version_key(path):
    for part in Path(path).parts:
        m = re.search(r'(?:第([一二三四五六七八九十\d]+)版|v(\d+))', part, re.I)
        if m: return m.group(0).lower()
    return ''


def enrich(snapshot, root):
    """Add supplemental sources/media/prompts without changing the eight fields."""
    root = Path(root)
    for episode in snapshot['episodes']:
        # Merge only duplicate IDs inside the same already version-scoped episode.
        merged, by_id = [], {}
        for shot in episode['shots']:
            prior = by_id.get(shot['id'])
            source_records = shot.pop('_legacy_sources', None)
            source_resolution = shot.pop('_source_resolution', None)
            source = {'path': shot['source'], 'fields': dict(shot['fields']),
                      'notes': list(shot.get('supplement', {}).get('notes', [])), 'differences': []}
            if prior is None:
                sources = source_records or [source]
                notes = [note for record in sources for note in record.get('notes', [])]
                shot['supplement'] = {'sources': sources, 'media': [], 'prompts': [], 'notes': notes}
                if source_resolution:
                    shot['supplement']['source_resolution'] = source_resolution
                by_id[shot['id']] = shot
                merged.append(shot)
            else:
                prior['supplement']['sources'].append(source)
                if source['fields'] != prior['fields']:
                    prior['issues'].append('同鏡號來源內容不同，待確認來源：' + source['path'])
                prior['supplement']['notes'].extend(source['notes'])
                for key in ('assets', 'generations', 'reviews', 'issues'):
                    for item in shot[key]:
                        if item not in prior[key]: prior[key].append(item)
        episode['shots'][:] = merged
        if episode.get('source_resolution'):
            episode['source_resolution']['conflicts'] = list(episode['source_resolution'].get('conflicts', []))
        episode['issues'][:] = list(dict.fromkeys(episode['issues']))

    entries = {entry['path']: entry for entry in snapshot['files']}
    grid_index = {}
    for path, entry in entries.items():
        if Path(path).suffix.lower() not in {'.md', '.markdown'}: continue
        try: text = (root / path).read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError): continue
        for label, destination in re.findall(r'\[([^\]\n]+)\]\(([^)\n]+)\)', text):
            if '://' in destination: continue
            target = (Path(path).parent / destination).as_posix()
            if target in entries and entries[target]['kind'] == 'grid':
                members = _shot_ids(label)
                if members: grid_index.setdefault(target, []).extend(members)

    for ep in snapshot['episodes']:
        shots = ep['shots']
        for path, entry in entries.items():
            if entry.get('episode') and entry['episode'] != ep['id']: continue
            if entry['kind'] in {'document', 'qc'}:
                if 'H3' not in path and '提示詞' not in path: continue
                try: content = (root / Path(path)).read_text(encoding='utf-8-sig')
                except (OSError, UnicodeError): continue
                lines = content.splitlines()
                for idx, line in enumerate(lines):
                    head = re.match(r'^#{1,4}\s+(S\d{1,3}[A-Z]?)(?![A-Za-z0-9])', line, re.I)
                    if not head: continue
                    target = next((s for s in shots if _id_key(s['id']) == _id_key(head.group(1))), None)
                    if not target: continue
                    end = next((n for n in range(idx + 1, len(lines)) if re.match(r'^#{1,4}\s+', lines[n])), len(lines))
                    section = '\n'.join(lines[idx + 1:end])
                    for block in re.findall(r'```(?:text)?\s*\n(.*?)```', section, re.I | re.S):
                        if block.strip(): target['supplement']['prompts'].append({'text': block.strip(), 'kind': 'h3', 'source': path})
                continue
            rel = Path(path)
            role, kind = _role(rel), _kind(rel)
            ids = _shot_ids(rel.stem)
            if role == 'grid': ids = list(dict.fromkeys(ids + grid_index.get(path, [])))
            if not ids and role != 'reference_asset': continue
            for shot in shots:
                linked_ids = ids
                if role == 'reference_asset':
                    code = rel.stem.split('_', 1)[0]
                    reference = re.compile(r'(?<![A-Za-z0-9])' + re.escape(code) + r'(?![A-Za-z0-9])', re.I)
                    linked_ids = [shot['id'] for shot in shots
                                  if reference.search('\n'.join(map(str, shot['fields'].values())) + '\n' +
                                                     '\n'.join(shot['supplement']['notes']))]
                if _id_key(shot['id']) not in [_id_key(v) for v in linked_ids]: continue
                evidence = 'filename_boundary'
                if role == 'grid' and path in grid_index: evidence = 'grid_index'
                if role == 'reference_asset': evidence = 'text_reference'
                shot['supplement']['media'].append({'path': path, 'kind': kind, 'role': role,
                    'shot_ids': linked_ids, 'evidence': evidence})
    return snapshot
