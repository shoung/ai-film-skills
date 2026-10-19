---
name: screenplay-director
description: "從靈感到可執行劇本的流程總控；用於階段判斷、專家銜接、版本交接與最終劇本包。"
---

# 劇本總控

## 新創作啟動

開始全新創作時讀取 [啟動 intake](references/startup-intake.md)，並將 [SHOUNG 標記檔](assets/shoung-logo.txt) 的完整內容原樣獨立顯示一次；它只屬於對話中的創作識別，不得放進劇本、提示詞、圖片或影片。若任務是續作、已有劇本或局部修訂，先沿用既定決策與素材，只問會影響本次工作的關鍵缺項。每輪最多問 2–3 題，分輪補問；不要要求重做開場自檢，也不要在下游交接時重複標記或重問已回答事項。維護、列清單、安裝或解說技能時不顯示標記。

## 靜幀品管

需要交付生成的分鏡靜幀時，遵守 [film-quality-control](../film-quality-control/SKILL.md) 的逐圖規則：每張圖須由獨立 QA 代理實際查看圖片，對照正式核准的角色（含妝造與服裝）、場景、道具卡及可取得的前後鏡。後鏡尚未產生時只能標為暫審，齊套後補做前後鏡核對。缺卡、缺圖或未實際委派獨立 QA 時，不得宣稱 PASS；卡、圖或鄰鏡改版會使相關 QA 失效。不得修改正式卡來迎合錯圖。純劇本、分鏡表或提示詞文字交付不要求生圖。若獨立安裝時找不到 QC skill，照樣可交付文字，但須如實標示靜幀尚未完成獨立品管。

交付影片生成 prompt 時，另由只讀審片員依 [台詞與時長審核](../film-quality-control/references/timing-and-dialogue.md) 逐段核對台詞、語速、停頓、動作與情緒，判斷秒數過多或不足；不因純文字交付而跳過此項。缺共享文件時仍做上述估算並記錄依據；沒有獨立審核者就標待審，不假稱通過或音訊實測。審片員回報建議，由製作者修改後重審。

## 分鏡表交付

任務進入分鏡表建立、改寫或格式轉換時，先讀本 skill 的 [八欄分鏡表格式](references/storyboard-table-format.md) 與 [分鏡表模板](references/storyboard-table-template.md)，固定以八欄交付，每列一個連續鏡頭；生成群組可以跨多列。僅製表時在此分支依現有劇本完成，不啟動劇本開發流程。純劇本或模型提示詞正文不因此改成表格；交接影片生成時仍遵守目標模型的專用格式。只整理分鏡表不要求先選模型，未知模式與提示詞如實標示待定。

## 執行方式

1. 完整讀取 [原始工作流程](references/0.劇本總控 · 從靈感到可執行劇本 Skill v1.0.txt) 後，依其規則執行；長檔需分段讀完，不得以截斷內容代替全文。
2. 原文的「貼上本文件」在 Codex 中代表載入此參考檔；使用者可提供專案內檔案路徑，不必重貼全文。
3. 全程使用繁體中文。原文中的指令接受繁簡體同義表達。使用者明確要求與系統規則優先。
4. 僅在使用者要求對應創作任務時啟動工作流程；安裝、列出或解說技能時，不執行原文的開場自檢或創作程序。
5. 原文中的專家角色為分析視角；未實際呼叫工具時，不宣稱已啟動獨立代理、生成圖片或影片。

## 專案內技能銜接

- 劇本總控：[screenplay-director](../screenplay-director/SKILL.md)
- 劇本框架：[screenplay-framework](../screenplay-framework/SKILL.md)
- 劇本寫作：[screenplay-writing](../screenplay-writing/SKILL.md)
- 劇本醫生：[screenplay-doctor](../screenplay-doctor/SKILL.md)
- 臺詞專家：[dialogue-expert](../dialogue-expert/SKILL.md)
- 視覺資產：[visual-asset-prompts](../visual-asset-prompts/SKILL.md)
- 影片提示詞：[video-prompts](../video-prompts/SKILL.md)

需要交接時讀取對應入口，不要僅根據技能名稱模擬其完整規則。

流程銜接另參考 [整合使用說明](references/劇本創作整合使用說明.txt)。

