# 創作台原版等價實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 移植固定原版 UI／功能，提供八欄分鏡與每鏡圖詞同屏、既有專案適配。
**Architecture:** 原版 dashboard 前端加八欄視圖；安全 HTTP facade 接 project_reader 與 creator view-model adapter。原始文件為真源。
**Tech Stack:** Python 標準庫、原生 HTML/CSS/JS。
**Spec:** ../specs/2026-11-16-workbench-parity-design.md，使用者已明確確認直接實作。

## Global Constraints

八欄原欄序；繁體介面；QA 唯讀不冒認通過；不改私有專案；固定上游 37232f6；無付費生成；保留安全邊界；獨立 Luna QA。

## Review Focus

九欄與 MD/CSV 分歧不可丟資料；跨版本同鏡號隔離；多鏡影片不得誤當單鏡；無剪輯資料不能造時間線；切鏡不得殘留圖詞。

### Task 1：資料適配

Files: scripts/project_reader.py、scripts/legacy_adapter.py、tests/test_legacy_adapter.py。
Produces: project_snapshot(root) 相容既有欄位，episodes.shots 保留八欄 fields，另附 sources/media/prompts 等。
- [x] 先新增並觀察九欄／鏡號邊界／重複來源／版本隔離／圖詞映射測試失敗。
- [x] 實作讀取與唯讀適配，統一來源關聯。
- [x] 跑 unittest 新舊讀取測試；盤點真專案 54 鏡與來源歧義。

### Task 2：原版 UI

Files: assets/dashboard/index.html、app.js、styles.css、tokens.css、NOTICE.txt。
Consumes: 原版 projects/status/tree/series/episode/search/file/media API；episode.board.shots 額外包含 fields 與媒體／提示詞旁表。
- [x] 保留並移植原版完整 UI，改繁體、八欄主表與詳情圖詞雙欄。
- [x] 保持全部七階段互動、搜尋、深連結、編輯、鍵盤與響應式。
- [x] 以合成資料執行瀏覽器驗證，對照原版截圖。

### Task 3：view-model 與 HTTP facade

Files: scripts/creator_views.py、scripts/dashboard_server.py、tests/test_creator_views.py、tests/test_dashboard_server.py。
Consumes: Task 1 snapshot。Produces: 原版前端所需完整 API 契約、以八欄原值投影的 board、真正來源 docs／media／review。
- [x] 先測 API shape、原文保存版本衝突、未驗證 QA 與缺剪輯資料。
- [x] 實作 facade，保留現有 CLI/token、Range、路徑防護與編輯權限。
- [x] 舊測試與新 API 測試通過。

### Task 4：整合、獨立驗收與文件

Files: SKILL.md、README.md、docs/reviews/2026-11-16-workbench-parity.*。
- [x] 建立功能等價矩陣，明列來源／位置／操作證據。
- [x] 乾淨 Luna QA 重跑單元與原版／移植版桌面窄版 E2E、真專案唯讀圖詞抽查。
- [x] 修正所有阻塞，補文件／授權，兩副本同步並驗證 hash。
- [x] 開啟真專案創作台供試用；未確認項不宣稱等價。遠端推送另依授權。
