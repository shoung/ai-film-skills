"""Safe reader for local storyboard projects (Python standard library only)."""
import csv
import hashlib
import json
import os
import re
import tempfile
import threading
from pathlib import Path, PurePosixPath

COLUMNS = ['編號', '畫面描述', '攝影機描述', '聲音描述', '旁白對白', '時長', '影片生成方式', '畫面prompt']
SKIP = {'.git', '.svn', '.hg', '.agents', '.codex', '_work', 'node_modules', '__pycache__', '.venv', 'venv', '.idea', '.vscode'}
TEXT = {'.md', '.markdown', '.csv', '.txt'}
READ_ONLY_TEXT = {'.html', '.htm'}
MEDIA = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp3', 'wav', 'm4a', 'mp4', 'mov', 'webm'}
QC_NAME = re.compile(r'(?:^|[-_.])(qc|qa|review|generation|asset|shot)(?:[-_.]|$)', re.IGNORECASE)
MAX_FILE = 16 * 1024 * 1024
MAX_JSON = 8 * 1024 * 1024
MAX_FILES = 5000
MAX_DEPTH = 12
_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def _safe(root, relative):
    root = Path(root).resolve(strict=True)
    rel = PurePosixPath(str(relative).replace('\\', '/'))
    if rel.is_absolute() or not rel.parts or any(p in ('..', '.') or p.startswith('.') or p in SKIP for p in rel.parts):
        raise ValueError('不允許存取此路徑')
    target = root.joinpath(*rel.parts)
    if target.is_symlink():
        raise ValueError('不允許透過符號連結存取')
    resolved = target.resolve(strict=False)
    if root not in resolved.parents:
        raise ValueError('路徑超出專案範圍')
    for parent in target.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError('不允許透過符號連結存取')
    return target


def _version(data):
    return hashlib.sha256(data).hexdigest()


def _unpipe(line):
    value = line.strip()
    if value.startswith('|'):
        value = value[1:]
    if value.endswith('|') and not value.endswith('\\|'):
        value = value[:-1]
    cells, cell, i = [], [], 0
    while i < len(value):
        char = value[i]
        if char == '\\' and i + 1 < len(value) and value[i + 1] == '|':
            cell.append('|')
            i += 2
            continue
        if char == '|':
            cells.append(''.join(cell).strip())
            cell = []
        else:
            cell.append(char)
        i += 1
    cells.append(''.join(cell).strip())
    return cells


def _is_header(cells):
    return cells == COLUMNS


def _blank_shot(shot_id, source, row_index, fields):
    return {'id': shot_id, 'source': source, 'row_index': row_index, 'fields': fields,
            'assets': [], 'generations': [], 'reviews': [], 'issues': []}


def _tables(text):
    lines = text.splitlines()
    shots, issues, columns = [], [], None
    table_count = 0
    i = 0
    while i + 1 < len(lines):
        if '|' not in lines[i] or not re.fullmatch(r'\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*', lines[i + 1]):
            i += 1
            continue
        header = _unpipe(lines[i])
        separators = _unpipe(lines[i + 1])
        i += 2
        legacy = len(header) == 9 and header[0] == COLUMNS[0] and header[2:] == COLUMNS[1:]
        if len(header) in (8, 9) and len(separators) == len(header) and not (_is_header(header) or legacy):
            issues.append('發現非本規格八欄欄名或欄序的表格，已略過')
        if not (_is_header(header) or legacy) or len(separators) != len(header):
            while i < len(lines) and '|' in lines[i]:
                i += 1
            continue
        columns = columns or header
        table_count += 1
        row_index = 0
        while i < len(lines) and '|' in lines[i]:
            row = _unpipe(lines[i])
            i += 1
            row_index += 1
            if len(row) != len(header):
                issues.append('分鏡資料第 ' + str(row_index) + ' 列欄數與欄名不符')
                continue
            shot_id = row[0].strip()
            if shot_id.lower() in ('合計', '總計', '小計', 'total', 'subtotal', '總秒數', '總長度'):
                continue
            if not shot_id:
                issues.append('分鏡資料第 ' + str(row_index) + ' 列缺少鏡號')
                continue
            fields = dict(zip(COLUMNS, row if not legacy else [row[0], *row[2:]]))
            shot = _blank_shot(shot_id, '', row_index, fields)
            if legacy and row[1].strip(): shot['supplement'] = {'sources': [], 'media': [], 'prompts': [], 'notes': [row[1].strip()]}
            shots.append(shot)
    if table_count > 1:
        issues.append('同一文件包含多份八欄分鏡表，已依文件順序合併')
    return columns or [], shots, issues


