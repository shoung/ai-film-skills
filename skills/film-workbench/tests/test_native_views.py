import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import creator_views
import unittest

class NativeViewTests(unittest.TestCase):
 def test_native_script_and_assets_and_prompts_take_precedence(self):
    script = '''## 本版鎖定\n不應顯示\n### 1-1 派出所櫃檯／日／內｜時間碼\n林（低聲）：等等我\n△推門\n林 VO：我回來了\n## 人物底稿\n附錄'''
    assets = '''## 角色資產\n### @林\n類型：角色\n文生圖提示詞：\n```text\n角色完整prompt\n```\n#### @林_雨衣\n文生圖提示詞：\n```text\n雨衣狀態prompt\n```'''
    rows = [{'id':'S01','row_index':1,'fields':{'編號':'S01','畫面描述':'[場次/時間]1-1 櫃檯','攝影機描述':'緩推','聲音描述':'雨聲','旁白對白':'林：好','時長':'0.5秒','影片生成方式':'T2VA','畫面prompt':'p'},'source':'board.csv'}]
    ep=creator_views.read_episode('EP1',{'劇本.md':script,'視覺設定.md':assets},native_shots=rows,video_documents=[{'path':'影片提示詞.md','content':'## S01|生成請求\n```text\n完整多鏡提示詞\n```\n\n## S50|後製'}],image_documents=[{'path':'圖片提示詞.md','content':'## 單幀 S01_start\n```text\nkeyframe\n```'}])
    self.assertEqual(ep['source_format']['劇本.md'],'native')
    self.assertEqual(len(ep['script']['scenes']),1)
    self.assertEqual(len(ep['board']['shots']),1); self.assertEqual(ep['board']['shots'][0]['sec'],0.5)
    self.assertEqual(ep['settings']['items'][0]['name'],'林')
    self.assertEqual(ep['settings']['items'][1]['parent'],'林')
    self.assertEqual(ep['settings']['items'][1]['cat'],'造型')
    self.assertIsInstance(ep['settings']['items'][0]['desc'],list)
    self.assertIn('角色完整prompt',ep['settings']['items'][0]['fields']['文生圖提示詞'])
    self.assertEqual(ep['videoPrompts'][0]['text'],'完整多鏡提示詞')
    self.assertEqual(ep['videoPrompts'][0]['prompt'],'完整多鏡提示詞')
    self.assertEqual(ep['videoPrompts'][0]['shot_ids'],['S01'])
    self.assertEqual(next(p for p in ep['imagePrompts'] if p['title']=='單幀 S01_start')['prompt'],'keyframe')
    self.assertFalse(any('剧本.md' in p for p in ep['problems']))

 def test_pure_text_heading_and_native_block_contract(self):
    from native_views import parse_script
    script=parse_script('前言不入\n1-1 房間 日 內\n阿明（壓低聲音）：走\n△關門\n林 VO：回來了\n## 人物底稿\n不入')
    scene=script['scenes'][0]
    self.assertEqual({k:scene[k] for k in ('id','space','place','time')},{'id':'1-1','space':'內','place':'房間','time':'日'})
    self.assertEqual([b['k'] for b in scene['blocks']],['line','action','line'])
    self.assertEqual(scene['blocks'][0],{'k':'line','tag':'','who':'阿明','paren':'壓低聲音','text':'走'})
    self.assertEqual(scene['blocks'][2]['tag'],'VO')

 def test_voice_tags_are_inferred_from_parenthetical_without_rewriting(self):
    from native_views import parse_script
    blocks=parse_script('### 1-1 房間 日 內\n小安（畫外音）：我回來了\n甲（OS）：聽見了')["scenes"][0]['blocks']
    self.assertEqual((blocks[0]['k'],blocks[0]['who'],blocks[0]['paren'],blocks[0]['tag'],blocks[0]['text']),('line','小安','畫外音','VO','我回來了'))
    self.assertEqual((blocks[1]['who'],blocks[1]['paren'],blocks[1]['tag']),('甲','OS','OS'))

 def test_camera_field_derives_only_unambiguous_scale_without_editing_fields(self):
    fields={'編號':'S09','畫面描述':'角色嘴部側臉','攝影機描述':'側臉嘴部大特寫，緩推','聲音描述':'','旁白對白':'','時長':'2秒','影片生成方式':'T2VA','畫面prompt':'x'}
    shot=creator_views.map_shot({'id':'S09','fields':fields})
    self.assertEqual(shot['scale'],'大特写')
    self.assertTrue(shot['close'])
    self.assertEqual(shot['framing'],fields['攝影機描述'])
    self.assertEqual(shot['fields'],fields)
    fields['攝影機描述']='先全景再特寫'
    self.assertEqual(creator_views.map_shot({'id':'S09','fields':fields})['scale'],'')

 def test_markdown_innerouter_year_and_timecode(self):
    from native_views import parse_script
    scene=parse_script('### 1-3 派出所櫃檯／1950年／內外｜00:00.500\n動作')["scenes"][0]
    self.assertEqual((scene['space'],scene['time']),('內外','1950年'))

 def test_full_heading_cleans_time_lock_suffix(self):
    from native_views import parse_script
    heading='### 1-7 派出所櫃檯旁、機構院落與修車攤／1970年及往事／內外｜04:21.5–05:30（68.5秒，暫估）'
    scene=parse_script(heading+'\n動作')["scenes"][0]
    self.assertEqual(scene['place'],'派出所櫃檯旁、機構院落與修車攤')
    self.assertEqual(scene['time'],'1970年及往事')
    self.assertEqual(scene['space'],'內外')

 def test_asset_name_removes_trailing_separator(self):
    from native_views import parse_assets
    item=parse_assets('## 角色資產\n### @警員1950 ---\n文生圖提示詞：\n```text\nprompt\n```')['items'][0]
    self.assertEqual(item['name'],'警員1950')

 def test_native_settings_schema_categories_and_prompt_body(self):
    from native_views import parse_assets
    settings=parse_assets('製作形態：寫實\n時代背景：1950年；光線：冷色\n## 場景資產\n### @車站\n文生圖提示詞：\n```text\n完整場景 prompt\n```\n## 道具資產\n### @手電筒\n描述：舊物')
    self.assertEqual(settings['form'],'寫實')
    self.assertEqual(settings['era']['period'],'1950年')
    self.assertEqual(settings['items'][0]['cat'],'地點')
    self.assertEqual(settings['items'][1]['cat'],'道具')
    self.assertEqual(settings['items'][0]['fields']['文生圖提示詞'],'完整場景 prompt')
    self.assertIsInstance(settings['items'][0]['desc'],list)

 def test_exact_suffix_shot_ids_and_complete_json_request(self):
    from native_views import parse_text_prompts
    prompts=parse_text_prompts([{'path':'v.md','content':'## S01A|請求\n時長：4秒\n模式：T2VA\n```json\n{"shots":["S01A","S01B"],"text":"full"}\n```'}])
    self.assertEqual(prompts[0]['shot_ids'],['S01A','S01B'])
    self.assertEqual(prompts[0]['sec'],4.0)
    self.assertEqual(prompts[0]['mode'],'T2VA')
    self.assertIn('"shots"',prompts[0]['prompt'])

 def test_native_prompt_parser_ignores_upstream_motions_and_image_ids(self):
    from native_views import parse_text_prompts
    docs=[{'path':'v.md','content':'## MOTION-001 · 原版\n```text\nold\n```\n## S02|native\n```text\nnew\n```'}]
    self.assertEqual([p['id'] for p in parse_text_prompts(docs)],['S02|native'])
    imgs=parse_text_prompts([{'path':'i.md','content':'## IMG-01 · old\nold\n## 圖像 E01\n```text\nnew\n```'}],image=True)
    self.assertEqual(imgs[0]['id'],'圖像 E01')

 def test_empty_native_rows_do_not_erase_legacy_board(self):
    ep=creator_views.read_episode('EP001',{'剧本.md':None,'分镜.md':'## SHOT-EP001-001 · 雨夜\n时长：2秒'},native_shots=[])
    self.assertEqual(len(ep['board']['shots']),1)
    self.assertEqual(ep['source_format']['分鏡.md'],'upstream')

 def test_native_board_scene_duration_and_metrics(self):
    rows=[{'id':'S03','fields':{'編號':'S03','畫面描述':'[場次/時間]1-3 櫃檯','攝影機描述':'定鏡','聲音描述':'','旁白對白':'','時長':'0.5秒','影片生成方式':'T2VA','畫面prompt':'x'},'source':'board.csv'}]
    ep=creator_views.read_episode('EP001',{'劇本.md':'## 1-3 櫃檯／日／內\n林：好'},native_shots=rows)
    self.assertEqual(ep['board']['shots'][0]['scene'],'1-3')
    self.assertEqual(ep['board']['shots'][0]['sec'],0.5)
    self.assertIn('shots',ep['metrics'])
    self.assertEqual(ep['board']['note'],'')
    self.assertEqual(ep['board']['blocking'],[])

 def test_actual_native_scene_link_markup(self):
    row={'id':'S01A','fields':{'編號':'S01A','畫面描述':'【場次／時碼】1-1；00:00–00:03；畫面動作','攝影機描述':'固定','聲音描述':'','旁白對白':'','時長':'3秒','影片生成方式':'T2VA','畫面prompt':'x'}}
    ep=creator_views.read_episode('EP1',{'劇本.md':'### 1-1 房間 日 內\n角色：你好'},native_shots=[row])
    self.assertEqual(ep['board']['shots'][0]['scene'],'1-1')

 def test_invalid_native_script_does_not_claim_success(self):
    ep=creator_views.read_episode('EP1',{'劇本.md':'### 1-1 標題\n文字'})
    self.assertEqual(ep['source_format']['劇本.md'],'upstream')
    self.assertTrue(ep['problems'])

 def test_h3_postproduction_without_body_is_ignored(self):
    from native_views import parse_text_prompts
    self.assertEqual(parse_text_prompts([{'path':'v.md','content':'## S50 後製\n剪輯備註：淡出'}]),[])
    ep=creator_views.read_episode('EP1',{},video_documents=[{'path':'v.md','content':'## S50 後製\n剪輯備註：淡出'}])
    self.assertEqual(ep['videoPrompts'],[])
    self.assertFalse(ep['problems'])

 def test_read_episode_group_header_and_image_tokens(self):
    ep=creator_views.read_episode('EP1',{},video_documents=[{'path':'v.md','content':'## G01|S01、S02\n```json\n{"shot_ids":["S01","S02"],"prompt":"one request"}\n```\n## S01A|solo\n```text\nA\n```\n## S010|not S01\n```text\nzero\n```'}],image_documents=[{'path':'i.md','content':'## 單幀 S01A_start\n```text\nframe A\n```\n## 圖像 B01\n```text\nasset B\n```'}])
    self.assertEqual([p['shot_ids'] for p in ep['videoPrompts']],[['S01','S02'],['S01A'],['S010']])
    self.assertEqual([p['shot_ids'] for p in ep['imagePrompts']],[['S01A'],[]])
    self.assertEqual(ep['videoPrompts'][0]['source']['path'],'v.md')

 def test_generic_postprocess_metadata_is_not_a_video_prompt(self):
    from native_views import try_parse_text_prompts
    prompts,recognized=try_parse_text_prompts([{'path':'v.md','content':'## S99 後製\n模式：後製\n時長：0秒\n剪輯備註：淡出\n## G07 後製整理\n備註：片尾字幕'}])
    self.assertTrue(recognized)
    self.assertEqual(prompts,[])
    prompts,recognized=try_parse_text_prompts([{'path':'v.md','content':'## S99 後製\n後製指示：黑底片名。不使用影像生成。'}])
    self.assertTrue(recognized)
    self.assertEqual(prompts,[])

 def test_image_base_and_final_fences_are_both_retained(self):
    from native_views import parse_text_prompts
    prompts=parse_text_prompts([{'path':'i.md','content':'## 圖像 E01\n### base\n```text\nbase prompt\n```\n### final\n```text\nfinal prompt\n```'}],image=True)
    self.assertEqual(len(prompts),2)
    self.assertNotEqual(prompts[0]['id'],prompts[1]['id'])
    self.assertEqual([p['prompt'] for p in prompts],['base prompt','final prompt'])
    self.assertEqual([p['source']['heading'] for p in prompts],['圖像 E01 · base','圖像 E01 · final'])

 def test_plain_seedance_and_json_requests_stay_single_complete_units(self):
    from native_views import parse_text_prompts
    plain=parse_text_prompts([{'path':'v.md','content':'## S03 · Seedance\n一鏡連續跟拍主角轉身離開。'}])
    self.assertEqual(len(plain),1)
    self.assertIn('連續跟拍',plain[0]['prompt'])
    structured=parse_text_prompts([{'path':'v.md','content':'## G01|S01、S02\n```json\n{"shots":["S01","S02"],"prompt":"single request"}\n```'}])
    self.assertEqual(len(structured),1)
    self.assertIn('"shots"',structured[0]['prompt'])

 def test_native_asset_image_prompts_include_state_cards(self):
    settings='## 角色資產\n### @林\n文生圖提示詞：\n```text\nbase image prompt\n```\n#### @林_雨衣\n文生圖提示詞：\n```text\nraincoat image prompt\n```'
    ep=creator_views.read_episode('EP1',{'視覺設定.md':settings})
    self.assertEqual([p['title'] for p in ep['imagePrompts']],['林','林_雨衣'])
    self.assertEqual(ep['imagePrompts'][1]['prompt'],'raincoat image prompt')

if __name__ == '__main__': unittest.main()
