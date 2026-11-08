---
name: antigravity-writer
description: 全套件文字創作與實質修訂的第一分流提供者（Google Antigravity CLI），由 Codex 負責協同編排、結構驗證與代碼處理。
---

# Antigravity 寫作分流提供者

本規範定義套件所有文字產出之路由標準。依套件政策，所有劇本、大綱、台詞、分鏡提示詞、視覺描述、報告與其他文字成果（written deliverables，包含各類報告與非創意文本）及其實質修訂，一律優先採用 Google Antigravity CLI（`agy`）；Codex 專職協調編排、程式碼與品質檢驗，嚴禁擅自代筆。完整執行細節請參閱 [提供者工作流程規範](references/provider-workflow.md)。

## 核心原則
- **原生跳過派工**：若當前環境已為 Antigravity，直接就地撰寫，嚴禁再次調用輔助腳本或發起遞迴進程。
- **降級門檻**：僅當二進位檔缺失（PATH 無 `agy`）或帳號、每日、每週點數確認耗盡時，方可降級由 Codex 接替寫作。缺少輔助腳本不等於缺少 CLI。降級提供者一律為 `codex`，原因僅限 `not_installed` 或 `quota_exhausted`。
- **嚴格阻擋**：一般配額超出、每分鐘速率限制、否定句配額訊息、認證、網路、逾時、權限或內容審查失敗均不可降級（退出碼 20），此時提供者一律為 `null`。不得認定 HTTP 200 即足夠；非空但含錯誤或軟性拒絕診斷者一律阻擋。
- **安全防界**：純寫作無須工具；輔助腳本強制停用所有工具（no-tools：commands、read、write、url 與 mcp 工具），僅接受明確輸入文件，並注入已派工標記。短暫故障採有限次重試，嚴格遵守網路與權限規範，嚴禁自動安裝軟體、購買點數或修改全域設定。
- **套件適用邊界**：本政策僅適用於本套件內部流程規範，不宣稱全域系統安裝狀態。毋需預先檢查配額，而是在每次寫作任務中檢查 CLI 安裝狀態（`not_installed`），並由實際執行回傳之配額錯誤（`quota_exhausted`）判定。

## 輔助腳本協定
輔助函式介面為 `route(brief, executable=None, timeout=180, model=None)`，外部命令調用統一介面（從技能目錄執行）：
```bash
python3 scripts/route_writer.py --brief /abs/brief.txt --output /abs/result.json
```
輔助腳本以 `--brief` 讀取 UTF-8 檔案後，透過行內 `-p "<brief>"` 傳入原生指令（`--model` 僅在確認為已驗證 slug 時選填）。

Brief 必須包含相關素材正文而非僅路徑。超長素材應採必要節錄，完整保留鎖定台詞，依邏輯邊界分塊後交由 QA 檢驗組合。非提示詞內容（製作備忘、QA 憑據）置於可複製 prompt 之外。

### 產出結構與退出碼
腳本自行將結果寫入 `result.json`，內部不執行 Codex 生成。狀態僅限 `written`、`fallback`、`blocked` 三種，各欄位定義如下：
- `provider`：成功時為 `antigravity`，降級時為 `codex`，阻擋時一律為 `null`。
- `status`：執行狀態，可為 `written`、`fallback` 或 `blocked`。
- `reason`：狀態判定原因；`written` 時固定為 `antigravity_available`；`fallback` 時僅限 `not_installed` 或 `quota_exhausted`；`blocked` 時記錄具體阻擋原因代碼。
- `text`：寫作產出之正文字串（降級或阻擋時為空）。
- `error`：選填之診斷錯誤訊息（降級或阻擋時記錄診斷，不置於 `text`）。
- `cli_version`：真實 CLI 版本字串（若有提供，嚴禁造假）。
- `conversation_id`：真實對話識別代碼（若有提供，嚴禁造假）。

對應退出碼規範：
- **退出碼 0（`written`）**：成功產出合法文本，`provider` 為 `antigravity`，`reason` 為 `antigravity_available`，記錄真實 `cli_version` 與 `conversation_id`。
- **退出碼 10（`fallback`）**：符合二進位檔缺失（`not_installed`）或帳號/日/週配額確認耗盡（`quota_exhausted`）之合規降級，`provider` 必為 `codex`，絕不回傳 pending 或 null 提供者降級。
- **退出碼 20（`blocked`）**：遭遇阻擋性錯誤，`provider` 一律為 `null`，中止並回報，嚴禁自動降級。

## 原生命令與憑據分離
缺少輔助腳本不等於缺少 CLI。若在缺少輔助腳本時直接調用原生命令，必須提供與輔助腳本相同之無工具（no-tools）安全保護，明確宣告全部六項拒絕權限，且不使用未支援的標誌：
```bash
agy -p "<brief>" --mode plan --output-format json --print-timeout 180s --settings '{"permissions":{"deny":["command(*)","read_file(*)","write_file(*)","read_url(*)","execute_url(*)","mcp(*)"]}}'
```
手動調用者必須自行檢查實際執行狀態、輸出是否非空與錯誤診斷（`error`），並遵循相同的降級規範。寫作憑據必須與正文分離（置於外部註解或獨立 metadata），欄位包含 `provider`、`status`、`cli_version`、`conversation_id` 與 `reason`，產出後須執行獨立品質檢驗。
