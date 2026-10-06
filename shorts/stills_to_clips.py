"""Turn still images (key art, screenshots) into 1080x1920 Ken Burns clips that build.py can cut like footage.
usage: python3 stills_to_clips.py --out work/stills img1.jpg img2.png ... [--seconds 14]"""
import argparse, os, subprocess
ap = argparse.ArgumentParser(); ap.add_argument('images', nargs='+'); ap.add_argument('--out', default='work/stills'); ap.add_argument('--seconds', type=float, default=14)
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); W, H, FPS = 1080, 1920, 30; N = int(a.seconds * FPS)
moves = [  # (zoom expr, x expr, y expr) — slow drifts; build.py adds the punchy zooms on top
    (f"1.08+0.22*in/{N}", "(iw-iw/zoom)*(0.2+0.6*in/%d)" % N, "(ih-ih/zoom)*0.45"),
    (f"1.30-0.20*in/{N}", "(iw-iw/zoom)*(0.8-0.6*in/%d)" % N, "(ih-ih/zoom)*0.5"),
    (f"1.05+0.30*in/{N}", "(iw-iw/zoom)*0.5", "(ih-ih/zoom)*(0.1+0.7*in/%d)" % N),
]
for i, img in enumerate(a.images):
    for j, (z, x, y) in enumerate(moves):
        out = os.path.join(a.out, f"{os.path.splitext(os.path.basename(img))[0]}-{j}.mp4")
        # scale up 2x before zoompan so the zoom has pixels to work with, then cover-crop to 9:16
        vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
              f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS}")
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-framerate', str(FPS), '-t', str(a.seconds), '-i', img,
                        '-vf', vf, '-r', str(FPS), '-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p', out], check=True)
        print('wrote', out)
