# Antigravity 寫作提供者工作流程規範

## 1. 雙引擎職責劃分
- **Antigravity (`agy`)**：主責所有劇本、大綱、對白、分鏡提示詞、視覺描述、報告與其他文字成果（written deliverables，包含各類報告與非創意文本）之原創產出及實質修訂，此為全套件統一政策。
- **Codex**：主責自足式 Brief 組裝、呼叫輔助腳本、程式碼維護、格式校驗與獨立品管審核。代理協調、程式與 QA 屬於工程職責，嚴禁代筆改寫文字成果。
- **原生防遞迴**：若當前環境為 Antigravity，跳過派工直接就地寫作，嚴禁重複執行腳本。缺少輔助腳本不等於缺少 CLI。
- **適用範疇**：本工作流政策僅適用於本套件內部協作規範，不宣稱為全域系統安裝依據。毋需預先檢查配額，而是在每次寫作任務中檢查 CLI 安裝狀態（`not_installed`），並由實際運行結果識別配額錯誤（`quota_exhausted`）。

## 2. 輔助腳本介面與調用
輔助模組函式介面為：
```python
route(brief, executable=None, timeout=180, model=None)
```
外部 CLI 調用格式（由技能目錄執行，`--brief` 僅為 Python 輔助腳本選項）：
```bash
python3 scripts/route_writer.py --brief /abs/brief.txt --output /abs/result.json
```
- **原生指令映射**：輔助腳本以 `--brief` 讀取 UTF-8 檔案後，透過行內 `-p "<brief>"` 傳入原生指令（`--model` 僅在確認為已驗證 slug 時選用）。
- **權限與工具限制**：純寫作腳本強制停用所有工具（no-tools：commands、read、write、url 與 mcp 工具），僅接受顯式輸入文件，並注入已派工標記。
- **暫態故障處理**：採有限度重試；嚴格遵守網路與權限規範（遇網路或權限問題直接阻擋，不得降級或繞過），嚴禁自動安裝軟體、購買點數或修改全域環境設定。

## 3. 狀態機與退出碼規範
輔助腳本將判定寫入 `result.json`，內部不執行 Codex 生成。狀態僅限 `written`、`fallback`、`blocked` 三種，各欄位定義如下：
- `provider`：成功時為 `antigravity`，降級時為 `codex`，阻擋時一律為 `null`。
- `status`：執行狀態（`written`、`fallback`、`blocked`）。
- `reason`：判定原因（`written` 為 `antigravity_available`；`fallback` 為 `not_installed` 或 `quota_exhausted`；`blocked` 為特定阻擋代碼）。
- `text`：產出文字內容（降級或阻擋時為空）。
- `error`：選填錯誤診斷訊息（降級或阻擋時記錄診斷，不放入 `text`）。
- `cli_version`：真實 CLI 版本（若有提供，不可填造假值）。
- `conversation_id`：真實對話 ID（若有提供，不可填造假值）。

| 退出碼 | 狀態 (`status`) | 提供者 (`provider`) | 允許原因 (`reason`) 與判定條件 |
|---|---|---|---|
| **0** | `written` | `antigravity` | 執行成功、輸出非空且無錯誤或軟性拒絕診斷。`reason` 為 `antigravity_available`。記錄真實 `cli_version` 與 `conversation_id`（若有提供，不可填造假值）。推進至獨立品管。 |
| **10** | `fallback` | `codex` | 僅限二進位檔缺失（`not_installed`，PATH 無 `agy`）或帳號/日/週配額確認耗盡（`quota_exhausted`）。提供者一律為 `codex`，絕無 pending 或 null 提供者降級。允許 Codex 接替。 |
| **20** | `blocked` | `null` | 一般配額超限、每分鐘速率限制、否定句配額、認證／網路／逾時／權限／內容審查失敗。不得認定 HTTP 200 即足夠；非空但含錯誤或部分／軟性拒絕診斷者一律阻擋。提供者一律為 `null`。終止並報錯，嚴禁代筆。 |

## 4. 自足式 Brief 構建規範
Brief 必須包含素材文本正文，不得僅提供檔案路徑：
1. **內含完整素材**：涵蓋目標段落、對白、角色設定與特定模型語法。
2. **長篇素材處理**：依需求擷取必要節錄，鎖定之關鍵文本與台詞必須完整保留；於邏輯邊界分塊處理，最終由品管檢驗組裝完整性。
3. **非提示詞內容分離**：製作備忘、品管紀錄與提供者憑據一律置於可複製 prompt 之外。

## 5. 寫作憑據與品管閉環
寫作憑據必須獨立於正文外（如外部註解或獨立 metadata），欄位包含 `provider`、`status`、`cli_version`、`conversation_id` 與 `reason`，嚴禁污染提示詞正文。產出後必須經獨立品管審查與盲測；若有實質修訂需求，由 Codex 彙整回饋再次派工由 `agy` 實質修訂。
