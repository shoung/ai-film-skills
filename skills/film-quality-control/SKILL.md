---
name: film-quality-control
description: "核對 AI 影片的分鏡、靜幀空間與資產連續性、生成模式、提示詞獨立性與台詞時長，綜合雙軌審核（製作審查與獨立盲審）並記錄品管證據；適用於影像製作及交付前品管。"
---

# 影像製作品管

本次對話首次使用本套件時，先由主代理完成 [版本檢查](../screenplay-director/references/skill-update-check.md)。若未安裝共用規範，查 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)，與實際安裝目錄的 Git 提交或 `.ai-film-skills-revision` 比對。確認有新版時先問要更新或沿用，版本無法驗證時簡短說明。本次對話已檢查則沿用結果。

依本次交付範圍檢查，不自動擴大成生圖或生影任務。新案啟動沿用 [screenplay-director 共用啟動 intake](../screenplay-director/references/startup-intake.md) 與已知決策，僅關鍵阻礙補問（每輪最多 2–3 題）；缺少共用 intake 時，全新案在對話中顯示一次 `SHOUNG`，維護／續作不重複，標記不入 prompt。純文字不要求生圖；交付實際生成靜幀依本技能逐圖獨立看圖，無審核者標待審，不偽造 PASS。

## 文本創作與修復路由（Antigravity CLI 優先）

所有文字修復、提示詞改寫及劇本實質調整，優先路由至 Google Antigravity CLI (`agy`) 撰寫，詳見 [Antigravity 撰寫工作流](../antigravity-writer/SKILL.md)。

Codex 負責品管排程、機讀格式檢驗、雜湊簽章與腳本執行；審片員與審核員（`reviewer_role = "independent_qa"`）採唯讀模式回報問題與修復建議，不自行篡改創作文本。所有實質修訂由 Antigravity 撰寫完成後重審。僅在未安裝 CLI 或確認配額耗盡（具體 quota 訊號，非一般 429、網路、認證、超時或權限錯誤）時降級 Codex，或因內容過濾明確拒絕時降級至當前預設 LLM。已在 Antigravity 執行環境下的工作直接處理，不遞迴調用。審核紀錄與回執嚴格置於提示詞外部。

## 生成請求為獨立單元與分組準則

生成請求（Generation Request）是提示詞製作與品管審核的基本單位，可包含單鏡或多鏡。分組合理性依敘事因果、對白動作、停頓時間、模式能力、重抽成本與素材清晰度審查；非自動一鏡一請求或同場景必合併。八欄分鏡表每列維持一個連續鏡頭。

I2VA/FL2VA/L2VA 限單連續鏡頭為工作流程穩定性政策，非模型能力宣稱；Ref2VA 可支援多鏡。

## 請求自足性與起始狀態

參考計畫與實際素材的對照依 [參考圖控制規範](references/reference-control.md) 審查；計畫圖不能通過為已提交實圖。每張圖的用途與控制邊界、模型掛圖順序及修鏡影響皆納入既有雙軌審核，不以字面鎖定或創作台顯示取代獨立看圖與簽章驗證。

每個生成請求必須完全自足。僅實際隨請求提交的參考素材有效，人物或道具卡不提供先前時序狀態。各請求必須明確建立起始狀態（除非由實際提交之首幀或銜接幀提供）。鎖定台詞逐字對齊。

有跨鏡、跨場或跨集的持續變化時，以 [跨場資產連續性](references/asset-continuity.md) 核對場景固定布局和人物、道具及場景的有效狀態，將所需的可見起始狀態帶入分鏡與提交內容。

## 五項交付門檻與雙軌審核

1. **鏡頭與生成模式相容**：分鏡表每列為一個連續鏡頭；一次生成群組可連結一列或多列。I2VA、FL2VA、L2VA 嚴格限單一連續鏡頭，正文不可暗藏切鏡、反打或蒙太奇。詳讀 [模式與鏡頭規則](references/mode-and-shot-rules.md)。
2. **交付的每張靜幀有獨立視覺 QA**：實際出圖後呼叫 QA 子代理逐張看圖，比對正式參考卡、鏡位、相鄰鏡頭及有效的場內狀態，核對人物、道具、場景及其相對位置。要求 1080p 單幀時，另核對交付檔的實際像素與畫幅。空間關係待釐清時使用場景示意圖，再依修正版本重審。無子代理或無法看圖時標記待審，不以自評代替，不偽造 PASS。純文字不需生圖。執行前讀 [視覺 QA 與修復](references/visual-qa.md)。
3. **版本、簽章與審核證據吻合**：八欄分鏡表維持固定欄位；生成群組、資產與 QA 記錄於獨立登錄檔旁表。修改文本、秒數或素材會使簽章失效，必須重審。欄位見 [登錄格式](references/package-schema.md)。
4. **台詞、表演與秒數相容**：有鎖定台詞時，送生成前依 [鎖定台詞核對](references/locked-dialogue-reconciliation.md) 對照劇本、分鏡與當次提交正文。另由只讀審片員依 [台詞與時長審核](references/timing-and-dialogue.md) 逐段核對發音字數、語速、停頓、情緒與動作耗時；無獨立審片員標待審。
5. **提示詞雙軌審核通過**：包含製作品管審核（覆蓋、分組、台詞、連續性）與盲審獨立請求審核（純 prompt 與實際提交資產，檢驗可讀性、隱性依賴與指令衝突）。詳讀 [提示詞審核規範](references/prompt-review.md)。

## 結構檢查 vs 語意檢查

- **結構檢查（Structure Check）**：由 `scripts/validate_package.py` 驗證 JSON 規格、鏡號連結、模式相容、檔案存在與雜湊簽章。退出碼 0 僅代表機讀結構合規，不能證明視覺特徵一致或表演精準。
  ```text
  python scripts/validate_package.py /absolute/path/package.json
  python scripts/validate_package.py /absolute/path/package.json --delivery
  ```
- **語意檢查（Semantic Check）**：由獨立審核員審閱文本可讀性、表演因果節拍、語速可行性，以及視覺 QA 實際看圖比對。純文字做文本語意審核，嚴禁虛構視覺 PASS。

## 交付紀錄與模板

交付時列出實際檢查範圍、通過項目、待審或退件項目及證據路徑。使用 [登錄模板](assets/package-template.json)、[提示詞審核模板](assets/prompt-review-template.json)、[視覺待審模板](assets/qa-review-template.json) 與 [時長待審模板](assets/timing-review-template.json) 保存真實審核紀錄，模板不含假通過資料。
