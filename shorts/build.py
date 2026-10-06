"""Build a 9:16 fast-cut Short from recorded footage.
usage: python3 build.py --footage work/raw/footage.webm --music work/beat.wav --config ironveil.json --out out/ironveil-short.mp4 [--seed 1]
"""
import argparse, json, os, random, subprocess, shutil
ap = argparse.ArgumentParser()
ap.add_argument('--footage', nargs='+', required=True); ap.add_argument('--music', required=True)
ap.add_argument('--config', default='ironveil.json'); ap.add_argument('--out', default='out/short.mp4')
ap.add_argument('--seed', type=int, default=1); ap.add_argument('--work', default='work/build')
a = ap.parse_args(); cfg = json.load(open(a.config)); rng = random.Random(a.seed)
W, H, FPS = 1080, 1920, 30
os.makedirs(a.work, exist_ok=True); os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
def run(cmd): subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE if False else None)
def probe(f): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).decode().strip())

beat = 60 / cfg['bpm']; body = cfg['duration'] - cfg['endcard']
# Cut pattern in beats: opens on the 2-beat intro (matches the beat's drop), then gets more frantic each phrase.
pattern = [2, 2, 1, 1, 2, 1, 1, .5, .5, 1, 2, 1, 1, .5, .5, 1, 1, .5, .5, .5, .5, 1, 2, 1, .5, .5, 1, 1, .5, .5, .5, .5, 1, 1]
segs, tcum, bcum = [], 0.0, 0.0
for i, nb in enumerate(pattern * 3):
    if tcum >= body: break
    L = min(nb * beat, body - tcum)
    segs.append({'len': L, 'beats': nb, 'at': tcum, 'downbeat': bcum % 4 == 0}); tcum += L; bcum += nb
# end card: one long slow-motion clip keeps the game alive under the darkened CTA
segs.append({'len': cfg['endcard'] + 0.2, 'beats': 8, 'at': body, 'downbeat': True, 'end': True})

# Pick source moments spread across all footage, shuffled, skipping the first 2 s (loading).
sources = []
for f in a.footage:
    d = probe(f); sources.append((f, d))
pool = []
def detail_scores(f):
    """Per-second visual-detail score: JPEG size of a small thumbnail (busy frames compress worse)."""
    d = os.path.join(a.work, 'thumbs', os.path.basename(os.path.dirname(f)) + '_' + os.path.splitext(os.path.basename(f))[0])
    if not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', f, '-vf', 'fps=1,scale=160:-2', '-q:v', '4', os.path.join(d, '%05d.jpg')], check=True)
    return [os.path.getsize(os.path.join(d, n)) for n in sorted(os.listdir(d))]
for f, d in sources:
    sc = detail_scores(f); cut = sorted(sc)[int(len(sc) * cfg.get('detail_drop', 0.4))] if sc else 0
    for t in range(2, int(d - 2.5)):
        if sc[min(t, len(sc) - 1)] >= cut: pool.append((f, float(t), d, sc[min(t, len(sc) - 1)]))
rng.shuffle(pool)
# A caption (or the hook) may name a footage file substring in "clip": cuts under it come from that footage.
def wanted_clip(at):
    if at < cfg['hook_seconds'] and cfg.get('hook_clip'): return cfg['hook_clip']
    for c in cfg['captions']:
        if c.get('clip') and c['at'] - 0.3 <= at < c['at'] + c['for']: return c['clip']
    return None
def take(clip, best=False):
    hits = [idx for idx, e in enumerate(pool) if clip is None or clip in os.path.basename(os.path.dirname(e[0])) or clip in os.path.basename(e[0])]
    if not hits: return None
    idx = max(hits, key=lambda i: pool[i][3]) if best else hits[0]
    return pool.pop(idx)
for i, s in enumerate(segs):
    e = take(wanted_clip(s['at']), best=s['at'] < cfg['hook_seconds']) or take(None)
    if e is None: pool.extend((f, 2.0 + (d - 2.5) * rng.random(), d, 0) for f, d in sources); e = take(None)
    f, start, d = e[:3]
    speed = 0.6 if s.get('end') else (rng.choice([1.0, 1.5, 2.0]) if s['beats'] >= 1 else 1.0)
    start = min(start, max(2.0, d - s['len'] * speed - 0.2))
    s.update(src=f, start=start, speed=speed, zoom_in=(i % 2 == 0), amt=0.08 if s.get('end') else rng.uniform(.10, .20), focus=rng.choice([.15, .5, .85]))

layout = cfg.get('layout', 'crop')
def seg_filter(s):
    n = max(2, int(round(s['len'] * FPS)))
    z = f"min(1+{s['amt']}*in/{n},{1+s['amt']})" if s['zoom_in'] else f"max({1+s['amt']}-{s['amt']}*in/{n},1)"
    if layout == 'crop':
        lay = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}:(iw-{W})*{s['focus']}:(ih-{H})*0.4"
    else:
        lay = (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:8,eq=brightness=-0.2[bg];"
               f"[b]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    return (f"setpts=PTS/{s['speed']},fps={FPS},{lay},"
            f"zoompan=z='{z}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
            f"{cfg.get('grade', 'eq=saturation=1.35:contrast=1.08')},unsharp=5:5:0.8,setsar=1")

