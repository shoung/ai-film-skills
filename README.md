# AI Film Skills

一組用於 AI 影視創作流程的可攜式 skills，涵蓋劇本開發、台詞診斷、視覺資產提示詞、影片分鏡提示詞，以及 MiniMax H3 影片生成提示詞。

## 包含的 skills

| Skill | 用途 |
|---|---|
| `screenplay-director` | 從靈感到可執行劇本的流程總控、階段判斷與專家銜接 |
| `screenplay-framework` | 建立方向卡、人物設定、專案檔案與故事大綱 |
| `screenplay-writing` | 依專案檔案與大綱擴寫、續寫及修訂劇本 |
| `screenplay-doctor` | 從結構、人物、節奏等角度診斷劇本並提出修改任務 |
| `dialogue-expert` | 逐句診斷台詞，分析角色語言與提出替換建議 |
| `visual-asset-prompts` | 從劇本產生角色、場景、道具與狀態的視覺資產提示詞 |
| `video-prompts` | 產生影片分鏡、時間碼、角色音色與影片生成提示詞 |
| `h3-prompt-writing` | 為 MiniMax H3 的 T2VA、I2VA、FL2VA、Ref2VA 等模式撰寫提示詞 |
| `film-quality-control` | 核對分鏡／生成模式、資產版本及每張靜幀的獨立視覺 QA 證據 |

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

5. 影像製作建議一併安裝 `screenplay-director`、`visual-asset-prompts`、`video-prompts`、`h3-prompt-writing` 與 `film-quality-control`，保留其相對目錄。共享啟動提問／SHOUNG 文字 LOGO 由導演提供，品管詳細規則、模板及檢查器由 `film-quality-control` 提供。單獨安裝可做其原有純文字工作；缺少共享依賴時，依入口的替代規則標記限制，不能宣稱完成未執行的視覺 QA。

## 影像品管規則

- 分鏡表維持八欄、每列一個連續鏡頭，另用登錄檔連結鏡號、正式卡、靜幀、生成群組與 QA。
- 本流程的 I2VA／FL2VA／L2VA 限單一連續鏡頭；多鏡提示詞應改可用的 T2VA／Ref2VA，或拆成單鏡生成後剪接。此為可靠性政策，目標模型的實際功能另行確認。
- 每張正式交付靜幀須由實際獨立 QA 子代理看圖，核對正式角色／服裝／妝造／場景／道具卡及前後鏡。檔案、來源或鄰鏡變更後，受影響審核必須重做；程式通過不代表視覺一致。
- 只讀審片員逐段核對台詞、發音長度、語速、停頓、情緒與動作，判斷 prompt 秒數是否過多或不足；區分並行與依序動作、合理留白與拖拍。時間審核綁定台詞／秒數版本，文字估算不冒稱成片實測。
- 新創作任務只問尚缺的重要資料，續作沿用既有決策；SHOUNG 文字 LOGO 只在開新案顯示一次，不進圖片或影片提示詞。維護、列清單與單純解說不啟動訪談。

可從 `film-quality-control/assets/package-template.json` 建立登錄，按 [欄位說明](skills/film-quality-control/references/package-schema.md) 填入真實資料後執行：

```text
python skills/film-quality-control/scripts/validate_package.py /absolute/path/package.json --delivery
python -m unittest discover -s skills/film-quality-control/tests -v
```

不產出圖片的純文字任務只需相應結構檢查，不因品管流程強迫生圖。QA 缺來源或證據時須列待審，不能填入虛構的通過紀錄。

## 來源與署名

本倉庫所收錄 skills 的共同來源與署名為：**Elio_AIGC（抖音／B站）**。

本次補充的缺漏提問、獨立品管、少量試作及局部修復流程，參考 [FEICAI CLUB 的 ad-storyboarder](https://github.com/feicaiclub/ad-storyboarder)（MIT）後依本倉庫工作流程重新設計。SHOUNG 為本專案的啟動文字識別，不取代原作者署名。沒有引入該倉庫的外部生成服務或執行環境依賴。

## 注意事項

- 各 skill 的具體規則以該 skill 目錄內的 `SKILL.md` 及其參考檔為準。
- 使用前請自行確認內容是否符合你的平台規範、著作權與使用情境。
