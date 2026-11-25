---
name: film-workbench
description: 開啟本地 AI 影視創作台，以七階段介面閱讀劇本、設定、八欄分鏡、同鏡圖片與提示詞、成片及獨立 QA；支援既有專案匯入與原文編輯。
---

# 本地 AI 影視創作台 (Film Workbench)

本次對話首次使用時，由主代理依 [版本檢查](../screenplay-director/references/skill-update-check.md) 核對一次。單獨安裝時，以實際安裝的 Git 提交或 `.ai-film-skills-revision` 比對 [上游 main](https://github.com/shoung/ai-film-skills/commits/main/)。有新版先確認是否更新，無法驗證則簡述後繼續。

僅在使用者要求開啟創作台時啟動服務。創作台以七階段介面顯示專案原檔、分鏡、素材與 QA 登錄，並依使用者要求編輯文字檔。瀏覽與儲存的功能範圍以本機檔案為限，生成、渲染與審核各有自己的工作流程。

## 啟動與停止

使用 Python 3.9 以上的標準庫，從技能目錄執行，或把腳本路徑改為絕對路徑。安裝時保留 `scripts/` 與 `assets/dashboard/` 的相對位置。

```bash
python scripts/dashboard_server.py /absolute/project --port 0 --detach
python scripts/dashboard_server.py /absolute/project --status
python scripts/dashboard_server.py /absolute/project --stop
```

在本機瀏覽器開啟輸出的登入網址，或在啟動命令加上 `--open`。網址含本機存取權杖，請妥善保管。同一專案會沿用已執行的服務和網址。更新程式後，用同一專案路徑執行 `--stop` 再重開。

## 讀取與儲存

依 [操作說明](README.md) 查閱七階段、編輯表格或原文。解析以專案原檔及 [原生專案讀取契約](references/native-project-format.md) 為準。檔案版本衝突（HTTP 409）時，載入最新版本並確認合併內容後再儲存。QA JSON 是唯讀登錄，修改創作資料後依 [film-quality-control](../film-quality-control/SKILL.md) 重新審核。
