#!/usr/bin/env python3
"""Run a supplied writing brief through agy; return an auditable routing decision."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


QUOTA = re.compile(
    r'\bquota[_-]exhausted\b|\bquota\s+(?:(?:has been|is|was)\s+)?(?:fully\s+)?(?:exhausted|depleted)\b|'
    r'\b(?:exhausted|depleted)\s+(?:your\s+|the\s+)?(?:weekly\s+|daily\s+)?quota\b|'
    r'\b(?:weekly|daily|monthly|five.hour|5.hour|account)\s+quota\s+(?:limit\s+)?exceeded\b|'
    r'\binsufficient\s+(?:ai\s+)?credits\b|\b(?:no|zero)\s+(?:remaining\s+)?credits\b|'
    r'(?:額度|额度|配額|配额).{0,20}(?:用盡|用尽|耗盡|耗尽|不足)', re.I)

# A quota phrase embedded in a rate limit, an inaccessible account status, or a
# negative diagnostic is not evidence that the writing budget is exhausted.
QUOTA_UNCONFIRMED = re.compile(
    r'per[\s_-]?(?:minute|second)|\brate[\s_-]?limit|\b(?:rpm|tpm)\b|'
    r'authenticat\w*\s+(?:required|failed|failure)|unauthori[sz]ed|unauthenticated|'
    r'invalid\s+credentials|permission\s+(?:denied|required)|forbidden|'
    r'network|time[\s_-]?out|timed\s+out|could\s+not\s+be\s+determined|\bunknown\b|'
    r'\b(?:not|no)\s+(?:\w+\s+){0,3}quota|'
    r'(?:exhausted|depleted)[\s\x27\x22:={]{0,8}(?:false|no|0)\b|'
    r'(?:每分鐘|每分钟|每秒|驗證失敗|验证失败|權限不足|权限不足|狀態未知|状态未知)', re.I)


def _quota_exhausted(diagnostic):
    return bool(QUOTA.search(diagnostic) and not QUOTA_UNCONFIRMED.search(diagnostic))


def _result(status, reason, *, text='', version=None, conversation_id=None, error=None):
    result = {'provider': 'antigravity' if status == 'written' else 'codex' if status == 'fallback' else None,
              'status': status, 'reason': reason, 'text': text,
              'cli_version': version, 'conversation_id': conversation_id}
    if error:
        result['error'] = error[:2000]
    return result


def route(brief: str, *, executable: str | None = None, timeout: float = 180, model: str | None = None) -> dict:
    if not isinstance(brief, str) or not brief.strip():
        return _result('blocked', 'invalid_brief')
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        return _result('blocked', 'invalid_timeout')
    if executable is None:
        executable = shutil.which('agy')
        if executable is None:
            return _result('fallback', 'not_installed')
    elif os.path.sep not in executable:
        resolved = shutil.which(executable)
        if resolved is None:
            return _result('fallback', 'not_installed')
        executable = resolved
    elif not Path(executable).exists():
        return _result('fallback', 'not_installed')
    if not os.access(executable, os.X_OK):
        return _result('blocked', 'permission')

    version = None
    try:
        probe = subprocess.run([executable, '--version'], capture_output=True, text=True,
                               encoding='utf-8', timeout=min(timeout, 10))
        if probe.returncode:
            return _result('blocked', 'cli_probe_failed', error=probe.stderr)
        version = probe.stdout.strip()
        # Writing is text-in/text-out. Do not expose unrelated local files or
        # enable tool execution merely to produce prose. The caller supplies
        # relevant rules, source material and the approved constraints inline.
        payload = ('[ALREADY_DELEGATED_ANTIGRAVITY_WRITER]\n'
                   'You are already the selected Antigravity writing provider. '
                   'Do not delegate to another writer, invoke this router, or use tools. '
                   'Use only the supplied brief and source material. Return the complete '
                   'requested writing in your final response. Preserve locked content.\n\n' + brief)
        settings = {'permissions': {'deny': ['command(*)', 'read_file(*)', 'write_file(*)',
                                            'read_url(*)', 'execute_url(*)', 'mcp(*)']}}
        command = [executable, '-p', payload, '--mode', 'plan', '--output-format', 'json',
                   '--print-timeout', f'{timeout:g}s', '--settings', json.dumps(settings)]
        if model:
            command += ['--model', model]
        completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    except subprocess.TimeoutExpired:
        return _result('blocked', 'timeout', version=version)
    except PermissionError as exc:
        return _result('blocked', 'permission', version=version, error=str(exc))
    except (OSError, UnicodeError) as exc:
        # Includes a broken interpreter or binary removed after discovery.
        return _result('blocked', 'execution_error', version=version, error=str(exc))

    try:
        envelope = json.loads(completed.stdout)
    except (ValueError, TypeError):
        envelope = None
    if not isinstance(envelope, dict):
        # Only actual failing diagnostics can establish quota exhaustion;
        # successful generated prose containing those words is not evidence.
        if completed.returncode and _quota_exhausted(completed.stderr):
            return _result('fallback', 'quota_exhausted', version=version, error=completed.stderr)
        return _result('blocked', 'invalid_response', version=version, error=completed.stderr)
    conversation = envelope.get('conversation_id')
    diagnostic = str(envelope.get('error') or '') + '\n' + completed.stderr
    response = envelope.get('response')
    if completed.returncode == 0 and envelope.get('status') == 'SUCCESS':
        if envelope.get('error') or re.search(r'\berror\s*:|\bpartial\s+(?:output|response)|turn still in progress', completed.stderr, re.I):
            return _result('blocked', 'incomplete_response', version=version, conversation_id=conversation, error=diagnostic)
        if re.search(r'auto-denied|soft.denied|no output produced|permission.{0,30}(?:denied|required)', completed.stderr, re.I):
            return _result('blocked', 'permission', version=version, conversation_id=conversation, error=diagnostic)
        if isinstance(response, str) and response.strip():
            return _result('written', 'antigravity_available', text=response, version=version, conversation_id=conversation)
        return _result('blocked', 'empty_response', version=version, conversation_id=conversation)
    if _quota_exhausted(diagnostic):
        return _result('fallback', 'quota_exhausted', version=version, conversation_id=conversation, error=diagnostic)
    return _result('blocked', 'cli_error', version=version, conversation_id=conversation, error=diagnostic)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--brief', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('--model', help='An explicitly selected, already verified model slug.')
    args = parser.parse_args(argv)
    try:
        result = route(args.brief.read_text(encoding='utf-8'), timeout=args.timeout, model=args.model)
    except (OSError, UnicodeError) as exc:
        result = _result('blocked', 'brief_read_error', error=str(exc))
    try:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except OSError as exc:
        print(json.dumps(_result('blocked', 'output_write_error', error=str(exc)), ensure_ascii=False))
        return 20
    print(json.dumps({k: result[k] for k in ('provider', 'status', 'reason')}, ensure_ascii=False))
    return {'written': 0, 'fallback': 10, 'blocked': 20}[result['status']]


if __name__ == '__main__':
    sys.exit(main())
