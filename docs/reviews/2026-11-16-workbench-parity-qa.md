# Film Workbench 原版功能等價 QA 報告

日期：2026-11-16（Asia/Taipei）
基準：ZenStory `drama-skills` commit `37232f6d22e174c36e321d2e3a1a3ae871e7d602`，以同一公開 EP001 fixture 對照。
被測版本：`ai-film-skills-publish/skills/film-workbench`。

## 結論

本輪指定驗收範圍已通過。reader、view model、HTTP API、編輯衝突、安全邊界及公開 fixture 單元測試全數通過；overview、七個工作階段、分鏡圖詞同鏡閱讀、搜尋/路由、主題、窄版、剪輯時間線與真專案唯讀資料都有操作證據。

IAB 對 QA 子代理不可用。**所有瀏覽器點擊由主代理使用 IAB 代行**；主代理回報 AX 內容、DOM 量測及截圖觀察，本 QA 獨立檢視並判定，沒有宣稱自己親自點擊。讀碼與測試由 QA 子代理獨立執行。

原始公開剪輯 fixture 沒有配音時，原版與移植版都顯示 4 條有資料軌。另在暫存公開 fixture 的三段剪輯單加入明確配音宣告（不新增音檔），原版與移植版都顯示第 5 條配音軌，三段 `.tl-voice` 元素皆存在；兩邊均仍標示未渲染成片。這驗證配音宣告的軌道呈現，不代表音訊檔已製作或實際渲染。

## 功能驗收矩陣

|範圍|結果|證據與限制|
|---|---|---|
|Overview 與製作進度|PASS|公開 fixture 顯示 1 集、八項進度及下一步；重載後沒有虛構的空 project 集。|
|七個工作階段導覽|PASS|EP001 概況、劇本、設定、分鏡、提示詞、成片、審查逐頁操作。概況顯示 2 場；劇本有 SC001/SC002 與台詞；設定 7 項；分鏡 22 鏡/62 秒/平均 2.82 秒並有節奏條及站位；提示詞頁顯示影片詞、首幀詞、圖片詞；審查有 2 項。|
|精確八欄|PASS|真專案 DOM 有 54 個鏡頭 article/table rows；欄序逐字為「編號、畫面描述、攝影機描述、聲音描述、旁白對白、時長、影片生成方式、畫面prompt」。列表及詳情不增加第九欄。|
|圖與提示詞同鏡同屏|PASS|真專案 S01 顯示首幀/尾幀 1920×1080、S01–S21 整張宮格標示、長度 79/506 的提示詞、已載入 4 秒影片；切至 S01A 顯示其首幀、提示詞與已載入影片（5.166667秒），沒有 S01 殘留；S22 顯示 S22–S46 整張宮格與自身提示詞，沒有誤配 S01 圖片。桌面圖詞左右並排。|
|缺少素材與候選標示|PASS|公開 fixture 的缺圖明示「此鏡尚無已登錄圖片」；grid 標整張及鏡號範圍，不冒充單鏡圖；影片候選與來源版本有狀態標示。|
|提示詞全文與複製|PASS|公開 fixture 顯示圖片/影片/首幀詞；真專案實際長提示詞可閱讀，圖詞切鏡同步。點擊公開提示詞複製後，剪貼簿讀回 859 字元且以 `A heavy middle-aged hand` 開頭。|
|剪輯時間線與播放器|PASS|原版與移植版皆顯示 3 cuts/9 秒、畫面/字幕/畫面文字/音效 4 軌，且明示未渲染。暫存公開 fixture 加入明確配音宣告後，兩邊都顯示第 5 條配音軌及 3 個 `.tl-voice` 元素；仍無成片，未新增或假稱音檔已製作。|
|審查|PASS|顯示 MUST 1 / COULD 1，具定位、證據、影響、建議與複製請求；沒有介面批准/點擊通過。|
|搜尋|PASS|「火箭军」命中台詞、MOTION、剪輯結果；點台詞定位 EP001-SC001 並顯示已知台詞；亂詞回無結果；Esc 關閉；Ctrl+K 開啟並聚焦輸入框。|
|深連結與瀏覽歷史|PASS|`#/EP001/board/SHOT-EP001-001` reload 保留同鏡；back 關閉 inspector 回分鏡；forward 恢復同鏡 inspector。|
|多專案/分集切換|PASS|合成兩專案 metadata 使用相同 id，UI selector 仍可選乙→甲；甲 overview 有 2 集。點下一集到 `#/EP002/` 顯示 EP002，再回上一集到 `#/EP001/`；與 API project scope 回歸一致。|
|主題|PASS|按鈕切換 `documentElement.dataset.theme` 至 light 並更新按鈕狀態。|
|窄版|PASS|390px viewport（clientWidth 375）下 inspector 寬 375px、內容單欄 324px，圖與 prompt 同鏡上下排列，stagebar 可橫向捲動。|
|原文編輯及 409 衝突|PASS|公開 demo 筆記可打開編輯並保存，磁碟內容更新；外部修改後舊版本保存被拒、提示未保存並提供複製/載入最新；載入後 editor 顯示外部版本且保存按鈕 disabled。HTTP 測試也驗過 query-string 編輯、版本衝突及目標不一致拒絕。|
|編輯權限與舊專案文件分類|PASS|Node UI contract 用真實 editable/writable metadata 驗證 `.csv/.md/.markdown/.txt` 可編輯、HTML 與 QC JSON 唯讀；舊專案檔案依 tree 上的 episode metadata 分類，`第六版/EP001` 合併為單一、不含斜線的 route id，保留既有 EP001 路由規則。|
|真專案唯讀完整性|PASS|54 鏡、51 提示詞、13 設定在 UI 可見；178 個來源檔重新計算 SHA-256，178/178 匹配、0 變更、0 缺檔。驗收未開讀真劇本全文。|
|HTML 舊總覽安全|PASS|HTML/HTM 以純文字 `<pre>` 顯示，唯讀，script 不執行；有單元測試驗證。|

