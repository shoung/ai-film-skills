"""Versioned edits to Markdown storyboard rows, without reserializing the document."""
import re
from pathlib import Path

try:
    from . import project_reader as reader
except ImportError:
    import project_reader as reader


LINE_END = re.compile(r'(\r\n|\n|\r)')
CELL_BREAK = re.compile(r'<br\s*/?>', re.I)
CELL_PIPE = re.compile(r'(\\*)\|')


def _escape_pipe(value):
    return CELL_PIPE.sub(lambda match: '\\' * (2 * len(match[1]) + 1) + '|', value)


def _parse(content):
    parts = LINE_END.split(content)
    lines = parts[::2]
    tables = []
    for start, end, header, separators in reader._markdown_tables(lines):
        legacy = len(header) == 9 and header[0] == reader.COLUMNS[0] and header[2:] == reader.COLUMNS[1:]
        if len(separators) != len(header) or not (legacy or header == reader.COLUMNS):
            continue
        columns = [i for i in range(len(header)) if not (legacy and i == 1)]
        groups = []
        group = {'start': start, 'end': start, 'rows': [], 'summary': None}
        for index in range(start, end):
            raw = reader._unpipe(lines[index])
            if len(raw) != len(header) or not reader._shot_id(raw[0]):
                raise ValueError(f'第 {index + 1} 行分鏡資料格式不完整，請用原文編輯修正')
            shot_id = reader._shot_id(raw[0])
            cells = [CELL_BREAK.sub('\n', raw[i]) for i in columns]
            if shot_id.lower() in reader.SUMMARY_IDS:
                group['summary'] = cells
                groups.append(group)
                group = {'start': index + 1, 'end': index + 1, 'rows': [], 'summary': None}
                continue
            cells[0] = shot_id
            group['rows'].append({'key': index, 'cells': cells, 'raw': raw,
                                  'note': raw[1] if legacy else ''})
            group['end'] = index + 1
        if group['rows'] or not groups:
            groups.append(group)
        # A header-only table at EOF has no separator newline yet.
        newline = parts[2 * start - 1] if 2 * start - 1 < len(parts) else '\n'
        tables.append({'groups': groups, 'legacy': legacy, 'newline': newline})
    if not tables:
        raise ValueError('找不到可編輯的 Markdown 八欄分鏡表')
    return parts, tables


def _public(tables):
    return [{'groups': [{'rows': [{k: row[k] for k in ('key', 'cells', 'note')} for row in group['rows']],
                         'summary': group['summary']} for group in table['groups']]} for table in tables]


def _edit_group(parts, group, draft, legacy, newline, ids):
    if not isinstance(draft, list):
        raise ValueError('分鏡列格式不正確')
    originals = {row['key']: row for row in group['rows']}
    lines = []
    for row in draft:
        if not isinstance(row, dict):
            raise ValueError('分鏡列格式不正確')
        key, cells = row.get('key'), row.get('cells')
        if not isinstance(cells, list) or len(cells) != len(reader.COLUMNS) or not all(isinstance(cell, str) for cell in cells):
            raise ValueError('每個分鏡列必須包含八個文字欄位')
        if key is not None and (type(key) is not int or key not in originals):
            raise ValueError('分鏡列來源不符')
        original = originals.pop(key, None)
        shot_id = cells[0].strip()
        if original and shot_id != original['cells'][0]:
            raise ValueError('既有鏡號不得變更')
        if not original and (not re.fullmatch(r'[^\s|/\\?#<>]+', shot_id) or reader._shot_id(shot_id) != shot_id):
            raise ValueError('請填寫有效的新增鏡號（不可包含空白或路徑符號）')
        if shot_id.lower() in reader.SUMMARY_IDS or shot_id in ids:
            raise ValueError(f'鏡號重複或為保留名稱：{shot_id}')
        ids[shot_id] = None
        if original and cells == original['cells']:
            lines.append(parts[2 * key])
            continue
        values = [shot_id] + [LINE_END.sub('<br>', cell.strip()) for cell in cells[1:]]
        if legacy:
            values.insert(1, original['note'] if original else '')
        if original:
            previous = list(original['cells'])
            current = list(cells)
            if legacy:
                previous.insert(1, original['note'])
                current.insert(1, original['note'])
            values = [raw if before == after else value
                      for raw, before, after, value in zip(original['raw'], previous, current, values)]
        lines.append('| ' + ' | '.join(_escape_pipe(value) for value in values) + ' |')

    start, end = group['start'], group['end']
    if lines == parts[2 * start:2 * end:2]:
        return 2 * start, 2 * end, None
    if start * 2 >= len(parts):
        return len(parts), len(parts), newline + newline.join(lines)
    if end * 2 >= len(parts):
        # The table ends the document without a newline. When its last shot is
        # removed, keep the separator but remove the separator's trailing EOL.
        return 2 * start if lines else 2 * start - 1, len(parts), newline.join(lines)
    return 2 * start, 2 * end, ''.join(line + newline for line in lines)


def document(root, path, *, draft=None, expected_version=None):
    if Path(path).suffix.lower() not in {'.md', '.markdown'}:
        raise ValueError('表格編輯僅支援 Markdown 分鏡檔')
    current = reader.read_document(root, path)
    if expected_version is not None and current['version'] != expected_version:
        raise ValueError('文件已變更，請重新載入後再保存')
    parts, tables = _parse(current['content'])
    if draft is None:
        return {'path': current['path'], 'version': current['version'], 'tables': _public(tables)}
    if not isinstance(draft, list) or len(draft) != len(tables):
        raise ValueError('分鏡表來源不符')
    ids, edits = {}, []
    for table, groups in zip(tables, draft):
        if not isinstance(groups, list) or len(groups) != len(table['groups']):
            raise ValueError('分鏡段落來源不符')
        for group, rows in zip(table['groups'], groups):
            edits.append(_edit_group(parts, group, rows, table['legacy'], table['newline'], ids))
    for start, end, replacement in reversed(edits):
        if replacement is not None:
            parts[start:end] = [replacement]
    content = ''.join(parts)
    _, updated = _parse(content)
    updated_ids = [row['cells'][0] for table in updated for group in table['groups'] for row in group['rows']]
    if updated_ids != list(ids):
        raise ValueError('修改後無法辨識全部鏡頭，請檢查欄位中的 Markdown 標記')
    result = reader.read_document(root, path, content=content, expected_version=expected_version, preserve_bom=True)
    return {**result, 'tables': _public(updated)}
