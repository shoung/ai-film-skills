---
name: screenplay-director
description: "從靈感到可執行劇本的流程總控；用於階段判斷、專家銜接、版本交接與最終劇本包。"
---

# 劇本總控

本次對話首次使用本套件時，先由主代理完成 [版本檢查](references/skill-update-check.md)。若未安裝共用規範，查 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)，與實際安裝目錄的 Git 提交或 `.ai-film-skills-revision` 比對。確認有新版時先問要更新或沿用，版本無法驗證時簡短說明。本次對話已檢查則沿用結果。

## 新創作啟動

收到小說、連載或原著檔案而尚未完成來源分析時，先交 [screenplay-source-analysis](../screenplay-source-analysis/SKILL.md) 建立有原文位置可回查的分析與分集候選，再交 [screenplay-framework](../screenplay-framework/SKILL.md) 定改編方案。已有核准改編綱要時直接接續，沿用已知的來源證據與改編底線。

開始全新劇本時，先依 [啟動訪談](references/startup-intake.md#全新劇本分輪訪談) 分輪確認。把可以獨立回答的關鍵問題同輪提出，等回覆再問需要這些答案的後續問題，最後將核准或授權的創作方向交給下游。使用者已有足以支撐本次交付的核准綱要時，直接承接。新創作開場依 [共用識別標記規則](references/startup-intake.md#識別標記) 在對話中顯示 [SHOUNG 標記檔](assets/shoung-logo.txt) 完整內容一次。續作、既有劇本或局部修訂沿用既定決策，只補問本次的關鍵缺項。其他創作與製作的 2–3 題補問規則見 [共用啟動說明](references/startup-intake.md#其他創作與製作的補問)。

## 文本創作分流（Writing Provider Routing）

本技能涉及之大綱方向、場次規劃、劇本總控分析與實質修訂，優先路由至 Google Antigravity CLI（`agy`），由 Codex 負責流程總控、格式驗證與檔案讀寫，不逕自改寫創意文案。詳見 [antigravity-writer](../antigravity-writer/SKILL.md)。
- **降級與防遞迴**：若已在 Antigravity 內部執行，直接進行規劃與文案生成，嚴禁遞迴調用；若未安裝 writer 輔助腳本但存在 `agy` 命令，直接執行無頭調用；僅在 CLI 未安裝或確認配額耗盡時降級至 Codex，或因內容過濾明確拒絕時降級至當前預設 LLM。遇驗證、權限或網路錯誤應阻擋回報，不隱蔽替換。

## 靜幀品管

需要交付生成的分鏡靜幀時，遵守 [film-quality-control](../film-quality-control/SKILL.md) 的逐圖規則：每張圖須由獨立 QA 代理實際查看圖片，對照正式核准的角色（含妝造與服裝）、場景、道具卡及可取得的前後鏡。交付序列預期有後鏡但尚未產生時標為暫審，齊套後補核對相鄰鏡頭。缺卡、缺圖或未實際委派獨立 QA 時，不得宣稱 PASS；卡、圖或鄰鏡改版會使相關 QA 失效。不得修改正式卡來迎合錯圖。純劇本、分鏡表或提示詞文字交付不要求生圖。若獨立安裝時找不到 QC skill，照樣可交付文字，但須如實標示靜幀尚未完成獨立品管。

實際生成 1080p 單幀後，安排獨立子代理依 [空間核對與示意圖](../film-quality-control/references/visual-qa.md#空間核對與示意圖) 核對人物、道具與場景的相對位置及動線。若對照實圖仍難判斷，按關鍵問題補一張足以釐清的空間圖，再比對 [跨場資產連續性](../film-quality-control/references/asset-continuity.md) 與前後鏡。

交付影片生成 prompt 時，須依 [film-quality-control](../film-quality-control/SKILL.md) 與 [台詞與時長審核](../film-quality-control/references/timing-and-dialogue.md) 執行雙軌品管：包含製作審核（覆蓋度、分組、時長可行性）與盲測獨立請求審核（無隱式上下文、無未解析參照）。由只讀審片員回報問題，製作者修改後重審，不因純文字交付而跳過。

交付影片生成 prompt 時，另由只讀審片員依 [台詞與時長審核](../film-quality-control/references/timing-and-dialogue.md) 逐段核對台詞、語速、停頓、動作與情緒，判斷秒數過多或不足；不因純文字交付而跳過此項。缺共享文件時仍做上述估算並記錄依據；沒有獨立審核者就標待審，不假稱通過或音訊實測。審片員回報建議，由製作者修改後重審。

有鎖定台詞時，在交付可提交提示詞及實際送生成前做 [劇本、分鏡與提交正文的台詞核對](../film-quality-control/references/locked-dialogue-reconciliation.md)。比對說話者、逐字內容及順序，合併對回跨鏡的同一句台詞，並回報遺漏、重複或新增。

## 分鏡表交付

任務進入分鏡表建立、改寫或格式轉換時，先讀本 skill 的 [八欄分鏡表格式](references/storyboard-table-format.md) 與 [分鏡表模板](references/storyboard-table-template.md)，固定以八欄交付，每列一個連續鏡頭。生成請求為獨立單元，一個生成提示詞可對應單列，亦可依敘事因果、時長可行性與重試成本跨多列；同場景可拆分，蒙太奇可合併。純製表時在此分支依現有劇本完成，不啟動劇本開發流程。純劇本或模型提示詞正文不因此改成表格；交接影片生成時仍遵守目標模型的專用格式。只整理分鏡表不要求先選模型，未知模式與提示詞如實標示待定。

從劇本新編分鏡，或受託重做既有稿的分鏡設計時，先依 [分鏡方法庫的場次拆解](../video-prompts/references/storyboard-methods.md#依劇本設計分鏡) 規劃再填表。若無共享方法庫，先定本場目的與觀眾何時知道什麼，再找觸發、接收者的可見反應與結果，決定哪些節拍留在同一鏡、每個切點帶來什麼。用固定物定位空間與軸線，再把場內位置換成各鏡的畫面方位。交付前依鏡序核對劇本和鎖定台詞，追查人物與道具切出時的狀態及切回時的承接，並交代有意的時空省略。只做格式轉換時，沿用原稿的鏡頭設計、順序、鏡號與鎖定台詞。

若獨立安裝且需承接跨場變化，查劇本、資產卡及前場備註，在製作旁表記本場仍生效的空間與道具狀態，以及本場觸發或解除的變化。

## 執行方式

1. 完整讀取 [原始工作流程](references/0.劇本總控 · 從靈感到可執行劇本 Skill v1.0.txt) 後，依其規則執行；長檔需分段讀完，不得以截斷內容代替全文。
2. 原文的「貼上本文件」在 Codex 中代表載入此參考檔；使用者可提供專案內檔案路徑，不必重貼全文。
3. 全程使用繁體中文。原文中的指令接受繁簡體同義表達。使用者明確要求與系統規則優先。
4. 僅在使用者要求對應創作任務時啟動工作流程；安裝、列出或解說技能時，不執行原文的開場自檢或創作程序。
5. 原文中的專家角色為分析視角；未實際呼叫工具時，不宣稱已啟動獨立代理、生成圖片或影片。

## 專案內技能銜接

- 原著分析：[screenplay-source-analysis](../screenplay-source-analysis/SKILL.md)
- 本地創作台：[film-workbench](../film-workbench/SKILL.md)；查閱八欄分鏡、素材、草圖與 QA 登錄，原文保存不等於生成或審核通過。
- 分鏡草圖：[storyboard-grid](../storyboard-grid/SKILL.md)；需要理解既有分鏡表時，使用正式資產卡與資產圖片生成同畫幅的 25 宮格總覽，缺件先警示並停止生成。
- 劇本總控：[screenplay-director](../screenplay-director/SKILL.md)
- 劇本框架：[screenplay-framework](../screenplay-framework/SKILL.md)
- 劇本寫作：[screenplay-writing](../screenplay-writing/SKILL.md)
- 劇本醫生：[screenplay-doctor](../screenplay-doctor/SKILL.md)
- 臺詞專家：[dialogue-expert](../dialogue-expert/SKILL.md)
- 視覺資產：[visual-asset-prompts](../visual-asset-prompts/SKILL.md)
- 影片提示詞：[video-prompts](../video-prompts/SKILL.md)
- 文字寫作分流：[antigravity-writer](../antigravity-writer/SKILL.md)

需要交接時讀取對應入口，不要僅根據技能名稱模擬其完整規則。

流程銜接另參考 [整合使用說明](references/劇本創作整合使用說明.txt)。
