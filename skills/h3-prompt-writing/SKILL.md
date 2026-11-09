---
name: h3-prompt-writing
description: "Write MiniMax H3 video generation prompts for T2VA, I2VA, FL2VA, L2VA, and Ref2VA. Use when rewriting multimodal requests into H3 prompt structures, composing integrated_multimodal_description, overall_soundscape, and non_diegetic_music, aligning keyframes, or defining reference labels for images, videos, and audio."
---

# H3 Prompt Writing

新創作任務沿用 [screenplay-director 共用啟動 intake](../screenplay-director/references/startup-intake.md) 與已知決策，僅關鍵阻礙補問（每輪最多 2–3 題）。缺少共用 intake 時，全新案在對話中顯示一次 `SHOUNG`；續作、維護、交接不重複，標記不進 prompt。純文字不要求生圖；交付生成靜幀依 [film-quality-control](../film-quality-control/SKILL.md) 獨立看圖對卡，無審核者標待審，不偽造 PASS。

## 文本創作與修復路由（Antigravity CLI 優先）

所有提示詞創作、劇本改編及實質文字修訂，優先路由至 Google Antigravity CLI (`agy`) 撰寫，詳見 [Antigravity 撰寫工作流](../antigravity-writer/SKILL.md)。

Codex 負責編排、格式檢驗與結構驗證，不得改寫正文。僅在未安裝 CLI 或確認配額耗盡（具體 quota 訊號，非一般 429、網路、認證、超時或權限錯誤）時降級 Codex，或因內容過濾明確拒絕時降級至當前預設 LLM。已在 Antigravity 執行環境下的工作直接完成，絕不遞迴自我調用。創作回執（`provider`、`reason`、`cli_version`、`conversation_id`）置於提示詞外部。

## 生成請求為獨立單元與分組準則

一次影片生成提示詞為一個獨立交付單元（Generation Request），可包含單一鏡頭或多個連續鏡頭。分組依據為：敘事與因果關係、對白與動作停頓時間、目標模型與模式可用性、控制與重抽成本、素材清晰度；非自動一鏡一請求或同場景必合併。

八欄分鏡表每列維持一個連續鏡頭，生成群組可對應多列。I2VA/FL2VA/L2VA 限單連續鏡頭為工作流程穩定性政策，非模型能力宣稱；Ref2VA 可支援多鏡。

## 純分鏡表分支

使用者要求建立、改寫或轉換分鏡表時，讀取本地 [八欄分鏡表格式](references/storyboard-table-format.md) 與 [分鏡表模板](references/storyboard-table-template.md)，固定八欄與欄序，每列一個連續鏡頭；生成群組可在旁表中對應多列。純分鏡表任務在此分支完成，不啟動 H3 模型提示詞改寫或生成需求；純提示詞任務不自動附加分鏡表。

## 請求自足性與起始狀態

每個生成請求必須完全自足。僅實際隨請求提交的參考素材有效，人物或道具卡不提供先前時序狀態。各請求必須明確建立起始狀態（除非由實際提交之首幀或銜接幀提供）。請求內定義好的跨鏡回指合法，跨請求不得依賴外部隱性背景。鎖定的劇本台詞逐字保留。

## 提示詞精簡可讀與表演控制

讀取 [精簡格式與0.5秒規範](references/concise-format.md)、[表演控制共通規則](references/performance-control.md) 與合成示例 [format-example.md](references/format-example.md)。預設簡潔可讀，情節關鍵需要時才寫入可見時序控制，非每鏡強制列印目標、觸發、呼吸與眼神欄位。時序節拍使用 0.5 秒網格。製作備註與審核記錄置於模型欄位之外。

正文依使用者語言（繁體中文），模型欄位鍵、說話者 `(S1)`、台詞語法 `<d>[Language] ...</d>`、`<Picture N>`、`<Subject N>` 及關鍵幀對齊語法嚴格保留。

## 雙軌品質審核

交付可提交提示詞前，須通過獨立審片員雙軌審核：
1. **製作品管審核**：依 [台詞與時長審核](../film-quality-control/references/timing-and-dialogue.md) 比對台詞、動作與情緒，驗證秒數合理性。
2. **盲審獨立請求審核**：依 [提示詞審核規範](../film-quality-control/references/prompt-review.md) 僅憑提示詞與實際提交素材檢查獨立可讀性與指令衝突。
審片員採唯讀模式；缺獨立審片員時標記待審。純文字不捏造 PASS。

## 模式與欄位順序

- **基礎模式（T2VA/I2VA/FL2VA/L2VA）**：讀取 `references/base-en.txt`，依序輸出：
  1. `integrated_multimodal_description`
  2. `overall_soundscape`
  3. `non_diegetic_music`
  I2VA、FL2VA、L2VA 嚴格限制為單一連續鏡頭，正文不可暗藏切鏡、反打或蒙太奇。
- **全參考模式（Ref2VA）**：讀取 `references/ref-en.txt`，依序輸出：
  1. `subject_definitions`
  2. `summary`
  3. `retention_analysis`
  4. `detailed_description`
  5. `overall_soundscape`
  6. `non_diegetic_music`
  維持跨區塊標籤一致性。
