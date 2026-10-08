# 視頻提示詞生成工作流 V2.0（示例庫）

本文件只作為 `01_視頻提示詞生成SKILL_V2.0_執行主文件.md` 的參考庫。

> 格式更新：先讀同目錄 concise-format.md 與 format-example.md。它們優先於本庫的舊格式與時間精度；本庫只提供視聽寫法參考，不要求複製篇幅或情節。

調用原則：
- 主文件能獨立執行；本文件只在風格、專業視聽錨點、角色音色或寫法不確定時調用。
- 本文件示例不是封閉詞庫，不得機械照抄。
- 示例庫不得覆蓋主文件規則；衝突時以主文件為準。
- 示例只提供選擇方向，最終必須根據劇本、資產、視頻類型、畫幅比例、視覺風格和連續性動態生成。

---

## 風格解析種子

當用戶只給一個風格詞時，先內部解析，再輸出可執行的全局風格鎖定詞。

真人寫實：
- 媒介來源：電影攝影 / 電視劇攝影 / 紀錄片攝影 / 平臺短視頻實拍。
- 渲染方式：實拍 / naturalistic cinematography / handheld realism / practical lighting。
- 角色質感：真人演員 / natural skin tone / real skin texture。
- 運動質感：真實攝影運動 / restrained camera movement / handheld micro-shake。
- 材質語言：真實皮膚 / 布料紋理 / 舊牆肌理 / 雨水反光 / 膠片顆粒。
- 光影色彩：低飽和 / 冷暖對比 / 暗調 / 柔光 / 高反差。

3DCG：
- 媒介來源：遊戲過場 / 動畫電影 / 實時渲染 / 虛擬製片。
- 渲染方式：UE5 / PBR / physically based rendering / global illumination。
- 角色質感：數字人 / 動捕角色 / stylized 3D character。
- 運動質感：virtual camera / motion capture / cinematic motion blur。
- 材質語言：PBR材質 / subsurface scattering / ray-traced reflections。
- 光影色彩：volumetric lighting / controlled rim light / high dynamic range。

2D：
- 媒介來源：動畫 / 漫畫 / 插畫 / 分鏡動畫。
- 渲染方式：手繪 / 平塗 / 賽璐璐 / 水墨 / 厚塗。
- 角色質感：漫畫人物 / 卡通角色 / 手繪角色。
- 運動質感：limited animation / anime-style timing / parallax camera move。
- 材質語言：clean line art / paper texture / painterly brushwork / comic halftone。
- 光影色彩：color script / flat color blocks / stylized shadow / high saturation。

特殊風格化觸發詞：
- 回憶：slightly faded color, soft contrast, memory-like diffusion。
- 夢境：surreal lighting, soft focus, floating camera movement。
- 監控：fixed surveillance angle, low-resolution security footage, timestamp framing。
- 手機直播：vertical video framing, creator-style handheld, mobile video realism。
- 新聞畫面：broadcast news framing, compressed video texture, documentary lighting。
- 遊戲 UI：game interface overlay, virtual camera, HUD-like composition。

---

## 專業視覺錨點示例

以下只是方向，不是封閉詞庫。

低照度問題：
```text
low light cinematography
available light
natural shadow detail
controlled highlights
low noise shadows
filmic dynamic range
```

溼雨環境：
```text
wet pavement reflections
rain diffusion
soft specular highlights
backlit rain
moody overcast night
```

實景光源：
```text
practical light
warm spill light
ambient bounce light
mixed color temperature
soft key light
```

人物反應：
```text
50mm standard lens
85mm portrait lens
shallow depth of field
natural skin tone
real skin texture
```

道具文字：
```text
macro lens
extreme close-up
legible text
controlled reflections
```

色彩與質感：
```text
desaturated color grading
cool blue-gray palette
muted contrast
naturalistic cinematography
restrained realism
```

短視頻平臺影像：
```text
vertical video framing
creator-style handheld
mobile video realism
fast hook
jump cut rhythm
reaction shot timing
on-screen text readability
```

短漫劇節奏：
```text
fast-paced coverage
dramatic close-up
reaction shot timing
cliffhanger framing
phone screen insert
high information density
```

廣告產品鏡頭：
```text
product hero shot
clean commercial lighting
macro product detail
packshot framing
call-to-action framing
crisp product texture
```

3DCG 視聽語言：
```text
virtual camera
physically based rendering
global illumination
volumetric lighting
ray-traced reflections
motion blur
depth of field
```