print(f'{len(segs)} cuts over {body:.1f}s body + {cfg["endcard"]}s end card')
listfile = os.path.join(a.work, 'list.txt')
with open(listfile, 'w') as lf:
    for i, s in enumerate(segs):
        p = os.path.join(a.work, f'seg{i:02d}.mp4')
        run(['ffmpeg', '-y', '-v', 'error', '-ss', f"{s['start']:.3f}", '-t', f"{s['len'] * s['speed'] + 0.4:.3f}", '-i', s['src'],
             '-filter_complex', seg_filter(s), '-t', f"{s['len']:.4f}", '-r', str(FPS),
             '-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p', '-an', p])
        lf.write(f"file '{os.path.abspath(p)}'\n")
bodyfile = os.path.join(a.work, 'body.mp4')
run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', listfile, '-c', 'copy', bodyfile])

# ---- overlay pass: flashes on downbeat cuts, RGB-split hits on the others, text, end card, music
def tf(name, text):
    p = os.path.join(a.work, name + '.txt'); open(p, 'w').write(text); return p
font, font_url = cfg['font'], cfg.get('font_url', cfg['font'])
from PIL import ImageFont
def fit(text, base, fontfile=None, maxw=980):
    """Shrink a font size until the widest line fits inside the safe width."""
    f = ImageFont.truetype(fontfile or font, base); w = max(f.getlength(l) for l in text.split('\n'))
    return base if w <= maxw else max(36, int(base * maxw / w))
from PIL import ImageFont
def fit(text, base, fontfile=None, maxw=980):
    """Shrink a font size until the widest line fits inside the safe width."""
    f = ImageFont.truetype(fontfile or font, base); w = max(f.getlength(l) for l in text.split('\n'))
    return base if w <= maxw else max(36, int(base * maxw / w))
accent = cfg.get('accent', '0xFF2D55')
cuts = [s['at'] for s in segs[1:]]
flash = '+'.join(f"between(t,{s['at']:.3f},{s['at'] + 0.07:.3f})" for s in segs if s['downbeat'] and s['at'] > 0) or '0'
glitch = '+'.join(f"between(t,{s['at']:.3f},{s['at'] + 0.09:.3f})" for s in segs[1:] if not s['downbeat']) or '0'
E = body; D = cfg['duration']; hs = cfg['hook_seconds']
vf = [
    f"drawbox=c=white@0.85:t=fill:enable='{flash}'",
    f"rgbashift=rh=16:bh=-16:gv=6:enable='{glitch}'",
    # hook: slams in, holds, drops out
    f"drawtext=fontfile={font}:expansion=none:textfile={tf('hook', cfg['hook'])}:fontsize={fit(cfg['hook'], 96)}:fontcolor=white:line_spacing=10:"
    f"box=1:boxcolor={accent}@0.92:boxborderw=28:x=(w-text_w)/2:y=h*0.26-40*max(0\\,1-t*10):"
    f"alpha='if(lt(t,0.08),t/0.08,if(lt(t,{hs - 0.15}),1,max(0,({hs}-t)/0.15)))':enable='lt(t,{hs})'",
    # persistent watermark during the body
    f"drawtext=fontfile={font_url}:text={cfg['url']}:fontsize=44:fontcolor=white@0.85:borderw=3:bordercolor=black@0.6:"
    f"x=48:y=h-120:enable='between(t,{hs},{E})'",
]
for i, c in enumerate(cfg['captions']):
    y = 'h*0.62' if i % 2 == 0 else 'h*0.70'
    vf.append(f"drawtext=fontfile={font}:expansion=none:textfile={tf(f'cap{i}', c['text'])}:fontsize={fit(c['text'], 88)}:fontcolor=black:"
              f"box=1:boxcolor=white@0.96:boxborderw=24:x=(w-text_w)/2+{(-1) ** i * 6}*sin(t*40):y={y}:"
              f"enable='between(t,{c['at']},{c['at'] + c['for']})'")
vf += [
    f"drawbox=c=black@0.6:t=fill:enable='gte(t,{E})'",
    f"drawtext=fontfile={font_url}:text={cfg['url']}:fontsize={fit(cfg['url'], 120, font_url)}:fontcolor=white:borderw=4:bordercolor=black:"
    f"x=(w-text_w)/2:y=h*0.40+30*max(0\\,1-(t-{E})*8):alpha='min(1,(t-{E})*6)':enable='gte(t,{E})'",
    f"drawtext=fontfile={font}:expansion=none:textfile={tf('cta', cfg['cta_line'])}:fontsize={fit(cfg['cta_line'], 76)}:fontcolor=white:box=1:boxcolor={accent}@0.95:boxborderw=22:"
    f"x=(w-text_w)/2:y=h*0.40+190:alpha='min(1,max(0,(t-{E}-0.25)*6))':enable='gte(t,{E + 0.25})'",
    f"drawtext=fontfile={font}:expansion=none:textfile={tf('sub', cfg.get('cta_sub', 'NO DOWNLOAD  •  FREE  •  IN YOUR BROWSER'))}:fontsize={fit(cfg.get('cta_sub', ''), 40, maxw=1000)}:fontcolor=white@0.9:"
    f"x=(w-text_w)/2:y=h*0.40+330:alpha='min(1,max(0,(t-{E}-0.5)*6))':enable='gte(t,{E + 0.5})'",
    "vignette=PI/5",
]
fc = "[0:v]" + ",".join(vf) + f"[v];[1:a]atrim=0:{D},afade=t=out:st={D - 1.2}:d=1.2,volume=0.95[a]"
run(['ffmpeg', '-y', '-v', 'error', '-i', bodyfile, '-i', a.music, '-filter_complex', fc, '-map', '[v]', '-map', '[a]',
     '-t', str(D), '-r', str(FPS), '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
     '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', a.out])
print('wrote', a.out, f'{probe(a.out):.2f}s')
