# AI Film Skills

一組用於 AI 影視創作流程的可攜式 skills，涵蓋劇本開發、台詞診斷、視覺資產提示詞、影片分鏡提示詞，以及 MiniMax H3 影片生成提示詞。

## 包含的 skills

| Skill | 用途 |
|---|---|
| `screenplay-director` | 從靈感到可執行劇本的流程總控、階段判斷與專家銜接 |
| `screenplay-source-analysis` | 原著章節索引、抽樣快評、逐章證據、人物設定演進與改編分集候選 |
| `screenplay-framework` | 建立方向卡、人物設定、專案檔案與故事大綱 |
| `screenplay-writing` | 依專案檔案與大綱擴寫、續寫及修訂劇本 |
| `screenplay-doctor` | 從結構、人物、節奏等角度診斷劇本並提出修改任務 |
| `dialogue-expert` | 逐句診斷台詞，分析角色語言與提出替換建議 |
| `visual-asset-prompts` | 從劇本產生角色、場景、道具與狀態的視覺資產提示詞 |
| `video-prompts` | 產生影片分鏡、時間碼、角色音色與影片生成提示詞 |
| `storyboard-grid` | 依既有分鏡表、資產卡與資產圖生成同畫幅的 5×5 分鏡草圖，超過 25 鏡自動分頁 |
| `film-workbench` | 七階段本地創作台：八欄分鏡與同鏡圖詞、劇本／設定／提示詞／成片／審查、來源差異與原文編輯 |
| `h3-prompt-writing` | 為 MiniMax H3 的 T2VA、I2VA、FL2VA、Ref2VA 等模式撰寫提示詞 |
| `film-quality-control` | 核對分鏡／生成模式、資產版本、生成請求獨立性與雙軌品管證據 |
| `antigravity-writer` | 全套件文字創作與實質修訂的第一分流提供者（Google Antigravity CLI），由 Codex 協同編排與品管 |

## 使用方式

1. 將需要的 skill 資料夾放入你的 agent skill 目錄，例如：

   ```text
   .agents/skills/<skill-name>/
   ```

2. 確認保留各 skill 內的 `SKILL.md` 與 `references/` 參考檔。部分 skill 的 `SKILL.md` 會要求先完整讀取對應的原始工作流程。
3. 在支援 skills 的 agent 中，以 `$skill-name` 呼叫。例如：

   ```text
   $screenplay-framework
   請根據以下題材建立方向卡、人物設定與故事大綱：……
   ```

4. 建議依序使用：`screenplay-framework` → `screenplay-doctor` → `screenplay-writing`；需要影像製作時，再接續使用 `visual-asset-prompts` 與 `video-prompts`。

   已備妥分鏡表、正式資產卡及參考圖片後，可使用 `$storyboard-grid` 生成便於理解分鏡的草圖總覽。每張固定 25 宮格、無格間留白，僅以格線分隔，每格左上角只標原鏡號；整張及各格沿用影片寬高比，超過 25 鏡續頁，末頁空格留白。缺少分鏡表或必要資產卡／圖片時，先警示並停止生成。詳見 [25 宮格分鏡草圖](skills/storyboard-grid/SKILL.md)。

5. 影像製作建議一併安裝 `screenplay-director`、`visual-asset-prompts`、`video-prompts`、`h3-prompt-writing`、`film-quality-control` 與 `antigravity-writer`，保留其相對目錄。共享啟動提問／SHOUNG 文字 LOGO 由導演提供，品管詳細規則、模板及檢查器由 `film-quality-control` 提供，文字創作路由由 `antigravity-writer` 規範。單獨安裝可做其原有純文字工作；缺少共享依賴時，依入口的替代規則標記限制，不能宣稱完成未執行的視覺 QA。

### 每次對話首次使用的版本檢查

