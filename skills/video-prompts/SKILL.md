---
name: video-prompts
description: "根據劇本編製八欄分鏡表，或依 Seedance／MiniMax H3 格式產生影片提示詞、時間碼及角色音色；支援分鏡表建立與格式轉換。"
---

# 影片提示詞

交付可提交的影片生成 prompt 前，由只讀審片員依 [台詞與時長審核](../film-quality-control/references/timing-and-dialogue.md) 逐段比對劇本台詞與 prompt，綜合發音字數、語速、停頓、情緒、動作及並行／先後順序，檢查秒數不拖不趕。此項適用純文字 prompt，不要求生圖或付費試音；純分鏡表且未寫生成 prompt 則不強迫啟動完整包。缺共享規則時依上述原則估算並列依據；未實際獨立審核則標待審，不宣稱通過。不得新增或刪除鎖定台詞來遷就時間。

新創作任務沿用 [screenplay-director 的共用啟動 intake](../screenplay-director/references/startup-intake.md)，沿用已提供的劇本、設定、模型與先前決策；僅在關鍵資訊無法合理推斷且會阻礙本次輸出時補問，每輪最多 2–3 題。若獨立安裝而缺少共用 intake，全新案在對話中顯示一次 `SHOUNG`；續作、維護、交接不重複，標記不進 prompt 或媒體。純分鏡表或提示詞文字不要求生圖。若本次實際交付生成的靜幀，遵守 [film-quality-control](../film-quality-control/SKILL.md) 逐圖獨立看圖與對卡；缺 QC 或獨立審核者時不得宣稱 PASS。

## 分鏡表交付

使用者要求建立、改寫或轉換「分鏡表」時，先讀 [八欄分鏡表格式](references/storyboard-table-format.md) 與 [分鏡表模板](references/storyboard-table-template.md)，固定使用其八欄與欄序，每列一個連續鏡頭；生成群組可以跨多列。僅製表或轉格式時在此分支完成，不啟動下方模型專用流程；模型未知的欄位如實標示待定。這是外部製作表，不取代下列 Seedance／H3 提示詞正文；只要求模型提示詞時，不自動加一份分鏡表。

## 目前格式規範

先讀 [精簡格式與0.5秒時間規範](references/concise-format.md)，再讀相關工作流程。格式衝突時本規範優先；舊指南的六欄保留，但行動目標、觸發與每段秒數須在動作段內各自換行，不受「只能六行」限制。

參考 [去識別化短範例](references/format-example.md)。只仿格式與內容密度，不沿用示例情節。修訂時不得更動使用者鎖定的段落。

為每列單鏡及 I2VA／FL2VA／L2VA 模式限制，參照 [共用鏡頭與模式規則](../film-quality-control/references/mode-and-shot-rules.md)。這是本工作流程的穩定性政策，不代表所有模型的官方能力界線；目標模型的實際模式依其已確認能力使用。若獨立安裝缺少共用 QC，仍遵守下列單鏡規則，不宣稱官方能力或視覺 QA 已確認。


## 執行方式

1. **先判斷交付類型，再確認模型**：純分鏡表、既有分鏡整理或格式轉換，依上方八欄規範處理，不啟動模型專用工作流程；模型未知的欄位如實標示待定，不代選模型或補造 prompt。需要撰寫或改寫可直接提交的模型專用 prompt 時，沿用使用者已明確指定的模型；尚未指定才先反問：「這次要寫哪一種 prompt 格式：Seedance，還是 MiniMax H3？」得到答案前，不開始模型專用 prompt。
2. **依模型切換規則**：
   - 使用者選 **Seedance**：完整讀取 [Seedance 參考指南](references/03_Seedance 提示詞指南.md)、[Seedance 原始工作流程](references/01_視頻提示詞生成SKILL_V2.0_執行主文件.md) 與必要的 [示例庫](references/02_視頻提示詞生成SKILL_V2.0_示例庫.md)，依 Seedance 的提示詞結構與參考素材指代方式撰寫。
   - 使用者選 **MiniMax H3**：改用 [h3-prompt-writing](../h3-prompt-writing/SKILL.md) 及其 `references/` 規則撰寫；不得把 Seedance 的欄位或格式硬套到 H3 prompt。
   - **兩種模型共同必讀**：開始撰寫或修改人物表演前，完整讀取 [表演控制共通規則](references/performance-control.md)。人物表演必須落實角色目標、情緒起點與轉變、精確觸發點、呼吸／停頓、可見臉部與身體證據，以及不得提前發生的反應；不能只寫「生氣地說」「很悲傷」。這是兩種模型的共同表演要求，不改動各自的輸出格式。
3. 原文的「貼上本文件」在 Codex 中代表載入此參考檔；使用者可提供專案內檔案路徑，不必重貼全文。
4. 全程使用繁體中文。模型要求保留的欄位名稱、標籤、時間碼或英文台詞，依目標模型規則保留。使用者明確要求與系統規則優先。
5. 僅在使用者要求對應任務時啟動工作流程；模型專用提示詞須先確認模型，純分鏡表依八欄規範處理。安裝、列出或解說技能時，不執行原文的開場自檢或創作程序。
6. 原文中的專家角色為分析視角；未實際呼叫工具時，不宣稱已啟動獨立代理、生成圖片或影片。

## 專案內技能銜接

- 劇本總控：[screenplay-director](../screenplay-director/SKILL.md)
- 劇本框架：[screenplay-framework](../screenplay-framework/SKILL.md)
- 劇本寫作：[screenplay-writing](../screenplay-writing/SKILL.md)
- 劇本醫生：[screenplay-doctor](../screenplay-doctor/SKILL.md)
- 臺詞專家：[dialogue-expert](../dialogue-expert/SKILL.md)
- 視覺資產：[visual-asset-prompts](../visual-asset-prompts/SKILL.md)
- 影片提示詞：[video-prompts](../video-prompts/SKILL.md)

需要交接時讀取對應入口，不要僅根據技能名稱模擬其完整規則。

遇到風格、視聽錨點、音色或寫法不確定時，讀取 [示例庫](references/02_視頻提示詞生成SKILL_V2.0_示例庫.md)；主流程規則優先。

### 模型分流檢查（模型專用提示詞交付）

交付模型專用提示詞前確認以下事項；純分鏡表改用其 reference 的交付前核對：

- 已先取得使用者的模型選擇。
- Seedance 輸出有依據 Seedance reference，並清楚綁定動作、鏡頭與時間節點。
- MiniMax H3 輸出有依據 `h3-prompt-writing` 的模式、欄位順序與參考標籤規則。
- 已依共通規則核對人物表演：觸發先於反應、轉移注意力時眼神先於頭部、動作自然連續，並保留可讀的呼吸／停頓與收束；無臺詞也有明確動作、視覺或聲音觸發點。
- 表演寫入目標模型既有欄位；沒有新增心理分析欄位、套用不合劇情的眼淚，或以多餘微動作壓過主要行動。
- 沒有混用兩種模型的格式，也沒有在未確認模型前生成完整 prompt。

