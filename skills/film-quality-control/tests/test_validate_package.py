import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from validate_package import generation_signature, validate_package


class PackageValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_asset(self, asset_id, role="frame", content=None, approved=None, producer_id="artist"):
        content = content if content is not None else ("bytes:" + asset_id).encode()
        path = self.root / (asset_id + ".dat")
        path.write_bytes(content)
        item = {
            "id": asset_id,
            "role": role,
            "path": path.name,
            "version": "v1",
            "sha256": hashlib.sha256(content).hexdigest(),
            "producer_id": producer_id,
        }
        if approved is not None:
            item["approved"] = approved
        return item

    def package(self, **updates):
        data = {"assets": [], "shots": [], "generations": [], "reviews": []}
        data.update(updates)
        return data

    def issues(self, data, delivery=False):
        issues = validate_package(data, self.root, delivery=delivery)
        self.assertIsInstance(issues, list)
        for issue in issues:
            self.assertIn(issue.get("severity"), ("error", "warning"))
            self.assertIsInstance(issue.get("code"), str)
            self.assertTrue(issue["code"].isascii())
            self.assertIsInstance(issue.get("target"), str)
            self.assertIsInstance(issue.get("message"), str)
        return issues

    def has_error(self, issues):
        return any(item["severity"] == "error" for item in issues)

    def assert_rejected(self, data, delivery=False):
        self.assertTrue(self.has_error(self.issues(data, delivery)), self.issues(data, delivery))

    def assert_code(self, issues, code):
        self.assertIn(code, {issue["code"] for issue in issues}, issues)

    def valid_review(self, shot_id, frame, assets, neighbor_frames=None, checks=None, reviewer="qa"):
        viewed = {a["id"]: a["sha256"] for a in assets if a["role"] != "frame"}
        return {
            "id": "review-" + shot_id,
            "shot_id": shot_id,
            "frame_sha256": frame["sha256"],
            "reviewer_id": reviewer,
            "reviewer_role": "independent_qa",
            "status": "pass",
            "viewed_assets": viewed,
            "neighbor_frames": neighbor_frames or {},
            "checks": checks or {
                "identity": "pass", "wardrobe": "pass", "makeup": "pass",
                "scene": "pass", "continuity": "pass", "prompt_alignment": "pass",
            },
            "evidence": [frame["path"]],
        }

    def test_single_shot_fl_is_valid(self):
        data = self.package(
            assets=[self.write_asset("start"), self.write_asset("end")],
            shots=[{"id": "s1"}],
            generations=[{"id": "g1", "mode": "FL2VA", "shot_ids": ["s1"],
                          "image_inputs": [{"asset_id": "start", "role": "first_frame"},
                                           {"asset_id": "end", "role": "last_frame"}],
                          "prompt": "保持同一連續鏡頭。"}],
        )
        self.assertFalse(self.has_error(self.issues(data)))

    def test_fl_with_multiple_shots_is_rejected(self):
        first, last = self.write_asset("a"), self.write_asset("b")
        data = self.package(assets=[first, last], shots=[{"id": "s1"}, {"id": "s2"}], generations=[
            {"id": "g", "mode": "FL2VA", "shot_ids": ["s1", "s2"], "image_inputs": [
                {"asset_id": "a", "role": "first_frame"}, {"asset_id": "b", "role": "last_frame"}], "prompt": "同一鏡頭"}])
        self.assert_code(self.issues(data), "SINGLE_SHOT_MODE")

    def test_hidden_cut_inside_one_shot_is_rejected(self):
        frame = self.write_asset("frame")
        for prompt in ("SHOT 1先對話，然後切至SHOT 2。", "鏡頭中切到另一景，再切回原人物。"):
            with self.subTest(prompt=prompt):
                data = self.package(assets=[frame], shots=[{"id": "s1"}], generations=[
                    {"id": "g", "mode": "I2VA", "shot_ids": ["s1"],
                     "image_inputs": [{"asset_id": "frame", "role": "first_frame"}], "prompt": prompt}])
                self.assert_code(self.issues(data), "PROMPT_CONTAINS_CUT")

    def test_negative_no_cut_instruction_is_not_misclassified(self):
        data = self.package(assets=[self.write_asset("a")], shots=[{"id": "s1"}], generations=[
            {"id": "g", "mode": "I2VA", "shot_ids": ["s1"],
             "image_inputs": [{"asset_id": "a", "role": "first_frame"}],
             "prompt": "不要切鏡、不要反打，整段維持同一連續鏡頭；no cuts."}])
        self.assertFalse(self.has_error(self.issues(data)))

    def test_cut_phrase_negation_is_local_and_does_not_mask_later_cut(self):
        frame = self.write_asset("frame")
        prompts = [
            ("避免任何切鏡；保持連續鏡頭。", False),
            ("無切鏡、無轉場，全程不反打。", False),
            ("不要反打，保持連續鏡頭。", False),
            ("no jump cuts; one continuous shot.", False),
            ("without any cuts; single unbroken shot without a cut.", False),
            ("no cuts. At 4s reverse shot.", True),
            ("不切鏡。接著反打朋友。", True),
            ("插鏡展示道具，再回主鏡頭。", True),
            ("蒙太奇快速切換不同場景。", True),
            ("jump cut to the next moment.", True),
        ]
        for prompt, should_reject in prompts:
            with self.subTest(prompt=prompt):
                data = self.package(assets=[frame], shots=[{"id": "s1"}], generations=[
                    {"id": "g", "mode": "I2VA", "shot_ids": ["s1"],
                     "image_inputs": [{"asset_id": "frame", "role": "first_frame"}], "prompt": prompt}])
                issues = self.issues(data)
                if should_reject:
                    self.assert_code(issues, "PROMPT_CONTAINS_CUT")
                else:
                    self.assertFalse(self.has_error(issues), issues)

    def test_h3_dialogue_text_is_excluded_from_cut_detection(self):
        frame = self.write_asset("dialogue-frame")
        prompts = [
            "保持單一連續鏡頭；no cuts. <d>[English] Cut the cake.</d>",
            "保持單一連續鏡頭；不要切鏡。<d>[普通話] 台詞裡說「反打」這個詞。</d>",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                data = self.package(assets=[frame], shots=[{"id": "s1"}], generations=[
                    {"id": "g", "mode": "I2VA", "shot_ids": ["s1"],
                     "image_inputs": [{"asset_id": "dialogue-frame", "role": "first_frame"}], "prompt": prompt}])
                issues = self.issues(data)
                self.assertFalse(self.has_error(issues), issues)

    def test_first_or_last_frame_role_must_match_mode(self):
        cases = [
            ("I2VA", [{"asset_id": "a", "role": "last_frame"}]),
            ("L2VA", [{"asset_id": "a", "role": "first_frame"}]),
            ("FL2VA", [{"asset_id": "a", "role": "first_frame"}]),
        ]
        for mode, inputs in cases:
            with self.subTest(mode=mode):
                self.assert_rejected(self.package(shots=[{"id": "s1"}], generations=[
                    {"id": "g", "mode": mode, "shot_ids": ["s1"], "image_inputs": inputs, "prompt": "連續鏡頭"}]))

    def test_ref2va_can_cover_multiple_shots_with_reference_purpose(self):
        data = self.package(assets=[self.write_asset("a", "character_card")], shots=[{"id": "s1"}, {"id": "s2"}], generations=[
            {"id": "g", "mode": "Ref2VA", "shot_ids": ["s1", "s2"],
             "image_inputs": [{"asset_id": "a", "role": "identity_reference"}], "prompt": "人物參考"}])
        self.assertFalse(self.has_error(self.issues(data)))

    def test_video_modes_reject_extra_image_inputs_and_incompatible_asset_roles(self):
        frame = self.write_asset("frame")
        character = self.write_asset("character", "character_card")
        cases = [
            ("I2VA", [{"asset_id": "frame", "role": "first_frame"}, {"asset_id": "character", "role": "identity_reference"}], "FRAME_INPUT_MISMATCH"),
            ("FL2VA", [{"asset_id": "frame", "role": "first_frame"}, {"asset_id": "frame", "role": "last_frame"}, {"asset_id": "character", "role": "identity_reference"}], "FRAME_INPUT_MISMATCH"),
            ("L2VA", [{"asset_id": "frame", "role": "last_frame"}, {"asset_id": "character", "role": "identity_reference"}], "FRAME_INPUT_MISMATCH"),
            ("I2VA", [{"asset_id": "character", "role": "first_frame"}], "INPUT_ASSET_ROLE_MISMATCH"),
        ]
        for mode, inputs, expected in cases:
            with self.subTest(mode=mode, inputs=inputs):
                data = self.package(assets=[frame, character], shots=[{"id": "s1"}], generations=[
                    {"id": "g", "mode": mode, "shot_ids": ["s1"], "image_inputs": inputs, "prompt": "連續鏡頭"}])
                self.assert_code(self.issues(data), expected)

    def test_ref2va_requires_a_reference_and_compatible_asset(self):
        scene = self.write_asset("scene", "scene_card")
        data = self.package(assets=[scene], shots=[{"id": "s1"}], generations=[
            {"id": "g", "mode": "Ref2VA", "shot_ids": ["s1"], "image_inputs": [], "prompt": "參考"}])
        self.assert_code(self.issues(data), "REFERENCE_INPUT_MISSING")
        data["generations"][0]["image_inputs"] = [{"asset_id": "scene", "role": "identity_reference"}]
        self.assert_code(self.issues(data), "INPUT_ASSET_ROLE_MISMATCH")

    def test_ref2va_rejects_hard_first_last_frame_roles(self):
        self.assert_rejected(self.package(shots=[{"id": "s1"}], generations=[
            {"id": "g", "mode": "Ref2VA", "shot_ids": ["s1"],
             "image_inputs": [{"asset_id": "a", "role": "first_frame"}], "prompt": "參考"}]))

    def test_t2va_must_not_have_image_inputs(self):
        self.assert_rejected(self.package(shots=[{"id": "s1"}], generations=[
            {"id": "g", "mode": "T2VA", "shot_ids": ["s1"],
             "image_inputs": [{"asset_id": "a", "role": "identity_reference"}], "prompt": "text"}]))

    def test_missing_file_and_wrong_hash_are_rejected_in_delivery(self):
        missing = {"id": "f", "role": "frame", "path": "missing.dat", "version": "v1", "sha256": "0" * 64}
        self.assert_rejected(self.package(assets=[missing]), delivery=True)
        asset = self.write_asset("f")
        asset["sha256"] = "0" * 64
        self.assert_rejected(self.package(assets=[asset]), delivery=True)

    def test_unapproved_current_card_is_rejected(self):
        card = self.write_asset("c", "character_card", approved=False)
        self.assert_rejected(self.package(assets=[card]), delivery=True)

    def test_frame_without_review_is_rejected(self):
        frame = self.write_asset("f")
        self.assert_rejected(self.package(assets=[frame], shots=[{"id": "s", "frame_asset_id": "f"}]), delivery=True)

    def test_review_by_frame_producer_is_rejected(self):
        frame = self.write_asset("f", producer_id="same-person")
        review = self.valid_review("s", frame, [], reviewer="same-person")
        self.assert_rejected(self.package(assets=[frame], shots=[{"id": "s", "frame_asset_id": "f"}], reviews=[review]), delivery=True)

    def test_failed_wardrobe_check_is_rejected(self):
        frame = self.write_asset("f")
        checks = {name: "pass" for name in ("identity", "wardrobe", "makeup", "scene", "continuity", "prompt_alignment")}
        checks["wardrobe"] = "fail"
        review = self.valid_review("s", frame, [], checks=checks)
        self.assert_rejected(self.package(assets=[frame], shots=[{"id": "s", "frame_asset_id": "f"}], reviews=[review]), delivery=True)

    def test_missing_neighbor_frame_record_is_rejected(self):
        first, second = self.write_asset("f1"), self.write_asset("f2")
        reviews = [self.valid_review("s1", first, []), self.valid_review("s2", second, [])]
        data = self.package(assets=[first, second], shots=[{"id": "s1", "frame_asset_id": "f1"}, {"id": "s2", "frame_asset_id": "f2"}], reviews=reviews)
        self.assert_rejected(data, delivery=True)

    def test_changed_current_card_invalidates_old_review(self):
        card = self.write_asset("card", "character_card", approved=True)
        frame = self.write_asset("frame")
        review = self.valid_review("s", frame, [card])
        card["sha256"] = "1" * 64
        data = self.package(assets=[card, frame], shots=[{"id": "s", "frame_asset_id": "frame"}], reviews=[review])
        self.assert_rejected(data, delivery=True)

    def test_changed_neighbor_frame_invalidates_old_review(self):
        first, second = self.write_asset("f1"), self.write_asset("f2")
        first_review = self.valid_review("s1", first, [], neighbor_frames={"f2": second["sha256"]})
        second_review = self.valid_review("s2", second, [], neighbor_frames={"f1": first["sha256"]})
        second["sha256"] = "2" * 64
        data = self.package(assets=[first, second], shots=[{"id": "s1", "frame_asset_id": "f1"}, {"id": "s2", "frame_asset_id": "f2"}], reviews=[first_review, second_review])
        self.assert_rejected(data, delivery=True)

    def test_not_applicable_requires_a_specific_reason(self):
        frame = self.write_asset("f")
        checks = {name: "pass" for name in ("identity", "wardrobe", "makeup", "scene", "continuity", "prompt_alignment")}
        checks["makeup"] = {"status": "not_applicable", "reason": " "}
        review = self.valid_review("s", frame, [], checks=checks)
        self.assert_rejected(self.package(assets=[frame], shots=[{"id": "s", "frame_asset_id": "f"}], reviews=[review]), delivery=True)

    def test_text_only_package_needs_no_visual_assets_or_reviews(self):
        self.assertFalse(self.has_error(self.issues(self.package(shots=[], assets=[], generations=[], reviews=[]), delivery=True)))

    def test_complete_visual_delivery_with_shot_specific_cards_and_na_passes(self):
        character = self.write_asset("character", "character_card", approved=True)
        scene = self.write_asset("scene", "scene_card", approved=True)
        first, second = self.write_asset("frame1"), self.write_asset("frame2")
        shots = [
            {"id": "s1", "frame_asset_id": "frame1", "reference_asset_ids": ["character"]},
            {"id": "s2", "frame_asset_id": "frame2", "reference_asset_ids": ["scene"]},
        ]
        na_checks = {"identity": "pass", "wardrobe": "pass", "makeup": {"status": "not_applicable", "reason": "本鏡頭角色未上妝，畫面沒有妝容可供比對。"},
                     "scene": "pass", "continuity": "pass", "prompt_alignment": "pass"}
        reviews = [
            self.valid_review("s1", first, [character], neighbor_frames={"frame2": second["sha256"]}, checks=na_checks),
            self.valid_review("s2", second, [scene], neighbor_frames={"frame1": first["sha256"]}),
        ]
        data = self.package(assets=[character, scene, first, second], shots=shots, reviews=reviews)
        issues = self.issues(data, delivery=True)
        self.assertFalse(self.has_error(issues), issues)

    def fl_delivery_package(self):
        first, last = self.write_asset("fl-first"), self.write_asset("fl-last")
        card = self.write_asset("fl-card", "character_card", approved=True)
        shot = {"id": "s1", "frame_asset_id": "fl-first", "additional_frame_asset_ids": ["fl-last"],
                "reference_asset_ids": ["fl-card"]}
        generation = {"id": "g1", "mode": "FL2VA", "shot_ids": ["s1"],
                      "image_inputs": [{"asset_id": "fl-first", "role": "first_frame"},
                                       {"asset_id": "fl-last", "role": "last_frame"}],
                      "prompt": "同一連續鏡頭，保持起始至結束的動作連續。", "duration_seconds": 6,
                      "producer_id": "video-maker",
                      "timing_review": {"reviewer_id": "timing-qa", "reviewer_role": "independent_qa", "status": "pass",
                                         "checks": {"dialogue_alignment": "pass", "delivery_feasibility": "pass", "pace_balance": "pass"},
                                         "evidence": [first["path"]]}}
        generation["timing_review"]["generation_sha256"] = generation_signature(generation)
        first_review = self.valid_review("s1", first, [card], neighbor_frames={"fl-last": last["sha256"]})
        last_review = self.valid_review("s1", last, [card], neighbor_frames={"fl-first": first["sha256"]})
        last_review["id"] = "review-s1-last"
        last_review["frame_asset_id"] = "fl-last"
        return self.package(assets=[first, last, card], shots=[shot], generations=[generation], reviews=[first_review, last_review])

    def test_complete_single_shot_fl_two_frame_delivery_passes(self):
        data = self.fl_delivery_package()
        issues = self.issues(data, delivery=True)
        self.assertFalse(self.has_error(issues), issues)

    def test_single_shot_fl_delivery_rejects_missing_tail_review(self):
        data = self.fl_delivery_package()
        data["reviews"].pop()
        self.assert_code(self.issues(data, delivery=True), "MISSING_REVIEW")

    def test_single_shot_fl_delivery_rejects_missing_internal_neighbor_evidence(self):
        data = self.fl_delivery_package()
        data["reviews"][1]["neighbor_frames"] = {}
        self.assert_code(self.issues(data, delivery=True), "NEIGHBOR_REVIEW_STALE")

    def test_reference_cards_are_scoped_to_each_shot_and_missing_reference_is_rejected(self):
        character = self.write_asset("character", "character_card", approved=True)
        scene = self.write_asset("scene", "scene_card", approved=True)
        frame = self.write_asset("frame")
        review = self.valid_review("s", frame, [character])
        data = self.package(assets=[character, scene, frame],
                            shots=[{"id": "s", "frame_asset_id": "frame", "reference_asset_ids": ["character"]}],
                            reviews=[review])
        self.assertFalse(self.has_error(self.issues(data, delivery=True)))
        data["shots"][0]["reference_asset_ids"] = ["missing-card"]
        self.assert_code(self.issues(data), "BROKEN_LINK")

    def test_absolute_and_parent_relative_asset_and_evidence_paths_are_allowed(self):
        nested = self.root / "package-dir"
        nested.mkdir()
        frame = self.write_asset("frame")
        card = self.write_asset("card", "character_card", approved=True)
        frame["path"] = "../frame.dat"
        card["path"] = str((self.root / "card.dat").resolve())
        review = self.valid_review("s", frame, [card])
        review["evidence"] = ["../frame.dat"]
        data = self.package(assets=[frame, card], shots=[{"id": "s", "frame_asset_id": "frame", "reference_asset_ids": ["card"]}], reviews=[review])
        self.assertFalse(self.has_error(validate_package(data, nested, delivery=True)))
        frame["path"] = str((self.root / "frame.dat").resolve())
        review["evidence"] = [str((self.root / "frame.dat").resolve())]
        self.assertFalse(self.has_error(validate_package(data, nested, delivery=True)))

    def test_sha256_format_is_checked_in_structure_scope(self):
        frame = self.write_asset("frame")
        frame["sha256"] = "not-a-hash"
        self.assert_code(self.issues(self.package(assets=[frame])), "INVALID_SHA256")

    def test_nested_delivery_types_return_issues_without_crashing(self):
        malformed_asset = {"id": "x", "role": [], "path": "x", "version": "v1", "sha256": "0" * 64, "producer_id": "artist"}
        self.assertTrue(self.has_error(self.issues(self.package(assets=[malformed_asset]), delivery=True)))
        data = self.package(shots=[{"id": "s", "frame_asset_id": []}], assets=[])
        self.assertTrue(self.has_error(self.issues(data, delivery=True)))
        frame = self.write_asset("bad-role-input")
        frame["role"] = []
        data = self.package(assets=[frame], shots=[{"id": "s"}], generations=[
            {"id": "g", "mode": "I2VA", "shot_ids": ["s"],
             "image_inputs": [{"asset_id": "bad-role-input", "role": "first_frame"}], "prompt": "連續鏡頭"}])
        role_issues = self.issues(data, delivery=True)
        self.assert_code(role_issues, "INVALID_ASSET_ROLE")
        self.assert_code(role_issues, "INPUT_ASSET_ROLE_MISMATCH")

    def test_delivery_rejects_frames_without_a_formal_reference_card(self):
        frame = self.write_asset("unsupported-frame")
        review = self.valid_review("s", frame, [])
        for references in ([], ["unsupported-frame"]):
            with self.subTest(references=references):
                data = self.package(assets=[frame], shots=[{"id": "s", "frame_asset_id": "unsupported-frame",
                                                            "reference_asset_ids": references}], reviews=[review])
                self.assert_code(self.issues(data, delivery=True), "MISSING_FORMAL_REFERENCE")
        frame = self.write_asset("frame")
        review = self.valid_review("s", frame, [], neighbor_frames={frame["id"]: []})
        data = self.package(assets=[frame], shots=[{"id": "s", "frame_asset_id": "frame"}], reviews=[review])
        self.assertTrue(self.has_error(self.issues(data, delivery=True)))

    def test_wrong_typed_inputs_return_issues_without_crashing(self):
        bad_values = [None, [], {"assets": None, "shots": "bad", "generations": 7, "reviews": {}},
                      {"assets": [None, 4, "x"], "shots": [1, {}], "generations": [None], "reviews": [False]},
                      {"assets": [{"id": [], "role": [], "path": [], "version": 1, "sha256": []}],
                       "shots": [{"id": [], "reference_asset_ids": 2}],
                       "generations": [{"id": "g", "mode": [], "shot_ids": ["s"],
                                        "image_inputs": [{"asset_id": [], "role": []}], "prompt": []}],
                       "reviews": []}]
        for value in bad_values:
            with self.subTest(value=value):
                issues = self.issues(value)
                self.assertTrue(self.has_error(issues))

    def test_delivery_rejects_orphan_frame_assets(self):
        frame = self.write_asset("orphan")
        self.assert_rejected(self.package(assets=[frame], shots=[]), delivery=True)

    def test_delivery_requires_card_version_hash_and_producer(self):
        card = self.write_asset("card", "character_card", approved=True)
        for key in ("version", "sha256"):
            with self.subTest(field=key):
                candidate = dict(card)
                candidate.pop(key)
                self.assert_rejected(self.package(assets=[candidate]), delivery=True)
        frame = self.write_asset("frame")
        frame.pop("producer_id")
        self.assert_code(self.issues(self.package(assets=[frame]), delivery=True), "MISSING_PRODUCER")

    def test_pending_review_is_draft_warning_but_fails_delivery(self):
        frame = self.write_asset("frame")
        review = self.valid_review("s", frame, [])
        review["status"] = "pending"
        data = self.package(assets=[frame], shots=[{"id": "s", "frame_asset_id": "frame"}], reviews=[review])
        structure_issues = self.issues(data)
        self.assertFalse(self.has_error(structure_issues), structure_issues)
        self.assert_code(structure_issues, "REVIEW_PENDING")
        self.assert_code(self.issues(data, delivery=True), "REVIEW_NOT_PASS")

    def timed_delivery_package(self, duration=7.5):
        frame = self.write_asset("timed-frame")
        card = self.write_asset("timed-character", "character_card", approved=True)
        shot = {"id": "s", "frame_asset_id": "timed-frame", "reference_asset_ids": ["timed-character"]}
        visual_review = self.valid_review("s", frame, [card])
        generation = {
            "id": "g", "mode": "T2VA", "shot_ids": ["s"], "image_inputs": [],
            "prompt": "角色沿著廊道慢步前行，說完台詞後停頓。",
            "duration_seconds": duration,
            "producer_id": "video-maker",
            "timing_review": {
                "reviewer_id": "timing-qa", "reviewer_role": "independent_qa", "status": "pass",
                "checks": {"dialogue_alignment": "pass", "delivery_feasibility": "pass", "pace_balance": "pass"},
                "evidence": [frame["path"]],
            },
        }
        generation["timing_review"]["generation_sha256"] = generation_signature(generation)
        return self.package(assets=[frame, card], shots=[shot], generations=[generation], reviews=[visual_review])

    def test_complete_timing_review_passes_delivery(self):
        data = self.timed_delivery_package()
        issues = self.issues(data, delivery=True)
        self.assertFalse(self.has_error(issues), issues)

    def test_timing_review_is_required_only_for_generations_at_delivery(self):
        data = self.timed_delivery_package()
        del data["generations"][0]["timing_review"]
        draft_issues = self.issues(data)
        self.assertFalse(self.has_error(draft_issues), draft_issues)
        self.assert_code(draft_issues, "TIMING_REVIEW_MISSING")
        self.assert_code(self.issues(data, delivery=True), "TIMING_REVIEW_MISSING")
        text_only = self.package(generations=[], shots=[], assets=[], reviews=[])
        self.assertFalse(self.has_error(self.issues(text_only, delivery=True)))

    def test_timing_review_pending_and_failed_are_rejected(self):
        for status in ("pending", "fail"):
            with self.subTest(status=status):
                data = self.timed_delivery_package()
                data["generations"][0]["timing_review"]["status"] = status
                self.assert_code(self.issues(data, delivery=True), "TIMING_REVIEW_NOT_PASS")

    def test_timing_review_requires_evidence(self):
        data = self.timed_delivery_package()
        data["generations"][0]["timing_review"]["evidence"] = []
        self.assert_code(self.issues(data, delivery=True), "TIMING_EVIDENCE_MISSING")
        data = self.timed_delivery_package()
        data["generations"][0]["timing_review"]["evidence"] = ["absent-proof.txt"]
        self.assert_code(self.issues(data, delivery=True), "TIMING_EVIDENCE_MISSING")

    def test_delivery_requires_positive_declared_generation_duration(self):
        for duration in (None, 0, -1):
            with self.subTest(duration=duration):
                data = self.timed_delivery_package(duration=duration)
                if duration is None:
                    del data["generations"][0]["duration_seconds"]
                self.assert_code(self.issues(data, delivery=True), "GENERATION_DURATION_INVALID")

    def test_timing_review_is_invalidated_by_prompt_or_duration_changes(self):
        for field, value in (("prompt", "修改後的台詞版本"), ("duration_seconds", 8)):
            with self.subTest(field=field):
                data = self.timed_delivery_package()
                data["generations"][0][field] = value
                self.assert_code(self.issues(data, delivery=True), "TIMING_REVIEW_STALE")

    def test_timing_reviewer_must_be_distinct_from_generation_producer(self):
        data = self.timed_delivery_package()
        data["generations"][0]["timing_review"]["reviewer_id"] = "video-maker"
        self.assert_code(self.issues(data, delivery=True), "TIMING_REVIEWER_NOT_INDEPENDENT")

    def test_cli_accepts_utf8_bom_package(self):
        package_dir = self.root / "繁體資料夾"
        package_dir.mkdir()
        path = package_dir / "package.json"
        path.write_text("\ufeff" + json.dumps(self.package(), ensure_ascii=False), encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPTS / "validate_package.py"), str(path)], capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])
    def run_cli(self, payload, malformed=False):
        package_path = self.root / "package.json"
        package_path.write_text(payload if malformed else json.dumps(payload), encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPTS / "validate_package.py"), str(package_path)],
                                capture_output=True, encoding="utf-8")
        return result

    def test_cli_exit_codes_and_json_output(self):
        valid = self.run_cli(self.package())
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(json.loads(valid.stdout)["ok"], True)
        invalid = self.run_cli(self.package(shots=[{"id": "s"}], generations=[
            {"id": "g", "mode": "I2VA", "shot_ids": ["missing"], "image_inputs": [], "prompt": ""}]))
        self.assertEqual(invalid.returncode, 1, invalid.stderr)
        self.assertIn("issues", json.loads(invalid.stdout))
        malformed = self.run_cli("{bad json", malformed=True)
        self.assertEqual(malformed.returncode, 2)
        self.assertTrue(malformed.stdout)
        self.assertEqual(json.loads(malformed.stdout)["scope"], "structure")
        malformed_delivery_path = self.root / "broken-delivery.json"
        malformed_delivery_path.write_text("{bad json", encoding="utf-8")
        malformed_delivery = subprocess.run([sys.executable, str(SCRIPTS / "validate_package.py"), str(malformed_delivery_path), "--delivery"],
                                            capture_output=True, encoding="utf-8")
        self.assertEqual(malformed_delivery.returncode, 2)
        self.assertEqual(json.loads(malformed_delivery.stdout)["scope"], "delivery")
        absent = subprocess.run([sys.executable, str(SCRIPTS / "validate_package.py"), str(self.root / "不存在.json")],
                                 capture_output=True, encoding="utf-8")
        self.assertEqual(absent.returncode, 2)
        self.assertIn("issues", json.loads(absent.stdout))


if __name__ == "__main__":
    unittest.main()


