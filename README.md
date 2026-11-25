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

## 安裝與啟動

將需要的完整 skill 目錄放在代理的技能路徑，例如 `.agents/skills/<skill-name>/`，保留資料夾內的 `SKILL.md`、參考、腳本、資源與授權檔。可用 `$screenplay-framework` 開始建立方向卡與大綱，也可依現有成果直接呼叫對應技能。

搭配多個 skills 時保留彼此的相對目錄。單獨安裝仍可依技能內的格式與備援完成其純文字工作。涉及共用品管、圖片或實際提交時，依入口核對必要素材和獨立證據。第一次使用依 [版本檢查](skills/screenplay-director/references/skill-update-check.md) 核對實際安裝版本。

## 製作流程

- **劇本**。全新劇本依 [啟動訪談](skills/screenplay-director/references/startup-intake.md) 分輪確認，已有核准方向就接續。有原著時用 [原著分析](skills/screenplay-source-analysis/SKILL.md) 建立證據與改編候選，再交框架定案。需要時用醫生診斷、寫作修訂或台詞專家調整。連載另查 [分集規劃與驗收](skills/screenplay-framework/references/serial-episode-planning.md)。
- **分鏡與素材**。新編鏡頭先按 [場次拆解](skills/video-prompts/references/storyboard-methods.md#依劇本設計分鏡)，再填 [八欄分鏡](skills/video-prompts/references/storyboard-table-format.md)。依 [參考圖控制](skills/film-quality-control/references/reference-control.md) 區分計畫與實際素材。分鏡表、正式資產卡與參考圖齊備時可用 [25 宮格草圖](skills/storyboard-grid/SKILL.md)。
- **提示詞與品管**。Seedance 用 [video-prompts](skills/video-prompts/SKILL.md)，MiniMax H3 用 [h3-prompt-writing](skills/h3-prompt-writing/SKILL.md)。實質創作與修訂依 [Antigravity 寫作分流](skills/antigravity-writer/SKILL.md)。交付前依 [film-quality-control](skills/film-quality-control/SKILL.md) 核對模式、資產連續性、鎖定台詞與獨立證據。
- **本地創作台**。以 Python 3.9 以上啟動，依 [工作台操作說明](skills/film-workbench/README.md) 匯入、查看及編輯專案。資料格式見 [原生專案讀取契約](skills/film-workbench/references/native-project-format.md)。

## 維護共用參考

八欄格式、模板、提示詞精簡格式及表演控制的維護來源在 `skills/video-prompts/references/`。單獨安裝用的寫作備援來源在 `skills/antigravity-writer/references/writer-fallback.md`。修改正式來源後執行下列指令，將同步後的副本一併納入變更。

```sh
python3 scripts/sync_skill_references.py
python3 scripts/sync_skill_references.py --check
```

## 來源與署名

既有劇本開發與提示詞工作流程的原始來源與署名為：**Elio_AIGC（抖音／B站）**。

新增原著分析、本地創作台及本次分鏡／參考控制擴充另參考 **ZenStory AI / drama-skills**，依 MIT 授權借用與改編；固定上游版本及授權全文見 [第三方來源與授權](THIRD_PARTY_NOTICES.md)，新技能內亦保留可獨立分發的授權檔。

場次拆解、切點與關鍵反應、跨場資產狀態、鎖定台詞核對，以及分集兌現與相鄰集承接，部分參考 [漫劇老李 Skill](https://github.com/lixiaoxiao9888-create/manju-laoli-skill/tree/a01e647ac10134918a5de1b18bfe9317e5541a44)（MIT），依本套件的製作流程改寫。改編範圍與授權全文見 [第三方來源與授權](THIRD_PARTY_NOTICES.md#漫劇老李-skill--short-drama-director-suite)。

本次補充的缺漏提問、獨立品管、少量試作及局部修復流程，參考 [FEICAI CLUB 的 ad-storyboarder](https://github.com/feicaiclub/ad-storyboarder)（MIT）後依本倉庫工作流程重新設計。SHOUNG 為本專案的啟動文字識別，不取代原作者署名。沒有引入該倉庫的外部生成服務或執行環境依賴。

## 注意事項

- 各 skill 的具體規則以該 skill 目錄內的 `SKILL.md` 及其參考檔為準。
- 使用前請自行確認內容是否符合你的平台規範、著作權與使用情境。
