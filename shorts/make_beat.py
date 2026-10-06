"""Synthesize a punchy 140 BPM electronic beat (placeholder music; swap for a licensed track).
usage: python3 make_beat.py out.wav [seconds] [bpm]"""
import sys, wave, numpy as np
out = sys.argv[1]; secs = float(sys.argv[2]) if len(sys.argv) > 2 else 26; bpm = float(sys.argv[3]) if len(sys.argv) > 3 else 140
sr = 44100; beat = 60 / bpm; n = int(secs * sr); t = np.arange(n) / sr
rng = np.random.default_rng(7)
L = np.zeros(n); R = np.zeros(n)
def add(sig, at, pan=0.0):
    i = int(at * sr); m = min(len(sig), n - i)
    if m <= 0: return
    L[i:i+m] += sig[:m] * (1 - max(pan, 0)); R[i:i+m] += sig[:m] * (1 + min(pan, 0))
def env(length, a=0.002, d=0.2, curve=6):
    k = int(length * sr); x = np.linspace(0, 1, k); e = np.exp(-x * curve)
    att = int(a * sr); e[:att] *= np.linspace(0, 1, att) if att else 1
    return e
def kick(): 
    k = int(0.45 * sr); x = np.arange(k) / sr; f = 42 + 160 * np.exp(-x * 28)
    ph = np.cumsum(2 * np.pi * f / sr); s = np.sin(ph) * np.exp(-x * 7)
    s += (rng.standard_normal(k) * np.exp(-x * 300)) * 0.6
    return np.tanh(s * 2.2) * 0.95
def clap():
    k = int(0.3 * sr); x = np.arange(k) / sr; s = np.zeros(k)
    for off in (0, 0.012, 0.024, 0.036):
        i = int(off * sr); s[i:] += rng.standard_normal(k - i) * np.exp(-np.arange(k - i) / sr * (12 if off < 0.03 else 9))
    b = np.convolve(s, np.ones(6) / 6, 'same'); s = s - b  # crude high-pass
    return s * 0.35
def hat(open_=False):
    k = int((0.25 if open_ else 0.06) * sr); x = np.arange(k) / sr
    s = rng.standard_normal(k); s = s - np.convolve(s, np.ones(8) / 8, 'same')
    return s * np.exp(-x * (10 if open_ else 60)) * 0.22
def saw(f, length, detune=0.0):
    k = int(length * sr); x = np.arange(k) / sr; s = np.zeros(k)
    for d in (-detune, 0, detune):
        ff = f * (2 ** (d / 1200)); s += 2 * ((x * ff) % 1) - 1
    return s / 3
def lowpass(s, cutoff):
    a = np.exp(-2 * np.pi * cutoff / sr); y = np.zeros_like(s); z = 0.0
    for i in range(len(s)): z = a * z + (1 - a) * s[i]; y[i] = z
    return y
def bass(f, length):
    s = saw(f, length) + 0.5 * np.sin(2 * np.pi * f * np.arange(int(length * sr)) / sr)
    return lowpass(s, 180) * env(length, d=1, curve=2.5) * 0.9
def stab(f, length):
    s = saw(f, length, 12) + saw(f * 2, length, 9) * 0.5
    return lowpass(s, 2600) * env(length, curve=9) * 0.28
def riser(length):
    k = int(length * sr); x = np.linspace(0, 1, k); s = rng.standard_normal(k)
    return lowpass(s, 400 + 6000 * x ** 2) * x ** 2 * 0.5 if False else (s * x ** 2 * 0.25)
def impact():
    k = int(1.2 * sr); x = np.arange(k) / sr; f = 30 + 90 * np.exp(-x * 9)
    s = np.sin(np.cumsum(2 * np.pi * f / sr)) * np.exp(-x * 3)
    s += rng.standard_normal(k) * np.exp(-x * 6) * 0.5
    return np.tanh(s * 2) * 0.9

# Notes (minor key, aggressive): E1 bass, chord stabs
E1, G1, A1, B1 = 41.2, 49.0, 55.0, 61.7
bass_pat = [E1, E1, E1, G1, E1, E1, A1, B1]
stab_notes = [(164.8, 196.0, 246.9), (196.0, 246.9, 293.7)]

intro = 2 * beat                      # half-bar impact + riser, then drop
add(impact(), 0); add(riser(intro), 0)
total_beats = int((secs - intro) / beat)
for b in range(total_beats):
    at = intro + b * beat; bar = b // 4; step = b % 4
    add(kick(), at)
    if step in (1, 3): add(clap(), at)
    for s8 in (0, 0.5): add(hat(open_=(s8 == 0.5 and step == 3)), at + s8 * beat, pan=0.3 if s8 else -0.3)
    for s16 in (0.25, 0.75):
        if rng.random() < 0.5: add(hat(), at + s16 * beat, pan=0.5)
    # bass on 8ths
    for s8 in (0, 0.5):
        note = bass_pat[(b * 2 + int(s8 * 2)) % len(bass_pat)]
        add(bass(note, beat * 0.45), at + s8 * beat)
    # stabs on off-beats, alternate chord every 2 bars
    if step in (0, 2):
        ch = stab_notes[(bar // 2) % 2]
        for f in ch: add(stab(f, beat * 0.4), at + beat * 0.5, pan=(f - 220) / 300)
    # fill before each 4-bar phrase: double-time kicks
    if bar % 4 == 3 and step == 3:
        for q in (0.25, 0.5, 0.75): add(kick() * 0.8, at + q * beat)
    # riser in the last bar of every 4-bar phrase
    if bar % 4 == 3 and step == 0: add(riser(4 * beat), at)

# sidechain: duck everything to the kick
duck = np.ones(n)
for b in range(total_beats):
    i = int((intro + b * beat) * sr); k = int(0.22 * sr)
    duck[i:i+k] = np.minimum(duck[i:i+k], 0.35 + 0.65 * (1 - np.exp(-np.arange(min(k, n - i)) / sr * 16)))
L *= duck; R *= duck
mix = np.stack([L, R], 1)
mix = np.tanh(mix * 1.6) * 0.98                        # soft limiter
fade = int(1.5 * sr); mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print('wrote', out, f'{secs}s @ {bpm} BPM, drop at {intro:.2f}s')
