import tempfile
from pathlib import Path

import creator_views
import native_views
from project_reader import project_snapshot

COLUMNS = ['編號', '畫面描述', '攝影機描述', '聲音描述', '旁白對白', '時長', '影片生成方式', '畫面prompt']


def test_bold_shot_identifier_matches_csv_without_changing_source():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        ep = root / 'EP01'
        ep.mkdir()
        header = '|'.join(COLUMNS)
        (ep / 'board.md').write_text(f'|{header}|\n|---|---|---|---|---|---|---|---|\n|**S01**|甲|定|雨|無|3|I2VA|p|', encoding='utf-8')
        (ep / 'board.csv').write_text(','.join(COLUMNS) + '\nS01,甲,定,雨,無,3,I2VA,p', encoding='utf-8')
        episode = project_snapshot(root)['episodes'][0]
        assert len(episode['shots']) == 1
        shot = episode['shots'][0]
        assert shot['id'] == 'S01'
        assert shot['fields']['編號'] == '**S01**'
        assert not episode['source_resolution']['conflicts']


def test_prompt_metadata_is_outside_code_and_not_itself_a_prompt():
    content = '## S01\n* **設計剪輯時長**：8s\n* **生成模式**：I2VA\n```text\n* **設計剪輯時長**：999 秒\n* **生成模式**：FL2VA\n實際 prompt\n```'
    prompts, recognized = native_views.try_parse_text_prompts([{'path': 'p.md', 'content': content}])
    assert recognized and len(prompts) == 1
    assert (prompts[0]['sec'], prompts[0]['mode']) == (8, 'I2VA')
    assert '**設計剪輯時長**：999 秒' in prompts[0]['prompt']
    prompts, recognized = native_views.try_parse_text_prompts([{'path': 'p.md', 'content': '## S01\n* **設計剪輯時長**：8s\n* **生成模式**：I2VA'}])
    assert recognized and prompts == []


def test_detail_closeup_and_composite_framing_are_distinct():
    def scale(camera):
        return creator_views.map_shot({'id': 'S01', 'fields': {'攝影機描述': camera}})['scale']
    assert scale('細節特寫') == '特写'
    assert scale('細節特寫至細節') == ''
    assert scale('全景至遠景') == ''


def test_tutorial_media_is_not_a_film_candidate_but_other_media_remains():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        for subdir in ['教學素材', '教学素材', 'tutorial-assets']:
            path = root / subdir / 'nested'
            path.mkdir(parents=True)
            (path / 'S01.mp4').write_bytes(b'video')
        (root / 'EP01').mkdir()
        (root / 'EP01' / 'S01.mp4').write_bytes(b'video')
        (root / 'EP01' / 'S01_start.png').write_bytes(b'image')
        (root / '教學素材' / 'notes.md').write_text('note', encoding='utf-8')
        snapshot = project_snapshot(root)
        assert set(snapshot['media']) == {'EP01/S01.mp4', 'EP01/S01_start.png'}
        assert any(f['path'] == '教學素材/notes.md' for f in snapshot['files'])
