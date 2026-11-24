#!/usr/bin/env python3
"""Compare verified records extracted from the script, storyboard and requests."""

import argparse
from itertools import groupby
import json
from pathlib import Path


def nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def check_shot_ids(value, target):
    if (not isinstance(value, list) or not value or not all(map(nonempty_string, value))
            or len(value) != len(set(value))):
        raise ValueError(f'{target}.shot_ids 須為不重複的非空鏡號陣列。')


def read_lines(document, target, *, locked=False):
    if not isinstance(document, dict) or not nonempty_string(document.get('source')):
        raise ValueError(f'{target}.source 須指出實際檢閱的來源及版本。')
    lines = document.get('lines')
    if not isinstance(lines, list):
        raise ValueError(f'{target}.lines 須為陣列。')
    for index, row in enumerate(lines, start=1):
        fields = ('id', 'speaker', 'text', 'location')
        if not isinstance(row, dict) or not all(nonempty_string(row.get(key)) for key in fields):
            raise ValueError(f'{target}.lines 第 {index} 筆須填寫 id、speaker、text、location。')
        location = f'{target} {row["location"]}'
        if not locked:
            check_shot_ids(row.get('shot_ids'), location)
        if 'fragment' in row and (locked or type(row['fragment']) is not int or row['fragment'] < 1):
            raise ValueError(f'{location} 的 fragment 須為分鏡或請求中從 1 起算的片段編號。')
    return [(f'{target} {row["location"]}', row) for row in lines]


def read_requests(requests, stage, add):
    if stage == 'storyboard':
        if requests not in (None, []):
            raise ValueError('storyboard 階段的 requests 須省略或為空陣列。')
        return []
    if not isinstance(requests, list) or not requests:
        raise ValueError(f'{stage} 階段須列出本次核對的請求。')

    lines = []
    seen_requests = set()
    for request in requests:
        if not isinstance(request, dict) or not nonempty_string(request.get('id')):
            raise ValueError('每個請求須有非空的 id。')
        request_id = request['id']
        target = f'{stage}/{request_id}'
        if request_id in seen_requests:
            raise ValueError(f'{target} 的請求 ID 重複。')
        seen_requests.add(request_id)
        shots = request.get('shot_ids')
        check_shot_ids(shots, target)
        request_lines = read_lines(request, target)
        for location, row in request_lines:
            if not set(row['shot_ids']).issubset(shots):
                add('SHOT_OUTSIDE_REQUEST', location, f'{row["id"]} 指向這次請求以外的鏡號。')
        lines.extend(request_lines)
    return lines


def fragment_shot_text(rows):
    return [
        (shots, ''.join(row['text'] for row in fragments))
        for shots, fragments in groupby(rows, key=lambda row: tuple(row['shot_ids']))
    ]


def compare(locked, lines, stage, add):
    occurrences = {}
    for index, (location, row) in enumerate(lines):
        line_id = row['id']
        if line_id in locked:
            occurrences.setdefault(line_id, []).append((index, location, row))
        else:
            add('UNEXPECTED_LINE', location, f'{line_id} 不在此範圍的鎖稿台詞清單中。')

    if list(occurrences) != [line_id for line_id in locked if line_id in occurrences]:
        add('LINE_ORDER', stage, '台詞播放順序與鎖稿不符。')

    shots_by_line = {}
    for line_id, (source, expected) in locked.items():
        uses = occurrences.get(line_id)
        if not uses:
            add('MISSING_LINE', stage, f'缺少 {line_id}（{source}）。')
            continue
        positions, locations, rows = zip(*uses)
        fragments = [row.get('fragment') for row in rows]
        valid_fragments = (len(rows) > 1 and fragments == list(range(1, len(rows) + 1))
                           and positions[-1] - positions[0] == len(rows) - 1)
        text_by_fragment_shots = []
        if len(rows) > 1 and all(part is None for part in fragments):
            add('DUPLICATE_LINE', '、'.join(locations), f'{line_id} 記入多次完整發話。')
        elif fragments != [None] and not valid_fragments:
            add('INVALID_FRAGMENTS', '、'.join(locations), f'{line_id} 的發話片段須連續且由 1 逐段編號。')
        else:
            spoken = ''.join(row['text'] for row in rows)
            if spoken != expected['text']:
                add('TEXT_MISMATCH', '、'.join(locations),
                    f'{line_id} 台詞不符。鎖稿 {expected["text"]!r}，此處 {spoken!r}。')
            elif valid_fragments:
                text_by_fragment_shots = fragment_shot_text(rows)
        for location, row in zip(locations, rows):
            if row['speaker'] != expected['speaker']:
                add('SPEAKER_MISMATCH', location,
                    f'{line_id} 說話者應為 {expected["speaker"]!r}，此處為 {row["speaker"]!r}。')
        shots = [shot for row in rows for shot in row['shot_ids']]
        shots_by_line[line_id] = ([shot for shot, _ in groupby(shots)], locations, text_by_fragment_shots)
    return shots_by_line


def audit(trace):
    issues = []

    def add(code, target, message):
        issues.append({'code': code, 'target': target, 'message': message})

    report = {'scope': None, 'stage': None, 'issues': issues}
    try:
        if not isinstance(trace, dict) or not nonempty_string(trace.get('scope')):
            raise ValueError('須以 scope 指出核對範圍。')
        stage = trace.get('stage')
        if stage not in ('storyboard', 'prompt', 'submission'):
            raise ValueError('stage 須為 storyboard、prompt 或 submission。')
        report.update(scope=trace['scope'], stage=stage)
        locked = {}
        for location, row in read_lines(trace.get('script'), 'script', locked=True):
            line_id = row['id']
            if line_id in locked:
                add('DUPLICATE_LOCKED_ID', location, f'鎖稿台詞 ID {line_id} 重複。')
            locked[line_id] = (location, row)
        board = read_lines(trace.get('storyboard'), 'storyboard')
        requests = read_requests(trace.get('requests'), stage, add)
    except ValueError as error:
        add('INVALID_TRACE', 'trace', str(error))
        return report

    if any(item['code'] == 'DUPLICATE_LOCKED_ID' for item in issues):
        return report

    board_shots = compare(locked, board, 'storyboard', add)
    if stage != 'storyboard':
        request_shots = compare(locked, requests, stage, add)
        for line_id, (shots, locations, fragment_text) in request_shots.items():
            if line_id not in board_shots:
                continue
            expected_shots, board_locations, expected_fragment_text = board_shots[line_id]
            if shots != expected_shots:
                add('SHOT_MISMATCH', '、'.join(locations), f'{line_id} 的發話鏡號與分鏡對照不符。')
            elif fragment_text and expected_fragment_text and fragment_text != expected_fragment_text:
                add('FRAGMENT_SHOT_MISMATCH', '、'.join(locations),
                    f'{line_id} 的發話片段在各鏡的文字與分鏡不符（{"、".join(board_locations)}）。')
    return report


def main():
    parser = argparse.ArgumentParser(description='比對已從來源核對的鎖定台詞紀錄。')
    parser.add_argument('trace', type=Path)
    args = parser.parse_args()
    try:
        report = audit(json.loads(args.trace.read_text(encoding='utf-8')))
    except (ValueError, OSError) as error:
        report = {'scope': None, 'stage': None, 'issues': [
            {'code': 'INVALID_TRACE', 'target': str(args.trace), 'message': str(error)}
        ]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(bool(report['issues']))


if __name__ == '__main__':
    raise SystemExit(main())
