import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'route_writer.py'


class WriterRoutingTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('route_writer', SCRIPT)
        self.router = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.router)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fake = self.root / 'agy'

    def tearDown(self):
        self.tmp.cleanup()

    def executable(self, envelope=None, exit_code=0, error='', sleep=0):
        # A local fake replaces only the external CLI/network boundary; real
        # subprocess execution, stdout parsing and provider decision are tested.
        body = (f'#!{sys.executable}\nimport sys, json, time\n'
                'if "--version" in sys.argv:\n print("1.5.3-test"); sys.exit(0)\n'
                f'time.sleep({sleep})\n'
                f'print({json.dumps(json.dumps(envelope) if envelope is not None else "")})\n'
                f'print({error!r}, file=sys.stderr)\n'
                f'sys.exit({exit_code})\n')
        self.fake.write_text(body)
        self.fake.chmod(0o755)
        return str(self.fake)

    def run_writer(self, path, timeout=5):
        return self.router.route('只寫一句測試文案。', executable=path, timeout=timeout)

    def test_success_uses_antigravity_text_and_provenance(self):
        result = self.run_writer(self.executable({'status': 'SUCCESS', 'response': '測試稿', 'conversation_id': 'test-id'}))
        self.assertEqual((result['provider'], result['status'], result['text']), ('antigravity', 'written', '測試稿'))
        self.assertEqual(result['conversation_id'], 'test-id')

    def test_missing_binary_allows_codex(self):
        result = self.run_writer(str(self.root / 'absent'))
        self.assertEqual((result['provider'], result['status'], result['reason']), ('codex', 'fallback', 'not_installed'))

    def test_explicit_exhausted_quota_allows_codex(self):
        for message in ('Your weekly quota has been exhausted.', 'QUOTA_EXHAUSTED', 'Insufficient credits for this request.'):
            with self.subTest(message=message):
                result = self.run_writer(self.executable({'status': 'ERROR', 'error': message}, 1))
                self.assertEqual((result['provider'], result['reason']), ('codex', 'quota_exhausted'))

    def test_auth_network_permission_and_generic_429_do_not_allow_fallback(self):
        for message in ('authentication required', '429 Too Many Requests', 'network connection timed out',
                        'Permission denied', 'RESOURCE_EXHAUSTED: temporarily out of capacity'):
            with self.subTest(message=message):
                result = self.run_writer(self.executable({'status': 'ERROR', 'error': message}, 1))
                self.assertEqual(result['status'], 'blocked')
                self.assertIsNone(result['provider'])

    def test_error_text_inside_successful_creative_output_is_not_quota_failure(self):
        result = self.run_writer(self.executable({'status': 'SUCCESS', 'response': '角色說：「quota exhausted」。'}))
        self.assertEqual(result['status'], 'written')

    def test_empty_success_and_malformed_output_are_blocked(self):
        for envelope in ({'status': 'SUCCESS', 'response': ''}, None, ['unexpected']):
            with self.subTest(envelope=envelope):
                result = self.run_writer(self.executable(envelope))
                self.assertEqual(result['status'], 'blocked')

    def test_timeout_is_not_quota(self):
        result = self.run_writer(self.executable({'status': 'SUCCESS', 'response': 'late'}, sleep=1), timeout=0.5)
        self.assertEqual((result['status'], result['reason']), ('blocked', 'timeout'))

    def test_existing_nonexecutable_is_not_not_installed(self):
        self.fake.write_text('broken install')
        result = self.run_writer(str(self.fake))
        self.assertEqual(result['status'], 'blocked')

    def test_soft_denied_nonempty_response_is_not_delivered(self):
        result = self.run_writer(self.executable({'status': 'SUCCESS', 'response': 'partial'},
                                                error='a tool was auto-denied'))
        self.assertEqual(result['status'], 'blocked')

    def test_partial_output_with_error_is_not_delivered(self):
        cases = [({'status': 'SUCCESS', 'response': 'partial', 'error': 'authentication required'}, ''),
                 ({'status': 'SUCCESS', 'response': 'partial'}, 'ERROR: network connection lost; returning partial output')]
        for envelope, error in cases:
            with self.subTest(error=error):
                result = self.run_writer(self.executable(envelope, error=error))
                self.assertEqual(result['status'], 'blocked')

    def test_negated_or_rate_quota_errors_are_not_exhausted_credit(self):
        for message in ('Quota is not exhausted; authentication required.',
                        'Per-minute token quota exceeded. Retry after 2 seconds.',
                        'Quota temporarily exceeded due to rate limit.'):
            with self.subTest(message=message):
                result = self.run_writer(self.executable({'status': 'ERROR', 'error': message}, 1))
                self.assertEqual(result['status'], 'blocked')

    def test_quota_words_in_rate_auth_or_negative_diagnostics_are_blocked(self):
        messages = ('Per-minute quota exhausted. Retry in 60 seconds.',
                    'Authentication required; quota exhausted status could not be determined.',
                    'Quota exhausted: false; permission denied',
                    'quota_exhausted: false', 'Not quota exhausted; retry later.',
                    'Quota exhausted for requestsPerMinutePerProject.',
                    'Network timeout: quota exhausted status unknown.')
        for message in messages:
            for valid_json in (True, False):
                with self.subTest(message=message, valid_json=valid_json):
                    envelope = {'status': 'ERROR', 'error': message} if valid_json else None
                    result = self.run_writer(self.executable(envelope, 1, error=message))
                    self.assertEqual(result['status'], 'blocked')
                    self.assertIsNone(result['provider'])

    def test_cli_records_fallback_without_writing_as_codex(self):
        brief, output = self.root / 'brief.txt', self.root / 'receipt.json'
        brief.write_text('測試文字')
        env = dict(os.environ, PATH=str(self.root))
        completed = subprocess.run([sys.executable, '-B', str(SCRIPT), '--brief', str(brief), '--output', str(output)],
                                   capture_output=True, text=True, env=env)
        self.assertEqual(completed.returncode, 10, completed.stderr)
        receipt = json.loads(output.read_text())
        self.assertEqual((receipt['provider'], receipt['text']), ('codex', ''))

    def test_content_filter_refusal_routes_to_host_default_and_discards_partial(self):
        message = 'Your previous response was blocked by content safety filters: The model output could not be generated.'
        for envelope, code, stderr in (
            ({'status': 'ERROR', 'error': message, 'response': 'partial'}, 0, ''),
            ({'status': 'SUCCESS', 'error': message, 'response': 'partial'}, 0, ''),
            (None, 1, message),
            ({'status': 'ERROR', 'error': 'CONTENT_FILTERED'}, 1, ''),
        ):
            with self.subTest(envelope=envelope):
                result = self.run_writer(self.executable(envelope, code, error=stderr))
                self.assertEqual((result['status'], result['provider'], result['reason'], result['text']),
                                 ('fallback', 'default_llm', 'content_filtered', ''))

    def test_filter_mentions_and_unconfirmed_diagnostics_do_not_trigger_fallback(self):
        for message in ('Content filter check failed: network timeout.',
                        'Not blocked by content safety filters.',
                        'CONTENT_FILTERED: false; authentication required',
                        'Cannot determine whether output was blocked by content safety filters.',
                        'Permission denied', 'Content filter unavailable'):
            with self.subTest(message=message):
                result = self.run_writer(self.executable({'status': 'ERROR', 'error': message}, 1))
                self.assertEqual(result['status'], 'blocked')
        result = self.run_writer(self.executable({'status': 'SUCCESS', 'response': 'The story mentions CONTENT_FILTERED.'}))
        self.assertEqual(result['status'], 'written')

    def test_content_filter_cli_exit_and_receipt(self):
        self.executable({'status': 'ERROR', 'error': 'Output was blocked by content safety filters.'}, 0)
        brief, output = self.root / 'brief.txt', self.root / 'receipt.json'
        brief.write_text('Synthetic writing brief')
        completed = subprocess.run([sys.executable, '-B', str(SCRIPT), '--brief', str(brief), '--output', str(output)],
                                   capture_output=True, text=True, env=dict(os.environ, PATH=str(self.root)))
        self.assertEqual(completed.returncode, 10)
        self.assertEqual(json.loads(output.read_text())['provider'], 'default_llm')

    def test_cli_success_and_auth_failure_exit_codes(self):
        brief, output = self.root / 'brief.txt', self.root / 'receipt.json'
        brief.write_text('測試文字')
        env = dict(os.environ, PATH=str(self.root))
        for envelope, cli_exit, expected in (({'status': 'SUCCESS', 'response': '稿件'}, 0, 0),
                                             ({'status': 'ERROR', 'error': 'authentication required'}, 1, 20)):
            self.executable(envelope, cli_exit)
            completed = subprocess.run([sys.executable, '-B', str(SCRIPT), '--brief', str(brief), '--output', str(output)],
                                       capture_output=True, text=True, env=env)
            self.assertEqual(completed.returncode, expected, completed.stderr)


if __name__ == '__main__':
    unittest.main()
