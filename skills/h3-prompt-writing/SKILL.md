---
name: h3-prompt-writing
description: Write MiniMax H3 video generation prompts for T2VA, I2VA, FL2VA, L2VA, and Ref2VA. Use when rewriting multimodal requests into H3 prompt structures, composing integrated_multimodal_description, overall_soundscape, and non_diegetic_music, aligning keyframes, or defining reference labels for images, videos, and audio.
---

# H3 Prompt Writing

Portable to any agent that can read local files — no external API calls, MiniMax Hub tools, or proprietary runtime required. The agents/openai.yaml file only adds optional ChatGPT/Codex UI metadata; it does not restrict the skill to OpenAI agents.

Before delivering generation prompts, an actual independent read-only reviewer must compare source dialogue with each prompt and assess speech length/rate, pauses, emotional beats, action timing, and concurrency against its requested duration. Read [dialogue and duration QA](../film-quality-control/references/timing-and-dialogue.md). This also applies to text-only prompts; it does not require generating images, audio, or video. If the shared guide is absent, apply those checks and record assumptions; if no independent reviewer is available, mark timing QA pending. Do not claim audio measurement from text estimates. Keep timing-review records outside H3's required prompt fields, and re-review changes instead of silently trimming locked dialogue.

For a new creative task, reuse the shared [screenplay-director startup intake](../screenplay-director/references/startup-intake.md), if installed. Carry forward known story, asset, and mode decisions; ask only for missing information that materially blocks this request, in rounds of no more than 2–3 questions. Without that shared file, show `SHOUNG` once in the conversation only for a genuinely new project; do not repeat it for sequels, maintenance, or handoffs, and never put it in prompts or media. Text-only prompt or storyboard work does not require image generation. Any generated still delivered with the work requires an independent QA agent to inspect the actual image against approved character (including makeup and wardrobe), scene, and prop cards and available neighboring frames, following [film-quality-control](../film-quality-control/SKILL.md). If that skill or an independent reviewer is unavailable, label visual QA pending; never claim PASS.

## Storyboard tables

When the user requests a storyboard table, read the local [eight-column format](references/storyboard-table-format.md) and [table template](references/storyboard-table-template.md). Use their fixed column names and order, one row per continuous shot; a generation group may cover multiple rows. For a table-only task, finish in this branch without starting the model-prompt rewrite workflow below. This production table does not replace H3's mode-specific fields, section order, dialogue syntax, or reference labels. Do not append a table when the user only requests H3 prompt text. A table's visual/frame draft must not be presented as a complete H3 audiovisual request.

## Current delivery format

Read [concise formatting and half-second timing](references/concise-format.md) first. It overrides conflicting verbosity, timing precision, and default language examples in the older guides. Use the user's requested language for prose (Traditional Chinese in this workspace); retain model field names, labels, speaker IDs and dialogue syntax. Read the [anonymized short example](references/format-example.md) for format only, not story content.


## Workflow

1. Identify the input mode: T2VA, I2VA, FL2VA, L2VA, or full-reference Ref2VA.
2. For base text/keyframe modes, read `references/base-en.txt` and follow its final prompt structure.
3. For full-reference mode, read `references/ref-en.txt` and follow its six-section rewrite format.
4. Preserve the exact field names, section order and reference/dialogue labels from the selected guide. Apply concise-format.md to timing and layout; narrative boundaries use 0.5-second increments. Keep request duration compatible with the verified interface separately.
5. Before writing or revising character performance in any mode, read [Shared Performance Control](references/performance-control.md) in full. Apply it inside the existing shot description, not as a new top-level field. This same guide also applies to Seedance; it does not replace either model's format.

For the shared one-row-per-shot and single-shot I2VA/FL2VA/L2VA policy, use [mode and shot rules](../film-quality-control/references/mode-and-shot-rules.md) when installed; this is a workflow constraint, not a claim about every model's official capability. The limits in this skill still apply if the shared QC skill is absent.

## Base Modes

- T2VA: build the full audiovisual timeline from text.
- I2VA: start from the first frame and develop forward within one continuous shot.
- FL2VA: describe one continuous shot from first frame to last frame. Do not put a cut, reverse shot, montage, or second semantic shot inside the prompt, even if the text repeats `[Shot 1]` or hides the cut in prose. A continuous camera move or focus change within the same event is still one shot.
- L2VA: infer a plausible opening and converge to the supplied last frame within one continuous shot.

If a requested I2VA, FL2VA, or L2VA sequence needs multiple shots, use T2VA or full-reference Ref2VA when appropriate, or split it into per-shot generations and edit the results together. Shot count is determined by meaning, not just the number of `[Shot N]` labels.

Use `integrated_multimodal_description`, `overall_soundscape`, and `non_diegetic_music` in the order shown in `references/base-en.txt`.

## Full-Reference Mode

Ref2VA rewrites use `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, and `non_diegetic_music` in that order. Reference labels stay consistent across all sections.

Read `references/ref-en.txt` for label rules, retention analysis, and complete examples.

## Output Rules

- Write prose in the user's requested language; preserve dialogue, lyrics, and visible scene text verbatim. English field names and control syntax remain unchanged.
- Describe each shot by composition, subjects, environment, actions, camera, sound, and the exact point where referenced content appears.
- Avoid plot summaries, unresolved reference labels, and timing that does not match the requested duration.
- Build each performance beat from the character's objective and starting state through an exact dialogue word, physical event, visible change, or sound cue into breath/pause, observable facial/body response, and an ending state. State what must not react prematurely. Emotional labels alone are insufficient.
- For a shift of attention, let the eyes acquire the target before the head follows. Select readable eyelid, mouth, jaw, shoulder, or finger cues appropriate to the framing; do not stack every cue, invent pupil trembling, or add tears without script support.
- Keep performance directions outside `<d>` and integrate their timing into `integrated_multimodal_description` (base modes) or `detailed_description` (Ref2VA). Preserve the selected guide's language, dialogue, speaker-ID, reference, and keyframe rules.

