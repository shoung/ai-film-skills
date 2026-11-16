# 原著分析與八欄創作台實作計畫

> 執行方式：依使用者授權由 Luna 子代理處理互不重疊模組，主代理整合；最後由乾淨的 Luna QA 進行全套與 E2E 驗證。

**Goal:** 補齊原著分析、分鏡與參考圖方法，交付維持八欄格式與獨立 QA 的本機創作台。

**Architecture:** 新 skill 及參考文件擴充；Python 標準庫服務讀取原文件，靜態前端顯示與原文編輯。

**Tech Stack:** Python 3.9+、HTML/CSS/JavaScript、unittest。

**Spec:** `../specs/2026-11-16-source-analysis-workbench-design.md`

## 全域限制

- 使用繁體中文；不改八欄主表或現有獨立 QA 機制。
- 原著只讀、候選／正式決策分開；planned 圖不冒充 actual。
- 一個 generation 可對應多個 shot_ids；JSON QC 為原登錄真源。
- 創作台僅本機；無密鑰、外部生圖或剪輯執行。
- 借用上游程式保留 MIT 與 commit；不傳私人專案至外部寫作服務。

## Review Focus

1. 八欄 pipe／br／多表／CSV／非連號與重複鏡號 → parser 測試。
2. 多分集同鏡號與多鏡群組、缺失及多版本 QC → 映射與問題提示測試。
3. 非 UTF-8／空表／大型文件／缺媒體 → API 可恢復錯誤測試。
4. 外部同步修改及多視窗保存 → expected_version 衝突測試。
5. 路徑穿越、symlink、HTML／腳本內容、外站請求 → HTTP／瀏覽器測試。

## Task 1 原著分析

- [x] 新建 `skills/screenplay-source-analysis/`；引入章節索引及 attribution。
- [x] 先測試章界／繁體標題／源檔變更／覆蓋與續跑，再補實作。
- [x] 撰寫自足入口／交接與證據參考；通過 skill validator。

## Task 2 既有技能方法擴充

- [x] 新增分鏡方法與參考控制文檔，銜接 director/framework/video/H3/visual/QC。
- [x] 保留欄序／QA，計畫圖獨立於實際 image_inputs。
- [x] 檢查相對連結與情境適用性。

## Task 3 創作台後端

- [x] 以 spec API 測試八欄解析／分集／QC 映射。
- [x] 加入只讀媒體與有版本的文字編輯 API；安全與 Range 測試。
- [x] 實作 CLI／背景啟停；只使用標準庫。

## Task 4 創作台前端

- [x] 建立繁體中文專案／集數導覽、八欄／卡片、詳情與媒體預覽。
- [x] 原文編輯／保存／衝突提示；不注入文件 HTML，不偽造 QA。
- [x] 支援桌面與窄版、鍵盤及可見錯誤回饋。

## Task 5 整合與獨立驗證

- [x] 更新 README、skill metadata、MIT attribution 與操作說明；同步工作副本。
- [x] 獨立 QA 全套單元／HTTP／瀏覽器 E2E，修復後複驗。
- [x] 真實記錄結果與限制，交付啟動命令及本機連結。
