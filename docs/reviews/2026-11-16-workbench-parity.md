# 原版功能等價驗收紀錄

基準：ZenStory drama-skills `37232f6d22e174c36e321d2e3a1a3ae871e7d602`。本輪已實際啟動原版公開範例並對照移植版；API 原始樣本保存於本機 `_work/workbench-audit/original-*.json`（公開範例資料）。以下項目已按列出的範圍驗收，詳細證據、獨立 QA 判定與限制見 [QA 報告](2026-11-16-workbench-parity-qa.md)。不宣稱所有媒體／尺寸逐像素相同，也未執行外部生成或成片渲染。

## 功能矩陣

|功能|原版依據|移植驗收|證據／狀態|
|---|---|---|---|
|全劇總覽與待辦|DESIGN.md Information architecture / nextFor|真實資料計數與可執行下一步|通過：單集總覽、八項進度、審查待辦|
|七階段與分集|app.js route / stagebar|全部頁面可開、前後集切換|通過：七頁實際內容、多專案／前後集|
|劇本結構視圖|creator_views.parse_screenplay|場次、台詞與來源定位|通過：公開2場、台詞搜尋定位|
|設定卡|creator_views.parse_settings|人物、造型、場景、道具及關聯圖|通過：公開7項、既有專案13項|
|分鏡與節奏|app.js board / rhythmChecks|卡片表格、八欄、時間條|通過：22鏡／62秒、真專案54列精確八欄|
|單鏡圖詞|app.js renderInspector|圖詞同屏、首尾幀、片段、台詞、設定、審查、切鏡同步|通過：S01→S01A、跨組S22，桌面與窄版|
|提示詞頁面|app.js prompts / copyablePrompt|圖片詞與影片詞完整閱讀／複製|通過：26條公開詞、859字複製到剪貼簿|
|成片五軌|app.js film|實際剪輯資料呈現、無資料不假造|通過：3cut／9秒，無配音4軌／有宣告5軌雙邊一致；未渲染|
|審查卡|app.js review|分級、定位、複製請求，QA 仍獨立|通過：MUST／COULD卡與唯讀QC登錄|
|搜尋與路由|app.js palette / hash routes|全域搜尋、深連結與瀏覽歷史|通過：命中／無結果、reload、back／forward|
|原文編輯|app.js file/edit|定位、保存與409衝突|通過：一般入口、瀏覽器保存、外部修改拒覆寫／載入最新|
|主題／鍵盤／窄版|DESIGN.md Accessibility|桌面並排、窄版堆疊、搜尋與上下鏡快捷鍵|通過：主題、Ctrl+K／Esc、換鏡、375px窄版|
|舊專案適配|本輪設計|54鏡、九欄映射、MDCSV差異、中文草圖與鏡號關聯|通過：來源候選保留、宮格索引與首尾幀／H3／影片|
|安全與原始資料完整|本輪設計|Host/Origin/token/路徑/Range/原子保存、來源雜湊不變|通過：34項單元／API，178來源檔SHA256全相同|

## 執行記錄

- 使用者已明確確認設計直接實作。
- 設計經乾淨 Luna 審查，補明單鏡台詞與片段等價要求。
- 分支：`feat/workbench-parity`；沿用現有 Git checkout，不建立額外 worktree。
- 分工：reader/legacy adapter、完整 upstream UI、creator view-model/API facade；分工檔案不重疊。
- 真專案初始盤點 178 個檔案，來源雜湊存 `_work/workbench-audit/source-before.json`。驗收以唯讀方式進行。
- 獨立 QA 最終 34/34 單元／API 通過，來源 178/178 SHA256 相符。子代理無 IAB，瀏覽器由主代理代行並交回 AX／DOM／截圖觀察，QA 獨立判定；報告明列操作分工與未測範圍。
- 程式審查發現並修復編輯權限、保存 query/body 契約及目標一致性問題；新增回歸後通過。
