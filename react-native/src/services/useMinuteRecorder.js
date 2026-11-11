// Records the microphone in one-minute pieces (each uploaded as it finishes),
// and exposes the live voice level for visuals. Works on iOS, Android and web.
import { useEffect, useRef, useState } from 'react';
import { Platform } from 'react-native';
import {
  useAudioRecorder, useAudioRecorderState, RecordingPresets,
  requestRecordingPermissionsAsync, setAudioModeAsync,
} from 'expo-audio';

const PIECE_MS = 60000;
const isWeb = Platform.OS === 'web';

// ── Native (iOS / Android): expo-audio's own recorder, unchanged ───────────
function useNativeMinuteRecorder(onPiece) {
  const recorder = useAudioRecorder({ ...RecordingPresets.HIGH_QUALITY, isMeteringEnabled: true });
  const state = useAudioRecorderState(recorder, 80);
  const running = useRef(false);
  const timer = useRef(null);
  const chain = useRef(Promise.resolve());   // pieces are cut and uploaded strictly in order
  // Tracks how far into the current minute we are, net of time spent paused,
  // so resuming schedules the next cut for what's actually left of the
  // minute instead of a fresh 60s (which would make pieces drift longer).
  const pieceStartedAt = useRef(0);
  const pausedSince = useRef(0);
  const pausedMsThisPiece = useRef(0);
  const [paused, setPaused] = useState(false);

  const scheduleCut = (ms) => { timer.current = setTimeout(() => cutPiece(false), Math.max(ms, 1000)); };

  const cutPiece = (isLast) => {
    chain.current = chain.current.then(async () => {
      try { await recorder.stop(); } catch {}
      if (recorder.uri) await onPiece(recorder.uri, isLast);
      if (running.current && !isLast) {
        await recorder.prepareToRecordAsync();
        recorder.record();
        pieceStartedAt.current = Date.now();
        pausedMsThisPiece.current = 0;
        scheduleCut(PIECE_MS);
      }
    });
    return chain.current;
  };

  const start = async () => {
    const permission = await requestRecordingPermissionsAsync();
    if (!permission.granted) throw new Error('mic-denied');
    // shouldPlayInBackground keeps the mic session alive when the phone is
    // switched away from — needs enableBackgroundRecording in app.json's
    // expo-audio plugin config too (the native half of this), which a plain
    // Expo Go session can't pick up; a custom dev build can.
    await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true, shouldPlayInBackground: true });
    await recorder.prepareToRecordAsync();
    recorder.record();
    running.current = true;
    pieceStartedAt.current = Date.now();
    pausedMsThisPiece.current = 0;
    scheduleCut(PIECE_MS);
  };

  const pause = () => {
    if (!running.current || paused) return;
    clearTimeout(timer.current);
    recorder.pause();
    pausedSince.current = Date.now();
    setPaused(true);
  };

  const resume = () => {
    if (!running.current || !paused) return;
    pausedMsThisPiece.current += Date.now() - pausedSince.current;
    recorder.record();
    const elapsedInPiece = Date.now() - pieceStartedAt.current - pausedMsThisPiece.current;
    scheduleCut(PIECE_MS - elapsedInPiece);
    setPaused(false);
  };

  const stop = async () => {
    running.current = false;
    setPaused(false);
    clearTimeout(timer.current);
    await cutPiece(true);
    await chain.current;
  };

  // metering is dBFS (about -160 silence … 0 loudest); 0–1 is easier to animate
  const level = paused ? 0 : (state.metering == null ? 0 : Math.max(0, Math.min(1, (state.metering + 60) / 60)));
  return { start, stop, pause, resume, paused, level, isRecording: !!state.isRecording, durationMillis: state.durationMillis || 0 };
}