## 自行執行的測試

最終候選版（含 repo 內可攜公開 fixture）執行：

`python -m unittest discover -s tests -v`

結果：**32 passed / 0 failed / 0 skipped**，9.941 秒。包含 parser、公開 fixture API、真專案唯讀 adapter、八欄/九欄映射、資料來源衝突、鏡號邊界、明確宮格關聯、搜尋、session/cookie、Host/Origin/token、Range、路徑 traversal、query/body 編輯契約、409 與 HTML 唯讀。使用已授權的本機 loopback socket 驗證權限，未遇 Win10013。

另有純 JS contract smoke：viewEpisode、viewSettings、viewFilm、viewReview 4/4 回傳字串，無 TypeError；它只檢查基本輸入輸出形狀，不當作 UI 功能驗收。

## 限制

- 瀏覽器驗收由主代理代行，QA 子代理不能直接使用 IAB；本報告明確以其 AX/DOM/截圖摘要為證據來源。
- 配音第五軌已用暫存 fixture 的宣告資料驗證原版與移植版一致；沒有加入音檔，因此未驗證實際音訊播放或成片渲染。
- 沒有逐像素比對所有階段、所有視窗尺寸或所有媒體類型；本報告只對列出的公開/真專案操作與 API 邊界下結論。

## 證據檔

- 初步 reader/legacy QA：`_work/workbench-audit/qa-parity/reader-legacy.md`
- JS contract smoke：`_work/workbench-audit/qa-parity/js-contract-smoke.md`
- 詳細執行與 CUA 摘要：`_work/workbench-audit/qa-parity/full-unit-api.md`
- 真專案來源初始 hash：`_work/workbench-audit/source-before.json`
- 主代理的 hash 比對結果：`_work/workbench-audit/source-integrity-result.json`

## 補充 CUA 證據（主代理代行，QA 獨立判定）

- 公開提示詞點擊複製後，讀回剪貼簿為 859 字元，開頭為 `A heavy middle-aged hand`：複製操作 PASS。
- 合成兩個專案的 metadata 故意使用相同 id，project selector 仍可切換乙→甲；甲 overview 顯示 2 集，下一集到 `#/EP002/` 並顯示 EP002，上一步回 `#/EP001/`；PASS。這與 API project scoping 測試相符。
- 為驗證條件式第五軌，只在暫存公開 fixture 剪輯單加入配音宣告 `- 配音：0.40 制作成果/audio/L03.mp3`。原版 10793 與移植版 1830 reload 後均顯示 tracks `[画面, 字幕, 画面文字, 音效, 配音]`、各有 3 個 `.tl-voice`，並都保持 `missingFilm=true`。未建立音檔，未聲稱配音已製作或驗證實際音訊渲染；PASS（條件式軌道呈現）。


## 最終程式碼追加回歸（2026-11-16）

主代理追加修正後重跑完整 `python -m unittest discover -s tests -v`：**34 passed / 0 failed / 0 skipped**，12.496 秒。新測試驗證前端按 `writable/editable` metadata 與檔案副檔名呈現編輯能力（CSV、MD、Markdown、TXT 可編輯；HTML、QC JSON 唯讀），也驗證舊專案 episode metadata 分類和「第六版 · EP001」不含 `/` 的單一 route id。新增測試不改變已驗收的真專案第六版識別、公開 EP 路由、圖詞配對或來源檔。



## 最終 CSS 溢出檢查（2026-11-16）

主代理在正式服務 5405 代行 IAB 驗收並回報量測：真專案分鏡頁 `scrollWidth=clientWidth=1265`，54 個 pills 均無溢出；長攝影描述不再造成頁面水平捲動。S01 的圖詞欄寬仍為 378.9/397.9px，三張圖與長度 79/506 的提示詞維持同屏。服務成功載入，截圖沒有全頁水平捲動。這是 CSS-only 修正；產品 JS/Python 未變，因此不重跑單元測試。
