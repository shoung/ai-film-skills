---
name: video-prompts
description: "根據劇本編製八欄分鏡表，或依 Seedance／MiniMax H3 格式產生影片提示詞、時間碼及角色音色；支援分鏡表建立與格式轉換。"
---

# 影片提示詞

本次對話首次使用時，由主代理依 [版本檢查](../screenplay-director/references/skill-update-check.md) 核對一次。單獨安裝時，以實際安裝的 Git 提交或 `.ai-film-skills-revision` 比對 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)。有新版先確認是否更新，無法驗證則簡述後繼續。

新創作任務沿用 [screenplay-director 共用啟動 intake](../screenplay-director/references/startup-intake.md) 與已知決策，僅關鍵資訊阻礙輸出時補問（每輪最多 2–3 題）。缺少共用 intake 時，全新案在對話中顯示一次 `SHOUNG`；續作、維護、交接不重複，標記不進 prompt。純文字不要求生圖；交付生成靜幀依 [film-quality-control](../film-quality-control/SKILL.md) 獨立看圖對卡，無審核者標待審，不偽造 PASS。

## 選擇交付

- **八欄分鏡表**。使用 [格式](references/storyboard-table-format.md) 與 [模板](references/storyboard-table-template.md)，每列一個連續鏡頭。新編或重做鏡頭先用 [分鏡方法](references/storyboard-methods.md#依劇本設計分鏡) 確立觀眾視角、因果節拍、切點與狀態承接。格式轉換沿用原鏡號、鏡序、設計和鎖定台詞，待定項如實標示。純製表可在模型未定時完成。
- **模型提示詞**。沿用已知模型，只有未確認時才詢問 Seedance 或 MiniMax H3。Seedance 讀 [素材與寫法](<references/03_Seedance 提示詞指南.md>)、[精簡格式](references/concise-format.md) 與 [表演控制](references/performance-control.md)，按需參考 [範例](references/format-example.md)。H3 交由 [h3-prompt-writing](../h3-prompt-writing/SKILL.md)，單獨安裝時須另載入該技能才具備 H3 專用格式。

## 撰寫與交付

新編或重做分鏡、實質撰寫或修訂提示詞，依 [antigravity-writer](../antigravity-writer/SKILL.md) 分流。單獨安裝時用 [寫作備援](references/writer-fallback.md)。純格式轉換直接處理。

依 [精簡格式的模式與分組規則](references/concise-format.md#模式與分組) 選模式。跨場或跨集持續的變化查 [資產連續性](../film-quality-control/references/asset-continuity.md)，單獨安裝時從劇本、核准卡與前場備註確認本鏡有效狀態。參考圖規劃依 [掛圖規範](../film-quality-control/references/reference-control.md)，製作旁表區分計畫和實際附件。

可提交版依 [雙軌審核](../film-quality-control/references/prompt-review.md) 執行。適用的獨立審核者先盲審請求與實際附件，再讀全劇資料審查分組、鏡頭覆蓋、台詞與時長。依 [鎖定台詞核對](../film-quality-control/references/locked-dialogue-reconciliation.md) 核對劇本、分鏡與實際正文。缺共用規範時，仍逐句核對說話者、原文、順序、跨鏡銜接和可行秒數。缺獨立證據標待審。已要求且實際生成的 1080p 單幀另做 [空間核對](../film-quality-control/references/visual-qa.md#空間核對與示意圖)。

已有分鏡及正式資產卡與參考圖、需要草圖時，交由 [storyboard-grid](../storyboard-grid/SKILL.md)。
