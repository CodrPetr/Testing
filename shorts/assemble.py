"""Turn timestamped screencast frames into smooth 30 fps footage via motion interpolation.
usage: python3 assemble.py --cap work/cap2 --out work/cap2/footage.mp4 [--skip 15] [--scale 1080x1920]"""
import argparse, os, subprocess
ap = argparse.ArgumentParser(); ap.add_argument('--cap', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--skip', type=float, default=12, help='drop the first N seconds (loading, panels)'); ap.add_argument('--end', type=float, default=1e9); ap.add_argument('--scale', default='1080x1920')
ap.add_argument('--crop', default='', help='ffmpeg crop expr applied before scaling, e.g. 1080:1560:0:0 to drop the deploy bar')
a = ap.parse_args()
rows = [l.split() for l in open(os.path.join(a.cap, 'frames.txt')) if l.strip()]
frames = [(int(n), float(t)) for n, t in rows if a.skip <= float(t) <= a.end]
lst = os.path.join(a.cap, 'list.txt')
with open(lst, 'w') as f:
    for i, (n, t) in enumerate(frames):
        dur = (frames[i + 1][1] - t) if i + 1 < len(frames) else 1.0
        f.write(f"file 'f{n:04d}.jpg'\nduration {max(0.04, dur):.3f}\n")
    f.write(f"file 'f{frames[-1][0]:04d}.jpg'\n")
vfr = os.path.join(a.cap, 'vfr.mp4'); W, H = a.scale.split('x')
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-vf', (f'crop={a.crop},' if a.crop else '') + f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1', '-vsync', 'vfr',
                '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', vfr], check=True)
print('vfr', vfr, f'{len(frames)} frames, {frames[-1][1] - frames[0][1]:.0f}s')
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-stats', '-i', vfr, '-vf',
                "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:vsbmc=1:search_param=48",
                '-threads', '4', '-c:v', 'libx264', '-preset', 'fast', '-crf', '14', '-pix_fmt', 'yuv420p', a.out], check=True)
print('wrote', a.out)