在新的 AI 代理對話第一次使用任一 Skill 時，先比較實際安裝版本與本倉庫 `main`。有新版時，使用者可選擇先更新或沿用；同一對話切換 Skill 時沿用查核結果。若從 Git 檢出直接使用或以符號連結安裝，版本取自該檢出。獨立複製時，可在 Skill 目錄放入只含來源完整提交值的 `.ai-film-skills-revision`，更新副本時同步更新這個紀錄。 [版本查核與更新方式](skills/screenplay-director/references/skill-update-check.md)

## 原著改編與本地創作台

已有小說或連載原文時，先以 `$screenplay-source-analysis` 分析指定範圍，再由 `screenplay-framework` 接續定改編方案；抽樣結論與分集候選不能當成正式定稿。索引工具只處理章界、來源變更與覆蓋檢查，原文事實及改編取捨仍需依來源與獨立審核判定。

全新劇本在定大綱或撰寫正文前，先分輪確認題材、年代與世界規則、故事走向、結構及角色。首輪通常 2–4 題，同輪列出可獨立回答的問題與建議，等回覆後再追問有依賴的決策。問到方向足以開工後，整理創作綱要並確認，再交給寫作者。連載案另檢查本集兌現、集尾鉤子的預計兌現位置，以及下集第一個行動如何承接。 [劇本啟動與確認](skills/screenplay-director/references/startup-intake.md#全新劇本分輪訪談) · [連載分集規劃與驗收](skills/screenplay-framework/references/serial-episode-planning.md)

從劇本新編分鏡或重做鏡頭設計時，先依 [分鏡方法庫](skills/video-prompts/references/storyboard-methods.md#依劇本設計分鏡) 拆解場次目的、觀眾視角、戲劇節拍、切鏡理由與跨鏡狀態，再填八欄表。必要的製作說明放表外。參考素材依 [參考圖控制規範](skills/film-quality-control/references/reference-control.md) 記錄，planned 掛圖計畫與 actual 實圖分開，實際生成與 25 宮格草圖的缺圖門檻不變。

以 Python 3.9 以上從本倉庫啟動創作台（不需額外套件）：

```text
python skills/film-workbench/scripts/dashboard_server.py /absolute/path/to/project --port 0 --detach
python skills/film-workbench/scripts/dashboard_server.py /absolute/path/to/project --status
python skills/film-workbench/scripts/dashboard_server.py /absolute/path/to/project --stop
```

在本機瀏覽器開啟指令印出的登入網址。創作台沿用原版七階段介面，直接讀取專案 Markdown／CSV 及 QC 登錄；八欄主表不增欄，選鏡後圖與提示詞一起閱讀。既有九欄表的「修改」保留為附註，MD／CSV 差異與多個媒體候選會提示來源；匯入不改專案。原文編輯支援 Markdown／CSV／TXT，QA JSON 與 HTML 原始碼保持唯讀；儲存時如偵測到外部修改，會提示衝突而不覆蓋。操作說明見 [創作台 README](skills/film-workbench/README.md)。

同一專案重複啟動會沿用既有服務；更新程式後，先對該專案執行 `--stop` 再啟動，才能載入新版本。不要將本機登入網址的權杖公開。

創作台不呼叫生成模型，不將保存視為 QA 通過；顯示的審核值是原檔登錄紀錄，仍須依 [film-quality-control](skills/film-quality-control/SKILL.md) 驗證當前素材、簽章與獨立證據。安裝時請保留各技能內的 `scripts/`、`assets/` 與授權檔。詳細入口見 [film-workbench](skills/film-workbench/SKILL.md)。

## 本套件文字創作分流機制

- 本套件所有文字創作與實質內容修訂（劇本、大綱、人物設定、台詞、分鏡提示詞及視覺資產描述）一律優先路由至 Google Antigravity CLI（`agy`）。此為本套件產出優先級，非全域系統策略。
- Codex 專職流程總控、組裝 Brief、代碼維護、結構檢驗及格式處理，嚴禁悄悄代筆改寫創意內容。
- 僅在未安裝 CLI 或明確配額耗盡（具體 quota 訊號，非一般 429 速率限制、網路逾時、驗證或權限錯誤）時合規降級由 Codex 補位，或因內容過濾明確拒絕時降級至當前預設 LLM。
- 遇網路、逾時、驗證或權限等阻擋性錯誤，必須診斷回報並停止，嚴禁擅自切換代筆；寫作憑據（`provider`, `status`, `reason`, `cli_version`, `conversation_id`）一律記錄於模型提示詞外部。
- 若任務已處於 Antigravity 執行環境中，就地直接執行創作，嚴禁遞迴調用分流腳本。
- 詳細寫作路由與工作流程請參閱 [`skills/antigravity-writer/SKILL.md`](skills/antigravity-writer/SKILL.md) 與 [`skills/antigravity-writer/references/provider-workflow.md`](skills/antigravity-writer/references/provider-workflow.md)。

## 影像品管與提示詞生成規則

- **分鏡表格式**：分鏡表維持固定八欄、每列嚴格對應一個連續鏡頭；使用獨立登錄檔連結鏡號、正式卡、靜幀、生成群組與 QA。
- **生成請求為獨立單元**：一次生成請求（一段 Prompt）可包含單一鏡頭，亦可包含多個連續鏡頭。分組依據為：故事因果與敘事關聯、台詞表演動作停頓時間與介面時長可行性、目標模型與生成模式支援情況、控制精度與重抽重試成本，以及參考資產清晰度。不強制每鏡一提示詞、不設死板鏡頭數限制，亦不超出介面實際時長限制。同場景可依控制需求拆分成多個請求，蒙太奇可依因果合併為單一請求。
- **影片生成模式**：Seedance 與 MiniMax H3 的對白鏡一律採 Ref2VA，在提示詞開頭列出角色聲線及對應音檔。無對白鏡優先採 I2VA 或 FL2VA，兩者皆無法滿足鏡頭需求才採 Ref2VA。I2VA／FL2VA／L2VA 在本流程限單一連續鏡頭。詳見 [模式選擇](skills/film-quality-control/references/mode-and-shot-rules.md#生成模式選擇)。
- **請求自足性與時序狀態補正**：每個生成請求必須包含自身所需之風格描述、聲音語調與顯式綁定資產。特別注意：**人物或道具圖片綁定（`image_inputs`）本身不提供前一鏡的姿態或動作狀態**；跨請求參照必須在提示詞中重述必要的初始狀態，除非實際提交之首幀／接續幀（continuity frame）已提供該狀態。請求內部後向參照（後鏡參照前鏡）若有明確定義屬合法解析；外部全域風格段落不會自動生效。
- **跨場資產連續性**：同一資產沿用穩定識別碼與核准的固定空間。跨場或跨集的造型、場景、道具變化記錄觸發、生效及解除範圍，供資產、分鏡、提示詞與品管共同核對。 [跨場資產連續性](skills/film-quality-control/references/asset-continuity.md)
- **鎖定台詞核對**：在送生成前，以實際模型提示詞對回核准的劇本與分鏡，找出漏句、誤指派、改字、重複及順序問題。跨鏡延續與實際拆句分開記錄。 [鎖定台詞核對](skills/film-quality-control/references/locked-dialogue-reconciliation.md)
- **1080p 單幀空間審核**：生成後安排獨立子代理查看實圖，核對人物、道具與場景的相對位置、方向、可見性和連續性。空間關係難以判讀時，按需要補鳥瞰圖、平面圖、剖面圖或人物位置圖，供核對及修圖。 [靜幀空間品管](skills/film-quality-control/references/visual-qa.md#空間核對與示意圖)
- **提示詞風格與表演**：預設簡潔可讀、單一主動作鏈與清晰運鏡；角色行動目標、觸發點、呼吸與眼神均為創作者內在推理，非必印輸出欄位；時間節奏在需要時採用 0.5 秒網格，非每半秒皆須指令；鎖定台詞與 H3 必要欄位語法嚴格保留；製作備註置於 Prompt 外部。多情境提示詞範例請參閱 [`skills/video-prompts/SKILL.md`](skills/video-prompts/SKILL.md) 與 [`skills/h3-prompt-writing/SKILL.md`](skills/h3-prompt-writing/SKILL.md)。
- **雙軌品管審核**：
  1. **獨立盲測審核**：僅憑該提示詞與實際提交資產／設定（完全隔離劇本隱式上下文與其他 Prompt），審查提示詞可讀性、隱式上下文洩漏、未解析參照、屬性超載與衝突。
  2. **全劇製作審核**：審查分組邏輯、劇本覆蓋度、鎖定台詞一致性、畫面銜接連續性與時長可行性。
  - **審核順序與獨立性**：若由同一獨立審核代理人或審核員執行雙軌審核，必須「先隔離盲測、後全劇製作」，因審核員一旦閱讀全劇後即無法忽視隱式脈絡；禁止作者角色扮演或自審。若無實質獨立之 QA 代理人或獨立真人審核員，審核狀態一律標記為 `pending`。正規表達式（Regex）等代碼檢查能力有限，不設虛構盲測腳本，實質語意審核必須由實質獨立之 QA 代理人或獨立真人審核員執行。
- **審核獨立性與修復流程**：審查員僅唯讀回報問題，由原寫作者（Antigravity 或合規降級之 Codex）修復後再由審查員複審，非一律只能由 Antigravity 處理。每張交付靜幀須由實際獨立 QA 看圖對卡；文字任務做台詞時長與結構審查，不強迫生圖，亦嚴禁偽造通過紀錄。登錄架構與驗證欄位詳見 [`skills/film-quality-control/SKILL.md`](skills/film-quality-control/SKILL.md) 與 [`skills/film-quality-control/references/package-schema.md`](skills/film-quality-control/references/package-schema.md)。

可從 `film-quality-control/assets/package-template.json` 建立登錄，按欄位說明填入真實資料後執行：

```text
python skills/film-quality-control/scripts/validate_package.py /absolute/path/package.json
python skills/film-quality-control/scripts/validate_package.py /absolute/path/package.json --delivery
```

不產出圖片的純文字任務只需相應結構與時長檢查，不因品管流程強迫生圖。QA 缺來源或證據時須列待審，不能填入虛構的通過紀錄。

## 來源與署名

既有劇本開發與提示詞工作流程的原始來源與署名為：**Elio_AIGC（抖音／B站）**。

新增原著分析、本地創作台及本次分鏡／參考控制擴充另參考 **ZenStory AI / drama-skills**，依 MIT 授權借用與改編；固定上游版本及授權全文見 [第三方來源與授權](THIRD_PARTY_NOTICES.md)，新技能內亦保留可獨立分發的授權檔。

場次拆解、切點與關鍵反應、跨場資產狀態、鎖定台詞核對，以及分集兌現與相鄰集承接，部分參考 [漫劇老李 Skill](https://github.com/lixiaoxiao9888-create/manju-laoli-skill/tree/a01e647ac10134918a5de1b18bfe9317e5541a44)（MIT），依本套件的製作流程改寫。改編範圍與授權全文見 [第三方來源與授權](THIRD_PARTY_NOTICES.md#漫劇老李-skill--short-drama-director-suite)。

本次補充的缺漏提問、獨立品管、少量試作及局部修復流程，參考 [FEICAI CLUB 的 ad-storyboarder](https://github.com/feicaiclub/ad-storyboarder)（MIT）後依本倉庫工作流程重新設計。SHOUNG 為本專案的啟動文字識別，不取代原作者署名。沒有引入該倉庫的外部生成服務或執行環境依賴。

## 注意事項

- 各 skill 的具體規則以該 skill 目錄內的 `SKILL.md` 及其參考檔為準。
- 使用前請自行確認內容是否符合你的平台規範、著作權與使用情境。
