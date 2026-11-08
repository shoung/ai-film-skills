# AI Film Skills 系統升級實作計畫（2026-11-08）

- **基準版本**：`63e0dc7ec7e6f5940ae4e296b3a9f45b54445ac8`｜**語言**：繁體中文（保留 H3 語法與 Elio_AIGC、FEICAI 署名）
- **範圍定位**：本套件文字產出優先路由至 Google Antigravity CLI（`agy`），非全域系統策略；無 CLI 或配額耗盡時由 Codex 合規補位。

## 1. 核准規格（Approved Specifications）
- **生成單元與工程政策**：Prompt 為獨立審核單元，依因果、對白動作時長、模型模式、成本與資產拆合。單鏡首尾幀為流程穩定政策非官方極限。
- **時序狀態漏洞修補**：圖片綁定不提供前鏡姿態動作；跨請求須重述必要初始狀態，除非實際提交首幀／接續幀已具備。同請求內後鏡參照前鏡合法。
- **精簡可讀與表演**：單一主動作鏈與直觀運鏡；目標、呼吸、眼神為內在推理非必印欄位；可選 0.5 秒網格；鎖定台詞與 H3 必備欄位嚴格保留；備註置外。
- **雙軌審核順序**：同一獨立審查代理人或審查員須先隔離盲測後全劇製作（避免劇本隱式偏見，禁止作者自審或角色扮演）；無實質獨立之 QA 代理人或獨立真人審查員則標記 `pending`。Regex 能力有限不設虛構腳本，須由實質獨立之 QA 代理人或獨立真人審核。
- **缺陷修復**：審查員唯讀回報，由 Antigravity 或合規 Codex 補位作者修訂後複審。文字任務不強迫生圖，嚴禁偽造 PASS 憑據。
- **詳細指引連結**：分流見 [antigravity-writer](../../../skills/antigravity-writer/SKILL.md) 與 [工作流](../../../skills/antigravity-writer/references/provider-workflow.md)；品管見 [film-quality-control](../../../skills/film-quality-control/SKILL.md) 與 [schema](../../../skills/film-quality-control/references/package-schema.md)；範例見 [video-prompts](../../../skills/video-prompts/SKILL.md) 及 [h3](../../../skills/h3-prompt-writing/SKILL.md)。

## 2. 角色分工（Roles）
- **Antigravity Writer**：撰寫 Markdown 文檔、JSON 架構定義與範本、時序狀態補正說明、審核規則與多情境範例。
- **Codex**：實作 `scripts/route_writer.py`、擴充 `scripts/validate_package.py` 結構校驗與自動化測試；僅於無 CLI 或配額耗盡時補位代筆。

## 3. 實際介面（Actual Interfaces）
- **`scripts/route_writer.py` 調用約定**：
  - 參數：`--brief <file> --output <file> [--timeout 180] [--model <model>]`
  - 退出碼：`0`（`written`，Antigravity 成功）、`10`（`fallback`，無 CLI 或配額耗盡由 Codex 補位）、`20`（`blocked`，認證或逾時阻擋）。
  - 輸出欄位：`provider`, `status`, `reason`, `text`, `cli_version`, `conversation_id`。
- **`prompt_review` 結構（不含 prompt/duration/mode 等生成欄位）**：
  - 欄位：`reviewer_id`, `reviewer_role`, `status`, `prompt_sha256`, `checks`（`grouping`, `self_contained`, `reference_binding`, `readability`）、`production_evidence`, `isolation_evidence`。
  - `prompt_sha256` 雜湊覆蓋實際生成欄位：`prompt`, `duration_seconds`, `mode`, `shot_ids`, `image_inputs`, `text_reference_bindings`, `submitted_asset_hashes`（時間戳記獨立不入雜湊）。
  - `text_reference_bindings`：`[{label: "@alias", asset_id: "..."}]`，`asset_id` 須已宣告於 `image_inputs`。

## 4. 驗證核對清單（Verification Checklist）
> 文件撰寫不包含執行測試；未產生真實執行證據前，所有驗證項目均標記為計劃中（PLANNED）。

- [ ] `CLI 正常調用`：Antigravity 產出文本，輸出 `written`，Exit 0（PLANNED）
- [ ] `無 CLI / 配額耗盡`：偵測環境缺失或 quota 信號，輸出 `fallback`，Exit 10（PLANNED）
- [ ] `阻擋錯誤`：認證失敗、網路逾時或一般 429 報錯，輸出 `blocked`，Exit 20（PLANNED）
- [ ] `原生環境防遞迴`：處於 Antigravity 環境時就地寫作，不自調腳本（PLANNED）
- [ ] `時序狀態校驗`：未附首幀／接續幀且跨請求未重述初始狀態者退件（PLANNED）
- [ ] `參照綁定檢驗`：`text_reference_bindings` 之 `@alias` 未宣告於 `image_inputs` 於 `--delivery` 報錯（PLANNED）
- [ ] `雙軌審核順序`：同一審核員先隔離盲測後製作審查；無獨立審核員標記 pending（PLANNED）
- [ ] `雜湊完整性`：`prompt_sha256` 嚴格校驗 generation 欄位與資產雜湊匹配（PLANNED）
- [ ] `靜幀品管證據`：每張交付靜幀具獨立對卡紀錄，純文字任務不虛構 PASS（PLANNED）
