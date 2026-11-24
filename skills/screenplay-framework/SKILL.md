---
name: screenplay-framework
description: "將故事靈感轉成方向卡、專案檔案、人物設定與大綱；需要時分析對標作品 DNA。"
---

# 劇本框架

本次對話首次使用本套件時，先由主代理完成 [版本檢查](../screenplay-director/references/skill-update-check.md)。若未安裝共用規範，查 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)，與實際安裝目錄的 Git 提交或 `.ai-film-skills-revision` 比對。確認有新版時先問要更新或沿用，版本無法驗證時簡短說明。本次對話已檢查則沿用結果。

## 全新劇本的入口

開發全新劇本時，先讀 [共用啟動訪談](../screenplay-director/references/startup-intake.md#全新劇本逐題訪談)。沿用上游已確認的創作綱要和授權。以原著改編立項時，若核准改編綱要與來源分析皆缺，先交 [screenplay-source-analysis](../screenplay-source-analysis/SKILL.md) 分析相關範圍。訪談要先查明可取得的事實，每回合以繁體中文提出一個會改變本案的決策，等使用者答覆再追問。確認方向摘要後才開始方向卡、角色設定或大綱。單獨安裝時依同一原則辦理，適用的核准綱要或明確委託直接開工可依授權接續。

## 文本創作分流（Writing Provider Routing）

本技能涉及之方向卡、專案檔案、人物設定、故事大綱及對標 DNA 分析等實質文案創作，優先路由至 Google Antigravity CLI（`agy`），由 Codex 負責任務編排與架構檢核，不逕自代筆原創內容。詳見 [antigravity-writer](../antigravity-writer/SKILL.md)。
- **降級與防遞迴**：若已在 Antigravity 內部執行，直接產出設定與大綱，嚴禁遞迴調用；若未安裝 writer 輔助腳本但存在 `agy` 命令，直接執行無頭調用；僅在 CLI 未安裝或確認配額耗盡時降級至 Codex，或因內容過濾明確拒絕時降級至當前預設 LLM。遇驗證、權限或網路錯誤應阻擋回報，不隱蔽替換。

## 執行方式

以原著改編立項時，讀取原著分析交接中的證據與候選，沿用核准的改編底線、人物動機、關鍵因果及知情進度。由本階段根據來源與已確認方向整合候選，核定後形成正式大綱或角色卡。

編排連載分集大綱或核定分集前，依 [連載分集規劃與驗收](references/serial-episode-planning.md) 核對每集局部兌現、前後集承接、鉤子與兌現紀錄。改編須逐項標示必留事件、來源位置及揭露進度，隨核定大綱交給寫作與會診。未定的候選和缺少正文的相鄰集保留其查核狀態。

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
