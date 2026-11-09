---
name: screenplay-framework
description: "將故事靈感轉成方向卡、專案檔案、人物設定與大綱；需要時分析對標作品 DNA。"
---

# 劇本框架

## 文本創作分流（Writing Provider Routing）

本技能涉及之方向卡、專案檔案、人物設定、故事大綱及對標 DNA 分析等實質文案創作，優先路由至 Google Antigravity CLI（`agy`），由 Codex 負責任務編排與架構檢核，不逕自代筆原創內容。詳見 [antigravity-writer](../antigravity-writer/SKILL.md)。
- **降級與防遞迴**：若已在 Antigravity 內部執行，直接產出設定與大綱，嚴禁遞迴調用；若未安裝 writer 輔助腳本但存在 `agy` 命令，直接執行無頭調用；僅在 CLI 未安裝或確認配額耗盡時降級至 Codex，或因內容過濾明確拒絕時降級至當前預設 LLM。遇驗證、權限或網路錯誤應阻擋回報，不隱蔽替換。

## 執行方式

1. 完整讀取 [原始工作流程](references/1.劇本框架 · 項目檔案生成 Skill v2.0.txt) 後，依其規則執行；長檔需分段讀完，不得以截斷內容代替全文。
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
- 文字寫作分流：[antigravity-writer](../antigravity-writer/SKILL.md)

需要交接時讀取對應入口，不要僅根據技能名稱模擬其完整規則。
