# 原著分析與八欄創作台設計

## 已確認需求

依本次對比分析與使用者授權，先新增原著改編分析並整合分鏡方法／參考圖控制，再提供本機創作台。保留八欄主表、獨立 QA、生成群組與鏡頭的多對一關係。使用者允許借用 drama-skills 程式碼，完成後由乾淨的 Luna QA 驗證。

## 方案與決策

採用獨立 `screenplay-source-analysis` skill、既有 skills 的參考方法擴充，以及獨立 `film-workbench` skill／Python 本機工具。沿用原文件為真源，解析為唯讀卡片；原文編輯提供版本衝突保護。這是承接前輪建議的實作方案。

不整包取代原技能：對方五文件語法與我們八欄表／QC 旁表不同。借用章節索引與適合的工作台程式／視覺資源，保留上游版本與 MIT 授權；不引入供應商生成接口與剪輯執行器。

## 原著分析

- 索引 → 指定範圍或抽樣快評 → 逐章證據 → 劇情單元／人物設定演進 → 製作形態判定 → 分集候選。
- 來源只讀、位置可回查、原文變更可驗證、章級覆蓋可檢查及續跑。
- 候選不是正式大綱或資產卡；由 framework／director 接續，writing provider 仍遵循既有規範。

## 分鏡與素材控制

- 新增竪屏群戲／軸線、動作場面、首尾幀派生、修鏡 ID 與下游同步方法，保留八欄欄序。
- 表外參考計畫區分 planned 與 actual，明列順序、用途、控制／不得控制；實際 generation 仍只收真實素材。
- 分鏡／提示詞／資產變更沿用獨立 QA 與失效規則；不把模型卡經驗寫成官方能力。

## 創作台範圍

Python 標準庫本機 HTTP 服務與零建置靜態前端，繁體中文介面。以專案根目錄啟動，支援根目錄式與分集子目錄式專案。

- 專案文件瀏覽／搜尋、分集切換、進度與資料缺項。
- Markdown 八欄表解析（含 escaped pipe、`<br>`、多表），原欄名與原鏡序不變；支援相同八欄的 CSV。
- 鏡頭詳情串起 QC `assets/shots/generations/reviews`，不將多鏡 generation 攤平成單鏡或冒認審核通過。
- 圖片／音訊／影片及 storyboard-grid PNG 預覽；非生成／渲染介面。
- 允許文字原文編輯（Markdown、CSV、TXT），保存需版本匹配及原子替換；QC JSON 只讀以免繞過核准與簽章。
- 主動安全邊界：僅 loopback、Host／Origin 核對、session token、防路徑穿越／symlink、隱藏敏感／版本控制目錄、HTML 僅作文字呈現。

## 模組契約

`film-workbench/scripts/project_reader.py` 提供 `project_snapshot(root)` 與 `read_document(root, relative_path)`；`dashboard_server.py` 啟動 CLI 與 API。前端直接呼叫：

- `GET /api/project` → `{name, episodes:[{id,name,files,shots,packages,issues,grids}], files:[{path,name,kind,episode}], issues}`。
- shot → `{id, source, row_index, fields:{八欄名稱:原內容}, assets:[], generations:[], reviews:[], issues:[]}`；欄序由 `columns` 回傳。
- `GET /api/file?path=...` → `{path, content, version, editable}`。
- `PUT /api/file` JSON `{path,content,expected_version}` → `{path,version}`，衝突 HTTP 409。
- `GET /api/media?path=...` → 白名單媒體 bytes（支援 Range）。
- 認證：啟動 URL fragment `#token=...`；前端保存在 sessionStorage，API 使用 `X-Film-Token` header。media 使用同源 session cookie；`POST /api/session` 可用相同 header 建 cookie。token 不寫入專案檔。
- API 錯誤 → `{error:繁體中文說明}`。
- CLI：`python scripts/dashboard_server.py PROJECT --port 0 [--open]`，預設不自動開瀏覽器；列出實際 URL。支援 `--detach`、`--status`、`--stop`，連線狀態存在使用者 runtime／暫存目錄，不在創作文檔內。

## 驗收

全套原有單元測試、新索引測試、八欄／QC 映射與 HTTP 安全／保存衝突測試，由獨立 QA 重跑。使用合成專案執行桌面與窄版瀏覽器 E2E：載入、切集、原欄序、鏡頭／生成群組／QA、媒體、編輯保存、外部修改衝突及惡意文字不執行。沒有實際生圖或付費接口測試。
