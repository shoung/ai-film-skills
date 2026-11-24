# 第三方來源與授權

## ZenStory AI / drama-skills

- 來源：https://github.com/zenstory-ai/drama-skills
- 固定版本：`37232f6d22e174c36e321d2e3a1a3ae871e7d602`
- 授權：MIT，Copyright (c) 2026 drama-skills contributors。
- 本次用途：`screenplay-source-analysis` 的章節索引／分析工作流；`film-workbench` 的本機創作台設計、相關程式與視覺資源改編；分鏡方法與參考圖控制工作流參考。
- 改編範圍：繁體中文與本套件入口、八欄 Markdown／CSV 分鏡格式、既有 QC JSON 旁表、圖格瀏覽、獨立 QA、工作台讀寫與啟停功能。沒有整包引入上游五文件格式、供應商 adapter 或剪輯執行器。
- 2026-11-16 創作台等價移植：`film-workbench/assets/dashboard/{index.html,app.js,styles.css,tokens.css}` 以原版完整介面為基礎改編；`film-workbench/scripts/upstream/{creator_views.py,creator_markdown_check.py}` 保留原版文件呈現解析器，旁附 MIT LICENSE。上層以資料適配維持八欄主表；不執行上游生成或剪輯 CLI，也不以移入的文件語法檢查器替代本套件獨立 QA。
- `film-workbench/tests/fixtures/creator-first` 保存同版本 `examples/creator-first` 的公開創作文件，以及上游 `tests/test_dashboard_server.py` 的 CUT_LIST／REVIEW 公開測試資料，供解析及 API 回歸驗證，另附上游授權；不含使用者專案內容。
- 可獨立安裝的上述新技能各附 `LICENSE.upstream`；本通知不取代既有技能的原作者署名。

```text
MIT License

Copyright (c) 2026 drama-skills contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 漫劇老李 Skill / Short-Drama Director Suite

- 來源：[manju-laoli-skill](https://github.com/lixiaoxiao9888-create/manju-laoli-skill)
- 固定版本：`a01e647ac10134918a5de1b18bfe9317e5541a44`（V7.5.0-SLIM）。
- 授權：[MIT](https://github.com/lixiaoxiao9888-create/manju-laoli-skill/blob/a01e647ac10134918a5de1b18bfe9317e5541a44/LICENSE)，Copyright (c) 2026 Short-Drama Director Suite contributors。
- 改編範圍：將場面調度、對白接收與反應、切鏡與留鏡、跨鏡狀態承接等方法改寫為繁體中文，納入現有八欄分鏡工作流程。參考 [場面調度](https://github.com/lixiaoxiao9888-create/manju-laoli-skill/blob/a01e647ac10134918a5de1b18bfe9317e5541a44/short-drama-director/references/blocking-direction.md)、[鏡頭與表演](https://github.com/lixiaoxiao9888-create/manju-laoli-skill/blob/a01e647ac10134918a5de1b18bfe9317e5541a44/sd-storyboard-engine/references/shot-economy-and-acting.md) 與 [剪輯轉場](https://github.com/lixiaoxiao9888-create/manju-laoli-skill/blob/a01e647ac10134918a5de1b18bfe9317e5541a44/sd-qc-engine/references/editing-transition-gate.md)。
- 延伸參考：[場景空間與狀態](https://github.com/lixiaoxiao9888-create/manju-laoli-skill/blob/a01e647ac10134918a5de1b18bfe9317e5541a44/short-drama-director/references/asset-spatial-ledger.md) 與 [連續性台帳](https://github.com/lixiaoxiao9888-create/manju-laoli-skill/blob/a01e647ac10134918a5de1b18bfe9317e5541a44/sd-qc-engine/references/continuity-ledger.md)、[劇本與提示詞台詞比對](https://github.com/lixiaoxiao9888-create/manju-laoli-skill/blob/a01e647ac10134918a5de1b18bfe9317e5541a44/sd-feed-engine/scripts/script_feed_diff.py)、[分集規劃](https://github.com/lixiaoxiao9888-create/manju-laoli-skill/blob/a01e647ac10134918a5de1b18bfe9317e5541a44/sd-script-engine/references/episode-planning.md) 與 [圓桌審閱](https://github.com/lixiaoxiao9888-create/manju-laoli-skill/blob/a01e647ac10134918a5de1b18bfe9317e5541a44/sd-script-engine/references/roundtable-review.md)。資產生效範圍、台詞逐字核對與相鄰集驗收依本套件的格式重新設計。

```text
MIT License

Copyright (c) 2026 Short-Drama Director Suite contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