def _csv(path):
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return [], [], ['CSV 分鏡文件是空的']
    header = rows[0]
    legacy = len(header) == 9 and header[0] == COLUMNS[0] and header[2:] == COLUMNS[1:]
    if not (_is_header(header) or legacy):
        return [], [], ['CSV 欄名或欄序不符合八欄格式']
    shots, issues = [], []
    for index, row in enumerate(rows[1:], 1):
        if len(row) != len(header):
            issues.append('CSV 第 ' + str(index) + ' 列欄數與欄名不符')
            continue
        shot_id = row[0].strip()
        if shot_id.lower() in ('合計', '總計', '小計', 'total', 'subtotal', '總秒數', '總長度'):
            continue
        if not shot_id:
            issues.append('CSV 第 ' + str(index) + ' 列缺少鏡號')
            continue
        fields = dict(zip(COLUMNS, row if not legacy else [row[0], *row[2:]]))
        shot = _blank_shot(shot_id, '', index, fields)
        if legacy and row[1].strip(): shot['supplement'] = {'sources': [], 'media': [], 'prompts': [], 'notes': [row[1].strip()]}
        shots.append(shot)
    return header, shots, issues


def _episode(path):
    version = next((match.group(0) for part in PurePosixPath(path).parts
                    for match in [re.search(r'(?:第[一二三四五六七八九十\d]+版|v\d+)', part, re.I)] if match), None)
    for part in PurePosixPath(path).parts:
        if re.fullmatch(r'(?:EP|E|集)?\d{1,4}', part, re.I):
            return (version + ' · ' if version else '') + part
    return version


