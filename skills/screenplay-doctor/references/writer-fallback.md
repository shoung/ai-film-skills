<!-- 維護來源：skills/antigravity-writer/references/writer-fallback.md -->

# 單獨安裝的文字創作分流

共用寫作技能可用時，依其提供者規格執行。僅安裝本技能時，先整理自足的 Brief，包含必要素材及逐字鎖定的內容。若已在 Antigravity 內就地撰寫。否則，有 `agy` 時將 Brief 放入 `payload`，開頭加入 `[ALREADY_DELEGATED_ANTIGRAVITY_WRITER]` 並要求只用提供的材料、停用工具且不再派工。

```bash
agy -p "$payload" --mode plan --output-format json --print-timeout 180s --settings '{"permissions":{"deny":["command(*)","read_file(*)","write_file(*)","read_url(*)","execute_url(*)","mcp(*)"]}}'
```

程序退出碼 0、JSON 的 `status` 為 `SUCCESS`、`response` 非空且沒有 `error`，並確認 stderr 沒有失敗、不完整回應或拒絕的診斷，才接受正文。CLI 缺失或明確確認點數用盡時由 Codex 接替。內容過濾明確拒絕時丟棄該次輸出，交會話的預設 LLM 依其規範處理。一般 429、認證、網路、逾時、權限或不明錯誤回報阻礙。將真實的提供者、狀態、原因、可取得的 CLI 版本與對話 ID 記在正文之外。