// ── Web: a raw MediaRecorder, kept open for the whole recording ────────────
// expo-audio's web recorder tears the microphone down and re-acquires it with
// a fresh getUserMedia() call every single minute (see prepareToRecordAsync →
// createMediaRecorder in its source). Repeatedly releasing and re-grabbing a
// hardware device races with the browser's own cleanup — the next minute's
// recording can start before real audio is flowing, producing a near-empty
// piece (confirmed: every other minute came back as a ~110-byte stub, just
// the WebM container, no audio). The mic is never released here until Stop,
// so there's nothing to race.
//
// One thing this still needs to get right: MediaRecorder's start(timeslice)
// writes the WebM file header into only the *first* chunk — every chunk
// after that is a continuation fragment with no header of its own, invalid
// as a standalone file (confirmed: ffmpeg's "EBML header parsing failed" on
// every piece after the first, when this used start(PIECE_MS)). So each
// minute instead gets its own start()/stop() cycle on the one persistent
// stream — the mic connection itself is never touched between pieces, only
// the recorder is stopped and restarted on top of it, and stop() always
// produces one complete, independent, valid file.
//
// Screen Lock & Background Survival:
// 1. Screen Wake Lock API keeps the display awake while recording so phones don't auto-sleep.
// 2. An active looping silent HTML5 <audio> element + MediaSession API tells Android/iOS this
//    is an active media playback stream, preventing the OS from suspending the CPU or muting
//    the mic if the user manually locks the phone or switches apps.
// 3. An inline Web Worker timer drives minute piece-cutting so background DOM setTimeout
//    throttling never freezes or delays piece uploads.

const SILENT_WAV_BASE64 = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';