def project_snapshot(root):
    root = Path(root).resolve(strict=True)
    files, docs, packages, media, issues = [], [], [], [], []
    count = 0
    for base, dirs, names in os.walk(root, followlinks=False):
        depth = len(Path(base).relative_to(root).parts)
        if depth >= MAX_DEPTH:
            dirs[:] = []
        else:
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in SKIP
                       and 'ai-film-skills' not in d.lower()
                       and not (Path(base) / d).is_symlink()
                       and not (Path(base) / d / 'SKILL.md').exists()]
        for name in names:
            path = Path(base) / name
            if name.startswith('.') or path.is_symlink():
                continue
            count += 1
            if count > MAX_FILES:
                issues.append('專案檔案數超過掃描上限，後續檔案未列入')
                break
            rel = path.relative_to(root).as_posix()
            ext = path.suffix.lower()
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if ext in TEXT | READ_ONLY_TEXT or ext == '.json':
                if size > (MAX_JSON if ext == '.json' else MAX_FILE):
                    issues.append('文件超過讀取上限：' + rel)
                    continue
                kind = 'document' if ext in TEXT | READ_ONLY_TEXT else 'qc'
                entry = {'path': rel, 'name': name, 'kind': kind, 'episode': _episode(rel)}
                if ext in TEXT | READ_ONLY_TEXT:
                    entry['editable'] = ext in {'.md', '.markdown', '.csv', '.txt'}
                    docs.append((path, entry))
                else:
                    entry['editable'] = False
                    try:
                        obj = json.loads(path.read_text(encoding='utf-8-sig'))
                    except (OSError, UnicodeError, json.JSONDecodeError):
                        issues.append('QC JSON 無法以 UTF-8 JSON 讀取：' + rel)
                    else:
                        package_keys = ('assets', 'shots', 'generations', 'reviews')
                        named_package = name.lower() == 'package.json'
                        qc_named = bool(QC_NAME.search(name))
                        if not isinstance(obj, dict):
                            if named_package or qc_named:
                                issues.append('QC JSON 頂層必須是物件：' + rel)
                        elif any(k in obj for k in package_keys) or named_package:
                            if not all(k in obj and isinstance(obj[k], list) for k in package_keys):
                                issues.append('QC 套件欄位缺漏或型別錯誤：' + rel)
                            else:
                                kind = 'package'
                                entry['kind'] = kind
                                packages.append((path, obj, entry))
                files.append(entry)
            elif ext[1:] in MEDIA:
                media.append(rel)
                kind = 'grid' if ('grid' in name.lower() or 'storyboard' in name.lower() or '宮格' in name) and ext == '.png' else 'media'
                files.append({'path': rel, 'name': name, 'kind': kind, 'episode': _episode(rel)})
    episodes = {}

    def ensure_episode(ep):
        return episodes.setdefault(ep, {'id': ep, 'name': ep if ep != 'project' else root.name,
                                        'files': [], 'shots': [], 'packages': [], 'issues': [], 'grids': []})

    for entry in files:
        ep = entry['episode'] or 'project'
        episode = ensure_episode(ep)
        episode['files'].append(entry)
        if entry['kind'] == 'grid':
            episode['grids'].append(entry)
    for path, entry in docs:
        try:
            if path.suffix.lower() == '.csv':
                columns, shots, parse_issues = _csv(path)
            else:
                columns, shots, parse_issues = _tables(path.read_text(encoding='utf-8-sig'))
        except (OSError, UnicodeError, csv.Error):
            ensure_episode(entry['episode'] or 'project')['issues'].append('分鏡文件無法讀取：' + entry['path'])
            continue
        ep = ensure_episode(entry['episode'] or 'project')
        ep['issues'].extend(parse_issues)
        for shot in shots:
            shot['source'] = entry['path']
            shot['_columns'] = columns
            ep['shots'].append(shot)
    # Collapse duplicate MD/CSV rows into one logical shot before package linking.
    # Keep every source candidate so the view adapter can expose conflicts explicitly.
    for ep in episodes.values():
        logical, by_id = [], {}
        for shot in ep['shots']:
            candidate = {'path': shot['source'], 'fields': dict(shot['fields']),
                         'notes': list(shot.get('supplement', {}).get('notes', []))}
            existing = by_id.get(shot['id'])
            if existing is None:
                shot['_legacy_sources'] = [candidate]
                by_id[shot['id']] = shot
                logical.append(shot)
                continue
            existing['_legacy_sources'].append(candidate)
            warning = '同一分集存在重複鏡號來源，已合併為待確認的邏輯鏡頭'
            if warning not in ep['issues']:
                ep['issues'].append(warning)
            if candidate['fields'] != existing['fields']:
                existing['issues'].append('同鏡號來源內容不同，待確認來源：' + candidate['path'])
            existing['supplement'] = existing.get('supplement') or {'notes': []}
            existing['supplement']['notes'].extend(candidate['notes'])
            existing['issues'].extend(issue for issue in shot['issues'] if issue not in existing['issues'])
        ep['shots'][:] = logical
    columns = COLUMNS[:]
    records = []
    for path, package, entry in packages:
        ep_id = entry['episode'] or 'project'
        episode = ensure_episode(ep_id)
        episode['packages'].append(entry)
        base = path.parent
        assets_by_id = {}
        for asset in package['assets']:
            if not isinstance(asset, dict):
                episode['issues'].append('QC 套件 assets 含非物件資料：' + entry['path'])
                continue
            asset_id = asset.get('id')
            if isinstance(asset_id, str) and isinstance(asset.get('path'), str):
                if asset_id in assets_by_id:
                    ensure_episode(ep_id)['issues'].append('QC 套件內資產 ID 重複：' + asset_id)
                copied = dict(asset)
                copied['_base'] = base
                assets_by_id[asset_id] = copied
            else:
                episode['issues'].append('QC 套件資產缺少字串 id 或 path：' + entry['path'])
        for shot_record in package['shots']:
            if not isinstance(shot_record, dict):
                episode['issues'].append('QC 套件 shots 含非物件資料：' + entry['path'])
                continue
            shot_id = shot_record.get('id')
            if isinstance(shot_id, str):
                records.append(('package_shot', shot_record, base, ep_id, assets_by_id, entry['path']))
            else:
                episode['issues'].append('QC 套件鏡頭缺少字串 id：' + entry['path'])
        for kind in ('generations', 'reviews'):
            for record in package[kind]:
                if isinstance(record, dict):
                    records.append((kind, record, base, ep_id, assets_by_id, entry['path']))
                else:
                    episode['issues'].append('QC 套件 ' + kind + ' 含非物件資料：' + entry['path'])
    for kind, record, base, record_ep, assets_by_id, source_file in records:
        if kind == 'package_shot':
            ids = [record.get('id')]
            asset_ids = record.get('reference_asset_ids', [])
            if not isinstance(asset_ids, list):
                asset_ids = []
            asset_ids = list(asset_ids) + [v for v in [record.get('frame_asset_id')] + (record.get('additional_frame_asset_ids') if isinstance(record.get('additional_frame_asset_ids'), list) else []) if isinstance(v, str)]
        else:
            ids = record.get('shot_ids', [])
            if kind == 'reviews' and isinstance(record.get('shot_id'), str):
                ids = [record['shot_id']]
            asset_ids = []
        if isinstance(ids, str):
            ids = [ids]
        if not isinstance(ids, list):
            continue
        for shot_id in ids:
            candidates = [(ep, shot) for ep in episodes.values() for shot in ep['shots']
                          if shot['id'] == shot_id and (record_ep == 'project' or ep['id'] == record_ep)]
            if len(candidates) > 1:
                for _ep, shot in candidates:
                    shot['issues'].append('QC 鏡號重複，無法確定對應來源')
                continue
            if not candidates:
                target_ep = ensure_episode(record_ep)
                target_ep['issues'].append('QC 套件記錄找不到對應鏡號：' + str(shot_id) + '（' + source_file + '）')
                continue
            for ep, shot in candidates:
                if kind == 'package_shot':
                    for asset_id in asset_ids:
                        asset = assets_by_id.get(asset_id)
                        if not asset:
                            shot['issues'].append('找不到資產登錄：' + str(asset_id))
                            continue
                        rendered = dict(asset)
                        rendered['source_file'] = source_file
                        source_path = rendered.get('path')
                        if isinstance(source_path, str):
                            try:
                                rendered['source_path'] = source_path
                                rendered['path'] = (asset['_base'] / source_path).resolve(strict=False).relative_to(root).as_posix()
                            except (ValueError, OSError):
                                rendered['path'] = None
                                shot['issues'].append('QC 媒體路徑超出專案範圍')
                        rendered.pop('_base', None)
                        if rendered not in shot['assets']:
                            shot['assets'].append(rendered)
                    continue
                target = shot['generations'] if kind == 'generations' else shot['reviews']
                record_view = dict(record)
                record_view['source_file'] = source_file
                if record_view not in target:
                    target.append(record_view)
    for ep in episodes.values():
        shot_ids = [shot['id'] for shot in ep['shots']]
        if len({shot['source'] for shot in ep['shots']}) > 1:
            ep['issues'].append('偵測到多份分鏡來源，請確認是否屬於同一集')
        if len(shot_ids) != len(set(shot_ids)):
            ep['issues'].append('同一分集存在重複鏡號，QC 對應可能有歧義')
        if len(ep['packages']) > 1:
            ep['issues'].append('同一分集存在多份 QC 套件，請確認版本來源')
        if not ep['shots']:
            ep['issues'].append('找不到八欄分鏡表')
        for shot in ep['shots']:
            if not shot['assets']:
                shot['issues'].append('缺少 QC 資產資料')
            for asset in shot['assets']:
                if asset.get('path') and asset['path'] not in media:
                    shot['issues'].append('媒體不存在：' + asset['path'])
            if not shot['generations']:
                shot['issues'].append('缺少 QC generation 資料')
            if not shot['reviews']:
                shot['issues'].append('缺少 QC review 資料')
            shot.pop('_columns', None)
    if not any(ep['shots'] for ep in episodes.values()):
        issues.append('找不到八欄分鏡表')
    snapshot = {'name': root.name, 'episodes': list(episodes.values()), 'files': files,
            'issues': issues, 'columns': columns, 'media': media}
    from legacy_adapter import enrich
    return enrich(snapshot, root)


