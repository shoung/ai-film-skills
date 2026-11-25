---
name: dialogue-expert
description: "逐句診斷劇本臺詞的七個維度，提供改寫理由、替換清單與角色語言辨識度分析。"
---

# 臺詞專家

本次對話首次使用時，由主代理依 [版本檢查](../screenplay-director/references/skill-update-check.md) 核對一次。單獨安裝時，以實際安裝的 Git 提交或 `.ai-film-skills-revision` 比對 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)。有新版先確認是否更新，無法驗證則簡述後繼續。

## 依委託選診斷範圍

收到台詞診斷或改寫委託後，依 [七維診斷與交付](references/dialogue-diagnosis.md) 執行。劇本是分析材料，單純提供劇本不會自動啟動診斷。按指定場、角色、維度或全稿處理，明確寫下已覆蓋的範圍。結構尚在調整時，依委託做局部試調；總控的全量潤稿在結構鎖定後進行。

台詞分析、替換理由及實質改寫依 [antigravity-writer](../antigravity-writer/SKILL.md) 分流。單獨安裝時用 [寫作備援](references/writer-fallback.md)。

引用原句，讓每項問題和替換理由可回查場次與維度。鎖定台詞的修改留在候選清單，採納、更新鎖稿後才可進入正式版本。需要調整因果、人物關係或場次結構時，標明影響並轉 [劇本醫生](../screenplay-doctor/SKILL.md)；只將已採納的替換交 [劇本寫作](../screenplay-writing/SKILL.md) 整合。報告以繁體中文撰寫，保留原台詞語言、口音與字詞。接受繁簡同義指令。

AI 配音、TTS 或影片生成用途依 [配音標點與氣口](references/dialogue-diagnosis.md#配音標點與氣口) 核對。要核實影片提示詞可行時長，依 [影像品管](../film-quality-control/references/timing-and-dialogue.md) 進行，缺少獨立證據時如實標示。

原始流程署名 Elio_AIGC（抖音／B 站）。[原始台詞診斷](<references/4.臺詞專家 · 全量診斷 Skill v1.0.txt>) 為歷史資料，現行任務依本入口與其現行規範執行。
