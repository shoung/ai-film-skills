---
name: screenplay-director
description: "從靈感到可執行劇本的流程總控；用於階段判斷、專家銜接、版本交接與最終劇本包。"
---

# 劇本總控

本次對話首次使用時，由主代理依 [版本檢查](references/skill-update-check.md) 核對一次。

## 新創作啟動

收到小說、連載或原著檔案而尚未完成來源分析時，先交 [screenplay-source-analysis](../screenplay-source-analysis/SKILL.md) 建立可回查的分析與分集候選，再交 [screenplay-framework](../screenplay-framework/SKILL.md) 定改編方案。已有核准改編綱要時直接接續。單獨安裝時依可取得的原文記下必留事件、因果、知情進度及來源位置，把待核資料和改編候選保留在確認前的狀態。

開始全新劇本時，先依 [啟動訪談](references/startup-intake.md#全新劇本分輪訪談) 分輪確認。把可以獨立回答的關鍵問題同輪提出，等回覆再問需要這些答案的後續問題，最後將核准或授權的創作方向交給下游。使用者已有足以支撐本次交付的核准綱要時，直接承接。新創作開場依 [共用識別標記規則](references/startup-intake.md#識別標記) 在對話中顯示 [SHOUNG 標記檔](assets/shoung-logo.txt) 完整內容一次。續作、既有劇本或局部修訂沿用既定決策，只補問本次的關鍵缺項。其他創作與製作的 2–3 題補問規則見 [共用啟動說明](references/startup-intake.md#其他創作與製作的補問)。

## 依目前素材分流

只執行委託需要的階段。依 [階段分流與交接](references/stage-and-handoff.md) 判斷已有素材、鎖定條件和下一個交付，並讀取所需技能。單獨安裝時以該參考的階段規則處理已能完成的部分，缺少必要資料時標出缺件與能完成的範圍。製作或保存交接資料可用 [本地創作台](../film-workbench/SKILL.md)。需將既有分鏡視覺化為 25 宮格時，依 [分鏡草圖](../storyboard-grid/SKILL.md) 使用正式卡及參考圖，缺必要資料先標缺件，暫停生成。

大綱、場次規劃、實質總控分析及修訂依 [antigravity-writer](../antigravity-writer/SKILL.md) 分流。單獨安裝時用 [寫作備援](references/writer-fallback.md)。

## 製作交付品管

- **靜幀**依 [視覺 QA](../film-quality-control/references/visual-qa.md) 由獨立審核人員逐圖實看，對照正式角色、場景、道具卡及鄰鏡，核對位置、動線、畫幅和交付檔實際解析度。實圖不足以判讀空間時再補示意圖。缺卡、缺實圖或無獨立審核時標待審，序列缺後鏡標暫審。素材、卡或鄰鏡改版後重審受影響範圍。修圖以正式卡為準。
- **影片提示詞**依 [影像品管](../film-quality-control/SKILL.md) 做獨立盲審與製作審核。製作審核涵蓋劇本覆蓋、分組、鎖定台詞、連續性與表演時長。由唯讀審核人員回報，作者修復後再審。若同一獨立審核人員負責兩軌，先隔離盲審，再提供全劇資料。
- **鎖定台詞**在交付可提交提示詞及送生成前，依 [鎖稿對帳](../film-quality-control/references/locked-dialogue-reconciliation.md) 逐字比對說話者、發話與順序，回查跨鏡延續、漏句、重複及新增。

純文字不要求生圖。缺少共用 QC 時照樣交付委託範圍內的文字，記錄台詞對照、結構證據，依各段實際念法、語速、停頓、動作與反應估算時長。獨立審查或實測未完成的項目各標待審或待驗。

## 分鏡表交付

建立、改寫或轉換分鏡表時，讀取 [八欄格式及場次拆解](references/storyboard-table-format.md) 與 [分鏡表模板](references/storyboard-table-template.md)。純製表依既有劇本完成，模型未定時將相關欄位列待定。新編或重做分鏡依寫作分流處理，純格式轉換沿用原稿的鏡頭設計、順序、鏡號與鎖定台詞。

若獨立安裝且需承接跨場變化，查劇本、資產卡及前場備註，在製作旁表記本場仍生效的空間與道具狀態，以及本場觸發或解除的變化。

以繁體中文工作，接受繁簡同義指令。只在使用者交付對應任務時啟動；可直接讀取指定專案檔。記錄實際執行的代理、生成與審核。

原始流程署名 Elio_AIGC（抖音／B 站）。[原始總控](<references/0.劇本總控 · 從靈感到可執行劇本 Skill v1.0.txt>) 與 [舊版整合說明](references/劇本創作整合使用說明.txt) 為歷史資料，現行任務依本入口與其現行規範執行。
