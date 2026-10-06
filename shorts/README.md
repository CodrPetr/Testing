# Shorts pipeline for ironveil.live

Produces a 1080x1920 fast-cut vertical ad (YouTube Shorts / TikTok) from scripted matches of the game.

```
node capture.mjs --out work/cap4 --seconds 360          # host + join a 1v1 in two headless browsers, stream the host's frames
node capture_fpv.mjs --out work/cap7 --seconds 200      # same, but buys Wasp FPV drones and pilots one
python3 assemble.py --cap work/cap4 --out work/cap4/footage.mp4 --skip 100 --end 220 \
        --crop 1080:1560:0:0 --scale 720x1280          # frames -> smooth 30 fps via motion interpolation
python3 make_beat.py work/beat.wav 26 140               # placeholder 140 BPM beat (swap for a licensed track)
python3 build.py --footage work/cap*/footage.mp4 --music work/beat.wav \
                 --config ironveil.json --out out/ironveil-short.mp4
```

- `capture.mjs` opens two browsers, hosts a room, joins it with the friend code, starts the battle, then drives both sides
  (select all, jump the camera to a flag, click to advance, number keys to deploy, air strikes aimed at the enemy side).
  The host's screen is streamed with Chrome's screencast API into timestamped JPEG frames. The cloud container has no
  GPU, so the game renders at roughly one frame per second; `assemble.py` rebuilds real time from the timestamps and
  motion-interpolates to 30 fps. On a machine with a GPU, Playwright's `recordVideo` would replace both steps.
- `build.py` plans cuts on the beat grid (longer cuts early, half-beat cuts by the end), gives every cut a zoom punch and a
  random speed-up, flashes white on downbeat cuts and RGB-splits the others, then layers hook text, captions, a watermark
  and an end card. Copy lives in `ironveil.json`; a caption's `clip` names the capture its cuts must come from, so
  "FLY THE FPV DRONE YOURSELF" sits over the drone footage.
- `stills_to_clips.py` turns key art into Ken Burns clips that can be mixed in as footage.
- `make_beat.py` synthesizes a 140 BPM track so cuts line up; replace `--music` with any track at the same BPM.

Game UI hooks used by the driver: `#host-game`, `#objective-A..G` (camera jump), `#camera-zoom-in`, `#camera-rotate`,
`#close-army`, `#close-map`, `#toggle-army`, `.roster-card`, `#catalog-category` (troop category dialog), number keys
to buy, `#pilot-unit` (FPV takeover, needs a DOM click), keys W/A/D/F/Ctrl in flight.
