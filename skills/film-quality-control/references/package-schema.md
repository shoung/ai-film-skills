# 資產／鏡頭／生成／QA 登錄

登錄檔為八欄分鏡表旁表。鏡號穩定，依實際順序排列；插鏡使用 S002A，不必為修一鏡重編全表。只登錄本次正式交付版本，未選用候選不列入當次正式包。版號與 SHA-256 並用。`package.json` 採 UTF-8，相對路徑以 package.json 所在目錄為根。空陣列適用純文字任務，補入真實圖像與審核後才是視覺包，不填虛構 hash／QA。純提示詞任務不要求圖片 QA，分鏡表尚未撰寫提示詞時可留空 generations。

## assets
每項包含 `id`、`role`、`path`、`version`、`sha256`。
- `role`：`character_card`、`scene_card`、`prop_card`、`frame`。服裝／妝造卡亦以 character_card 登錄，id 區分其用途與狀態。
- 正式卡加 `approved: true`，表示有實際批准依據；可另附 `approval_source` 記錄對話或檔案位置。不可代填批准。
- frame 加 `producer_id`，為產圖代理（或使用者／外部來源）之真實識別。獨立 QA 身份不得與 producer_id 相同，未知來源應先釐清，不可留空規避。
- 可附 `dimensions`、`outfit_state`、`scene_state`、`notes` 供人工核對；要求 1080p 單幀時，從交付檔讀取實際寬高並記在 `dimensions` 或 QA 證據。檢查器不辨識圖像像素或臉部。

## shots
每項包含 `id`、`reference_asset_ids`；交付靜幀時加 `frame_asset_id`。
- 同一鏡有首尾兩張或其他關鍵幀時，以主幀在前，其他幀按時間排序列入 `additional_frame_asset_ids`，仍屬同鏡，不可為存尾幀憑空新增鏡號。每張幀均須接受獨立 QA。
- `duration_seconds`、`outfit_state`、`scene_state`、`continuity_notes` 可附加。`reference_asset_ids` 應列出該鏡正式依據，避免僅將圖列入 assets 卻未綁定鏡頭。
- 適用的資產狀態可在 `continuity_notes` 指向 [跨場資產連續性](asset-continuity.md) 條目、來源與生效節拍，共用穩定 ID 和固定布局。狀態圖依既有資產角色登錄，文件或示意圖可作為 QA 文字證據的引用。
- 有正式 frame 的鏡頭在交付前至少須綁定一份正式卡；空 references 或僅列其他 frame 不能代替正式依據（若圖有人物卻僅有場景卡，獨立 QA 仍應因缺身份依據列為待審）。
- 不是每張圖都適合首幀。正視身份卡不能直接當作劇情起始畫面；分鏡圖若僅供構圖參考，應標註為 composition_reference，不能標為 first_frame。

## generations
每項包含 `id`、`mode`（`T2VA`、`I2VA`、`FL2VA`、`L2VA`、`Ref2VA`）、`shot_ids`、`prompt`、`duration_seconds`、`producer_id`。純提示詞任務不要求圖片 QA，但須逐段進行台詞時長與提示詞審核；若僅有分鏡表而尚未撰寫 prompt，可保持 `generations: []`。
- **image_inputs**：每項含 `asset_id`、`role`（`first_frame`、`last_frame`、`identity_reference`、`scene_reference`、`prop_reference`、`composition_reference`）及模型所需 `label`（如 Picture 1；正文引用時必填，未引用可選）。H3 `<Subject N>` 定義由提交之 `<Picture N>` 解析。音訊／視訊參考若 package schema 尚未機讀支援，應列為待人工審核之警示並附證據，嚴禁偽報為圖片資產；機器警示需人工情境證據判定，非一律硬性阻擋。
- **text_reference_bindings**：陣列項為 `{label, asset_id}`，供正文 `@alias` 綁定；其 `asset_id` 必須已在 `image_inputs` 中明確宣告。台詞中提及前鏡純屬劇情文本，不可視為元數據引用。
- **timing_review** 使用 [時長審核模板](../assets/timing-review-template.json)。簽章 `generation_sha256` 由 `generation_signature(generation)` 算出，涵蓋 `prompt`、`duration_seconds`、`shot_ids`。將這些欄位以 `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)` 序列化、編碼為 UTF-8 後計算 SHA-256。三項 `checks` 均須通過，且 `reviewer_id` 與 `producer_id` 不同。
- **prompt_review** 使用 [提示詞審核模板](../assets/prompt-review-template.json)。`prompt_sha256` 由 `prompt_checks.prompt_signature(generation, assets_by_id)` 算出，涵蓋 `prompt`、`duration_seconds`、`mode`、`shot_ids`、`image_inputs`、`text_reference_bindings`，以及當次圖片資產的 `submitted_asset_hashes: {asset_id: sha256}`，沿用上述 JSON 序列化與 SHA-256。四項 `checks` 均須通過，且 `reviewer_id` 與 `producer_id` 不同。兩軌應留獨立證據，詳見 [提示詞審核](prompt-review.md)。

## reviews
草稿可用 [視覺待審模板](../assets/qa-review-template.json)。實際看圖後填入 `frame_sha256` 與證據。以下為合成的靜幀通過紀錄格式：
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
- 空間與狀態觀察記在 `scene`、`continuity` 對應的 `evidence` 檔。若核對了同場較早或跨集的實圖、布局／狀態條目或示意圖，證據一併記錄所用路徑、版本及可取得的雜湊。這些補充依據仍需人工核對。
- N/A 寫成 `{"status":"not_applicable","reason":"無人物的道具特寫說明"}`，不可沒有理由。
- 修改卡片或換 prompt 改變語意（說話者、動作起點、鏡位、鏡序或參考綁定）時，必須手動使圖像審核之 `prompt_alignment` 退回待審；布局、狀態或示意圖修正改變空間預期時，同樣使受影響的 `scene`、`continuity` 與審核整體狀態退回待審。時長與提示詞審核依相應簽章檢查失效；用實際重審版本的雜湊與新證據更新紀錄。

## 檢查器的實際邊界
`scripts/validate_package.py` 在草稿模式檢查欄位、關聯、模式與切鏡規則，缺少時長或提示詞複核、簽章不符時發出警告。`--delivery` 另核對正式資產檔案與 SHA-256、卡片核准狀態、每張正式幀的獨立審核及證據，並要求每個生成請求的 `timing_review` 與 `prompt_review` 通過、簽章相符及證據檔案存在。機器警告由審核者依實際情境判定。退出碼 0 僅代表通過機讀檢查。
