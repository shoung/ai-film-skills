---
name: antigravity-writer
description: 全套件文字創作與實質修訂的第一分流提供者（Google Antigravity CLI），由 Codex 負責協同編排、結構驗證與代碼處理。
---

# Antigravity 寫作分流提供者

本次對話首次使用時，由主代理依 [版本檢查](../screenplay-director/references/skill-update-check.md) 核對一次。單獨安裝時，以實際安裝的 Git 提交或 `.ai-film-skills-revision` 比對 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)。有新版先確認是否更新，無法驗證則簡述後繼續。

套件內的文字成果與實質修訂優先交由 Google Antigravity CLI（`agy`）撰寫，包括劇本、提示詞、分析報告及其他非創意文本。Codex 負責組裝寫作需求、流程協調、程式碼與品管。

執行前讀取 [寫作分流協定](references/provider-workflow.md)。該文件包含輔助腳本用法、獨立安裝時的原生命令、退出碼、接替條件與憑據格式。已在 Antigravity 環境中時就地寫作，無需再次派工。
