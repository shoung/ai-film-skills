---
name: screenplay-doctor
description: "對劇本、大綱、單集、單場或單點問題進行多視角圓桌會診，產出診斷與修改任務清單。"
---

# 劇本醫生

本次對話首次使用時，由主代理依 [版本檢查](../screenplay-director/references/skill-update-check.md) 核對一次。單獨安裝時，以實際安裝的 Git 提交或 `.ai-film-skills-revision` 比對 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)。有新版先確認是否更新，無法驗證則簡述後繼續。

## 委託與範圍

收到會診委託後直接依 [圓桌會診](references/roundtable-review.md) 選對應範圍。用完整劇本做全劇會診，用現有大綱、單集、單場或單點材料做相應診斷。已有可用素材與範圍時直接開始。專案檔與對標報告可選。以繁體中文工作，接受繁簡同義指令。

會診分析、報告與修改任務清單依 [antigravity-writer](../antigravity-writer/SKILL.md) 分流。單獨安裝時用 [寫作備援](references/writer-fallback.md)。

會診涉及連載分集的開場、因果、結尾或跨集連續性時，依 [連載分集規劃與驗收](../screenplay-framework/references/serial-episode-planning.md) 核對本集局部兌現、相鄰集第一動作及鉤子紀錄。大綱階段先做因果複述。已有劇本時，先隱去解說及審查資訊讀正文，再提出問題發生的集數、場次、可見證據和修正後的複查項。原著改編另核對必留內容、來源及揭露進度。單獨安裝時用現有大綱或正文完成同樣檢查，缺件標待驗。正文由具首讀條件的獨立讀者實際讀完時，才記為獨立冷讀。由製作者執行時標記為製作者自查。

將修改目標、證據、影響範圍和保留內容交給 [劇本寫作](../screenplay-writing/SKILL.md)，由作者採納或依授權處理。圓桌角色代表分析視角；如有實際委託獨立讀者，另外記錄各自讀到的版本與範圍。

原始流程署名 Elio_AIGC（抖音／B 站）。[原始圓桌會診](<references/3.劇本醫生 · 圓桌會診 Skill v1.0.txt>) 為歷史資料，現行任務依本入口與其現行規範執行。