2D 視聽語言：
```text
clean line art
color script
limited animation
2D compositing
parallax camera move
cel shading
anime-style timing
```

強風格詞。會改變作品氣質，只有當用戶明確指定或資產庫已有風格時才使用：
```text
Blade Runner inspired
neon noir
teal and orange color grading
Cinestill 800T
Kodak Portra 400
Denis Villeneuve cinematography
Impressionist oil painting
cyberpunk aesthetic
```

---

## 角色音色示例

通用格式：

```text
@角色名：{年齡感}，{聲線質感}，{語速}，{氣息狀態}，{情緒底色}，{禁止項}。
```

年輕女性，剋制現實文戲：
```text
@艾莉：年輕女性聲線，音色偏清但不甜膩，語速正常偏慢，氣息輕、尾音短，情緒底色剋制緊繃，禁止誇張哭腔和動漫化撒嬌。
```

中年母親，生活流親情文戲：
```text
@母親：中年女性聲線，音色偏低而疲憊，語速正常，氣息穩但略壓住情緒，情緒底色隱忍和試探，禁止戲劇化喊叫和過度哭訴。
```

年輕男性，懸疑或壓抑情緒：
```text
@阿遠：年輕男性聲線，音色偏低啞，語速正常偏慢，氣息略緊，情緒底色警惕和遲疑，禁止英雄化怒吼和誇張喘息。
```

兒童或少年角色：
```text
@小孩：兒童聲線，音色清亮但不過度可愛化，語速略快，氣息短，情緒底色直接和不設防，禁止尖叫式童聲和卡通化尾音。
```

旁白或說明角色：
```text
@旁白：成熟中性聲線，語速穩定，咬字清楚，氣息平穩，情緒底色剋制客觀，禁止播音腔過重和煽情拖腔。
```

---

## 本組劇情寫法示例

推薦：
```text
本組劇情：@阿遠 到達 @青槐路舊牆 後發現導航指向的門並不存在，他對照 16 號與 18 號，確認中間只有一面無門舊牆。
```

生活文戲推薦：
```text
本組劇情：@母親 端著 @湯碗 出現在廚房門口，@女兒 先拒絕又嘗試接過，兩人隔著飯桌短暫停住，關係變得更僵。
```

不推薦：
```text
本組劇情：本組製造懸疑，推動人物情緒，形成反轉。
```

原因：它只有編劇功能，沒有可見事件和明確動作。

---

## 全局風格與本組環境寫法示例

推薦：
```text
全局風格提示詞：
風格鎖定：真人寫實電影質感，低照度現實主義攝影，低飽和冷灰藍色調，雨夜溼潤反光，實用光源冷暖對比，剋制懸疑影像。
特殊風格化：不啟用。全片保持普通風格鎖定，不額外疊加夢境、回憶、監控、漫畫化、遊戲 UI 等局部風格。
```

本組環境推薦（一行格式，含持續聲音）：

```text
【本組環境】
深夜，雨夜街道，小雨。持續光源：路燈冷光+店鋪暖光。持續聲音：細雨聲、遠處車輛經過聲、手機導航提示音。氛圍：潮溼、壓抑、低飽和。
```

火場環境推薦：

```text
【本組環境】
夜晚，火場內部，濃煙遮擋。持續光源：火海橙紅主光，黑煙削弱遠景。持續聲音：火焰燃燒轟鳴、結構坍塌聲、遠處爆炸餘響。氛圍：灼熱、窒息、混亂。
```

室內科幻環境推薦：

```text
【本組環境】
深夜，溫室艙內部，室內封閉。持續光源：控制台紅色故障燈脈衝+休眠艙綠色狀態燈。持續聲音：低頻電流嗡鳴、遠處警報餘音。氛圍：壓抑、窒息、暗紅籠罩。
```

不推薦：
```text
每組重複輸出電影質感、基礎光影、基礎色調。
本組環境拆成 5 行分字段寫（字數浪費）；應壓為“環境：時間，地點；光：...；聲：...；氛圍：...”。
漏寫持續聲音導致環境聲在鏡頭聲音字段中反覆出現。
```

---

---

---

## 狀態資產引用示例

### 有視覺資產庫：正式狀態資產

