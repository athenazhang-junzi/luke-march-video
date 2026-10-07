#!/usr/bin/env python3
"""Verify bundled media, immutable timing, and music presence. No network calls."""
import hashlib
import json
from pathlib import Path
from compose import probe, validate_timeline

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'assets/manifest.json').read_text())
for item in manifest['assets']:
    p = root / item['path']
    assert p.is_file(), p
    assert hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256'], p
    assert p.stat().st_size == item['bytes'], p
assert len(list((root / 'assets/scenes').glob('*.png'))) == 12
for i in range(1, 13):
    stream = probe(root / f'assets/scenes/{i:02}.png')['streams'][0]
    assert stream['width'] > 0 and stream['height'] > 0
v = next(s for s in probe(root / 'assets/reference-final-v5.mp4')['streams'] if s['codec_type'] == 'video')
assert (v['width'], v['height'], v['r_frame_rate'], int(v['nb_frames'])) == (1080, 1920, '60/1', 630)
a = probe(root / 'assets/luke-march.m4a')
assert 10.4 <= float(a['format']['duration']) <= 10.6
assert any(s['codec_type'] == 'audio' for s in a['streams'])
t = json.loads((root / 'references/timeline.json').read_text())
validate_timeline(t)
assert [s['start_frame'] for s in t['segments']] + [630] == [0,154,185,217,248,280,311,343,374,406,437,469,500,532,563,595,626,630]
print(f'PASS: {len(manifest["assets"])} media hashes, 12 scenes, original music, 630-frame timeline')
