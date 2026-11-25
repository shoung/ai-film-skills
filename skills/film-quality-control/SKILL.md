---
name: film-quality-control
description: "核對 AI 影片的分鏡、靜幀空間與資產連續性、生成模式、提示詞獨立性與台詞時長，綜合雙軌審核（製作審查與獨立盲審）並記錄品管證據；適用於影像製作及交付前品管。"
---

# 影像製作品管

本次對話首次使用時，由主代理依 [版本檢查](../screenplay-director/references/skill-update-check.md) 核對一次。單獨安裝時，以實際安裝的 Git 提交或 `.ai-film-skills-revision` 比對 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)。有新版先確認是否更新，無法驗證則簡述後繼續。

依交付範圍品管。新案沿用 [共用啟動 intake](../screenplay-director/references/startup-intake.md) 與已知決策，關鍵缺項才補問，每輪最多 2–3 題。缺少共用 intake 時，全新案在對話中顯示一次 `SHOUNG`，續作及維護延用既有決策。識別標記留在對話中。

審核者唯讀，回報差異、證據及修復建議。實質修訂依 [寫作分流](../antigravity-writer/SKILL.md) 或 [單獨安裝備援](references/writer-fallback.md) 執行，完成後重審。審核證據與寫作憑據放在可提交提示詞外。

## 交付檢查

1. **鏡頭、模式與分組**。八欄分鏡每列是一個連續鏡頭，生成請求依敘事、時長、控制需求與重抽成本分組。I2VA、FL2VA、L2VA 在本流程限單一連續鏡頭。依 [模式選擇與分組](references/mode-and-shot-rules.md) 核對分鏡、模式、起始狀態及掛圖。
2. **素材與連續性**。依 [參考圖控制](references/reference-control.md) 核對每張圖的用途、適用範圍和實際掛圖順序。以 [跨場資產連續性](references/asset-continuity.md) 查對有效的固定布局與起始狀態。交付生成靜幀時，依 [視覺 QA](references/visual-qa.md) 由獨立審核者逐張實看，對照正式卡、鄰鏡與場內狀態；要求 1080p 時另驗交付檔的像素與畫幅。純文字交付無需生成靜幀。
3. **提示詞雙軌審核**。依 [提示詞審核](references/prompt-review.md) 先從當次正文、實際附件及參數獨立盲審，再參照全劇做製作審核，核對覆蓋、分組與連續性。無獨立審核者或無法查閱所需證據時列待審。
4. **台詞與秒數**。有鎖定台詞時，交付可提交提示詞及送生成前依 [鎖定台詞對帳](references/locked-dialogue-reconciliation.md) 核對劇本、分鏡與本次正文。由唯讀審片員依 [台詞與時長審核](references/timing-and-dialogue.md) 核對發音、停頓、情緒及動作耗時。無獨立審片員列待審。
5. **證據和版本**。依 [登錄格式](references/package-schema.md) 將資產、鏡號、生成群組與 QA 記在八欄表之外。版本、語意或雜湊變更時，按受影響範圍重審。只登錄已完成的核對與目前版本的證據。

## 驗證與交付紀錄

從技能目錄執行：

```sh
python3 scripts/validate_package.py /absolute/path/package.json
python3 scripts/validate_package.py /absolute/path/package.json --delivery
```

草稿檢查欄位、鏡號、模式及登錄資料。交付模式另外核對實體資產、檔案雜湊與必要的獨立審核及證據；兩種模式的退出碼都只支持機讀檢查結論。語意、表演可行性及圖像一致性依上述人工或獨立審核證據判定。

使用 [登錄模板](assets/package-template.json)、[提示詞審核模板](assets/prompt-review-template.json)、[視覺待審模板](assets/qa-review-template.json) 及 [時長待審模板](assets/timing-review-template.json)。交付紀錄列範圍、通過、待審或退件及證據路徑。
