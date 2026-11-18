"""Safe reader for local storyboard projects (Python standard library only)."""
import csv
import hashlib
import html
import json
import os
import posixpath
import re
import tempfile
import threading
from pathlib import Path, PurePosixPath

COLUMNS = ['編號', '畫面描述', '攝影機描述', '聲音描述', '旁白對白', '時長', '影片生成方式', '畫面prompt']
SUMMARY_IDS = {'合計', '總計', '小計', 'total', 'subtotal', '總秒數', '總長度'}
TABLE_RULE = re.compile(r'\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*')
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


def _comparison_value(value):
    value = html.unescape(str(value or ''))
    value = re.sub(r'<br\s*/?>', '\n', value, flags=re.I)
    return re.sub(r'\s+', ' ', value).strip()


def _explicit_master_paths(root, docs, files):
    scanned = {entry['path'] for entry in files}
    masters = set()
    for path, entry in docs:
        if path.suffix.lower() not in {'.md', '.markdown'}:
            continue
        try:
            text = path.read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError):
            continue
        for label, destination in re.findall(r'\[([^\]\n]+)\]\(([^)\n]+)\)', text):
            if not re.search(r'主表|正式主表', label):
                continue
            if '://' in destination or destination.startswith(('/', '\\')):
                continue
            relative = posixpath.normpath(posixpath.join(PurePosixPath(entry['path']).parent.as_posix(), destination.split('#', 1)[0].replace('\\', '/')))
            if relative.startswith('../') or relative in {'.', '..'}:
                continue
            target = PurePosixPath(relative).as_posix()
            if target in scanned and Path(target).suffix.lower() in {'.md', '.markdown', '.csv'}:
                masters.add(target)
    return masters


def _unpipe(line):
    value = line.strip()
    if value.startswith('|'):
        value = value[1:]
    cells, cell, start = [], [], 0
    for match in re.finditer(r'(\\*)\|', value):
        backslashes = len(match[1])
        cell.append(value[start:match.start()] + '\\' * (backslashes // 2))
        start = match.end()
        if backslashes % 2:
            cell.append('|')
        else:
            cells.append(''.join(cell).strip())
            cell = []
    if cell or start != len(value) or not cells:
        cells.append((''.join(cell) + value[start:]).strip())
    return cells


def _is_header(cells):
    return cells == COLUMNS


def _blank_shot(shot_id, source, row_index, fields):
    return {'id': shot_id, 'source': source, 'row_index': row_index, 'fields': fields,
            'assets': [], 'generations': [], 'reviews': [], 'issues': []}


def _shot_id(cell):
    bold = re.fullmatch(r'(\*\*|__)(.+?)\1', cell)
    return bold.group(2).strip() if bold else cell.strip()


def _markdown_tables(lines):
    """Yield table spans outside fenced examples and HTML comments."""
    fence = None
    in_comment = False
    visible = []
    for line in lines:
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})([^\r\n]*)', line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            visible.append('')
        elif not in_comment and marker:
            fence = marker[1]
            visible.append('')
        else:
            was_in_comment = in_comment
            for token in re.findall(r'<!--|-->', line):
                in_comment = token == '<!--' if not in_comment else token != '-->'
            # Inline closed comments can be part of a cell. Multi-line comments
            # form a boundary so a table never consumes the surrounding prose.
            visible.append('' if was_in_comment or in_comment or line.lstrip().startswith('<!--') else line)
    i = 0
    while i + 1 < len(lines):
        if '|' not in visible[i] or not TABLE_RULE.fullmatch(visible[i + 1]):
            i += 1
            continue
        header = _unpipe(lines[i])
        separators = _unpipe(lines[i + 1])
        i += 2
        start = i
        while i < len(lines) and '|' in visible[i]:
            if i + 1 < len(lines) and TABLE_RULE.fullmatch(visible[i + 1]):
                break
            i += 1
        yield start, i, header, separators


