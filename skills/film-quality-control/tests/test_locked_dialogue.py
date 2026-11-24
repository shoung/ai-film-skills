"""Synthetic traces exercise literal dialogue reconciliation."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[1] / 'scripts' / 'check_locked_dialogue.py'


def line(id_, text, *, speaker='阿寧', location='第 1 行', shot_ids=None, fragment=None):
    row = {'id': id_, 'speaker': speaker, 'text': text, 'location': location}
    if shot_ids is not None:
        row['shot_ids'] = shot_ids
    if fragment is not None:
        row['fragment'] = fragment
    return row


class LockedDialogueTests(unittest.TestCase):
    def setUp(self):
        self.trace = {
            'scope': '第 1 場，S001–S003',
            'stage': 'prompt',
            'script': {'source': 'script.md @ v2', 'lines': [
                line('C01-D01', '你先等我，別走。'), line('C01-D02', '好。', speaker='小禾'),
            ]},
            'storyboard': {'source': 'board.md @ v4', 'lines': [
                line('C01-D01', '你先等我，別走。', shot_ids=['S001', 'S002']),
                line('C01-D02', '好。', speaker='小禾', shot_ids=['S003']),
            ]},
            'requests': [
                {'id': 'G001', 'source': 'G001.txt @ v3', 'shot_ids': ['S001', 'S002'], 'lines': [
                    line('C01-D01', '你先等我，別走。', shot_ids=['S001', 'S002']),
                ]},
                {'id': 'G002', 'source': 'G002.txt @ v1', 'shot_ids': ['S003'], 'lines': [
                    line('C01-D02', '好。', speaker='小禾', shot_ids=['S003']),
                ]},
            ],
        }

    def audit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trace.json'
            path.write_text(json.dumps(self.trace, ensure_ascii=False), encoding='utf-8')
            run = subprocess.run([sys.executable, str(CHECKER), str(path)],
                                 capture_output=True, text=True, encoding='utf-8')
        self.assertIn(run.returncode, (0, 1), run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(run.returncode, bool(report['issues']))
        return report

    def codes(self):
        return {item['code'] for item in self.audit()['issues']}

    def test_one_utterance_can_continue_across_shots(self):
        self.assertEqual(self.codes(), set())

    def test_real_repetition_with_distinct_locked_occurrences_passes(self):
        for rows in (self.trace['script']['lines'], self.trace['storyboard']['lines'],
                     self.trace['requests'][1]['lines']):
            rows.append({**rows[-1], 'id': 'C01-D03', 'location': '第 3 行'})
        self.assertEqual(self.codes(), set())

    def test_storyboard_scope_can_be_audited_without_requests(self):
        self.trace['stage'] = 'storyboard'
        self.trace.pop('requests')
        self.assertEqual(self.audit()['stage'], 'storyboard')
        self.assertEqual(self.codes(), set())

    def test_empty_speech_is_valid_with_an_explicit_request(self):
        for source in [self.trace['script'], self.trace['storyboard'], *self.trace['requests']]:
            source['lines'] = []
        self.assertEqual(self.codes(), set())

    def test_missing_request_evidence_cannot_pass(self):
        self.trace['stage'] = 'submission'
        self.trace['requests'] = []
        self.assertIn('INVALID_TRACE', self.codes())

    def test_missing_from_storyboard_and_extra_in_request_are_reported(self):
        self.trace['storyboard']['lines'].pop(0)
        self.trace['requests'][1]['lines'].append(line('extra-01', '先喝茶。', shot_ids=['S003']))
        found = self.audit()['issues']
        self.assertTrue(any(i['code'] == 'MISSING_LINE' and i['target'] == 'storyboard' for i in found))
        self.assertTrue(any(i['code'] == 'UNEXPECTED_LINE' and 'G002' in i['target'] for i in found))

    def test_request_gap_surfaces_even_when_storyboard_has_the_line(self):
        self.trace['requests'][1]['lines'].clear()
        self.assertIn('MISSING_LINE', self.codes())

    def test_wrong_speaker_and_spoken_punctuation_are_detected(self):
        row = self.trace['requests'][0]['lines'][0]
        row.update(speaker='小禾', text='你先等我,別走。')
        self.assertEqual(self.codes(), {'SPEAKER_MISMATCH', 'TEXT_MISMATCH'})

    def test_text_preserves_locale_and_whitespace(self):
        for changed in ('你先等我，别走。', '你先等我，別走。 '):
            with self.subTest(changed=changed):
                self.trace['requests'][0]['lines'][0]['text'] = changed
                self.assertIn('TEXT_MISMATCH', self.codes())

    def test_complete_line_repeated_again_at_next_cut_is_rejected(self):
        self.trace['requests'][0]['lines'] = [
            line('C01-D01', '你先等我，別走。', shot_ids=['S001']),
            line('C01-D01', '你先等我，別走。', shot_ids=['S002']),
        ]
        self.assertIn('DUPLICATE_LINE', self.codes())

    def test_literal_numbered_fragments_may_span_requests(self):
        self.trace['requests'][0]['shot_ids'] = ['S001']
        self.trace['requests'][0]['lines'] = [line('C01-D01', '你先等我，', shot_ids=['S001'], fragment=1)]
        self.trace['requests'][1]['shot_ids'].insert(0, 'S002')
        self.trace['requests'][1]['lines'].insert(0, line('C01-D01', '別走。', shot_ids=['S002'], fragment=2))
        self.assertEqual(self.codes(), set())
        self.trace['requests'][1]['lines'][0]['fragment'] = 3
        self.assertIn('INVALID_FRAGMENTS', self.codes())

    def test_dropped_fragment_is_rejected_even_when_remaining_text_is_full_line(self):
        self.trace['requests'][0]['lines'][0]['fragment'] = 1
        self.assertIn('INVALID_FRAGMENTS', self.codes())

    def test_moved_fragment_cut_is_detected_when_both_sources_specify_it(self):
        self.trace['stage'] = 'submission'
        self.trace['storyboard']['lines'][:1] = [
            line('C01-D01', '你先等我，', shot_ids=['S001'], fragment=1),
            line('C01-D01', '別走。', shot_ids=['S002'], fragment=2),
        ]
        self.trace['requests'][0]['lines'] = [
            line('C01-D01', '你先等我，別', shot_ids=['S001'], fragment=1),
            line('C01-D01', '走。', shot_ids=['S002'], fragment=2),
        ]
        self.assertEqual(self.codes(), {'FRAGMENT_SHOT_MISMATCH'})

    def test_subdividing_an_explicit_fragment_inside_its_shot_does_not_move_a_cut(self):
        self.trace['storyboard']['lines'][:1] = [
            line('C01-D01', '你先等我，', shot_ids=['S001'], fragment=1),
            line('C01-D01', '別走。', shot_ids=['S002'], fragment=2),
        ]
        self.trace['requests'][0]['lines'] = [
            line('C01-D01', '你先', shot_ids=['S001'], fragment=1),
            line('C01-D01', '等我，', shot_ids=['S001'], fragment=2),
            line('C01-D01', '別走。', shot_ids=['S002'], fragment=3),
        ]
        self.assertEqual(self.codes(), set())

    def test_reversed_request_order_is_detected(self):
        self.trace['requests'].reverse()
        self.assertIn('LINE_ORDER', self.codes())

    def test_correct_text_at_the_wrong_shot_fails(self):
        self.trace['requests'][0]['lines'][0]['shot_ids'] = ['S002']
        self.assertIn('SHOT_MISMATCH', self.codes())

    def test_request_cannot_claim_a_shot_outside_its_group(self):
        self.trace['requests'][0]['shot_ids'] = ['S001']
        self.assertIn('SHOT_OUTSIDE_REQUEST', self.codes())

    def test_duplicate_locked_id_cannot_hide_a_required_occurrence(self):
        self.trace['script']['lines'][1]['id'] = 'C01-D01'
        self.assertIn('DUPLICATE_LOCKED_ID', self.codes())

    def test_malformed_fragment_type_fails_as_an_input_issue(self):
        self.trace['requests'][0]['lines'][0]['fragment'] = True
        self.assertIn('INVALID_TRACE', self.codes())


if __name__ == '__main__':
    unittest.main()
