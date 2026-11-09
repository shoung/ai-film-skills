---
name: video-prompts
description: "根據劇本編製八欄分鏡表，或依 Seedance／MiniMax H3 格式產生影片提示詞、時間碼及角色音色；支援分鏡表建立與格式轉換。"
---

# 影片提示詞

新創作任務沿用 [screenplay-director 共用啟動 intake](../screenplay-director/references/startup-intake.md) 與已知決策，僅關鍵資訊阻礙輸出時補問（每輪最多 2–3 題）。缺少共用 intake 時，全新案在對話中顯示一次 `SHOUNG`；續作、維護、交接不重複，標記不進 prompt。純文字不要求生圖；交付生成靜幀依 [film-quality-control](../film-quality-control/SKILL.md) 獨立看圖對卡，無審核者標待審，不偽造 PASS。

## 文本創作與修復路由（Antigravity CLI 優先）

所有劇本、大綱、分鏡提示詞及實質文字修訂，優先路由至 Google Antigravity CLI (`agy`) 撰寫，詳見 [Antigravity 撰寫工作流](../antigravity-writer/SKILL.md)。

Codex 負責流程編排、格式檢驗、結構驗證與腳本測試，不得改寫創作正文。僅在未安裝 CLI 或確認配額耗盡（具體 quota 訊號，非一般 429、網路、認證、超時、權限或內容過濾）時方可降級 Codex。已在 Antigravity 執行環境下的工作直接完成，絕不遞迴自我調用。創作回執（`provider`、`reason`、`cli_version`、`conversation_id`）嚴格置於提示詞外部。

## 生成請求為獨立單元與分組準則

一次影片生成提示詞為一個獨立交付單元（Generation Request），可包含單一鏡頭或多個連續鏡頭。分組依據為：敘事與因果關係、對白與動作停頓時間、目標模型與模式可用性、控制與重抽成本、素材清晰度；絕非自動一鏡一請求或同場景必合併。八欄分鏡表維持固定欄位與每列一個連續鏡頭，生成群組可對應多列。

I2VA/FL2VA/L2VA 限單連續鏡頭為本工作流程的穩定性政策，非模型能力宣稱；Ref2VA 角色與場景參考可支援多鏡。

## 請求自足性與起始狀態

每個生成請求必須完全自足。僅實際隨請求提交的參考素材有效，角色或道具卡不提供先前時序狀態。各請求必須明確建立起始狀態（除非由實際提交之首幀或銜接幀提供）。請求內定義好的跨鏡回指合法，跨請求不得依賴外部隱性背景。鎖定的劇本台詞逐字保留。

## 提示詞精簡可讀與表演控制

本規範適用於 Seedance 及 H3。生成影片提示詞時，畫面方位、構圖與運動必須遵循 [精簡格式](references/concise-format.md) 規範，一律以觀眾視角的畫面座標為準，切鏡後即時重建方位關係。

預設簡潔可讀。角色行動目標、刺激觸發、呼吸與眼神微動為構思工具，非每鏡強制列印欄位；僅在情節關鍵且具備可見性時加入時序控制。維持主動作鏈與直觀運鏡，避免堆砌鏡頭焦段與冗餘微動作。

時間節拍使用時按 0.5 秒網格對齊。製作備註（群組ID、八欄對照、剪輯估值、素材登錄ID）嚴格置於可複製提示詞正文之外。所有範例均為合成格式示例，非實際生成紀錄。

## 品管與雙軌審核

交付可提交提示詞前，須通過雙軌審核：
1. **製作品管審核**：依 [台詞與時長審核](../film-quality-control/references/timing-and-dialogue.md) 核對分組合理性、鏡頭覆蓋、台詞逐字對齊及秒數可行性（字數、語速、停頓、情緒、動作先後／並行）。
2. **盲審獨立請求審核**：依 [提示詞審核規範](../film-quality-control/references/prompt-review.md)，僅憑 prompt 與實際提交素材檢驗可讀性、隱性依賴、未解析代號與指令過載。

審片員採唯讀模式報告問題，不擅改文本；無獨立審片員時標記待審。純文字不強求生圖，亦不捏造 PASS。

## 分鏡表交付

使用者要求建立、改寫或轉換「分鏡表」時，讀取 [八欄分鏡表格式](references/storyboard-table-format.md) 與 [分鏡表模板](references/storyboard-table-template.md)，固定八欄與欄序，每列一個連續鏡頭；生成群組可在旁表中對應多列。此分支只處理純表格，不啟動模型提示詞改寫或生成需求；純提示詞任務不自動附加分鏡表。

## 執行方式

1. **判斷交付類型並確認模型**：純分鏡表依八欄規範處理；撰寫模型專用 prompt 時，沿用既有指定模型，未指定則先詢問確認（Seedance 或 MiniMax H3）。
2. **依模型切換規則**：
   - 使用者選 **Seedance**：讀取 [Seedance 參考指南](references/03_Seedance 提示詞指南.md) 與 [Seedance 執行文件](references/01_視頻提示詞生成SKILL_V2.0_執行主文件.md)（示例庫 [02](references/02_視頻提示詞生成SKILL_V2.0_示例庫.md) 選讀），依 [精簡格式與0.5秒規範](references/concise-format.md) 及 [表演控制](references/performance-control.md) 撰寫。
   - 使用者選 **MiniMax H3**：改用 [h3-prompt-writing](../h3-prompt-writing/SKILL.md) 及其參考文件；不混用兩者格式。
3. 全程使用繁體中文。模型要求的欄位名稱、標籤、時間碼或英文台詞依規範保留。未實際呼叫工具時，不宣稱已啟動獨立代理或生成影像。

## 專案內技能銜接

- 劇本總控：[screenplay-director](../screenplay-director/SKILL.md) | 劇本寫作：[screenplay-writing](../screenplay-writing/SKILL.md)
- 視覺資產：[visual-asset-prompts](../visual-asset-prompts/SKILL.md) | 影片提示詞：[video-prompts](../video-prompts/SKILL.md)
- 製作品管：[film-quality-control](../film-quality-control/SKILL.md)