function useWebMinuteRecorder(onPiece) {
  const streamRef = useRef(null);
  const recorderRef = useRef(null);
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const meterBuf = useRef(null);
  const rafId = useRef(null);
  const running = useRef(false);
  const timer = useRef(null);
  const workerRef = useRef(null);
  const wakeLockRef = useRef(null);
  const silentAudioRef = useRef(null);
  const chain = useRef(Promise.resolve());   // pieces are cut and uploaded strictly in order
  const startedAt = useRef(0);
  const pieceStartedAt = useRef(0);
  const pausedSince = useRef(0);
  const pausedMsThisPiece = useRef(0);
  const [level, setLevel] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [paused, setPaused] = useState(false);
  const [durationMillis, setDurationMillis] = useState(0);

  // ── Wake Lock: keep screen on while recording ───────────────────────────
  const acquireWakeLock = async () => {
    if (typeof navigator !== 'undefined' && 'wakeLock' in navigator) {
      try {
        wakeLockRef.current = await navigator.wakeLock.request('screen');
        wakeLockRef.current.addEventListener('release', () => {
          wakeLockRef.current = null;
        });
        console.log('[live] screen wake lock acquired');
      } catch (err) {
        console.warn('[live] wake lock request failed:', err?.message || err);
      }
    }
  };

  const releaseWakeLock = async () => {
    if (wakeLockRef.current) {
      try { await wakeLockRef.current.release(); } catch {}
      wakeLockRef.current = null;
    }
  };

  // ── Background Audio Keeper & MediaSession: prevent OS background muting ─
  const startBackgroundKeeper = () => {
    try {
      if (!silentAudioRef.current && typeof document !== 'undefined') {
        const audio = document.createElement('audio');
        audio.id = 'sgk-bg-keeper';
        audio.src = SILENT_WAV_BASE64;
        audio.loop = true;
        audio.setAttribute('playsinline', 'true');
        audio.setAttribute('webkit-playsinline', 'true');
        audio.volume = 0.01;
        document.body.appendChild(audio);
        silentAudioRef.current = audio;
      }
      silentAudioRef.current?.play().catch((e) => {
        console.warn('[live] background audio play deferred:', e?.message || e);
      });
    } catch (err) {
      console.warn('[live] background keeper init error:', err);
    }

    if (typeof navigator !== 'undefined' && 'mediaSession' in navigator) {
      try {
        navigator.mediaSession.metadata = new MediaMetadata({
          title: 'SGK Pravachana Recording',
          artist: 'Microphone Active (Do not close tab)',
          album: 'Live Discourse Session',
        });
        navigator.mediaSession.playbackState = 'playing';
      } catch {}
    }
  };

  const stopBackgroundKeeper = () => {
    if (silentAudioRef.current) {
      try {
        silentAudioRef.current.pause();
        silentAudioRef.current.remove();
      } catch {}
      silentAudioRef.current = null;
    }
    if (typeof navigator !== 'undefined' && 'mediaSession' in navigator) {
      try {
        navigator.mediaSession.playbackState = 'none';
      } catch {}
    }
  };

  // ── Unthrottled Web Worker Timer for Minute Slicing ─────────────────────
  const initWorker = () => {
    if (typeof Worker === 'undefined' || typeof Blob === 'undefined' || typeof URL === 'undefined') return null;
    try {
      const blob = new Blob([`
        let timerId = null;
        self.onmessage = function(e) {
          const data = e.data || {};
          if (data.action === 'schedule') {
            if (timerId) clearTimeout(timerId);
            timerId = setTimeout(function() {
              self.postMessage('cut');
            }, Math.max(data.ms || 60000, 1000));
          } else if (data.action === 'cancel') {
            if (timerId) { clearTimeout(timerId); timerId = null; }
          }
        };
      `], { type: 'application/javascript' });
      const worker = new Worker(URL.createObjectURL(blob));
      worker.onmessage = (e) => {
        if (e.data === 'cut' && running.current) {
          cutPiece(false);
        }
      };
      return worker;
    } catch (e) {
      console.warn('[live] web worker timer unavailable, fallback to setTimeout', e);
      return null;
    }
  };

  const pollMeter = () => {
    const analyser = analyserRef.current;
    if (analyser) {
      if (!meterBuf.current || meterBuf.current.length !== analyser.fftSize) {
        meterBuf.current = new Float32Array(analyser.fftSize);
      }
      analyser.getFloatTimeDomainData(meterBuf.current);
      let sumSquares = 0;
      for (const sample of meterBuf.current) sumSquares += sample * sample;
      const rms = Math.sqrt(sumSquares / meterBuf.current.length);
      // Same RMS-to-dBFS formula expo-audio itself uses natively, so the
      // waveform reads the same as it did before this change.
      const dbfs = rms === 0 ? -160 : 20 * Math.log10(rms);
      setLevel(Math.max(0, Math.min(1, (dbfs + 60) / 60)));
      setDurationMillis(Date.now() - startedAt.current);
    }
    rafId.current = requestAnimationFrame(pollMeter);
  };

  const cancelCutSchedule = () => {
    clearTimeout(timer.current);
    timer.current = null;
    workerRef.current?.postMessage({ action: 'cancel' });
  };

  const scheduleCut = (ms) => {
    cancelCutSchedule();
    const delay = Math.max(ms, 1000);
    if (workerRef.current) {
      workerRef.current.postMessage({ action: 'schedule', ms: delay });
    } else {
      timer.current = setTimeout(() => cutPiece(false), delay);
    }
  };

  const teardown = () => {
    cancelAnimationFrame(rafId.current);
    rafId.current = null;
    cancelCutSchedule();
    if (workerRef.current) {
      try { workerRef.current.terminate(); } catch {}
      workerRef.current = null;
    }
    releaseWakeLock();
    stopBackgroundKeeper();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    audioCtxRef.current?.close().catch(() => {});
    audioCtxRef.current = null;
    analyserRef.current = null;
  };

  const mimeTypeRef = useRef('');

  const newRecorderOnTheOpenStream = () => {
    const recorder = new MediaRecorder(streamRef.current, {
      ...(mimeTypeRef.current ? { mimeType: mimeTypeRef.current } : {}), bitsPerSecond: 128000,
    });
    recorder.ondataavailable = (e) => {
      if (!e.data || e.data.size === 0) return;
      const uri = URL.createObjectURL(e.data);
      const isLast = !running.current;
      // strictly in order, and Stop can await the very last one
      chain.current = chain.current.then(() => onPiece(uri, isLast));
    };
    return recorder;
  };

  const cutPiece = (isLast) => {
    cancelCutSchedule();
    chain.current = chain.current.then(() => new Promise((resolve) => {
      const recorder = recorderRef.current;
      if (!recorder || recorder.state === 'inactive') { resolve(); return; }
      recorder.addEventListener('stop', () => {
        if (running.current && !isLast) {
          recorderRef.current = newRecorderOnTheOpenStream();
          recorderRef.current.start();
          pieceStartedAt.current = Date.now();
          pausedMsThisPiece.current = 0;
          scheduleCut(PIECE_MS);
        }
        resolve();
      }, { once: true });
      recorder.stop();   // valid whether the recorder is 'recording' or 'paused'; fires one ondataavailable, then 'stop'
    }));
    return chain.current;
  };

  const start = async () => {
    let stream;
    const audioConstraints = {
      audio: {
        channelCount: 1,
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: true,
      }
    };
    try {
      stream = await navigator.mediaDevices.getUserMedia(audioConstraints);
    } catch {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch {
        throw new Error('mic-denied');
      }
    }
    streamRef.current = stream;

    // Monitor track state
    const track = stream.getAudioTracks()[0];
    if (track) {
      track.onmute = () => console.warn('[live] microphone track muted by system');
      track.onunmute = () => console.log('[live] microphone track unmuted');
      track.onended = () => console.warn('[live] microphone track ended');
    }

    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    const ctx = new AudioContextClass();
    if (ctx.state === 'suspended') await ctx.resume().catch(() => {});
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);
    audioCtxRef.current = ctx;
    analyserRef.current = analyser;

    mimeTypeRef.current = typeof MediaRecorder.isTypeSupported === 'function' && MediaRecorder.isTypeSupported('audio/webm')
      ? 'audio/webm' : '';
    running.current = true;
    workerRef.current = initWorker();
    await acquireWakeLock();
    startBackgroundKeeper();

    recorderRef.current = newRecorderOnTheOpenStream();
    recorderRef.current.start();   // no timeslice — one complete file per start()/stop() cycle
    pieceStartedAt.current = Date.now();
    pausedMsThisPiece.current = 0;
    scheduleCut(PIECE_MS);
    setIsRecording(true);
    startedAt.current = Date.now();
    rafId.current = requestAnimationFrame(pollMeter);
  };

  // MediaRecorder's own pause()/resume() keep the same recorder and stream —
  // the eventual piece file is one continuous recording with the paused
  // stretch simply missing, not a stop/restart that would need stitching.
  const pause = () => {
    if (!running.current || paused) return;
    cancelCutSchedule();
    recorderRef.current?.pause();
    cancelAnimationFrame(rafId.current);
    pausedSince.current = Date.now();
    setPaused(true);
    setLevel(0);
    stopBackgroundKeeper();
  };

  const resume = () => {
    if (!running.current || !paused) return;
    const pausedMs = Date.now() - pausedSince.current;
    pausedMsThisPiece.current += pausedMs;
    startedAt.current += pausedMs;   // so durationMillis reflects recorded time, not wall-clock
    startBackgroundKeeper();
    acquireWakeLock();
    recorderRef.current?.resume();
    const elapsedInPiece = Date.now() - pieceStartedAt.current - pausedMsThisPiece.current;
    scheduleCut(PIECE_MS - elapsedInPiece);
    rafId.current = requestAnimationFrame(pollMeter);
    setPaused(false);
  };

  /** Stops and resolves only after the last piece has been uploaded. */
  const stop = async () => {
    running.current = false;
    setIsRecording(false);
    setPaused(false);
    cancelCutSchedule();
    releaseWakeLock();
    stopBackgroundKeeper();
    await cutPiece(true);
    await chain.current;
    teardown();
  };

  useEffect(() => {
    const handleVisibility = async () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'visible' && running.current) {
        // Re-acquire wake lock if released by OS while backgrounded
        if (!wakeLockRef.current) {
          await acquireWakeLock();
        }
        // Resume AudioContext if suspended by OS
        if (audioCtxRef.current && audioCtxRef.current.state === 'suspended') {
          await audioCtxRef.current.resume().catch(() => {});
        }
        // If an entire piece interval elapsed while frozen, trigger immediate cut
        const elapsedThisPiece = Date.now() - pieceStartedAt.current - pausedMsThisPiece.current;
        if (elapsedThisPiece >= PIECE_MS) {
          console.log('[live] cutting overdue piece after visibility restored');
          cutPiece(false);
        }
      }
    };
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', handleVisibility);
    }
    return () => {
      if (typeof document !== 'undefined') {
        document.removeEventListener('visibilitychange', handleVisibility);
      }
      teardown();
    };
  }, []);

  return { start, stop, pause, resume, paused, level, isRecording, durationMillis };
}

export function useMinuteRecorder(onPiece) {
  // isWeb is a fixed platform constant — this never changes across renders
  // for a running app instance, so branching which hook runs here is safe.
  return isWeb ? useWebMinuteRecorder(onPiece) : useNativeMinuteRecorder(onPiece);
}
