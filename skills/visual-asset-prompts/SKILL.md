---
name: visual-asset-prompts
description: "從劇本提取角色、場景、道具及多狀態視覺資產，生成文生圖提示詞與統一的 @資產名 清單，並記錄跨場資產的固定布局及狀態。"
---

# 視覺資產提示詞

本次對話首次使用時，由主代理依 [版本檢查](../screenplay-director/references/skill-update-check.md) 核對一次。單獨安裝時，以實際安裝的 Git 提交或 `.ai-film-skills-revision` 比對 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)。有新版先確認是否更新，無法驗證則簡述後繼續。

用劇本、專案設定和正式參考提取角色、場景、道具及需重用的視覺狀態，交付文生圖提示詞和可綁定圖像的 `@資產名`。正文依 [寫作分流](../antigravity-writer/SKILL.md) 或 [單獨安裝備援](references/writer-fallback.md) 撰寫，資產 ID、格式及版本由執行端核對。

## 執行

1. 依 [共用啟動 intake](../screenplay-director/references/startup-intake.md) 沿用既定資料。獨立安裝缺少共用規範時，全新案在對話中顯示一次 `SHOUNG`，只有關鍵缺項才補問，每輪最多 2–3 題。續作、維護及交接沿用既有決策，識別標記留在對話中。
2. 依 [資產提取與狀態規則](references/asset-method.md) 選資產、風格和有效狀態。預設以繁體中文撰寫，沿用使用者指定的語言、劇本鎖定內容與專案術語。
3. 用 [資產庫模板](assets/asset-library-template.md) 交付。核對重要視覺資產、重用狀態、比例、唯一名稱及引用範圍。純文字提示詞直接交付。要求交付生成圖像時，依 [影像品管](../film-quality-control/SKILL.md) 逐圖獨立看圖，缺少共享品管規則或可看圖的獨立審核者時標待審。

## 製作交接

- 提示詞與素材計畫按 [參考圖控制規範](../film-quality-control/references/reference-control.md) 記錄；使用實圖時再核對檔案與控制範圍。分鏡需要視覺草圖時，在分鏡表、正式資產卡及實圖齊備後交給 [25 宮格分鏡草圖](../storyboard-grid/SKILL.md)。
- 以 [跨場資產連續性](../film-quality-control/references/asset-continuity.md) 記錄穩定 ID、固定布局、變化起點及解除依據；共享文件缺少時，把這些項目記入現有資產登錄或製作備註。視覺卡描述外觀及空間，鏡頭調度與表演資料交給 [影片提示詞](../video-prompts/SKILL.md)。
