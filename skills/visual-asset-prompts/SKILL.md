---
name: visual-asset-prompts
description: "從劇本提取角色、場景、道具及多狀態視覺資產，生成文生圖提示詞與統一的 @資產名 清單。"
---

# 視覺資產提示詞

## 文本創作分流（Writing Provider Routing）

本技能涉及之文生圖提示詞（角色、場景、道具、狀態）與 `@資產名` 視覺特徵描述正文，優先路由至 Google Antigravity CLI（`agy`），由 Codex 負責資產 ID 清單核對、登錄檔維護與格式驗證，不逕自代寫視覺描述。詳見 [antigravity-writer](../antigravity-writer/SKILL.md)。
- **降級與防遞迴**：若已在 Antigravity 內部執行，直接產出提示詞，嚴禁遞迴調用；若未安裝 writer 輔助腳本但存在 `agy` 命令，直接執行無頭調用；僅在 CLI 未安裝或確認配額耗盡時降級至 Codex。遇驗證、權限或網路錯誤應阻擋回報，不隱蔽替換。

## 執行方式

新創作任務沿用 [screenplay-director 的共用啟動 intake](../screenplay-director/references/startup-intake.md)，不重問已知決策；獨立安裝缺少該檔時，僅為全新案在對話中顯示一次 `SHOUNG`，每輪最多補問 2–3 個關鍵缺項；續作、維護、交接不重複。標記不進 prompt 或媒體。純文字資產提示詞不要求生圖。若本次實際交付生成靜幀，依 [film-quality-control](../film-quality-control/SKILL.md) 逐圖獨立看圖與對卡；缺 QC 或獨立審核者時不得宣稱 PASS。

1. 完整讀取 [原始工作流程](references/2.視覺資產提示詞生成SKILL_V1.0.md) 後，依其規則執行；長檔需分段讀完，不得以截斷內容代替全文。
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

轉交影片生成 prompt 時，提醒下游由只讀審片員做 [台詞與時長審核](../film-quality-control/references/timing-and-dialogue.md)；單純資產提取不因此改寫台詞或強迫生成影片。
