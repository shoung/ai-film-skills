import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import creator_views


class CreatorViewTests(unittest.TestCase):
    def test_maps_eight_fields_and_keeps_source_supplement_without_fake_timeline(self):
        fields={'編號':'S01','畫面描述':'雨中街道','攝影機描述':'緩推','聲音描述':'雨聲','旁白對白':'無','時長':'3秒','影片生成方式':'T2VA','畫面prompt':'wet street'}
        shot=creator_views.map_shot({'id':'S01','fields':fields,'supplement':{'sources':[{'path':'a.csv','fields':fields,'notes':[]}],'media':[{'path':'S01_start.png','role':'first_frame','evidence':'filename_boundary'}],'prompts':[],'notes':[]}})
        ep=creator_views.read_episode('EP001',{'分鏡.md':''})
        self.assertEqual(shot['fields'],fields)
        self.assertEqual(shot['supplement']['sources'][0]['path'],'a.csv')
        self.assertEqual(shot['refState'],'pending')
        self.assertEqual(shot['refs'],[])
        self.assertIsNone(ep['cutlist'])
        self.assertEqual(ep['metrics']['shots'],0)

    def test_structured_screenplay_settings_and_review_are_parsed(self):
        ep=creator_views.read_episode('EP001',{'剧本.md':'# EP001 · 雨夜\n## EP001-SC001 内 · 车站 · 夜\n林：等等我','视觉设定.md':'## 人物 · 林\n- 外观：蓝外套'},'## blocker · REV-001 · 问题一\n- 位置：SHOT-EP001-001\n- 证据：台词需确认')
        self.assertEqual(ep['script']['scenes'][0]['blocks'][0]['who'],'林')
        self.assertEqual(ep['settings']['items'][0]['name'],'林')
        self.assertEqual(ep['review']['verdictTone'],'warn')
        self.assertFalse(ep['review']['independent'])

    def test_upstream_parsers_match_public_creator_fixture(self):
        root=Path(__file__).resolve().parent / 'fixtures' / 'creator-first' / '剧集' / 'EP001'
        docs={name:(root/name).read_text(encoding='utf-8') for name in ('剧本.md','视觉设定.md','分镜.md','图片提示词.md','视频提示词.md')}
        ep=creator_views.read_episode('EP001',docs)
        self.assertEqual(len(ep['script']['scenes']),2)
        self.assertEqual(len(ep['settings']['items']),7)
        self.assertEqual(len(ep['board']['shots']),22)
        self.assertEqual(len(ep['imagePrompts']),4)
        self.assertEqual(len(ep['videoPrompts']),22)
        self.assertEqual(ep['metrics']['seconds'],62.0)


if __name__ == '__main__': unittest.main()
