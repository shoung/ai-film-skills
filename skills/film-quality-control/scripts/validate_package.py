#!/usr/bin/env python3
"""Validate the structure and audit evidence of a film package.

Passing this checker means only that the declared structure and evidence are
consistent. It does not mean that any image was visually inspected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ASSET_ROLES = {"character_card", "scene_card", "prop_card", "frame"}
GENERATION_MODES = {"T2VA", "I2VA", "FL2VA", "L2VA", "Ref2VA"}
INPUT_ROLES = {"first_frame", "last_frame", "identity_reference", "scene_reference", "prop_reference", "composition_reference"}
REFERENCE_ROLES = INPUT_ROLES - {"first_frame", "last_frame"}
REVIEW_CHECKS = ("identity", "wardrobe", "makeup", "scene", "continuity", "prompt_alignment")
TIMING_CHECKS = ("dialogue_alignment", "delivery_feasibility", "pace_balance")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _issue(severity: str, code: str, target: str, message: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "target": target, "message": message}


def generation_signature(generation: dict[str, Any]) -> str:
    """Return a stable SHA-256 for the prompt and timing inputs reviewed by QA."""
    if not isinstance(generation, dict):
        raise TypeError("generation must be a mapping")
    payload = {key: generation.get(key) for key in ("prompt", "duration_seconds", "shot_ids")}
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _list_field(data: dict[str, Any], key: str, issues: list[dict[str, str]]) -> list[Any]:
    value = data.get(key, [])
    if not isinstance(value, list):
        issues.append(_issue("error", "INVALID_TYPE", key, f"{key} 必須是陣列。"))
        return []
    return value


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _resolve_package_path(base_dir: Path, value: Any) -> Path | None:
    if not _nonempty_str(value):
        return None
    try:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (base_dir / path).resolve()
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


def _has_affirmative_cut(prompt: str) -> bool:
    # H3 dialogue blocks contain literal spoken words, not camera directives.
    text = re.sub(r"<d\b[^>]*>.*?</d\s*>", " ", prompt, flags=re.IGNORECASE | re.DOTALL).casefold()
    # A second explicitly numbered Shot is strong evidence of a concealed cut.
    shot_numbers = set(re.findall(r"\bshot\s*#?\s*(\d+)\b", text, flags=re.IGNORECASE))
    if len(shot_numbers) > 1:
        return True
    patterns = (
        r"切鏡|切到|切至|切換到|切換至|插鏡|反打|蒙太奇|跳切|轉場|轉至|再切回",
        r"\b(?:jump\s*cuts?|cut\s+(?:to|back|away)|cuts\s+(?:to|back|away)|reverse\s+(?:shot|angle)|insert\s+shot|montage|match\s+cut)\b",
    )
    negative_prefix = re.compile(
        r"(?:不要(?:有|任何)?|不可(?:有|任何)?|不得(?:有|任何)?|避免(?:任何)?|無(?:任何)?|不|禁止|勿|"
        r"no\s+(?:(?:any\s+)?(?:jump|reverse|insert)\s+)?|without\s+(?:(?:any\s+)?(?:jump|reverse|insert)\s+)?|"
        r"don't\s+|do\s+not\s+|avoid(?:\s+any)?\s+)$"
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            prefix = text[max(0, match.start() - 48):match.start()]
            if negative_prefix.search(prefix):
                continue
            return True
    return False


def validate_package(data: dict, base_dir: Path, delivery: bool = False) -> list[dict]:
    """Return machine-readable issues for a package mapping.

    Paths declared in the package are interpreted relative to ``base_dir``.
    This function validates metadata and evidence only; it never inspects image
    pixels or claims that visual review took place.
    """
    issues: list[dict[str, str]] = []
    if not isinstance(data, dict):
        return [_issue("error", "INVALID_TYPE", "$", "package 根節點必須是 JSON 物件。")]
    try:
        root = Path(base_dir).resolve()
    except (TypeError, ValueError, OSError):
        root = Path.cwd().resolve()
        issues.append(_issue("error", "INVALID_BASE_DIR", "$", "package 根目錄無效。"))

    assets_raw = _list_field(data, "assets", issues)
    shots_raw = _list_field(data, "shots", issues)
    generations_raw = _list_field(data, "generations", issues)
    reviews_raw = _list_field(data, "reviews", issues)

    assets: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(assets_raw):
        target = f"assets[{index}]"
        if not isinstance(item, dict):
            issues.append(_issue("error", "INVALID_TYPE", target, "資產必須是物件。"))
            continue
        asset_id = item.get("id")
        if not _nonempty_str(asset_id):
            issues.append(_issue("error", "INVALID_ID", target, "資產 id 必須是非空字串。"))
            continue
        if asset_id in assets:
            issues.append(_issue("error", "DUPLICATE_ID", target, f"重複資產 id：{asset_id}"))
            continue
        assets[asset_id] = item
        if not isinstance(item.get("role"), str) or item.get("role") not in ASSET_ROLES:
            issues.append(_issue("error", "INVALID_ASSET_ROLE", f"{target}.role", "未知的資產 role。"))
        for required in ("path", "version", "sha256"):
            if not _nonempty_str(item.get(required)):
                issues.append(_issue("error", "MISSING_ASSET_FIELD", f"{target}.{required}", f"資產缺少有效的 {required}。"))
        if item.get("role") == "frame" and not _nonempty_str(item.get("producer_id")):
            issues.append(_issue("error", "MISSING_PRODUCER", f"{target}.producer_id", "正式 frame 必須記錄 producer_id。"))
        if "sha256" in item and (not isinstance(item.get("sha256"), str) or not SHA256_RE.fullmatch(item["sha256"])):
            issues.append(_issue("error", "INVALID_SHA256", f"{target}.sha256", "資產 sha256 必須是 64 位十六進位字串。"))
        if delivery:
            if isinstance(item.get("role"), str) and item.get("role") in {"character_card", "scene_card", "prop_card"} and item.get("approved") is not True:
                issues.append(_issue("error", "CARD_NOT_APPROVED", target, "正式角色、場景或道具卡必須 approved=true。"))
            path = _resolve_package_path(root, item.get("path"))
            if path is None:
                issues.append(_issue("error", "INVALID_ASSET_PATH", f"{target}.path", "資產路徑必須是有效的相對或絕對路徑。"))
            elif not path.is_file():
                issues.append(_issue("error", "ASSET_MISSING", target, "宣告的資產檔案不存在。"))
            elif not SHA256_RE.fullmatch(str(item.get("sha256", ""))):
                issues.append(_issue("error", "INVALID_SHA256", f"{target}.sha256", "資產 sha256 必須是 64 位十六進位字串。"))
            else:
                try:
                    actual = hashlib.sha256(path.read_bytes()).hexdigest()
                except OSError as exc:
                    issues.append(_issue("error", "ASSET_READ_ERROR", target, f"無法讀取資產檔案：{exc}"))
                else:
                    if actual.lower() != item["sha256"].lower():
                        issues.append(_issue("error", "ASSET_HASH_MISMATCH", target, "檔案 SHA-256 與宣告值不一致。"))

    shots: dict[str, dict[str, Any]] = {}
    ordered_shots: list[dict[str, Any]] = []
    for index, item in enumerate(shots_raw):
        target = f"shots[{index}]"
        if not isinstance(item, dict):
            issues.append(_issue("error", "INVALID_TYPE", target, "鏡頭必須是物件。"))
            continue
        shot_id = item.get("id")
        if not _nonempty_str(shot_id):
            issues.append(_issue("error", "INVALID_ID", target, "鏡頭 id 必須是非空字串。"))
            continue
        if shot_id in shots:
            issues.append(_issue("error", "DUPLICATE_ID", target, f"重複鏡頭 id：{shot_id}"))
            continue
        shots[shot_id] = item
        ordered_shots.append(item)
        frame_id = item.get("frame_asset_id")
        if frame_id is not None:
            asset = assets.get(frame_id) if isinstance(frame_id, str) else None
            if asset is None:
                issues.append(_issue("error", "BROKEN_LINK", f"{target}.frame_asset_id", "frame_asset_id 未連結到已宣告資產。"))
            elif asset.get("role") != "frame":
                issues.append(_issue("error", "WRONG_ASSET_ROLE", f"{target}.frame_asset_id", "shot 靜幀必須連到 role=frame 資產。"))
        additional_frames = item.get("additional_frame_asset_ids", [])
        if not isinstance(additional_frames, list):
            issues.append(_issue("error", "INVALID_TYPE", f"{target}.additional_frame_asset_ids", "additional_frame_asset_ids 必須是陣列。"))
        else:
            seen_frames = {frame_id} if isinstance(frame_id, str) else set()
            for additional_index, additional_id in enumerate(additional_frames):
                additional_target = f"{target}.additional_frame_asset_ids[{additional_index}]"
                if not isinstance(additional_id, str) or additional_id not in assets:
                    issues.append(_issue("error", "BROKEN_LINK", additional_target, f"無效 additional frame 連結：{additional_id}"))
                elif assets[additional_id].get("role") != "frame":
                    issues.append(_issue("error", "WRONG_ASSET_ROLE", additional_target, "additional frame 必須連到 role=frame 資產。"))
                elif additional_id in seen_frames:
                    issues.append(_issue("error", "DUPLICATE_FRAME_LINK", additional_target, "同一 shot 不可重複綁定同一張 frame。"))
                else:
                    seen_frames.add(additional_id)
        refs = item.get("reference_asset_ids", [])
        if not isinstance(refs, list):
            issues.append(_issue("error", "INVALID_TYPE", f"{target}.reference_asset_ids", "reference_asset_ids 必須是陣列。"))
        else:
            for ref_id in refs:
                if not isinstance(ref_id, str) or ref_id not in assets:
                    issues.append(_issue("error", "BROKEN_LINK", f"{target}.reference_asset_ids", f"無效參考資產連結：{ref_id}"))
        duration = item.get("duration_seconds")
        if duration is not None and (isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0):
            issues.append(_issue("error", "INVALID_DURATION", f"{target}.duration_seconds", "duration_seconds 必須是正數。"))

    generation_ids: set[str] = set()
    for index, item in enumerate(generations_raw):
        target = f"generations[{index}]"
        if not isinstance(item, dict):
            issues.append(_issue("error", "INVALID_TYPE", target, "generation 必須是物件。"))
            continue
        gen_id = item.get("id")
        if not _nonempty_str(gen_id):
            issues.append(_issue("error", "INVALID_ID", target, "generation id 必須是非空字串。"))
        elif gen_id in generation_ids:
            issues.append(_issue("error", "DUPLICATE_ID", target, f"重複 generation id：{gen_id}"))
        else:
            generation_ids.add(gen_id)
        mode = item.get("mode")
        if not isinstance(mode, str) or mode not in GENERATION_MODES:
            issues.append(_issue("error", "INVALID_MODE", f"{target}.mode", "未知的生成模式。"))
        shot_ids = item.get("shot_ids")
        if not isinstance(shot_ids, list) or not shot_ids:
            issues.append(_issue("error", "INVALID_SHOT_IDS", f"{target}.shot_ids", "shot_ids 必須是非空陣列。"))
            shot_ids = []
        for shot_id in shot_ids:
            if not isinstance(shot_id, str) or shot_id not in shots:
                issues.append(_issue("error", "BROKEN_LINK", f"{target}.shot_ids", f"無效 shot 連結：{shot_id}"))
        if isinstance(mode, str) and mode in {"I2VA", "FL2VA", "L2VA"} and len(shot_ids) != 1:
            issues.append(_issue("error", "SINGLE_SHOT_MODE", f"{target}.shot_ids", f"{mode} 必須只綁定一個 shot。"))
        inputs = item.get("image_inputs", [])
        if not isinstance(inputs, list):
            issues.append(_issue("error", "INVALID_TYPE", f"{target}.image_inputs", "image_inputs 必須是陣列。"))
            inputs = []
        input_roles: list[str] = []
        for input_index, input_item in enumerate(inputs):
            input_target = f"{target}.image_inputs[{input_index}]"
            if not isinstance(input_item, dict):
                issues.append(_issue("error", "INVALID_TYPE", input_target, "圖片輸入必須是物件。"))
                continue
            role = input_item.get("role")
            if not isinstance(role, str) or role not in INPUT_ROLES:
                issues.append(_issue("error", "INVALID_INPUT_ROLE", f"{input_target}.role", "未知的圖片用途。"))
            else:
                input_roles.append(role)
            asset_id = input_item.get("asset_id")
            if not isinstance(asset_id, str) or asset_id not in assets:
                issues.append(_issue("error", "BROKEN_LINK", f"{input_target}.asset_id", "圖片輸入未連結到已宣告資產。"))
        if mode == "T2VA" and inputs:
            issues.append(_issue("error", "T2VA_HAS_IMAGES", f"{target}.image_inputs", "T2VA 不可帶圖片輸入。"))
        expected_roles = {"I2VA": ["first_frame"], "FL2VA": ["first_frame", "last_frame"], "L2VA": ["last_frame"]}
        if isinstance(mode, str) and mode in expected_roles and sorted(input_roles) != sorted(expected_roles[mode]):
            issues.append(_issue("error", "FRAME_INPUT_MISMATCH", f"{target}.image_inputs", f"{mode} 必須恰好使用相符的首幀／尾幀輸入，不可混入其他圖片用途。"))
        if mode == "Ref2VA":
            if not input_roles:
                issues.append(_issue("error", "REFERENCE_INPUT_MISSING", f"{target}.image_inputs", "Ref2VA 至少需要一張參考圖片。"))
            elif any(role not in REFERENCE_ROLES for role in input_roles):
                issues.append(_issue("error", "REFERENCE_INPUT_MISMATCH", f"{target}.image_inputs", "Ref2VA 必須使用參考用途，不能使用首幀或尾幀用途。"))
        compatible_assets = {
            "first_frame": {"frame"}, "last_frame": {"frame"},
            "identity_reference": {"character_card"}, "scene_reference": {"scene_card"},
            "prop_reference": {"prop_card"}, "composition_reference": {"frame", "scene_card"},
        }
        for input_index, input_item in enumerate(inputs):
            if not isinstance(input_item, dict):
                continue
            role = input_item.get("role")
            asset_id = input_item.get("asset_id")
            asset = assets.get(asset_id) if isinstance(asset_id, str) else None
            if isinstance(role, str) and role in compatible_assets and asset is not None:
                asset_role = asset.get("role")
                if not isinstance(asset_role, str) or asset_role not in compatible_assets[role]:
                    issues.append(_issue("error", "INPUT_ASSET_ROLE_MISMATCH", f"{target}.image_inputs[{input_index}]", f"圖片用途 {role} 與資產 role {asset_role} 不相容。"))
        duration = item.get("duration_seconds")
        if "duration_seconds" in item or delivery:
            if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
                issues.append(_issue("error", "GENERATION_DURATION_INVALID", f"{target}.duration_seconds", "交付 generation 必須有正數 duration_seconds。"))
        producer_id = item.get("producer_id")
        if "producer_id" in item and not _nonempty_str(producer_id):
            issues.append(_issue("error", "INVALID_PRODUCER", f"{target}.producer_id", "generation producer_id 必須是非空字串。"))
        if delivery and not _nonempty_str(producer_id):
            issues.append(_issue("error", "GENERATION_PRODUCER_MISSING", f"{target}.producer_id", "交付 generation 必須記錄 producer_id。"))
        prompt = item.get("prompt")
        if not isinstance(prompt, str):
            issues.append(_issue("error", "INVALID_TYPE", f"{target}.prompt", "prompt 必須是字串。"))
        elif isinstance(mode, str) and mode in {"I2VA", "FL2VA", "L2VA"} and _has_affirmative_cut(prompt):
            issues.append(_issue("error", "PROMPT_CONTAINS_CUT", f"{target}.prompt", "提示詞疑似要求同一生成任務中切鏡；請人工閱讀完整提示詞確認。"))
        timing = item.get("timing_review")
        timing_severity = "error" if delivery else "warning"
        if not isinstance(timing, dict):
            issues.append(_issue(timing_severity, "TIMING_REVIEW_MISSING", f"{target}.timing_review", "每個交付 generation 都需要逐 prompt 時間與台詞 QA 紀錄。"))
            continue
        if timing.get("reviewer_role") != "independent_qa":
            issues.append(_issue(timing_severity, "TIMING_REVIEWER_ROLE_INVALID", f"{target}.timing_review.reviewer_role", "timing reviewer_role 必須是 independent_qa。"))
        timing_reviewer = timing.get("reviewer_id")
        if not _nonempty_str(timing_reviewer):
            issues.append(_issue(timing_severity, "TIMING_REVIEWER_MISSING", f"{target}.timing_review.reviewer_id", "timing review 必須記錄 reviewer_id。"))
        elif delivery and timing_reviewer == producer_id:
            issues.append(_issue("error", "TIMING_REVIEWER_NOT_INDEPENDENT", f"{target}.timing_review.reviewer_id", "generation producer 不可審核自己的時間與台詞。"))
        if timing.get("status") != "pass":
            issues.append(_issue(timing_severity, "TIMING_REVIEW_NOT_PASS", f"{target}.timing_review.status", "timing review 尚未 pass。"))
        timing_checks = timing.get("checks", {})
        if not isinstance(timing_checks, dict):
            issues.append(_issue(timing_severity, "TIMING_CHECKS_INVALID", f"{target}.timing_review.checks", "timing checks 必須是物件。"))
        else:
            for timing_check in TIMING_CHECKS:
                if timing_checks.get(timing_check) != "pass":
                    issues.append(_issue(timing_severity, "TIMING_CHECK_NOT_PASS", f"{target}.timing_review.checks.{timing_check}", f"timing check {timing_check} 必須 pass。"))
        timing_evidence = timing.get("evidence", [])
        if not isinstance(timing_evidence, list) or not timing_evidence:
            issues.append(_issue(timing_severity, "TIMING_EVIDENCE_MISSING", f"{target}.timing_review.evidence", "timing review 必須列出至少一份 evidence。"))
        elif delivery:
            for evidence_path in timing_evidence:
                resolved = _resolve_package_path(root, evidence_path)
                if resolved is None or not resolved.is_file():
                    issues.append(_issue("error", "TIMING_EVIDENCE_MISSING", f"{target}.timing_review.evidence", "timing review evidence 檔案不存在或路徑無效。"))
        signature = timing.get("generation_sha256")
        try:
            current_signature = generation_signature(item)
        except (TypeError, ValueError, OverflowError):
            current_signature = None
        if not isinstance(signature, str) or not SHA256_RE.fullmatch(signature) or signature != current_signature:
            issues.append(_issue(timing_severity, "TIMING_REVIEW_STALE", f"{target}.timing_review.generation_sha256", "timing review 必須綁定目前 prompt、duration_seconds 與 shot_ids 的 SHA-256。"))

    review_ids: set[str] = set()
    reviews_by_frame: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for index, item in enumerate(reviews_raw):
        target = f"reviews[{index}]"
        if not isinstance(item, dict):
            issues.append(_issue("error", "INVALID_TYPE", target, "review 必須是物件。"))
            continue
        review_id = item.get("id")
        if not _nonempty_str(review_id):
            issues.append(_issue("error", "INVALID_ID", target, "review id 必須是非空字串。"))
        elif review_id in review_ids:
            issues.append(_issue("error", "DUPLICATE_ID", target, f"重複 review id：{review_id}"))
        else:
            review_ids.add(review_id)
        shot_id = item.get("shot_id")
        shot = shots.get(shot_id) if isinstance(shot_id, str) else None
        if shot is None:
            issues.append(_issue("error", "BROKEN_LINK", f"{target}.shot_id", "review 未連結到已宣告 shot。"))
        explicit_frame_id = item.get("frame_asset_id")
        if explicit_frame_id is not None:
            explicit_frame = assets.get(explicit_frame_id) if isinstance(explicit_frame_id, str) else None
            if explicit_frame is None or explicit_frame.get("role") != "frame":
                issues.append(_issue("error", "BROKEN_LINK", f"{target}.frame_asset_id", "review frame_asset_id 必須連結到 role=frame 資產。"))
            elif shot is not None:
                shot_frame_ids = [shot.get("frame_asset_id")]
                additional = shot.get("additional_frame_asset_ids", [])
                if isinstance(additional, list):
                    shot_frame_ids.extend(additional)
                if explicit_frame_id not in shot_frame_ids:
                    issues.append(_issue("error", "REVIEW_FRAME_MISMATCH", f"{target}.frame_asset_id", "review 的 frame 必須屬於所連結 shot 的正式靜幀序列。"))
        review_severity = "error" if delivery else "warning"
        if item.get("reviewer_role") != "independent_qa":
            issues.append(_issue(review_severity, "INVALID_REVIEWER_ROLE", f"{target}.reviewer_role", "reviewer_role 必須是 independent_qa。"))
        if item.get("status") != "pass":
            status_code = "REVIEW_NOT_PASS" if delivery else ("REVIEW_PENDING" if item.get("status") == "pending" else "REVIEW_INCOMPLETE")
            issues.append(_issue(review_severity, status_code, f"{target}.status", "review 尚未通過；只有 delivery 階段的 pass 紀錄可作為通過證據。"))
        viewed = item.get("viewed_assets", {})
        if not isinstance(viewed, dict):
            issues.append(_issue(review_severity, "INVALID_TYPE", f"{target}.viewed_assets", "viewed_assets 必須是物件。"))
            viewed = {}
        for viewed_id, viewed_hash in viewed.items():
            if not isinstance(viewed_id, str) or not isinstance(viewed_hash, str) or not SHA256_RE.fullmatch(viewed_hash):
                issues.append(_issue("error", "INVALID_SHA256", f"{target}.viewed_assets.{viewed_id}", "viewed_assets 的每個 SHA 必須是 64 位十六進位字串。"))
        neighbors = item.get("neighbor_frames", {})
        if not isinstance(neighbors, dict):
            issues.append(_issue(review_severity, "INVALID_TYPE", f"{target}.neighbor_frames", "neighbor_frames 必須是物件。"))
            neighbors = {}
        for neighbor_id, neighbor_hash in neighbors.items():
            if not isinstance(neighbor_id, str) or not isinstance(neighbor_hash, str) or not SHA256_RE.fullmatch(neighbor_hash):
                issues.append(_issue("error", "INVALID_SHA256", f"{target}.neighbor_frames.{neighbor_id}", "neighbor_frames 的每個 SHA 必須是 64 位十六進位字串。"))
        if "frame_sha256" in item and (not isinstance(item.get("frame_sha256"), str) or not SHA256_RE.fullmatch(item["frame_sha256"])):
            issues.append(_issue("error", "INVALID_SHA256", f"{target}.frame_sha256", "review frame_sha256 必須是 64 位十六進位字串。"))
        elif "frame_sha256" not in item:
            issues.append(_issue(review_severity, "MISSING_REVIEW_HASH", f"{target}.frame_sha256", "review 尚未記錄 frame_sha256。"))
        checks = item.get("checks", {})
        if not isinstance(checks, dict):
            issues.append(_issue(review_severity, "INVALID_TYPE", f"{target}.checks", "checks 必須是物件。"))
            checks = {}
        for check in REVIEW_CHECKS:
            value = checks.get(check)
            if value == "pass":
                continue
            if isinstance(value, dict) and value.get("status") == "not_applicable" and _nonempty_str(value.get("reason")):
                continue
            issues.append(_issue(review_severity, "CHECK_NOT_PASSED", f"{target}.checks.{check}", "必備檢查必須 pass，或以具體理由標記 not_applicable。"))
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list) or not evidence:
            issues.append(_issue(review_severity, "MISSING_EVIDENCE", f"{target}.evidence", "review 必須列出至少一份 evidence 檔案。"))
        elif delivery:
            for evidence_path in evidence:
                resolved = _resolve_package_path(root, evidence_path)
                if resolved is None:
                    issues.append(_issue("error", "INVALID_EVIDENCE_PATH", f"{target}.evidence", "evidence 路徑必須是有效的相對或絕對路徑。"))
                elif not resolved.is_file():
                    issues.append(_issue("error", "EVIDENCE_MISSING", f"{target}.evidence", "review evidence 檔案不存在。"))

        if delivery and shot is not None:
            frame_id = item.get("frame_asset_id", shot.get("frame_asset_id"))
            if frame_id is None:
                frame_id = shot.get("frame_asset_id")
            frame = assets.get(frame_id) if isinstance(frame_id, str) else None
            shot_frame_ids = []
            primary_id = shot.get("frame_asset_id")
            if isinstance(primary_id, str):
                shot_frame_ids.append(primary_id)
            additional_ids = shot.get("additional_frame_asset_ids", [])
            if isinstance(additional_ids, list):
                shot_frame_ids.extend(additional_id for additional_id in additional_ids if isinstance(additional_id, str))
            if frame is None or frame.get("role") != "frame":
                issues.append(_issue("error", "REVIEW_FRAME_MISSING", target, "review 對應 shot 必須有正式 frame。"))
            elif frame_id not in shot_frame_ids:
                issues.append(_issue("error", "REVIEW_FRAME_MISMATCH", f"{target}.frame_asset_id", "review 的 frame 必須屬於所連結 shot 的正式靜幀序列。"))
            else:
                reviews_by_frame.setdefault((shot_id, frame_id), []).append(item)
                if item.get("frame_sha256") != frame.get("sha256"):
                    issues.append(_issue("error", "REVIEW_FRAME_STALE", f"{target}.frame_sha256", "review 的 frame SHA 與目前正式 frame 不一致。"))
                producer = frame.get("producer_id")
                reviewer = item.get("reviewer_id")
                if not _nonempty_str(producer) or not _nonempty_str(reviewer):
                    issues.append(_issue("error", "REVIEWER_IDENTITY_MISSING", target, "frame producer_id 與 reviewer_id 必須明確提供。"))
                elif reviewer == producer:
                    issues.append(_issue("error", "SELF_REVIEW", target, "frame producer 不可審核自己的靜幀。"))
                references = shot.get("reference_asset_ids", []) if isinstance(shot.get("reference_asset_ids", []), list) else []
                current_cards = {card_id: assets[card_id] for card_id in references
                                 if isinstance(card_id, str) and card_id in assets
                                 and isinstance(assets[card_id].get("role"), str)
                                 and assets[card_id].get("role") in {"character_card", "scene_card", "prop_card"}}
                for card_id, card in current_cards.items():
                    if viewed.get(card_id) != card.get("sha256"):
                        issues.append(_issue("error", "REVIEW_CARD_STALE", target, f"review 未記錄目前正式卡 {card_id} 的正確 SHA。"))
                # Reject extra or outdated review references too; they cannot stand in for current assets.
                for viewed_id, viewed_hash in viewed.items():
                    current = assets.get(viewed_id)
                    if current is None or viewed_hash != current.get("sha256"):
                        issues.append(_issue("error", "REVIEW_ASSET_STALE", target, f"review 引用的資產 {viewed_id} 不存在或已改版。"))

    if delivery:
        for shot_index, shot in enumerate(ordered_shots):
            frame_ids: list[Any] = []
            primary = shot.get("frame_asset_id")
            if primary is not None:
                frame_ids.append(primary)
            additional = shot.get("additional_frame_asset_ids", [])
            if isinstance(additional, list):
                frame_ids.extend(additional)
            has_formal_frame = any(isinstance(frame_id, str) and frame_id in assets and assets[frame_id].get("role") == "frame"
                                   for frame_id in frame_ids)
            if not has_formal_frame:
                continue
            references = shot.get("reference_asset_ids", [])
            has_formal_card = isinstance(references, list) and any(
                isinstance(ref_id, str) and ref_id in assets
                and isinstance(assets[ref_id].get("role"), str)
                and assets[ref_id].get("role") in {"character_card", "scene_card", "prop_card"}
                for ref_id in references
            )
            if not has_formal_card:
                issues.append(_issue("error", "MISSING_FORMAL_REFERENCE", f"shots[{shot_index}].reference_asset_ids", "有正式 frame 的 shot 至少需要綁定一張正式角色、場景或道具卡作為審核依據。"))
        frame_sequence: list[tuple[int, str, str]] = []
        for shot_index, shot in enumerate(ordered_shots):
            shot_id = shot.get("id")
            frame_ids: list[Any] = []
            primary = shot.get("frame_asset_id")
            if primary is not None:
                frame_ids.append(primary)
            additional = shot.get("additional_frame_asset_ids", [])
            if isinstance(additional, list):
                frame_ids.extend(additional)
            for frame_id in frame_ids:
                if isinstance(frame_id, str) and frame_id in assets and assets[frame_id].get("role") == "frame":
                    frame_sequence.append((shot_index, shot_id, frame_id))
        bound_frames = {frame_id for _, _, frame_id in frame_sequence}
        for asset_id, asset in assets.items():
            if asset.get("role") == "frame" and asset_id not in bound_frames:
                issues.append(_issue("error", "ORPHAN_FRAME", f"assets.{asset_id}", "正式 frame 必須由 shot primary 或 additional frame 欄位綁定。"))
        for position, (shot_index, shot_id, frame_id) in enumerate(frame_sequence):
            frame_reviews = reviews_by_frame.get((shot_id, frame_id), [])
            if not frame_reviews:
                issues.append(_issue("error", "MISSING_REVIEW", f"shots[{shot_index}].frame:{frame_id}", "每張正式 frame 都需要至少一份有效 review。"))
            expected_neighbors: dict[str, str] = {}
            if position > 0:
                previous = assets.get(frame_sequence[position - 1][2])
                if previous is not None:
                    expected_neighbors[previous.get("id")] = previous.get("sha256")
            if position + 1 < len(frame_sequence):
                following = assets.get(frame_sequence[position + 1][2])
                if following is not None:
                    expected_neighbors[following.get("id")] = following.get("sha256")
            for review in frame_reviews:
                neighbors = review.get("neighbor_frames", {})
                if not isinstance(neighbors, dict):
                    continue
                for neighbor_id, neighbor_hash in expected_neighbors.items():
                    if neighbors.get(neighbor_id) != neighbor_hash:
                        issues.append(_issue("error", "NEIGHBOR_REVIEW_STALE", f"reviews.{review.get('id')}.neighbor_frames", f"前後最近靜幀 {neighbor_id} 缺少正確 SHA 記錄。"))
                for neighbor_id, neighbor_hash in neighbors.items():
                    current = assets.get(neighbor_id)
                    if current is None or current.get("role") != "frame" or current.get("sha256") != neighbor_hash:
                        issues.append(_issue("error", "NEIGHBOR_REVIEW_STALE", f"reviews.{review.get('id')}.neighbor_frames", f"鄰鏡靜幀 {neighbor_id} 已改版或無效。"))
    return issues


def _write_json(payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    stream = getattr(sys.stdout, "buffer", None)
    if stream is not None:
        stream.write(encoded)
        stream.flush()
    else:
        sys.stdout.write(encoded.decode("utf-8"))


def _cli_error(message: str, delivery: bool = False) -> int:
    payload = {"ok": False, "scope": "delivery" if delivery else "structure",
               "issues": [_issue("error", "PACKAGE_READ_ERROR", "$", message)]}
    _write_json(payload)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate film package structure and audit evidence.")
    parser.add_argument("package_json", help="package.json 路徑")
    parser.add_argument("--delivery", action="store_true", help="執行交付階段檢查")
    args = parser.parse_args(argv)
    package_path = Path(args.package_json)
    try:
        raw = package_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        return _cli_error(f"無法讀取 package：{exc}", delivery=args.delivery)
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeError) as exc:
        return _cli_error(f"package JSON 格式錯誤：{exc}", delivery=args.delivery)
    issues = validate_package(data, package_path.resolve().parent, delivery=args.delivery)
    payload = {"ok": not any(issue["severity"] == "error" for issue in issues),
               "scope": "delivery" if args.delivery else "structure", "issues": issues}
    _write_json(payload)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

