---
name: video-prompts
description: "根據劇本與可選視覺資產庫產生以 Seedance 為主的影片分鏡提示詞、時間碼及角色音色；用於影片提示詞生成。"
---

# 影片提示詞

## 執行方式

1. 完整讀取 [原始工作流程](references/01_视频提示词生成SKILL_V2.0_执行主文件.md) 後，依其規則執行；長檔需分段讀完，不得以截斷內容代替全文。
2. 原文的「貼上本文件」在 Codex 中代表載入此參考檔；使用者可提供專案內檔案路徑，不必重貼全文。
3. 全程使用繁體中文。原文中的指令接受繁簡體同義表達。使用者明確要求與系統規則優先。
4. 僅在使用者要求對應創作任務時啟動工作流程；安裝、列出或解說技能時，不執行原文的開場自檢或創作程序。
5. 原文中的專家角色為分析視角；未實際呼叫工具時，不宣稱已啟動獨立代理、生成圖片或影片。

## 專案內技能銜接

- 劇本總控：[screenplay-director](../screenplay-director/SKILL.md)
- 劇本框架：[screenplay-framework](../screenplay-framework/SKILL.md)
- 劇本寫作：[screenplay-writing](../screenplay-writing/SKILL.md)
- 劇本醫生：[screenplay-doctor](../screenplay-doctor/SKILL.md)
- 台詞專家：[dialogue-expert](../dialogue-expert/SKILL.md)
- 視覺資產：[visual-asset-prompts](../visual-asset-prompts/SKILL.md)
- 影片提示詞：[video-prompts](../video-prompts/SKILL.md)

需要交接時讀取對應入口，不要僅根據技能名稱模擬其完整規則。

遇到風格、視聽錨點、音色或寫法不確定時，讀取 [示例庫](references/02_视频提示词生成SKILL_V2.0_示例库.md)；主流程規則優先。
