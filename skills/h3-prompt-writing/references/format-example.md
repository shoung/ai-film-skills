# H3 精簡格式範例

本範例示範 MiniMax H3 基礎模式與全參考（Ref2VA）模式的提示詞結構。製作備註置於提示詞正文之外。以下展示三種典型合成範例。

---

## 模式一：單一鏡頭 6 秒拿杯動作（Base T2VA 獨立請求）

備註：群組 G001（分鏡 S001）｜模式 T2VA｜時長 6.00 秒｜假設輸入：無｜分組依據：偏好單一連續事件完整呈現。

```text
integrated_multimodal_description: [Shot 1] 真實電影質感，平視中近景。晨光照耀的木桌前，一名男子安靜坐著。男子伸手端起桌上的白色陶瓷水杯喝水，隨後平穩放回桌面並收回右手。固定機位。

overall_soundscape: 水杯接觸木桌的清脆碰撞聲與安靜室內底噪。

non_diegetic_music: N/A
```

---

## 模式二：單一請求 8 秒兩鏡自然連接（Base T2VA 開空櫃與對白）

備註：群組 G002（分鏡 S002、S003）｜模式 T2VA｜時長 8.00 秒｜假設輸入：無｜分組依據：開櫃與困惑發話為連續因果事件，合併為單一請求以維持連貫。

```text
integrated_multimodal_description: [Shot 1] 真實電影質感，平視中景。廚房內一名女子站在高處木質櫥櫃前，伸手拉開櫃門，展現空無一物的內部層架。固定機位。[Shot 2] At 00:04.000, 切至女子正面近景，鏡頭緩慢微推。女子注視空置層架，帶著困惑語氣 (S1) 說道：<d>[Chinese] 沒有了？</d> 說完後維持凝視。

overall_soundscape: 木櫃門開啟的摩擦聲。

non_diegetic_music: N/A
```

---

## 模式三：跨請求獨立承接（Ref2VA 拿盒與放盒）

### 請求 A：拿起木盒

備註：群組 G003（分鏡 S004）｜模式 Ref2VA｜時長 4.00 秒｜假設輸入：<Picture 1>（人物甲 CHAR-01）、<Picture 2>（木盒 PROP-01）｜分組依據：取物動作起點，獨立請求確保動勢完整。

```text
subject_definitions:
<Subject 1>：<Picture 1> 中的男子。
<Subject 2>：<Picture 2> 中的木盒。

summary:
[reference generation] 在 4.00 秒的真實電影質感鏡頭中，<Subject 1> 於工作桌前伸手將 <Subject 2> 平穩抱起至胸前。

retention_analysis:
<Subject 1>: fully_preserved - 人物外貌與服裝特徵保持一致。
<Subject 2>: fully_preserved - 木盒外觀與尺寸保持一致。

detailed_description:
真實電影質感，室內暖調側光。[Shot 1] 起始狀態為 <Subject 2> 平放於工作桌上，<Subject 1> 雙手尚未接觸木盒。固定平視中景。<Subject 1> 雙手向前伸出，平穩托起 <Subject 2> 兩側並抱至胸前站定。

overall_soundscape:
木盒自桌面抬起時的微弱聲響。

non_diegetic_music:
N/A
```

### 請求 B：將木盒放入抽屜

備註：群組 G004（分鏡 S005）｜模式 Ref2VA｜時長 4.00 秒｜假設輸入：<Picture 1>（人物甲 CHAR-01）、<Picture 2>（木盒 PROP-01）、<Picture 3>（抽屜 PROP-02）｜分組依據：放物獨立段落，以自身資產與初始狀態自足承接。

```text
subject_definitions:
<Subject 1>：<Picture 1> 中的男子。
<Subject 2>：<Picture 2> 中的木盒。
<Subject 3>：<Picture 3> 中的抽屜。

summary:
[reference generation] 在 4.00 秒的真實電影質感鏡頭中，<Subject 1> 將手中的 <Subject 2> 平穩放入拉開的 <Subject 3> 內。

retention_analysis:
<Subject 1>: fully_preserved - 人物外貌與服裝特徵保持一致。
<Subject 2>: fully_preserved - 木盒外觀與尺寸保持一致。
<Subject 3>: fully_preserved - 抽屜結構與材質保持一致。

detailed_description:
真實電影質感，室內柔和光線。[Shot 1] 起始狀態為 <Subject 3> 呈完全拉開狀態，<Subject 1> 雙手已抱持 <Subject 2> 站立於抽屜前。固定平視中近景。<Subject 1> 彎腰將 <Subject 2> 平穩放入 <Subject 3> 槽內，隨後雙手鬆開並收回身側。

overall_soundscape:
木盒放置於抽屜底板的碰撞聲。

non_diegetic_music:
N/A
```
