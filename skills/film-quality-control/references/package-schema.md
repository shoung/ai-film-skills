# 資產／鏡頭／生成／QA 登錄

登錄檔是八欄分鏡表的旁表。鏡號穩定，依實際順序排列；插鏡可用 S002A，不必為修一鏡重編全部。只登錄本次正式交付版本，歷史候選另存；不要把未選用候選列進當次正式包。版號與 SHA-256 一起使用，不能只依賴檔名「final」。

`package.json` 採 UTF-8。檔案路徑可絕對或相對；相對以 package 所在資料夾為根。模板的空陣列適用純文字任務，補入真實圖像與真實審核後才是視覺包，不填虛構 hash／QA。

## assets

每項包含 `id`、`role`、`path`、`version`、`sha256`。

- role：`character_card`、`scene_card`、`prop_card`、`frame`。服裝／妝造卡也以 character_card 登錄，id 區分其用途與狀態。
- 正式卡加 `approved: true`，表示有實際批准依據；可另附 `approval_source` 記錄對話或檔案位置。不能因為程式要求而代填批准。
- frame 加 `producer_id`，是產圖代理的真實識別（或使用者／外部來源識別）。獨立 QA 身份不得相同，未知來源先釐清，不以留空規避。
- 可附 `dimensions`、`outfit_state`、`scene_state`、`notes` 供人工核對；目前檢查器不讀取圖像像素或辨識臉部，尺寸仍須實際查圖。

## shots

每項包含 `id`、`reference_asset_ids`；有交付靜幀時加 `frame_asset_id`。同一鏡有首尾兩張或其他關鍵幀時，以主幀在前，將其他幀按時間排序列入 `additional_frame_asset_ids`。這些仍是同一鏡，不能為了存尾幀憑空加一個 Shot。每張幀均須接受獨立 QA。

`duration_seconds`、`outfit_state`、`scene_state`、`continuity_notes` 可附加。`reference_asset_ids` 應列出該鏡正式角色／服裝／妝造／場景／道具依據，避免只把圖列進 assets 卻未綁定鏡頭。

有正式 frame 的鏡頭在交付前至少須綁定一份正式卡；空 references 或只列其他 frame 不能代替正式依據。這只是機讀最低門檻：若圖有人物卻只有場景卡，獨立 QA 仍應因缺身份依據列待審，不能因腳本檢查到「有一份卡」就自動通過。

不是每張圖都適合首幀。作為身份卡的正視照不能直接當作劇情起始畫面；分鏡圖若只供構圖參考，生成群組也要明寫 composition_reference，不能標作 first_frame。

## generations

每項包含 `id`、`mode`、`shot_ids`、`image_inputs`、`prompt`。交付前另填 `duration_seconds`（指定生成段秒數）、`producer_id`（prompt 製作者身份）與 `timing_review`。

- mode：`T2VA`、`I2VA`、`FL2VA`、`L2VA`、`Ref2VA`。可用性仍按目標模型確認。
- shot_ids 是所涵蓋的有序鏡號；一次多鏡生成仍逐鏡對齊。
- image_inputs 每項含 `asset_id`、`role`，以及模型需要的 `label`（例如 Picture 1）。role：`first_frame`、`last_frame`、`identity_reference`、`scene_reference`、`prop_reference`、`composition_reference`。
- prompt 保存本次可提交的完整正文；另外附模型、聲音、設定等 metadata 不影響既有格式。

`timing_review` 格式：

```json
{
  "reviewer_id": "真實獨立QA身份",
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

完成獨立 [時長審核](timing-and-dialogue.md) 後才可把對應項目設為 pass；審核者不能與 producer_id 相同。使用 `generation_signature(generation)` 計算簽章：把 `{prompt,duration_seconds,shot_ids}` 以 `json.dumps(sort_keys=True, ensure_ascii=False, separators=(',', ':'))` 編碼為 UTF-8，計算 SHA-256。檢查器會核對簽章，避免改了台詞或秒數後沿用舊審核；改動其他動作語意也因 prompt 改變而失效。

純提示詞不要求圖片 QA，但仍須逐段台詞／時長審核；只有分鏡表且尚未撰寫生成 prompt 時，可留空 generations，不製造假審核。單元測試以人工 fixture 驗證資料規則，不能視為真人或成片語速實測。

## reviews

最終通過紀錄包含以下欄位。未完成審核可先用待審模板保存，但 `--delivery` 不接受其為通過證據。

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

上例是欄位說明，示意字串不能提交成真實結果。`frame_asset_id` 必須屬於該鏡的主幀或 additional 幀；省略時沿用該鏡主幀。`viewed_assets` 包含該鏡所有正式 reference_asset_ids 與審核當時的 SHA。

按鏡序、再按同鏡幀序將正式幀展開；`neighbor_frames` 包含其中前後最近已提供的靜幀，包含同一鏡的首尾幀，序列首尾只需實際存在的一側。這同時檢查鏡內首尾一致性及跨鏡接續。frame_sha256 記錄被審的當前圖。N/A 寫成 `{"status":"not_applicable","reason":"無人物的地毯污漬特寫"}`，不可沒有理由。逐項觀察與工具看圖證據保存為 evidence 指向的檔案。

修改卡或鄰鏡時，新的實際 hash 使舊視覺審核失效。換 prompt 而改變說話者、動作起點、鏡位、鏡序或參考綁定時，也必須人工使圖像審核的 prompt_alignment 退回待審；時長審核則另由 generation_sha256 檢查失效。本版不自動辨識所有文字與圖像語意。不要用重算 hash 後直接覆蓋舊 QA 的方式假造重審。

## 檢查器的實際邊界

`scripts/validate_package.py` 以 Python 標準函式庫實作，檢查連結、模式、部分切鏡語句、檔案／SHA 與審核紀錄是否完整且仍適用。`--delivery` 需要圖像包的所有正式 assets 存在，卡片已核准、圖有獨立審核與實際證據路徑。

它不辨識圖片內容、不證實使用者的批准、不證實紀錄中的代理真實存在，也不取代讀 prompt 全文；這些由主代理核實。退出碼 0 的意思是「該範圍的機讀檢查通過」，不能寫成「臉部一致性已由程式認證」。
