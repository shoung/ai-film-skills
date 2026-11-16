import json
import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which('node'), 'Node is needed for frontend contract checks')
class UiContractTests(unittest.TestCase):
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
