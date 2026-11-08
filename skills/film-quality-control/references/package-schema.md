# 資產／鏡頭／生成／QA 登錄

登錄檔為八欄分鏡表旁表。鏡號穩定，依實際順序排列；插鏡使用 S002A，不必為修一鏡重編全表。只登錄本次正式交付版本，未選用候選不列入當次正式包。版號與 SHA-256 並用。`package.json` 採 UTF-8，相對路徑以 package.json 所在目錄為根。空陣列適用純文字任務，補入真實圖像與審核後才是視覺包，不填虛構 hash／QA。純提示詞任務不要求圖片 QA，分鏡表尚未撰寫提示詞時可留空 generations。

## assets
每項包含 `id`、`role`、`path`、`version`、`sha256`。
- `role`：`character_card`、`scene_card`、`prop_card`、`frame`。服裝／妝造卡亦以 character_card 登錄，id 區分其用途與狀態。
- 正式卡加 `approved: true`，表示有實際批准依據；可另附 `approval_source` 記錄對話或檔案位置。不可代填批准。
- frame 加 `producer_id`，為產圖代理（或使用者／外部來源）之真實識別。獨立 QA 身份不得與 producer_id 相同，未知來源應先釐清，不可留空規避。
- 可附 `dimensions`、`outfit_state`、`scene_state`、`notes` 供人工核對；檢查器不辨識圖像像素或臉部，尺寸需實際查圖。

## shots
每項包含 `id`、`reference_asset_ids`；交付靜幀時加 `frame_asset_id`。
- 同一鏡有首尾兩張或其他關鍵幀時，以主幀在前，其他幀按時間排序列入 `additional_frame_asset_ids`，仍屬同鏡，不可為存尾幀憑空新增鏡號。每張幀均須接受獨立 QA。
- `duration_seconds`、`outfit_state`、`scene_state`、`continuity_notes` 可附加。`reference_asset_ids` 應列出該鏡正式依據，避免僅將圖列入 assets 卻未綁定鏡頭。
- 有正式 frame 的鏡頭在交付前至少須綁定一份正式卡；空 references 或僅列其他 frame 不能代替正式依據（若圖有人物卻僅有場景卡，獨立 QA 仍應因缺身份依據列為待審）。
- 不是每張圖都適合首幀。正視身份卡不能直接當作劇情起始畫面；分鏡圖若僅供構圖參考，應標註為 composition_reference，不能標為 first_frame。

## generations
每項包含 `id`、`mode`（`T2VA`、`I2VA`、`FL2VA`、`L2VA`、`Ref2VA`）、`shot_ids`、`prompt`、`duration_seconds`、`producer_id`。純提示詞任務不要求圖片 QA，但須逐段進行台詞時長與提示詞審核；若僅有分鏡表而尚未撰寫 prompt，可保持 `generations: []`。
- **image_inputs**：每項含 `asset_id`、`role`（`first_frame`、`last_frame`、`identity_reference`、`scene_reference`、`prop_reference`、`composition_reference`）及模型所需 `label`（如 Picture 1；正文引用時必填，未引用可選）。H3 `<Subject N>` 定義由提交之 `<Picture N>` 解析。音訊／視訊參考若 package schema 尚未機讀支援，應列為待人工審核之警示並附證據，嚴禁偽報為圖片資產；機器警示需人工情境證據判定，非一律硬性阻擋。
- **text_reference_bindings**：陣列項為 `{label, asset_id}`，供正文 `@alias` 綁定；其 `asset_id` 必須已在 `image_inputs` 中明確宣告。台詞中提及前鏡純屬劇情文本，不可視為元數據引用。
- **timing_review**：格式如下：
```json
{
  "reviewer_id": "真實獨立QA識別",
  "reviewer_role": "independent_qa",
  "status": "pending",
  "generation_sha256": "審核當時的段落簽章",
  "checks": {
    "dialogue_alignment": "pending",
    "delivery_feasibility": "pending",
    "pace_balance": "pending"
  },
  "evidence": ["qa/G001-timing.md"]
}
```
簽章計算使用 `generation_signature(generation)`：涵蓋 `{prompt, duration_seconds, shot_ids}`，以 `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))` 編碼為 UTF-8 計算 SHA-256。三項 checks 均 pass 方可合格，審核者不得與 producer_id 相同。

- **prompt_review**：雙軌審核紀錄，交付模式必填：
```json
{
  "reviewer_id": "真實獨立QA識別",
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
簽章合約：`from prompt_checks import prompt_signature`，傳入 generation 與 `assets_by_id` 字典。雜湊涵蓋 `prompt`、`duration_seconds`、`mode`、`shot_ids`、`image_inputs`、`text_reference_bindings`，以及實際提交資產的 `submitted_asset_hashes: {asset_id: sha256}`。採用 `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')` 計算 SHA-256。4 項 checks 通過且 `reviewer_id != producer_id` 方可為 pass。模板保留 null/pending，不填入虛構 pass。

## reviews
靜幀交付通過紀錄包含以下欄位：
```json
{
  "id": "QA-S001-v1",
  "shot_id": "S001",
  "frame_asset_id": "FRAME-S001-v1",
  "frame_sha256": "當前圖的真實SHA256",
  "reviewer_id": "實際QA子代理識別",
  "reviewer_role": "independent_qa",
  "status": "pass",
  "viewed_assets": {"CHAR-09-v1": "被實際核對的正式卡SHA256"},
  "neighbor_frames": {"FRAME-S002-v1": "被核對的鄰鏡SHA256"},
  "checks": {
    "identity": "pass", "wardrobe": "pass", "makeup": "pass",
    "scene": "pass", "continuity": "pass", "prompt_alignment": "pass"
  },
  "evidence": ["qa/QA-S001-v1.md"]
}
```
- `frame_asset_id` 必須屬於該鏡主幀或 additional 幀；省略時預設沿用該鏡主幀。
- `viewed_assets` 包含該鏡所有正式 reference_asset_ids 與審核當時的 SHA。
- 鄰幀展開邏輯：按鏡序、再按同鏡幀序將正式幀展開（flatten shots then frames）；`neighbor_frames` 包含其中前後最近已提供的靜幀（包含同一鏡首尾幀，序列首尾只需實際存在的一側）。
- N/A 寫成 `{"status":"not_applicable","reason":"無人物的道具特寫說明"}`，不可沒有理由。
- 修改卡片或換 prompt 改變語意（說話者、動作起點、鏡位、鏡序或參考綁定）時，必須手動使圖像審核之 `prompt_alignment` 退回待審；時長與提示詞審核則由相應簽章檢查失效，嚴禁直接覆蓋舊 hash 假造審核。

## 檢查器的實際邊界
`scripts/validate_package.py` 以標準函式庫驗證連結、模式、切鏡語句、檔案／SHA 與簽章合約。草稿模式未附 `prompt_review` 或簽章不符發出 Warning；`--delivery` 模式強制要求正式 assets 存在、卡片已核准、frame 及 prompt 有獨立 pass 審核與證據檔案。機器警告需人工情境證據判定，非一律硬性阻擋。純提示詞審查不要求媒體生成。退出碼 0 代表機讀格式合規，不取代語意與畫質實質審核。所有範例均為合成格式示範，非執行通過紀錄。