def _tables(text):
    lines = re.split(r'\r\n|\n|\r', text)
    shots, issues, columns = [], [], None
    table_count = 0
    for start, end, header, separators in _markdown_tables(lines):
        legacy = len(header) == 9 and header[0] == COLUMNS[0] and header[2:] == COLUMNS[1:]
        if len(header) in (8, 9) and len(separators) == len(header) and not (_is_header(header) or legacy):
            issues.append('發現非本規格八欄欄名或欄序的表格，已略過')
        if not (_is_header(header) or legacy) or len(separators) != len(header):
            continue
        columns = columns or header
        table_count += 1
        for row_index, line in enumerate(lines[start:end], 1):
            row = _unpipe(line)
            if len(row) != len(header):
                issues.append('分鏡資料第 ' + str(row_index) + ' 列欄數與欄名不符')
                continue
            shot_id = _shot_id(row[0])
            if shot_id.lower() in SUMMARY_IDS:
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
        if shot_id.lower() in SUMMARY_IDS:
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
            dirs[:] = [d for d in sorted(dirs) if not d.startswith('.') and d not in SKIP
                       and 'ai-film-skills' not in d.lower()
                       and not (Path(base) / d).is_symlink()
                       and not (Path(base) / d / 'SKILL.md').exists()]
        for name in sorted(names):
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
                # Tutorial captures are documentation, not film footage candidates.
                if any(part in {'教學素材', '教学素材', 'tutorial-assets'} for part in Path(rel).parts[:-1]):
                    continue
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
    master_paths = _explicit_master_paths(root, docs, files)
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
        if columns:
            ep.setdefault('storyboard_sources', []).append(entry['path'])
        for shot in shots:
            shot['source'] = entry['path']
            shot['_columns'] = columns
            ep['shots'].append(shot)
    # Resolve same-episode exports as source copies; keep canonical fields from authority.
    for ep in episodes.values():
        docs_here = ep.get('storyboard_sources', [])
        explicit = sorted(master_paths.intersection(docs_here))
        markdown = sorted(p for p in docs_here if Path(p).suffix.lower() in {'.md', '.markdown'})
        master_conflict = len(explicit) > 1
        primary = (explicit[0] if explicit else (markdown[0] if markdown else (sorted(docs_here)[0] if docs_here else None)))
        reason = ('入口存在多個主表宣告，暫採排序首項' if master_conflict else
                  '入口明確標示主表' if explicit else ('原生 Markdown 優先' if markdown else '唯一可用來源'))
        by_id = {}
        ordered = []
        for shot in ep['shots']:
            by_id.setdefault(shot['id'], []).append(shot)
        source_ids = {source: {s['id'] for s in ep['shots'] if s['source'] == source} for source in docs_here}
        id_conflicts = []
        if len(docs_here) > 1:
            authority_ids = source_ids.get(primary, set())
            for source in docs_here:
                if source == primary: continue
                missing = sorted(authority_ids - source_ids[source])
                extra = sorted(source_ids[source] - authority_ids)
                if missing or extra:
                    id_conflicts.append({'source': source, 'missing_ids': missing, 'extra_ids': extra})
        resolution = {'primary': primary, 'reason': reason, 'resolved': not master_conflict,
                      'alternatives': [p for p in docs_here if p != primary],
                      'conflicts': list(id_conflicts)}
        if master_conflict:
            resolution['conflicts'].append({'kind': 'multiple_explicit_masters', 'paths': explicit})
        ep['source_resolution'] = resolution
        shot_order = list(dict.fromkeys([s['id'] for s in ep['shots'] if s['source'] == primary] + [s['id'] for s in ep['shots']]))
        for shot_id in shot_order:
            candidates = by_id[shot_id]
            # Repeated rows in a single document remain malformed, not an alias.
            per_source = {}
            for candidate in candidates:
                per_source.setdefault(candidate['source'], []).append(candidate)
            duplicate_sources = [p for p, rows in per_source.items() if len(rows) > 1]
            if duplicate_sources:
                message = '同一分集存在重複鏡號：' + shot_id
                if message not in ep['issues']: ep['issues'].append(message)
                for candidate in candidates:
                    if candidate['source'] in duplicate_sources:
                        candidate['issues'].append('同一文件內鏡號重複')
            preferred = next((s for s in candidates if s['source'] == primary), candidates[0])
            ordered.append(preferred)
            sources = []
            details = []
            for source in docs_here:
                candidate = next((s for s in per_source.get(source, [])), None)
                if not candidate: continue
                raw_diffs = [field for field in COLUMNS if candidate['fields'].get(field) != preferred['fields'].get(field)]
                diffs = [field for field in COLUMNS if field != '編號' and _comparison_value(candidate['fields'].get(field)) != _comparison_value(preferred['fields'].get(field))]
                record = {'path': source, 'fields': dict(candidate['fields']), 'notes': list(candidate.get('supplement', {}).get('notes', [])),
                          'differences': raw_diffs, 'substantive_differences': diffs}
                sources.append(record)
                details.append(record)
                if diffs and source != primary:
                    resolution['conflicts'].append({'source': source, 'shot_id': shot_id, 'fields': diffs})
            preferred['_legacy_sources'] = sources
            preferred['_source_resolution'] = dict(resolution, differences=details)
            for candidate in candidates:
                if candidate is preferred: continue
                preferred['issues'].extend(issue for issue in candidate['issues'] if issue not in preferred['issues'])
                preferred.setdefault('supplement', {'notes': []})['notes'].extend(candidate.get('supplement', {}).get('notes', []))
        ep['shots'][:] = ordered
        substantive = any(any(record['substantive_differences'] for record in s.get('_legacy_sources', []) if record['path'] != primary) for s in ordered)
        if master_conflict:
            msg = '同分集有多個主表宣告，請確認權威來源'
            if msg not in ep['issues']: ep['issues'].append(msg)
        if id_conflicts or (substantive and not explicit and len(docs_here) > 1):
            differences = []
            if id_conflicts: differences.append('鏡號缺漏或多出')
            if substantive: differences.append('欄位內容不同')
            msg = '分鏡來源存在差異（' + '、'.join(differences) + '），請檢視來源明細'
            if msg not in ep['issues']: ep['issues'].append(msg)
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
        ep['issues'][:] = list(dict.fromkeys(ep['issues']))
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


def read_document(root, relative_path, content=None, expected_version=None, *, preserve_bom=False):
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
    with _file_lock(path):
        current = path.read_bytes()
        if _version(current) != expected_version:
            raise ValueError('文件已變更，請重新載入後再保存')
        encoding = 'utf-8-sig' if preserve_bom and current.startswith(b'\xef\xbb\xbf') else 'utf-8'
        data = content.encode(encoding)
        if len(data) > MAX_FILE:
            raise ValueError('文件超過讀取上限')
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
