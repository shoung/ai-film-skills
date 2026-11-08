# 提示詞審核規範：雙軌審核與獨立簽章

提示詞審核（Prompt Review）旨在驗證影片生成請求之敘事完整性、工程可行性、文本自足性與模型可讀性。本規範明定審核維度、雙軌審查機制、簽章合約與證據要求。

## 1. 雙軌審核架構與審核順序
提示詞交付前必須通過兩條審核軌道。執行時**必須先在全新隔離環境中進行盲審獨立請求審核，隨後再進行具備全局視野的製作品管審核**。兩項審核可由同一名具備唯讀權限的獨立品管人員（`reviewer_role: "independent_qa"`）依序完成；若無可用審核員，狀態應標記為 `pending`，嚴禁偽造第二代理人或審核人證據。

### 軌道一：盲審獨立請求審核（Blind Isolated-Request Review）
審核員置於**隔離環境**中，僅提供：該生成請求 prompt、隨附資產（`image_inputs`、`text_reference_bindings`）與參數（mode、duration_seconds）。**嚴禁提供全片劇本、前後其他請求 prompt 或外部備忘錄**。
審查項目：
1. **文本自足性（self_contained）**：無未說明的隱形假設或未定義動機，顯式建立起始狀態（僅提交角色或道具卡不提供先前時序狀態）；無跨請求未提交之引用。
2. **未解析代號與參考綁定（reference_binding）**：正文中所有 `@alias`、`<Subject N>`、`<Picture N>` 均能在隨附資產中解析，無懸空標籤。若包含音訊或視訊參考，因 package schema 僅支援圖像，應發出警告並附人工評估證據，不可偽造為圖像資產；機器警告需以人工情境證據判定，而非一律硬性阻擋（hard block）。
3. **可讀性與無衝突（readability）**：主要動作鏈清晰，運鏡描述易讀；無堆砌無意義焦段（mm）或黑話，無微動作填料，時間節拍明確；無互相矛盾的空間方位或肢體衝突，單鏡模式下無暗藏切鏡。

### 軌道二：製作品管審核（Production Review）
審片員立足全劇本、八欄分鏡表與資產清單，進行上下文貫通檢查：
1. **分組邏輯（grouping）**：審查多鏡合併或單鏡拆分是否具備敘事因果、對白動作時長可行性、驗證之模式能力、重抽成本與素材清晰度之合理解釋；確認分組為合理決策而非機械套用。
2. **鏡頭覆蓋度（coverage）**：八欄分鏡表中的每一列連續鏡頭均被對應的生成群組覆蓋，無遺漏鏡頭，無未登錄的偷渡切鏡。
3. **台詞對齊（dialogue_alignment）**：原劇本鎖定台詞與說話者逐字對齊，嚴禁擅自刪減、漏句、增句或改變語氣。
4. **連續性（continuity）**：跨請求承接狀態合理，道具狀態、角色服裝、站位與軸線前後呼應。
5. **時長可行性（timing_feasibility）**：依 [台詞與時長審核](timing-and-dialogue.md) 評估發音字數、語速、呼吸停頓與動作耗時，確保指定秒數切實可行。

## 2. 審核角色與責任隔離
- 審核員身分標記為 `reviewer_role = "independent_qa"`，採**唯讀模式**：僅出具審核結論、問題清單與修復建議，`reviewer_id` 不得與 `producer_id` 相同，**嚴禁自行修改提示詞正文、分鏡或劇本**。
- 提示詞修訂必須透過寫作提供者路由（參閱 [antigravity-writer](../../antigravity-writer/SKILL.md)）執行；修訂優先由 Google Antigravity CLI（`agy`）處理，僅在二進位檔缺失（`not_installed`）或確認配額耗盡（`quota_exhausted`）時方具備降級由 Codex 接替之資格，而非一律假定由 `agy` 執行。修訂完成後送交審核員重新比對。
- 審核紀錄、品管憑據與製作備忘保存在獨立 QA 報告中，嚴格置於模型提示詞正文之外。

## 3. 結構檢查 vs 語意檢查
- **結構檢查（Structure Check）**：`scripts/validate_package.py` 驗證機讀欄位、鏡號、模式門檻與簽章。純提示詞 QA 不要求圖像素材或媒體生成。
- **語意檢查（Semantic Check）**：由獨立審核檢驗文字邏輯與可行性。結構通過不等於語意通過，亦不可虛構 PASS。
- **執行策略**：草稿模式（`validate_package.py package.json`）缺少 `prompt_review` 或簽章不符時發出 Warning；交付模式（`--delivery`）強制要求 `prompt_review` 為 `pass` 且簽章匹配。機器警告需人工證據判定，不必然一律阻擋。

## 4. 簽章合約：`prompt_signature`
為防止提示詞正文、秒數、模式或綁定資產被修改後沿用舊審核，系統使用簽章核對：
```python
from prompt_checks import prompt_signature
sig = prompt_signature(generation, assets_by_id)
```
計算規範：
1. 傳入 `generation` 與 `assets_by_id` 字典。
2. 涵蓋欄位：`prompt`、`duration_seconds`、`mode`、`shot_ids`、`image_inputs`、`text_reference_bindings`，以及由實際提交資產提取之雜湊字典 `submitted_asset_hashes: {asset_id: sha256}`。
3. 排序後以 UTF-8 編碼為標準 JSON（`json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)`）計算 SHA-256。
4. 審核通過時寫入 `prompt_review.prompt_sha256`。任何欄位更動或資產換版皆使簽章失效。

## 5. 證據路徑分離
審核紀錄必須包含獨立證據檔案路徑：
- `production_evidence`：記錄製作品管審核觀察（例如 `["qa/G001-production.md"]`）。
- `isolation_evidence`：記錄盲審獨立請求審核觀察（例如 `["qa/G001-isolation.md"]`）。

## 6. 示例（合成格式示範，非執行通過紀錄）
```json
{
  "reviewer_id": "獨立QA識別",
  "reviewer_role": "independent_qa",
  "status": "pending",
  "prompt_sha256": "簽章雜湊",
  "checks": {
    "grouping": "pending",
    "self_contained": "pending",
    "reference_binding": "pending",
    "readability": "pending"
  },
  "production_evidence": ["qa/G001-production.md"],
  "isolation_evidence": ["qa/G001-isolation.md"]
}
```
