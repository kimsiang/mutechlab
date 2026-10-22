"""Original music + SFX for the 30 s promo (numpy synthesis, no samples)."""
import numpy as np, random
from scipy.io import wavfile
from timeline import *

SR = 48000
random.seed(3); rng = np.random.default_rng(3)

def t_axis(dur): return np.arange(int(dur * SR)) / SR
def env(n, a=0.01, d=0.1, s=0.6, r=0.2, dur=None):
    t = np.arange(n) / SR; dur = dur or n / SR
    e = np.ones(n)
    e[t < a] = t[t < a] / a
    m = (t >= a) & (t < a + d); e[m] = 1 - (1 - s) * (t[m] - a) / d
    m = t >= a + d; e[m] = s
    rel = t > dur - r; e[rel] *= np.clip((dur - t[rel]) / r, 0, 1)
    return e
def note(freq, dur, kind="saw", vol=0.3, a=0.01, d=0.1, s=0.6, r=0.2, detune=0.0):
    t = t_axis(dur)
    if kind == "saw":
        w = sum(np.sin(2*np.pi*freq*(1+k*detune)*t + rng.random()*6) for k in (-1, 0, 1)) / 3
        w = 0.5*w + 0.5*(2*((freq*t) % 1) - 1) * 0.6
    elif kind == "sine": w = np.sin(2*np.pi*freq*t)
    elif kind == "tri": w = 2*np.abs(2*((freq*t) % 1) - 1) - 1
    else: w = np.sign(np.sin(2*np.pi*freq*t))
    return (w * env(len(t), a, d, s, r) * vol).astype(np.float32)
def lowpass(x, cutoff):
    from scipy.signal import butter, lfilter
    b, a = butter(2, cutoff / (SR/2)); return lfilter(b, a, x).astype(np.float32)
def place(buf, snd, t):
    i = int(t * SR); j = min(len(buf), i + len(snd))
    if j > i: buf[i:j] += snd[:j - i]