推薦：
```text
@趙無極_破敗 穿過 @天陰門廣場_白日練武，眾弟子讓開一條路。
@盧光_倒地受傷 撞在 @大殿門前_衝突後 的臺階上。
@古琴_震落 從琴案邊緣滑落，琴聲戛然而止。
@山神廟_毒煙瀰漫 中，@武松 閉氣追向 @廟門。
```

不推薦：
```text
@趙無極_憤怒 抬眼。
@林雪_驚訝 起身。
@孟凡_玩味消失 看向趙無極。
@盧光_嘲諷 走近。
```

原因：憤怒、驚訝、玩味、嘲諷是短暫表演或情緒，不是靜態視覺狀態。

### 無視覺資產庫：臨時狀態引用

允許建立：
```text
@趙無極_破敗：衣衫破損、塵土明顯、外來者狀態。
@盧光_倒地受傷：被拳擊飛後倒在臺階上。
@古琴_震落：被真氣震動後從琴板滑落。
@山神廟_毒煙瀰漫：黑煙持續影響空間識別。
```

禁止建立：
```text
@趙無極_出拳
@林雪_冷漠
@周執事_厲聲
@弟子_圍觀
```

原因：出拳、厲聲、圍觀是動作或行為；冷漠是表演氣質，不是需要複用的靜態視覺差異。

### 鏡頭字段中的狀態引用

動作字段推薦：
```text
動作：@趙無極_破敗 穿過 @練武方陣，肩背不縮，手指壓住破袖邊緣。
動作：@盧光_倒地受傷 撞上臺階後滑落，胸口衣料塌陷，手臂失力垂下。
```

畫面字段推薦：
```text
畫面：豎屏中景，正面平視機位，@山神廟_毒煙瀰漫 中黑煙壓住廟門，火光變渾。
```

光線字段注意：
```text
光線：手機屏幕藍光短暫照亮下巴。
```

說明：短暫手機光只寫光線事實，不建立 `@場景_手機藍光` 狀態；只有煙霧、火場、雨中、戰後等持續改變場景識別時，才建立場景狀態。

### 最終報告示例

有正式資產庫：
```text
狀態資產引用：
使用正式狀態資產：@趙無極_破敗、@盧光_倒地受傷、@古琴_震落
使用臨時狀態引用：無
建議補做狀態資產：@天陰門廣場_衝突後
```

無視覺資產庫：
```text
當前為臨時資產引用版。
使用臨時狀態引用：@趙無極_破敗、@盧光_倒地受傷、@古琴_震落
建議後續使用視覺資產 skill 補做正式多狀態資產庫。
```
## 鏡頭密度判斷示例

電影故事片文戲：
```text
視聽功能：文戲反應 / 對話拉扯。
傳播功能：沉浸、可信表演、情緒餘味。
鏡頭策略：1-3 鏡；優先固定鏡頭和剋制反打，不為每句臺詞切鏡。
記憶點：一個眼神、手部動作、道具觸感或臺詞後的停頓。
```

電影故事片動作：
```text
視聽功能：動作推進 / 複雜打鬥。
傳播功能：動作因果清楚、受擊結果有重量。
鏡頭策略：3-5 鏡；按攻擊發起 -> 閃避/防守 -> 接觸點 -> 受擊結果 -> 反應或下一動作方向拆。
記憶點：一次命中、兵器折斷、人物位置反轉或殺招結果。
```

短漫劇反轉：
```text
視聽功能：信息揭示 / 反轉爽點。
傳播功能：強情緒、強反應、信息推進。
鏡頭策略：4-7 鏡；鋪墊、揭示、主角反應、對手反應、結尾鉤子不能糊在一鏡裡。
記憶點：身份揭示、打臉反應、強臺詞或關係反轉。
```

短視頻生活流：
```text
視聽功能：開頭鉤子 / 口播推進 / 視覺反饋。
傳播功能：前3秒留人，移動端可讀，每幾秒有新信息。
鏡頭策略：開頭 hook 獨立成鏡；生活流可 1-2 鏡，不強行快切；口播超過 8 秒必須給視覺變化。
記憶點：一個可截圖動作、反應、道具或金句。
```

廣告宣傳片：
```text
視聽功能：產品展示 / 使用過程 / 結果反饋。
傳播功能：產品識別、賣點記憶、使用慾望、品牌收束。
鏡頭策略：產品首次出現獨立成鏡；每個賣點 1-2 鏡；品牌收束 1 鏡。
記憶點：產品外觀、賣點動作、結果畫面或品牌符號。
```
## 鏡頭字段寫法示例

