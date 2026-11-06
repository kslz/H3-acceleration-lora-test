"""Check local Markdown references and the identity of published media."""
from pathlib import Path
from urllib.parse import unquote
import hashlib
import json
import re
import csv

ROOT=Path(__file__).resolve().parents[1]

def main():
    refs=0
    for source in [ROOT/'README.md',*sorted((ROOT/'docs').glob('*.md'))]:
        text=source.read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if '://' in target: continue
            name,_,anchor=target.partition('#')
            dest=(source.parent/unquote(name)).resolve() if name else source
            assert dest.is_relative_to(ROOT) and dest.is_file(),(source,target)
            if anchor and dest.name=='videos.md' and anchor!='视频结果汇总':
                assert f'id="{anchor}"' in dest.read_text(encoding='utf-8'),(source,target)
            refs+=1
    manifest=json.loads((ROOT/'data/media-manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['videos'])==48
    assert len({(v['seed'],v['id'],v['region']) for v in manifest['videos']})==48
    for v in manifest['videos']:
        video=ROOT/v['path']
        assert video.is_file() and (ROOT/v['poster']).is_file()
        assert video.stat().st_size==v['size_bytes']<100*1024*1024
        assert hashlib.sha256(video.read_bytes()).hexdigest()==v['sha256']
        assert int(v['profile']['nb_frames'])==124 and v['profile']['r_frame_rate']=='24/1'
        if v['region']=='full': assert v['sha256']==v['source_sha256']
    with (ROOT/'data/full-scores.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.reader(f))
    assert len(rows)==15 and len(rows[0])==38
    assert all(len(r)==38 for r in rows)
    assert sum(c=='未评测' for r in rows[1:] for c in r)==84
    assert not any(re.search(r'\b(overall|blur|noise|artifact|temporal|color|technical_mean|aesthetic_mean|overall_mean)\b',c) for c in rows[0])
    print(f'OK: {refs} local references; 14 CSV rows, 38 Chinese columns, 84 unevaluated cells; 48 videos, hashes and 124-frame profiles.')

if __name__=='__main__':
    main()