def _file_lock(path):
    key = str(path.resolve(strict=False)).casefold()
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.Lock())


def read_document(root, relative_path, content=None, expected_version=None):
    path = _safe(root, relative_path)
    if path.suffix.lower() not in TEXT | READ_ONLY_TEXT | {'.json'}:
        raise PermissionError('此檔案不可透過文字 API 讀取或編輯')
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError('找不到文件') from exc
    if len(raw) > MAX_FILE:
        raise ValueError('文件超過讀取上限')
    version = _version(raw)
    editable = path.suffix.lower() in TEXT
    if content is None:
        try:
            decoded = raw.decode('utf-8-sig')
        except UnicodeError as exc:
            raise ValueError('文件不是有效的 UTF-8 文字') from exc
        return {'path': PurePosixPath(str(relative_path).replace('\\', '/')).as_posix(),
                'content': decoded, 'version': version, 'editable': editable}
    if not editable:
        raise PermissionError('此文件為唯讀來源')
    if not isinstance(content, str) or not isinstance(expected_version, str):
        raise ValueError('保存內容或版本格式不正確')
    data = content.encode('utf-8')
    with _file_lock(path):
        current = path.read_bytes()
        if _version(current) != expected_version:
            raise ValueError('文件已變更，請重新載入後再保存')
        fd, temporary = tempfile.mkstemp(prefix='.film-workbench-', dir=str(path.parent))
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if _version(path.read_bytes()) != expected_version:
                raise ValueError('文件已變更，請重新載入後再保存')
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {'path': PurePosixPath(str(relative_path).replace('\\', '/')).as_posix(),
            'version': _version(data)}
