---
name: screenplay-writing
description: "依專案檔案及已確認大綱擴寫劇本、續寫場次、依會診報告修訂或整合臺詞修改。"
---

# 劇本寫作

本次對話首次使用本套件時，先由主代理完成 [版本檢查](../screenplay-director/references/skill-update-check.md)。若未安裝共用規範，查 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)，與實際安裝目錄的 Git 提交或 `.ai-film-skills-revision` 比對。確認有新版時先問要更新或沿用，版本無法驗證時簡短說明。本次對話已檢查則沿用結果。

## 全新劇本的入口

直接收到全新劇本委託時，先確認有無適用的核准創作綱要、鎖定大綱或上游確認紀錄。創作方向尚未核准時依 [共用啟動訪談](../screenplay-director/references/startup-intake.md#全新劇本逐題訪談) 處理。單獨安裝時先查可取得的資料，每回合以繁體中文問一個關鍵決策，等回覆再追問，摘要確認後才開始實質寫作。已有核准方向或已受託直接開工時依授權接續。新案所需的大綱與人物設定可在方向確立後由框架銜接。已有劇本、續寫、局部改稿或純格式轉換依其既有材料和指定範圍處理。

## 文本創作分流（Writing Provider Routing）

本技能涉及之劇本正文擴寫、分場劇本撰寫、場次續寫及依據診斷報告的實質修訂，一律優先路由至 Google Antigravity CLI（`agy`），由 Codex 負責任務編排、章節對照與版本比對，不逕自代筆撰寫劇本文本。詳見 [antigravity-writer](../antigravity-writer/SKILL.md)。
- **降級與防遞迴**：若已在 Antigravity 內部執行，直接產出劇本文案，嚴禁遞迴調用；若未安裝 writer 輔助腳本但存在 `agy` 命令，直接執行無頭調用；僅在 CLI 未安裝或確認配額耗盡時降級至 Codex，或因內容過濾明確拒絕時降級至當前預設 LLM。遇驗證、權限或網路錯誤應阻擋回報，不隱蔽替換。

## 執行方式

連載分集的擴寫與敘事修訂，依 [連載分集規劃與驗收](../screenplay-framework/references/serial-episode-planning.md) 讀取核定大綱、鉤子紀錄與可得的相鄰集，將局部兌現與承接寫進正文。按本案時長及表演節奏編排，完成後做正文冷讀，更新鉤子兌現與待查項。單獨安裝時，把本集目標、阻力、換策與結果，前後集的狀態和第一個承接動作，以及主要鉤子的設置、預計和實際兌現位置記入既有創作筆記。原著改編另核對必留事件、來源與知情進度。只有製作者可讀稿時以「製作者自查」記錄，缺相鄰集正文則標待驗。

1. 完整讀取 [原始工作流程](references/2.劇本寫作 · 大綱擴寫與修訂 Skill v1.0.txt) 後，依其規則執行；長檔需分段讀完，不得以截斷內容代替全文。
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
