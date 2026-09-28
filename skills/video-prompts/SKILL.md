---
name: video-prompts
description: "根據劇本與可選視覺資產庫，依 Seedance 或 MiniMax H3 的指定格式產生影片分鏡提示詞、時間碼及角色音色；用於模型定向的影片提示詞生成。"
---

# 影片提示詞

## 執行方式

1. **先確認模型，後開始寫作**：只要使用者尚未明確指定模型，第一步必須反問：「這次要寫哪一種 prompt 格式：Seedance，還是 MiniMax H3？」在得到明確答案前，不開始產生分鏡、時間碼或完整 prompt；不要自行猜測模型。
2. **依模型切換規則**：
   - 使用者選 **Seedance**：完整讀取 [Seedance 參考指南](references/03_Seedance 提示詞指南.md)、[Seedance 原始工作流程](references/01_視頻提示詞生成SKILL_V2.0_執行主文件.md) 與必要的 [示例庫](references/02_視頻提示詞生成SKILL_V2.0_示例庫.md)，依 Seedance 的提示詞結構與參考素材指代方式撰寫。
   - 使用者選 **MiniMax H3**：改用 [h3-prompt-writing](../h3-prompt-writing/SKILL.md) 及其 `references/` 規則撰寫；不得把 Seedance 的欄位或格式硬套到 H3 prompt。
3. 原文的「貼上本文件」在 Codex 中代表載入此參考檔；使用者可提供專案內檔案路徑，不必重貼全文。
4. 全程使用繁體中文。模型要求保留的欄位名稱、標籤、時間碼或英文台詞，依目標模型規則保留。使用者明確要求與系統規則優先。
5. 僅在使用者確認模型並要求對應創作任務時啟動工作流程；安裝、列出或解說技能時，不執行原文的開場自檢或創作程序。
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

### 模型分流檢查

輸出前確認以下事項：

- 已先取得使用者的模型選擇。
- Seedance 輸出有依據 Seedance reference，並清楚綁定動作、鏡頭與時間節點。
- MiniMax H3 輸出有依據 `h3-prompt-writing` 的模式、欄位順序與參考標籤規則。
- 沒有混用兩種模型的格式，也沒有在未確認模型前生成完整 prompt。

