#!/usr/bin/env python3
"""Deterministic assembler. Run inside the project's VidMuse thread, after generation."""
import argparse
import json
import subprocess
from pathlib import Path


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))


def validate_timeline(t):
    if (t['fps'], t['width'], t['height'], t['total_frames']) != (60, 1080, 1920, 630):
        raise ValueError('Template must be 1080x1920, 60fps, 630 frames')
    cursor = 0
    for i, s in enumerate(t['segments']):
        if s['start_frame'] != cursor or s['end_frame'] <= cursor:
            raise ValueError(f'Gap/overlap/empty segment {i}')
        if s['kind'] not in ('video', 'image'):
            raise ValueError('Unsupported segment kind')
        cursor = s['end_frame']
    if cursor != 630 or t['segments'][0]['end_frame'] != 154:
        raise ValueError('Invalid intro or total duration')
    if {s['source_key'] for s in t['segments'][1:]} != {f'scene_{i:02}' for i in range(1, 13)}:
        raise ValueError('All 12 scenes required')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--timeline', type=Path, required=True)
    ap.add_argument('--media', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    t, m = json.loads(a.timeline.read_text()), json.loads(a.media.read_text())
    validate_timeline(t)
    if not m.get('thread_id'):
        raise ValueError('Record the real VidMuse thread_id before assembly')
    if set(m['scenes']) != {f'{i:02}' for i in range(1, 13)}:
        raise ValueError('scenes must contain keys 01 through 12')
    def resolve(p):
        p = Path(p)
        return (a.media.parent / p).resolve() if not p.is_absolute() else p.resolve()
    audio, opening = resolve(m['audio']), resolve(m['opening'])
    scenes = {k: resolve(v) for k, v in m['scenes'].items()}
    for f in [audio, opening, *scenes.values()]:
        if not f.is_file():
            raise FileNotFoundError(f)
    intro_start = float(m.get('opening_start', 0))
    if intro_start < 0 or float(probe(opening)['format']['duration']) - intro_start < 154 / 60 - 0.002:
        raise ValueError('Select a continuous full 154-frame motion window; do not pad a short opening')
    if not any(s['codec_type'] == 'audio' and s['codec_name'] == 'aac' for s in probe(audio)['streams']):
        raise ValueError('Use the bundled original AAC m4a, without changing the music')
    out = a.out.resolve()
    if out.exists():
        raise FileExistsError('Choose a new version filename; existing exports are preserved')
    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / (out.stem + '-segments')
    work.mkdir(exist_ok=False)
    paths = []
    for i, s in enumerate(t['segments']):
        count = s['end_frame'] - s['start_frame']
        p = work / f'{i:02}.mp4'
        cmd = ['ffmpeg', '-v', 'error', '-threads', '2']
        if s['kind'] == 'video':
            cmd += ['-ss', str(intro_start), '-i', str(opening)]
            vf = 'setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=60,setsar=1,format=yuv420p'
        else:
            cmd += ['-loop', '1', '-framerate', '60', '-i', str(scenes[s['source_key'][-2:]])]
            vf = 'split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[b];[fg]scale=1080:1920:force_original_aspect_ratio=decrease[f];[b][f]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p'
        cmd += ['-filter_complex_threads', '1', '-vf', vf, '-frames:v', str(count), '-an', '-c:v', 'libx264', '-threads', '2', '-preset', 'fast', '-crf', '18', '-video_track_timescale', '15360', str(p)]
        run(cmd)
        if int(next(x for x in probe(p)['streams'] if x['codec_type'] == 'video')['nb_frames']) != count:
            raise ValueError(f'Segment {i} frame count mismatch')
        paths.append(p)
        print(f'{i + 1}/{len(t["segments"])} segments', flush=True)
    concat = work / 'concat.txt'
    concat.write_text(''.join(f"file '{p.name}'\n" for p in paths))
    run(['ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(concat), '-i', str(audio), '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'copy', '-movflags', '+faststart', str(out)])
    result = probe(out)
    video = next(s for s in result['streams'] if s['codec_type'] == 'video')
    if int(video['nb_frames']) != 630 or video['r_frame_rate'] != '60/1':
        raise ValueError('Final output frame mismatch')
    if abs(float(result['format']['duration']) - 10.5) > 0.05:
        raise ValueError('Final duration differs from template')
    # Verify unchanged compressed AAC packets; container metadata can differ.
    def audio_hash(p):
        return run(['ffmpeg', '-v', 'error', '-i', str(p), '-map', '0:a:0', '-c:a', 'copy', '-f', 'hash', '-hash', 'sha256', '-']).strip()
    if audio_hash(out) != audio_hash(audio):
        raise ValueError('Music packets changed')
    (out.parent / (out.stem + '-project.json')).write_text(json.dumps({'thread_id': m['thread_id'], 'media': m, 'timeline': t, 'probe': result, 'audio_packet_hash': audio_hash(out)}, ensure_ascii=False, indent=2))
    print(out)


if __name__ == '__main__':
    main()