def music(dur=DURATION, t_white=T_WHITE, t_cut=T_CUT, t_image=T_IMAGE):
    buf = np.zeros(int(dur * SR), np.float32)
    bpm = 112; beat = 60 / bpm
    # chord progression (Dm – Bb – F – C), 2 bars each, sweeping up as the muon image appears
    chords = [(146.8, 174.6, 220.0), (116.5, 146.8, 174.6), (174.6, 220.0, 261.6), (130.8, 164.8, 196.0)]
    t = 0.0; bar = 0
    while t < dur - 0.1:
        ch = chords[(bar // 2) % 4]
        # pad
        for f in ch:
            place(buf, lowpass(note(f, beat*4, "saw", 0.07, a=0.4, d=0.5, s=0.8, r=0.8, detune=0.004), 900), t)
        # bass on 1 and 3
        for k in (0, 2):
            place(buf, lowpass(note(ch[0]/2, beat*0.9, "saw", 0.22, a=0.005, d=0.15, s=0.5, r=0.1), 300), t + k*beat)
        # arpeggio 16ths, grows denser after the reveal
        dens = 0.35 if t < t_cut else (0.6 if t < t_image else 0.9)
        for k in range(16):
            if rng.random() < dens:
                f = ch[k % 3] * (2 if k % 4 else 4)
                place(buf, note(f, beat*0.3, "tri", 0.09, a=0.003, d=0.08, s=0.3, r=0.08), t + k*beat/4)
        # kick + hat (from the cutaway onwards)
        if t >= t_cut:
            for k in range(4):
                tk = t_axis(0.25); kick = np.sin(2*np.pi*(55 + 120*np.exp(-tk*30))*tk) * np.exp(-tk*12) * 0.5
                place(buf, kick.astype(np.float32), t + k*beat)
                hat = (rng.random(int(0.05*SR)) * 2 - 1) * np.exp(-t_axis(0.05)*80) * 0.08
                place(buf, hat.astype(np.float32), t + k*beat + beat/2)
        t += beat*4; bar += 1
    # overall swell + duck before the end card
    g = np.ones_like(buf); tt = t_axis(dur)
    g *= np.clip(tt/1.5, 0, 1)
    g[tt > t_white] *= np.clip(1 - (tt[tt > t_white] - t_white)/2.6, 0, 1)
    return buf * g

def sfx(dur=DURATION, ev=None):
    """ev: dict of event times; defaults to the 30 s cut."""
    E = dict(cut=T_CUT, thump=T_CUT + 3.0, rain=(T_MUONS, T_WIDE + 3), image=T_IMAGE, logo=T_LOGO_IN, white=T_WHITE, extra=[])
    if ev: E.update(ev)
    buf = np.zeros(int(dur * SR), np.float32)
    # whoosh at the cutaway
    n = int(1.2*SR); w = (rng.random(n)*2-1) * np.hanning(n)
    place(buf, lowpass(w, 1800).astype(np.float32)*0.5, E['cut'])
    # deep thump as the tunnel comes into view
    tk = t_axis(0.8); th = np.sin(2*np.pi*(45 + 80*np.exp(-tk*8))*tk) * np.exp(-tk*5) * 0.8
    place(buf, th.astype(np.float32), E['thump'])
    # muon hits: short cyan 'ticks'
    for k in range(60):
        t0 = rng.uniform(*E['rain'])
        tk = t_axis(0.09); tick = np.sin(2*np.pi*(2400 + 600*rng.random())*tk) * np.exp(-tk*60) * 0.25
        place(buf, tick.astype(np.float32), t0)
    # rising chord when the image forms
    for i, f in enumerate((261.6, 329.6, 392.0, 523.3)):
        place(buf, note(f, 2.0, "sine", 0.18, a=0.02, d=0.3, s=0.5, r=1.0), E['image'] + i*0.12)
    # logo stinger
    for i, f in enumerate((196.0, 293.7, 392.0, 587.3)):
        place(buf, note(f, 2.5, "sine", 0.2, a=0.01, d=0.4, s=0.4, r=1.5), E['logo'] + i*0.08)
    # soft shimmer on the white card
    for i, f in enumerate((523.3, 659.3, 784.0)):
        place(buf, note(f, 2.5, "sine", 0.12, a=0.3, d=0.5, s=0.5, r=1.5), E['white'] + i*0.1)
    # extra events for longer cuts: ("boom", t) | ("ticks", t0, t1) | ("chord", t) | ("whoosh", t)
    for e in E['extra']:
        if e[0] == "boom":
            tk = t_axis(1.2); b = np.sin(2*np.pi*(40 + 90*np.exp(-tk*6))*tk) * np.exp(-tk*3.5) * 0.9; place(buf, b.astype(np.float32), e[1])
        elif e[0] == "ticks":
            for k in range(int((e[2]-e[1])*4)):
                tk = t_axis(0.09); tick = np.sin(2*np.pi*(2400 + 600*rng.random())*tk) * np.exp(-tk*60) * 0.2
                place(buf, tick.astype(np.float32), rng.uniform(e[1], e[2]))
        elif e[0] == "chord":
            for i, fq in enumerate((261.6, 329.6, 392.0, 523.3)):
                place(buf, note(fq, 2.0, "sine", 0.16, a=0.02, d=0.3, s=0.5, r=1.0), e[1] + i*0.12)
        elif e[0] == "whoosh":
            n = int(1.0*SR); w = (rng.random(n)*2-1) * np.hanning(n); place(buf, lowpass(w, 1800).astype(np.float32)*0.4, e[1])
    return buf

if __name__ == "__main__":
    m = music(); s = sfx()
    mix = m + s
    mix = np.tanh(mix * 1.2) * 0.9
    wavfile.write("audio.wav", SR, (mix * 32767).astype(np.int16))
    print("audio.wav", len(mix)/SR, "s")
