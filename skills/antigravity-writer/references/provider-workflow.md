# Antigravity 寫作分流協定

套件內的文字成果與實質修訂優先交給 Google Antigravity CLI（`agy`）。呼叫端組裝寫作需求、維護程式、檢查格式並安排獨立品管。已在 Antigravity 環境中時直接撰寫，避免遞迴派工。

## 準備與呼叫

寫作需求須附上相關原文、角色設定、鎖定限制與目標格式。長素材擷取必要段落，完整保留鎖定台詞，按敘事邊界分塊，完成後核對組裝結果。純寫作使用顯式提供的文字並停用工具。

從技能目錄呼叫輔助腳本：

```sh
python3 scripts/route_writer.py --brief /abs/brief.txt --output /abs/result.json
```

Python 介面為 `route(brief, *, executable=None, timeout=180, model=None)`。輔助腳本讀取 UTF-8，加入已派工標記後以 `-p` 傳入 CLI。`--model` 僅在已驗證模型識別碼並須明示指定時使用。單次呼叫包含版本探測與一次寫作。以實際回傳判斷配額與內容過濾，無需另查配額。

輔助腳本不存在而 `agy` 可用時，依 [單獨安裝的無工具命令](writer-fallback.md) 手動執行，沿用下方結果判定。呼叫端遵守目前環境的網路及權限設定，軟體安裝、購買點數或全域設定變更需有獨立授權。

## 路由結果

| 退出碼 | 狀態 | `provider` | 條件與處理 |
|---|---|---|---|
| 0 | `written` | `antigravity` | 程序與 JSON 均成功，正文非空，無錯誤、部分回應或軟性拒絕診斷。`reason` 為 `antigravity_available`，送獨立品管。 |
| 10 | `fallback` | `codex` | 找不到 CLI（`not_installed`）或執行診斷確認帳號點數或期間配額耗盡（`quota_exhausted`），由 Codex 接替。 |
| 10 | `fallback` | `default_llm` | CLI 診斷明確證實 Google 內容過濾拒絕（`content_filtered`）。即使回傳部分文字也丟棄。由目前宿主或會話的預設模型依自身規範獨立評估。 |
| 20 | `blocked` | `null` | 一般配額超限或速率限制（如每分鐘限制）、否定或不確定的配額、認證、網路、逾時、權限、未知錯誤或未確認成因的不完整回應。記錄診斷並停止分流。 |

HTTP 成功碼、創作正文提及過濾、一般拒絕或工具權限拒絕皆不足以判定內容過濾。接替模型使用目前環境已授權的能力，不硬編碼模型或另呼叫外部服務。輔助腳本只回傳路由決定，由呼叫端執行接替。

JSON 包含 `provider`、`status`、`reason`、`text`、`cli_version`、`conversation_id`，可另有 `error`。只有 `written` 帶正文，錯誤診斷放在 `error`。版本與對話 ID 沿用可取得的真實值，未知時保留空值。

## 交付與重審

在正文或可複製提示詞外記錄實際寫作者及 `provider`、`status`、`reason`、`cli_version`、`conversation_id`。路由結果中的 `default_llm` 是接替標記，完整憑據由呼叫端據實登錄。品管及盲審依交付項目執行，製作備忘與 QA 證據另存。實質修訂沿用本協定，完成後重審。
