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

## 來源與署名

本倉庫所收錄 skills 的共同來源與署名為：**Elio_AIGC（抖音／B站）**。

## 注意事項

- 各 skill 的具體規則以該 skill 目錄內的 `SKILL.md` 及其參考檔為準。
- 使用前請自行確認內容是否符合你的平台規範、著作權與使用情境。
