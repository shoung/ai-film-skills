import json
import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which('node'), 'Node is needed for frontend contract checks')
class UiContractTests(unittest.TestCase):
    def test_postproduction_is_optional_and_candidates_are_visible_without_cutlist(self):
        app=Path(__file__).resolve().parents[1]/'assets/dashboard/app.js'
        script='''
const assert=require('node:assert/strict');
const app=require(process.argv[1]);
const row={id:'EP001',has:{script:true,settings:true,board:true,imgp:true,vidp:true,cut:false,film:false,review:false},mediaCount:1};
assert.ok(!app.nextFor(row).text.includes('剪輯單'));
const episode={board:{shots:[{id:'S01',supplement:{media:[{kind:'video',role:'video_candidate',path:'EP001/S01.mp4',shot_ids:['S01']}]}}]},docs:{},media:{frames:{}},metrics:{},problems:[]};
const overview=app.viewEpisode(row,episode);
assert.ok(overview.includes('加入成片後可在這裡播放'));
assert.ok(!overview.includes('剪輯單寫好'));
const html=app.viewFilm(row,episode,'',new URLSearchParams());
assert.ok(html.includes('EP001%2FS01.mp4'));
assert.ok(html.includes('選用'));
assert.ok(!html.includes('還沒有剪輯單'));
const orphan=app.viewFilm(row,{...episode,media:{candidates:[{path:'EP001/S99.mp4',shot_ids:[]}] }},'',new URLSearchParams());
assert.ok(orphan.includes('S99.mp4'));
assert.ok(orphan.includes('未對應目前分鏡'));
'''
        result=subprocess.run(['node','-e',script,str(app)],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_editable_source_extensions_and_episode_metadata(self):
        app = Path(__file__).resolve().parents[1] / 'assets/dashboard/app.js'
        script = '''
const assert = require('node:assert/strict');
const app = require(process.argv[1]);
for (const path of ['board.csv','board.md','board.markdown','notes.txt']) {
  assert.equal(app.creatorEditable({path,editable:true}),true,path);
}
assert.equal(app.creatorEditable({path:'overview.html',editable:false}),false);
assert.equal(app.creatorEditable({path:'qc.json',editable:false}),false);
app.S.series={episodes:[{id:'第六版'},{id:'EP001'}]};
app.S.tree={tree:[{type:'directory',name:'第六版分鏡',children:[{type:'text',path:'第六版分鏡/board.csv',episode:'第六版'}]}]};
assert.equal(app.episodeName('第六版分鏡/board.csv'),'第六版');
assert.equal(app.episodeName('EP001/board.md'),'EP001');
'''
        result = subprocess.run(['node', '-e', script, str(app)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
