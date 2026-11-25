---
name: screenplay-source-analysis
description: 原著分析與改編前置提取技能。負責建立小說章節索引、行號驗證、抽樣快評、逐章提取劇情作用與改編候選，嚴格錨定原文證據並交接下游。
---

# 原著分析與改編前置規範 (screenplay-source-analysis)

本次對話首次使用時，由主代理依 [版本檢查](../screenplay-director/references/skill-update-check.md) 核對一次。單獨安裝時，以實際安裝的 Git 提交或 `.ai-film-skills-revision` 比對 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)。有新版先確認是否更新，無法驗證則簡述後繼續。

原著分析提供可回查的劇情證據與改編候選，由創作者決定取捨。保留原著檔案的文字與編碼，將索引和分析另存。索引工具負責章界、行號、來源版本及覆蓋率，劇情提取與證據查核交由分析者和獨立審核者。

## 工具

從技能目錄以 Python 3.9 以上執行。索引讀取 UTF-8 文字，支援阿拉伯或中文數字（含「兩」）及章、回、集、話、幕、節等章標。需要指定章標時，用 `index --unit` 選擇索引單位。

```bash
python scripts/novel_index.py index <SOURCE_FILE> --out <INDEX_FILE>
python scripts/novel_index.py verify <INDEX_FILE> <SOURCE_FILE>
python scripts/novel_index.py sample <INDEX_FILE> --count <N>
python scripts/novel_index.py coverage <INDEX_FILE> <ANALYSIS_DIR> --require-source-hash [--start <N>] [--end <N>]
```

`sequence` 是索引的連續章序，用於檔名、範圍和進度。`source_number` 保留原書的章號，可跳號、重號或分卷重啟。`line_start`、`line_end` 是原文中的起訖行號。

## 分析流程

1. **確認來源。** 由創作者確認使用權限。以 `輸入/` 或指定路徑的唯讀原文為準，將索引輸出至另一檔案。需要轉成 UTF-8 時，另存工作副本並記錄索引用的檔案。
2. **索引並驗證。** 建立索引後執行 `verify`，通過後以該份索引進行分析。無法自動辨識章界時，先檢查章標單位，必要時手工指定各章 `sequence` 及起訖行，檢查索引的章數與來源 SHA-256 後再執行 `verify`。原文變動時，先由創作者確認本批採用的來源版本，再建新索引。來源或章界改變時，按進度手冊另開批次。 [異常處理與進度](references/progress-record.md)
3. **確定範圍。** 長篇且未指定範圍時，先以 `sample` 選章，依快評範本交付樣本所得，請創作者確認接續分析的章序。短篇、指定範圍或明確要求全拆時，直接進行該範圍的逐章分析。 [抽樣快評範本](references/evidence-and-handoff.md#2-抽樣快評報告規範)
4. **逐章提取。** 以 `ch-<sequence>-extract.md` 記錄角色的抉擇、角色之間或與觀眾的資訊差，以及權力、情感與立場變化。事實結論附索引章序與原文起訖行號，只摘必要詞句，未交代之處標記 `【原文未明確】`。 [證據格式](references/evidence-and-handoff.md#1-證據標註規範) · [來源標記與續跑](references/progress-record.md)
5. **驗證覆蓋後彙總。** 使用上述含來源雜湊檢查的 `coverage` 指令，依進度手冊處理章檔診斷。範圍符合後，彙總劇情單元、高潮排序、人物與設定演進、製作形態和分集候選，標出本輪範圍及跳過的章節。 [改編候選與分集要求](references/evidence-and-handoff.md#3-改編候選提案規格-candidates)
6. **審核與交接。** 記錄獨立 QA 的範圍、證據與待審／通過／退回狀態。交付來源依據、候選及未決問題給 `screenplay-framework`，由創作者裁決取捨，再由 `screenplay-director` 決定後續階段。正式創作依 [antigravity-writer](../antigravity-writer/SKILL.md) 的規範。 [QA 檢核表](references/progress-record.md#4-獨立-qa-狀態管制與檢核表) · [交接清單](references/evidence-and-handoff.md#交接清單)

索引工具的上游版本與授權見 [來源說明](UPSTREAM-NOTICE.md)。
