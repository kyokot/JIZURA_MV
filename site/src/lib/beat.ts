// One clock for the whole page: every stack, title and meter moves to the same beat, with or without sound.
import { useSyncExternalStore } from 'react';

export const BPM = 120;
const SPB = 60 / BPM;

let ac: AudioContext | null = null;
let master: GainNode | null = null;
let origin = performance.now() / 1000; // when beat 0 happened, in performance time (seconds)
let acOrigin = 0; // the same moment in the audio clock
let timer = 0;
let nextBeat = 0;
let on = false;
const subs = new Set<() => void>();

/** beats since beat 0 (fractional) */
export const beatNow = () => (ac && on ? (ac.currentTime - acOrigin) / SPB : (performance.now() / 1000 - origin) / SPB);
export const frac = (x: number) => x - Math.floor(x);
/** 1 on the beat, falling away after it */
export const pulse = (b: number, k = 4) => Math.exp(-k * frac(b));
/** one hop per beat */
export const hop = (b: number) => Math.abs(Math.sin(Math.PI * b));

function drum(t: number, f0: number, f1: number, len: number, vol: number) {
  const o = ac!.createOscillator();
  const g = ac!.createGain();
  o.frequency.setValueAtTime(f0, t);
  o.frequency.exponentialRampToValueAtTime(f1, t + len);
  g.gain.setValueAtTime(vol, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + len);
  o.connect(g).connect(master!);
  o.start(t);
  o.stop(t + len + 0.02);
}

function rim(t: number, vol: number) {
  const n = ac!.sampleRate * 0.04;
  const buf = ac!.createBuffer(1, n, ac!.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n) ** 2;
  const s = ac!.createBufferSource();
  const g = ac!.createGain();
  const hp = ac!.createBiquadFilter();
  hp.type = 'highpass';
  hp.frequency.value = 1800;
  s.buffer = buf;
  g.gain.value = vol;
  s.connect(hp).connect(g).connect(master!);
  s.start(t);
}

const TUNE = [0, 3, 5, 7, 5, 3, 0, -2, 0, 3, 7, 10, 7, 5, 3, 5]; // minor pentatonic, one note per half beat

function schedule() {
  while (acOrigin + nextBeat * SPB < ac!.currentTime + 0.15) {
    const t = acOrigin + nextBeat * SPB;
    const bar = nextBeat % 4;
    drum(t, bar === 0 ? 150 : 120, 42, 0.28, bar === 0 ? 0.9 : 0.6); // the big drum
    rim(t + SPB / 2, 0.12);
    if (bar === 3) rim(t + SPB * 0.75, 0.1);
    for (let h = 0; h < 2; h++) {
      const note = TUNE[(nextBeat * 2 + h) % TUNE.length];
      const o = ac!.createOscillator();
      const g = ac!.createGain();
      const tt = t + (h * SPB) / 2;
      o.type = 'square';
      o.frequency.value = 220 * 2 ** (note / 12);
      g.gain.setValueAtTime(0.05, tt);
      g.gain.exponentialRampToValueAtTime(0.001, tt + 0.16);
      o.connect(g).connect(master!);
      o.start(tt);
      o.stop(tt + 0.18);
    }
    nextBeat++;
  }
}

export function setSound(want: boolean) {
  if (want === on) return;
  if (want) {
    ac ??= new AudioContext();
    master ??= (() => {
      const g = ac!.createGain();
      g.gain.value = 0.5;
      g.connect(ac!.destination);
      return g;
    })();
    void ac.resume();
    // keep the beat where it is: start the audio clock on the next whole beat of the silent clock
    const b = (performance.now() / 1000 - origin) / SPB;
    nextBeat = Math.ceil(b + 0.25);
    acOrigin = ac.currentTime + (nextBeat - b) * SPB - nextBeat * SPB;
    on = true;
    timer = window.setInterval(schedule, 40);
    schedule();
  } else {
    origin = performance.now() / 1000 - beatNow() * SPB;
    on = false;
    clearInterval(timer);
  }
  subs.forEach((f) => f());
}

export const useSound = () =>
  useSyncExternalStore(
    (f) => {
      subs.add(f);
      return () => subs.delete(f);
    },
    () => on,
    () => false,
  );

/** a short click of feedback for the tap game; silent unless sound is on */
export function blip(good: boolean) {
  if (!ac || !on) return;
  drum(ac.currentTime, good ? 880 : 180, good ? 1320 : 90, 0.09, 0.25);
}
