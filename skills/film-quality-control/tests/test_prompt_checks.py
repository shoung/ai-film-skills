"""Synthetic package fixtures exercise request boundaries, not actual model quality."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from validate_package import validate_package, generation_signature


class PromptChecksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.g = {'id': 'g1', 'mode': 'T2VA', 'shot_ids': ['s1'],
                  'duration_seconds': 6, 'producer_id': 'fixture-writer',
                  'image_inputs': [], 'prompt': '固定中景。灰衣女子把白杯放在木桌上。'}
        self.data = {'assets': [], 'shots': [{'id': 's1'}, {'id': 's2'}],
                     'generations': [self.g], 'reviews': []}

    def tearDown(self):
        self.tmp.cleanup()

    def codes(self, delivery=False):
        return {i['code'] for i in validate_package(self.data, self.root, delivery)}

    def add_image(self, label='Picture 1'):
        self.data['assets'].append({'id': 'card', 'role': 'character_card',
                                   'path': 'card.txt', 'version': 'v1', 'sha256': 'a' * 64})
        self.g['mode'] = 'Ref2VA'
        self.g['image_inputs'] = [{'asset_id': 'card', 'role': 'identity_reference', 'label': label}]

    def test_previous_request_without_input_is_flagged(self):
        for prompt in ('參考上一畫面，繼續剛才的動作。', '沿用上一段的服裝與姿勢。',
                       'Use the previous clip for her appearance.'):
            with self.subTest(prompt=prompt):
                self.g['prompt'] = prompt
                self.assertIn('IMPLICIT_CONTEXT', self.codes())

    def test_local_backward_shot_reference_is_allowed(self):
        self.g['shot_ids'] = ['s1', 's2']
        self.g['prompt'] = '鏡頭1（0–3秒）\n她拿起盒子。\n鏡頭2（3–6秒）\n承接鏡頭1，盒子已在她手上，放入抽屜。'
        self.assertNotIn('UNRESOLVED_SHOT_REFERENCE', self.codes())
        self.assertNotIn('IMPLICIT_CONTEXT', self.codes())

    def test_undefined_shot_reference_is_flagged(self):
        self.g['prompt'] = '鏡頭1（0–6秒）\n承接鏡頭9的姿勢。'
        self.assertIn('UNRESOLVED_SHOT_REFERENCE', self.codes())

    def test_previous_frame_explicitly_bound_to_current_input_is_allowed(self):
        self.add_image()
        self.g['prompt'] = '以本次提供的 <Picture 1>（上一段尾幀）為構圖參考。女子把手中白杯放回木桌。'
        self.assertNotIn('IMPLICIT_CONTEXT', self.codes())
        self.assertNotIn('UNRESOLVED_REFERENCE', self.codes())

    def test_dialogue_mentions_do_not_become_context_references(self):
        for prompt in ('[Shot 1] 她說：<d>[Chinese] 參考上一畫面，看看鏡頭9。</d>',
                       '鏡頭1（0–6秒）\n臺詞：她說：「上一畫面出現了 @小美。」',
                       '她說：「@人物甲。」', 'Dialogue: "<Picture 9>"'):
            with self.subTest(prompt=prompt):
                self.g['prompt'] = prompt
                self.assertNotIn('IMPLICIT_CONTEXT', self.codes())
                self.assertNotIn('UNRESOLVED_REFERENCE', self.codes())
                self.assertNotIn('UNRESOLVED_SHOT_REFERENCE', self.codes())

    def test_inline_shot_definitions_are_valid(self):
        for prompt in ('鏡頭1（0–3秒） A。鏡頭2（3–6秒） B。', '[Shot 1] A. [Shot 2] B.'):
            self.g['prompt'] = prompt
            self.g['shot_ids'] = ['s1', 's2']
            self.assertNotIn('UNRESOLVED_SHOT_REFERENCE', self.codes())

    def test_bound_alias_without_space_is_warning_not_false_rejection(self):
        self.add_image('@人物甲')
        self.g['prompt'] = '@人物甲移動。'
        self.assertNotIn('UNRESOLVED_REFERENCE', self.codes())
        self.assertIn('AMBIGUOUS_REFERENCE', self.codes())

    def test_unsubmitted_picture_is_rejected(self):
        self.add_image()
        self.g['prompt'] = '[Shot 1] <Picture 9>中的女子放下杯子。'
        self.assertIn('UNRESOLVED_REFERENCE', self.codes())

    def test_registered_but_unsubmitted_asset_cannot_bind_alias(self):
        self.add_image()
        self.g['image_inputs'] = []
        self.g['text_reference_bindings'] = [{'label': '@人物甲', 'asset_id': 'card'}]
        self.g['prompt'] = '@人物甲 放下白杯。'
        self.assertIn('REFERENCE_NOT_SUBMITTED', self.codes())

    def test_seedance_alias_resolves_to_submitted_asset(self):
        self.add_image()
        self.g['text_reference_bindings'] = [{'label': '@人物甲', 'asset_id': 'card'}]
        self.g['prompt'] = '@人物甲 放下白杯。'
        self.assertNotIn('UNRESOLVED_REFERENCE', self.codes())
        self.assertNotIn('REFERENCE_NOT_SUBMITTED', self.codes())

    def test_unknown_alias_is_rejected(self):
        self.g['prompt'] = '@不存在人物 放下白杯。'
        self.assertIn('UNRESOLVED_REFERENCE', self.codes())

    def test_h3_subject_definition_and_reference_resolve(self):
        self.add_image()
        self.g['prompt'] = 'subject_definitions:\n<Subject 1>：<Picture 1>的女子。\ndetailed_description:\n[Shot 1] <Subject 1>放下白杯。'
        self.assertNotIn('UNRESOLVED_REFERENCE', self.codes())
        self.g['prompt'] = '[Shot 1] <Subject 2>放下白杯。'
        self.assertIn('UNRESOLVED_REFERENCE', self.codes())

    def test_original_h3_natural_language_subject_definitions_resolve(self):
        self.add_image()
        for definition in ('<Subject 1> is the woman in <Picture 1>.',
                           '<Subject 1> 是 <Picture 1> 中的女子。',
                           'subject_definitions: <Subject 1> is the woman in <Picture 1>.'):
            with self.subTest(definition=definition):
                self.g['prompt'] = definition + '\ndetailed_description:\n[Shot 1] <Subject 1> 放下白杯。'
                self.assertNotIn('UNRESOLVED_REFERENCE', self.codes())

    def test_repeated_filler_is_readability_warning(self):
        self.g['prompt'] = '她的呼吸平穩，肩膀保持放鬆。' * 12
        self.assertIn('PROMPT_REPETITION', self.codes())

    def test_undefined_shared_settings_are_flagged_but_local_settings_allowed(self):
        self.g['prompt'] = '依照先前角色音色設定，沿用全局風格。'
        self.assertIn('IMPLICIT_CONTEXT', self.codes())
        self.g['prompt'] = '全局風格：真人寫實。角色音色設定：低聲平緩。\n鏡頭1（0–6秒）\n依照角色音色設定說話，沿用全局風格。'
        self.assertNotIn('IMPLICIT_CONTEXT', self.codes())

    def test_duplicate_shots_in_group_rejected(self):
        self.g['shot_ids'] = ['s1', 's1']
        self.assertIn('DUPLICATE_SHOT_IN_GENERATION', self.codes())

    def test_prompt_review_required_even_with_valid_timing_review(self):
        evidence = self.root / 'timing.txt'
        evidence.write_text('Synthetic timing fixture; not an actual QA pass.')
        self.g['timing_review'] = {'reviewer_id': 'fixture-qa', 'reviewer_role': 'independent_qa',
                                  'status': 'pass', 'generation_sha256': generation_signature(self.g),
                                  'checks': {k: 'pass' for k in ('dialogue_alignment', 'delivery_feasibility', 'pace_balance')},
                                  'evidence': ['timing.txt']}
        self.assertIn('PROMPT_REVIEW_MISSING', self.codes(delivery=True))

    def test_review_signature_changes_with_inputs_not_only_prompt(self):
        from prompt_checks import prompt_signature
        self.add_image()
        before = prompt_signature(self.g, {a['id']: a for a in self.data['assets']})
        self.g['image_inputs'][0]['role'] = 'composition_reference'
        self.assertNotEqual(before, prompt_signature(self.g, {a['id']: a for a in self.data['assets']}))
        after = prompt_signature(self.g, {a['id']: a for a in self.data['assets']})
        self.data['assets'][0]['sha256'] = 'b' * 64
        self.assertNotEqual(after, prompt_signature(self.g, {a['id']: a for a in self.data['assets']}))

    def reviewed(self):
        from prompt_checks import prompt_signature
        for name in ('production.txt', 'isolation.txt'):
            (self.root / name).write_text('Synthetic evidence fixture, not a real reviewer report.')
        self.g['prompt_review'] = {
            'reviewer_id': 'fixture-reviewer', 'reviewer_role': 'independent_qa', 'status': 'pass',
            'checks': {k: 'pass' for k in ('grouping', 'self_contained', 'reference_binding', 'readability')},
            'prompt_sha256': prompt_signature(self.g, {a['id']: a for a in self.data['assets']}),
            'production_evidence': ['production.txt'], 'isolation_evidence': ['isolation.txt']}

    def test_prompt_review_requires_both_evidence_and_independence(self):
        self.reviewed()
        self.assertNotIn('PROMPT_REVIEW_NOT_PASS', self.codes(True))
        self.assertNotIn('PROMPT_EVIDENCE_MISSING', self.codes(True))
        self.g['prompt_review']['isolation_evidence'] = ['missing.txt']
        self.g['prompt_review']['reviewer_id'] = self.g['producer_id']
        self.assertIn('PROMPT_EVIDENCE_MISSING', self.codes(True))
        self.assertIn('PROMPT_SELF_REVIEW', self.codes(True))

    def test_modified_prompt_invalidates_review(self):
        self.reviewed()
        self.g['prompt'] += '她轉頭。'
        self.assertIn('PROMPT_REVIEW_STALE', self.codes(True))

    def test_malformed_reference_metadata_returns_issues(self):
        self.add_image()
        self.g['image_inputs'][0]['asset_id'] = []
        self.assertIn('BROKEN_LINK', self.codes())

    def test_chinese_two_shot_headers_in_single_shot_mode_are_detected(self):
        self.add_image()
        self.data['assets'][0]['role'] = 'frame'
        self.data['assets'][0]['producer_id'] = 'fixture'
        self.g['mode'] = 'I2VA'
        self.g['image_inputs'][0]['role'] = 'first_frame'
        self.g['prompt'] = '鏡頭1（0–3秒）\n女子中景。\n鏡頭2（3–6秒）\n男子近景。'
        self.assertIn('PROMPT_CONTAINS_CUT', self.codes())


if __name__ == '__main__':
    unittest.main()