推薦（6 個鏡頭字段 + 組約束）：

```text
鏡頭1（0-5秒）
畫面：中景，正面略低機位，人物在畫面左側，16號和18號形成左右對照，中間舊牆留出空缺感，牆面潮溼起皮。
鏡頭：35mm（35mm cinematic lens），中淺景深，焦點從手機導航切到門牌。
運鏡：緩慢前推到牆面。
動作：@阿遠 站在 @青槐路舊牆 前，對照門牌號，視線從 16 號移到 18 號，手指停在手機屏幕上，肩膀微微僵住。
臺詞：無。停頓 1 秒，呼吸變淺，眉心收緊。
光線：街燈冷光照出牆面潮溼紋理，遠處店鋪暖光只落在地面邊緣。
```

有臺詞示例：

```text
鏡頭3（7-11秒）
畫面：近景，正面略低機位，人物居中，背景控制台紅光虛化。
鏡頭：50mm（50mm standard lens），淺景深，焦點鎖定在眼睛。
運鏡：固定。
動作：@艾莉 身體前傾，雙手撐在 @操作檯 邊緣，指關節發白。
臺詞：艾莉（聲音發啞）："……你他媽倒是給個信號啊。"；省略號處停 0.5 秒，喉嚨乾澀吞嚥；尾音咬字用力但氣息不足，嘴唇微顫。
光線：@培養皿 藍光短暫亮起又熄滅，照亮艾莉下巴後消失。
```

不推薦（舊版拆分格式——禁止使用）：

```text
鏡頭目的：確認空間異常。
視角/景別：中景，保留人物、16 號、18 號和中間舊牆的空間關係。
機位：人物正前方略低機位，牆面佔據畫面後半部。
焦段/光圈：35mm 自然電影鏡頭（35mm cinematic lens），中淺景深。
運鏡：緩慢前推到牆面。
主體動作：@阿遠 站在 @青槐路舊牆 前……（臺詞和標點混入動作）
環境細節：牆面潮溼起皮，門牌邊緣有雨水滑落。
構圖/取景：人物在畫面左側，16 號和18號形成左右對照，中間舊牆留出空缺感。
焦點/景深：焦點從手機導航切到牆面門牌，中淺景深保留空間關係。（景深與焦段/光圈字段重複）
臺詞：無。
標點節奏重點：無臺詞，停頓 1 秒，呼吸變淺。
微表情/身體錨點：眉心收緊；手指停在手機屏幕上；肩膀微微僵住。
聲音：細雨聲、遠處車輛經過聲、手機導航提示音停止。
光線：街燈冷光照出牆面潮溼紋理，遠處店鋪暖光只落在地面邊緣。
【關鍵約束】
有音效，無音樂，無字幕。
```

原因：字段過多，景深在兩處重複，臺詞與動作混在一起不利於語音合成。常見錯誤：畫面字段漏寫“機位”二字；應寫“正面平視機位”“側面略低機位”，不要只寫“正面平視”。
## 光線字段示例

推薦：
```text
光線：@手機 屏幕亮起藍光，只照亮手指、屏幕邊緣雨點和阿遠下巴。
```

推薦：
```text
光線：@黑傘手電 的冷白光掃過牆面，短暫照亮 @鑰匙 和半截 @17號舊門牌。
```

推薦：
```text
光線：404 門縫暖光變寬，鋪到 @熱粥碗 和門口冷地磚上。
```

不推薦：
```text
光線：本鏡頭新增手機藍光，偏離全局光線。
```

原因：這是技術說明，不是畫面事實。

---

## 標點節奏轉譯示例

逗號：
```text
短暫停頓或換氣，表現為吸氣、嘴唇微停、眼神輕微偏移。
```

句號：
```text
說完後停住，嘴唇閉合，下頜輕收，眼神停留。
```

問號：
```text
說完後看向對方或門縫，眼神尋找反應，停半秒。
```

省略號：
```text
中間停 0.5 秒，喉嚨吞嚥，呼吸卡住，嘴唇微張。
```

破折號：
```text
前半句中斷，角色換氣、動作停住或眼神突然斷開。
```

感嘆號：
```text
只允許表現為音量、呼吸或身體緊繃變化，禁止默認失控喊叫。
```

禁止只寫：
```text
句號落地。
尾音壓低。
問號上揚。
情緒落地。
聲音發虛。
```






