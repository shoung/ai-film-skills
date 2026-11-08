"""Conservative request-level lint and evidence checks; not a semantic reviewer."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re

CHECKS = ('grouping', 'self_contained', 'reference_binding', 'readability')
REF = re.compile(r'<\s*(?:Picture|Video|Audio|Subject)\s+\d+\s*>|\bPicture\s+\d+\b|@[\w\u3400-\u9fff-]+', re.I)
SHOT = re.compile(r'\[\s*Shot\s+(\d+)\s*\]|鏡頭\s*(\d+)', re.I)
HEADER = re.compile(
    r'(?:(?:^|[。.!?！？;；\n])\s*(?:(?:integrated_multimodal_description|detailed_description)\s*:\s*)?'
    r'\[\s*Shot\s+(\d+)\s*\]|(?:^|[。.!?！？;；\n])\s*鏡頭\s*(\d+)\s*[（(]|'
    r'\[\s*Shot\s+(\d+)\s*\](?=\s*(?:At\s+\d|[（(]\s*\d)))', re.I | re.M)


def outside_dialogue(prompt):
    text = re.sub(r'<d\b[^>]*>.*?</d\s*>', '', prompt, flags=re.I | re.S)
    text = re.sub(r'(?:說|说|問|问|喊|答|\bsays?\b|\bsaid\b|\basks?\b|\bdialogue\b)\s*[:：]?\s*'
                  r'(?:「[^」]*」|“[^”]*”|"[^"\n]*")', '', text, flags=re.I)
    lines = []
    for line in text.splitlines():
        if re.search(r'(?:臺詞|台詞|對白|对白|旁白)\s*[:：]', line):
            line = re.sub(r'「[^」]*」|“[^”]*”|"[^"\n]*"', '', line)
        lines.append(line)
    return '\n'.join(lines)


def label_key(label):
    value = str(label).strip().strip('<>').strip()
    match = re.fullmatch(r'(Picture|Video|Audio|Subject)\s+(\d+)', value, re.I)
    return f'{match[1].lower()}:{int(match[2])}' if match else value


def shot_headers(text):
    return [(match.start(), int(next(n for n in match.groups() if n))) for match in HEADER.finditer(text)]


def prompt_signature(generation, assets_by_id=None):
    assets_by_id = assets_by_id or {}
    payload = {key: generation.get(key) for key in (
        'prompt', 'duration_seconds', 'mode', 'shot_ids', 'image_inputs', 'text_reference_bindings')}
    input_ids = [item.get('asset_id') for item in generation.get('image_inputs', []) if isinstance(item, dict)]
    payload['submitted_asset_hashes'] = {asset_id: assets_by_id.get(asset_id, {}).get('sha256')
                                       for asset_id in input_ids if isinstance(asset_id, str)}
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def validate_prompt(generation, assets, root: Path, *, delivery=False, target='generation'):
    issues = []

    def add(code, message, severity='error', field='prompt'):
        issues.append({'severity': severity, 'code': code, 'target': f'{target}.{field}', 'message': message})

    prompt = generation.get('prompt')
    if not isinstance(prompt, str):
        return issues
    if not prompt.strip():
        add('EMPTY_PROMPT', '生成正文不能留空。')
    text = outside_dialogue(prompt)
    inputs = generation.get('image_inputs', [])
    inputs = inputs if isinstance(inputs, list) else []
    submitted = {x.get('asset_id') for x in inputs if isinstance(x, dict) and isinstance(x.get('asset_id'), str)}
    labels = {}
    for item in inputs:
        if not isinstance(item, dict) or not isinstance(item.get('label'), str) or not item['label'].strip():
            continue
        key = label_key(item['label'])
        if key in labels:
            add('DUPLICATE_REFERENCE_LABEL', '同一請求的素材標籤不可重複。', field='image_inputs')
        if isinstance(item.get('asset_id'), str) and item['asset_id'] in assets:
            labels[key] = item.get('asset_id')
    bindings = generation.get('text_reference_bindings', [])
    if not isinstance(bindings, list):
        add('INVALID_REFERENCE_BINDINGS', 'text_reference_bindings 必須是陣列。', field='text_reference_bindings')
        bindings = []
    for item in bindings:
        if not isinstance(item, dict) or not isinstance(item.get('label'), str) or not item['label'].strip():
            add('INVALID_REFERENCE_BINDINGS', '每個文字引用必須有 label 與 asset_id。', field='text_reference_bindings')
            continue
        key, asset_id = label_key(item['label']), item.get('asset_id')
        if not isinstance(asset_id, str) or asset_id not in submitted or asset_id not in assets:
            add('REFERENCE_NOT_SUBMITTED', '文字引用的資產必須實際列入本次 image_inputs。', field='text_reference_bindings')
            continue
        if key in labels and labels[key] != asset_id:
            add('DUPLICATE_REFERENCE_LABEL', '同一標籤指向不同素材。', field='text_reference_bindings')
        labels[key] = asset_id
    subjects = {label_key(m[1]) for m in re.finditer(
        r'(?m)^\s*(?:subject_definitions\s*[:：]\s*)?(<Subject\s+\d+>)\s*(?:[:：]|is\b|是)',
        text, re.I)}
    referenced = {label_key(match[0]) for match in REF.finditer(text)}
    for key in sorted(referenced):
        if key.startswith(('video:', 'audio:')):
            add('UNSUPPORTED_REFERENCE_MEDIA', '此登錄格式僅核對圖片；影片／音訊素材須另列實際提交證據並人工審核。', 'warning')
        elif key not in labels and key not in subjects:
            # Chinese prose need not put spaces around a reference token.
            # A known prefix is ambiguous, not proof of an unknown asset.
            # ASCII suffixes/underscores remain part of the asset identifier.
            prefixes = [label for label in labels if label.startswith('@') and key.startswith(label)
                        and re.match(r'[\u3400-\u9fff]', key[len(label):])]
            if prefixes:
                add('AMBIGUOUS_REFERENCE', f'{key} 緊接已綁定標籤，請確認引用邊界；可加入空格。', 'warning')
            else:
                add('UNRESOLVED_REFERENCE', f'正文引用 {key} 未在本次請求定義或綁定。')

    headers = shot_headers(text)
    defined_shots = {number for _, number in headers}
    for match in SHOT.finditer(text):
        number = int(next(group for group in match.groups() if group))
        if number not in defined_shots:
            add('UNRESOLVED_SHOT_REFERENCE', f'正文引用鏡頭 {number}，但本次正文沒有此鏡頭定義。')
    shot_ids = generation.get('shot_ids', [])
    if isinstance(shot_ids, list):
        valid_ids = [s for s in shot_ids if isinstance(s, str)]
        if len(valid_ids) != len(set(valid_ids)):
            add('DUPLICATE_SHOT_IN_GENERATION', '同一生成群組不可重複列入同一鏡號。', field='shot_ids')

    prior = re.compile(r'上一(?:畫面|画面|鏡|镜|段|組|组)|前一(?:鏡|镜|段|組|组)|'
                       r'前次|上次(?:生成|請求|请求)|繼續剛才|继续刚才|'
                       r'\bprevious\s+(?:shot|frame|clip|request|generation)\b', re.I)
    # Review suspicious references within their sentence. An actual bound image
    # can legitimately be a previous clip's last frame. A previous shot inside
    # the same submitted sequence is also a valid referent.
    for sentence_match in re.finditer(r'[^。.!?！？\n]+', text):
        sentence = sentence_match[0]
        if not prior.search(sentence):
            continue
        bound_here = any(label_key(ref[0]) in labels for ref in REF.finditer(sentence))
        local_before = [h for h in headers if h[0] <= sentence_match.start()]
        is_cross_request = re.search(r'上一[段組组]|前一[段組组]|前次|上次|previous\s+(?:clip|request|generation)', sentence, re.I)
        if bound_here or (len(local_before) >= 2 and not is_cross_request):
            continue
        add('IMPLICIT_CONTEXT', '疑似依賴未隨請求提供的前文；請改為具體狀態或明確綁定實際素材。', 'warning')
    for name, definition in (
        (r'(?:全局風格|全局风格)', r'(?:全局風格|全局风格|風格鎖定|风格锁定)\s*[:：]'),
        (r'(?:角色音色設定|角色音色设定)', r'(?:角色音色設定|角色音色设定)\s*[:：]')):
        if re.search(r'(?:沿用|依照|參考|参考|同|遵循).{0,8}' + name, text) and not re.search(definition, text):
            add('IMPLICIT_CONTEXT', '引用的共同風格或音色設定沒有隨本次正文提供。', 'warning')
    sentences = [s.strip() for s in re.split(r'[。.!?！？\n]', text) if len(s.strip()) >= 12]
    if any(count >= 3 for count in Counter(sentences).values()):
        add('PROMPT_REPETITION', '正文含多次相同敘述，請人工確認是否為冗文。', 'warning')

    severity = 'error' if delivery else 'warning'
    review = generation.get('prompt_review')
    if not isinstance(review, dict):
        add('PROMPT_REVIEW_MISSING', '需要製作複核與隔離閱讀複核的實際紀錄。', severity, 'prompt_review')
        return issues
    if review.get('reviewer_role') != 'independent_qa' or not isinstance(review.get('reviewer_id'), str) or not review['reviewer_id'].strip():
        add('PROMPT_REVIEWER_INVALID', '必須記錄實際獨立審核者身份。', severity, 'prompt_review')
    elif review['reviewer_id'] == generation.get('producer_id'):
        add('PROMPT_SELF_REVIEW', 'prompt 製作者不能充當自己的獨立複核者。', severity, 'prompt_review')
    checks = review.get('checks')
    if review.get('status') != 'pass' or not isinstance(checks, dict) or any(checks.get(k) != 'pass' for k in CHECKS):
        add('PROMPT_REVIEW_NOT_PASS', '分組、獨立完整性、素材綁定與可讀性皆須完成複核。', severity, 'prompt_review')
    try:
        signature = prompt_signature(generation, assets)
    except (TypeError, ValueError, OverflowError):
        signature = None
    if signature is None or review.get('prompt_sha256') != signature:
        add('PROMPT_REVIEW_STALE', '正文、模式、分組、秒數、素材或引用變更後須重新複核。', severity, 'prompt_review')
    for field in ('production_evidence', 'isolation_evidence'):
        paths = review.get(field)
        if not isinstance(paths, list) or not paths:
            add('PROMPT_EVIDENCE_MISSING', f'缺少 {field}。', severity, 'prompt_review')
            continue
        for path in paths:
            if not isinstance(path, str) or not path.strip():
                add('PROMPT_EVIDENCE_MISSING', f'{field} 含無效路徑。', severity, 'prompt_review')
            elif delivery:
                try:
                    exists = (root / path).is_file()
                except (OSError, ValueError):
                    exists = False
                if not exists:
                    add('PROMPT_EVIDENCE_MISSING', f'{field} 證據檔不存在。', severity, 'prompt_review')
    return issues
