# Shorts pipeline for ironveil.live

Produces a 1080x1920 fast-cut vertical ad (YouTube Shorts / TikTok) from a recording of the game.

```
node record.mjs --url https://ironveil.live --out work/raw --seconds 60        # record gameplay
python3 make_beat.py work/beat.wav 26 140                                      # placeholder beat (swap for a licensed track)
python3 build.py --footage work/raw/footage.webm --music work/beat.wav \
                 --config ironveil.json --out out/ironveil-short.mp4
```

- `record.mjs` drives the game in headless Chromium (random keys/clicks by default; pass `--actions my.mjs` exporting
  `default async (page, seconds, {width,height,out})` for scripted play). Writes `footage.webm` plus screenshots.
- `build.py` plans cuts on the beat grid (longer cuts early, half-beat cuts by the end), gives every cut a zoom punch and a
  random speed-up, flashes white on downbeat cuts and RGB-splits the others, then layers hook text, captions, a watermark,
  and an end card. All copy lives in `ironveil.json`.
- `make_beat.py` synthesizes a 140 BPM track so cuts line up; replace `--music` with any track at the same BPM.

`out/demo-standin.mp4` was cut from `standin/demo.html`, a placeholder arena, because the cloud environment's network
policy blocked ironveil.live. Allow the domain and rerun the three commands above to get the real one.
