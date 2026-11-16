---
name: film-workbench
description: 開啟/檢視/編輯本地AI影視創作台、檢查分集進度/八欄分鏡/素材QA。
---

# 本地 AI 影視創作台 (Film Workbench)

本地 AI 影視創作台是專為 AI 影視製作打造的輕量化本機檢視與輔助編輯工作台。

## 1. 核心定位與職責邊界

* **無相依本機工具**：基於 Python 3.9+ 標準庫實作，零第三方套件依賴。
* **核心職責**：視覺化呈現分集製作進度、八欄分鏡表檢視與編輯、素材與 QC 狀態查核。
* **邊界宣告**：
  * **不承擔劇本創作或生成生圖**：本創作台僅為本機查閱與文字整理介面，絕不呼叫模型、生成影片、渲染畫面或代替人工審核。
  * **不替代 QA 審核**：介面不提供人為編輯或點擊批准 QC 之按鈕，資料保存不代表 QA 通過，修改後必須依 `film-quality-control` 規範重新執行審查。
  * **按需啟動**：安裝或維護本技能時絕不自動啟動全專案後台服務，僅在使用者明確要求創作台時才啟動。

## 2. 命令列指令介面 (CLI Usage)

創作台伺服器腳本位於 `scripts/dashboard_server.py`，可於技能目錄執行或將腳本路徑改為絕對路徑調用：

```bash
# 啟動本機創作台 (自動指派連接埠並於背景執行)
python scripts/dashboard_server.py /absolute/project --port 0 --detach

# 啟動並以預設瀏覽器開啟 (選用 --open)
python scripts/dashboard_server.py /absolute/project --port 0 --detach --open

# 查詢創作台當前執行狀態 (同樣帶 PROJECT 路徑)
python scripts/dashboard_server.py /absolute/project --status

# 停止特定專案之創作台服務 (同樣帶 PROJECT 路徑)
python scripts/dashboard_server.py /absolute/project --stop
```

> [!SECURITY]
> **本機安全性**：伺服器啟動時印出包含 Token 之 Localhost 登入 URL，此權杖僅供本機存取，嚴禁對外公開或監聽公網。

## 3. 資料來源與單一真源 (Single Source of Truth)

同一專案重複啟動會沿用原服務與登入網址；若已更新技能程式，須先以該專案路徑執行 `--stop`，再重新啟動。關閉一次輸出網址的啟動命令，不代表已停止真正的服務程序。

* **磁碟原始檔案為準**：自動讀取專案根目錄或分集（episodes）資料夾檔案，原始 Markdown 與 CSV 檔案為真源。
* **八欄順序鎖定**：八欄分鏡表嚴格維持既定欄位順序，介面讀寫絕不任意調換或增減欄位。
* **QC 旁表唯讀呈現**：QC JSON 檢驗紀錄為唯讀顯示，介面不設編輯或手動批准按鈕。
* **媒體預覽支援**：支援本機圖片、影音及 25 格 PNG 序列表預覽；單一 generation 可關聯多個連續 shots。

## 4. 編輯儲存與 409 衝突保護

* **原文儲存支援**：支援編輯並回寫 `.md`、`.csv`、`.txt` 等原始文字檔。
* **409 版本衝突保護**：儲存時比對檔案版本，若版本不符返回 HTTP 409，強制使用者先重新讀取最新檔案或另存備份後自行合併，絕不盲目覆蓋。
* **品質重審機制**：在創作台儲存檔案不代表通過 QA，必須依 `film-quality-control` 重跑審核流程。

## 5. 歧義處理與異常處置

* **警示透明呈現**：若讀取到歧義檔案、多份分鏡表、重複 QC 或缺失媒體，介面清楚顯示來源與警示訊息。
* **不猜測、不自作主張**：系統絕不自行猜測最終版本，嚴禁私自偷偷修改或刪除源檔。

## 6. 目錄結構與相依維護

* 依賴腳本與前端靜態資源保持相對目錄結構：
  * `scripts/dashboard_server.py`：本機輕量 HTTP 服務伺服器。
  * `assets/dashboard/`：純 HTML/CSS/JS 前端靜態資源。
* 詳細操作說明已收錄於專案配套之 `README.md`，技能主檔不再另造冗餘說明。

---
### 相關規範
* [../film-quality-control/SKILL.md](../film-quality-control/SKILL.md)
* [../storyboard-grid/SKILL.md](../storyboard-grid/SKILL.md)
* [../screenplay-source-analysis/SKILL.md](../screenplay-source-analysis/SKILL.md)
