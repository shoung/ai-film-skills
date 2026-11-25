---
name: h3-prompt-writing
description: "Write MiniMax H3 video generation prompts for T2VA, I2VA, FL2VA, L2VA, and Ref2VA. Use when rewriting multimodal requests into H3 prompt structures, composing integrated_multimodal_description, overall_soundscape, and non_diegetic_music, aligning keyframes, or defining reference labels for images, videos, and audio."
---

# H3 Prompt Writing

本次對話首次使用時，由主代理依 [版本檢查](../screenplay-director/references/skill-update-check.md) 核對一次。單獨安裝時，以實際安裝的 Git 提交或 `.ai-film-skills-revision` 比對 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)。有新版先確認是否更新，無法驗證則簡述後繼續。

新創作任務沿用 [screenplay-director 共用啟動 intake](../screenplay-director/references/startup-intake.md) 與已知決策，僅關鍵阻礙補問（每輪最多 2–3 題）。缺少共用 intake 時，全新案在對話中顯示一次 `SHOUNG`；續作、維護、交接不重複，標記不進 prompt。純文字不要求生圖；交付生成靜幀依 [film-quality-control](../film-quality-control/SKILL.md) 獨立看圖對卡，無審核者標待審，不偽造 PASS。

## 選擇交付

- **八欄分鏡表**。使用 [格式](references/storyboard-table-format.md) 與 [模板](references/storyboard-table-template.md)。新編或重做鏡頭按該規範的場次拆解規則。格式轉換保留原鏡號、鏡序、設計與鎖定台詞。純製表可在模型未定時完成。
- **H3 提示詞**。先讀 [精簡格式](references/concise-format.md) 與 [表演控制](references/performance-control.md)。T2VA、I2VA、FL2VA、L2VA 依 [基礎模式指南](references/base-en.txt)，Ref2VA 依 [全參考指南](references/ref-en.txt)。各模式的欄位、段序、標籤及時間戳以選定指南為準。按需查 [合成範例](references/format-example.md)。

## 撰寫與交付

新編或重做分鏡、實質撰寫或修訂提示詞，依 [antigravity-writer](../antigravity-writer/SKILL.md) 分流。單獨安裝時用 [寫作備援](references/writer-fallback.md)。純格式轉換直接處理。

依 [精簡格式的模式與分組規則](references/concise-format.md#模式與分組) 選模式。跨場或跨集持續的變化查 [資產連續性](../film-quality-control/references/asset-continuity.md)，單獨安裝時從劇本、核准卡與前場備註確認本鏡有效狀態。參考圖規劃依 [掛圖規範](../film-quality-control/references/reference-control.md)，製作旁表區分計畫和實際附件。

可提交版依 [雙軌審核](../film-quality-control/references/prompt-review.md) 執行。適用的獨立審核者先盲審請求與實際附件，再讀全劇資料審查分組、鏡頭覆蓋、台詞與時長。依 [鎖定台詞核對](../film-quality-control/references/locked-dialogue-reconciliation.md) 把劇本、分鏡逐句對回實際正文的 `<d>` 與說話者標記。缺共用規範時，仍核對說話者、原文、順序、跨鏡銜接和可行秒數。缺獨立證據標待審。已要求且實際生成的 1080p 單幀另做 [空間核對](../film-quality-control/references/visual-qa.md#空間核對與示意圖)。
