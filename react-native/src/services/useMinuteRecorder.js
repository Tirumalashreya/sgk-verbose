// Records the microphone in one-minute pieces (each uploaded as it finishes),
// and exposes the live voice level for visuals. Works on iOS, Android and web.
import { useRef } from 'react';
import {
  useAudioRecorder, useAudioRecorderState, RecordingPresets,
  requestRecordingPermissionsAsync, setAudioModeAsync,
} from 'expo-audio';

const PIECE_MS = 60000;

export function useMinuteRecorder(onPiece) {
  const recorder = useAudioRecorder({ ...RecordingPresets.HIGH_QUALITY, isMeteringEnabled: true });
  const state = useAudioRecorderState(recorder, 80);
  const running = useRef(false);
  const timer = useRef(null);
  const chain = useRef(Promise.resolve());   // pieces are cut and uploaded strictly in order

  const cutPiece = (isLast) => {
    chain.current = chain.current.then(async () => {
      try { await recorder.stop(); } catch {}
      if (recorder.uri) await onPiece(recorder.uri, isLast);
      if (running.current && !isLast) {
        await recorder.prepareToRecordAsync();
        recorder.record();
        timer.current = setTimeout(() => cutPiece(false), PIECE_MS);
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
    timer.current = setTimeout(() => cutPiece(false), PIECE_MS);
  };

  /** Stops and resolves only after the last piece has been uploaded. */
  const stop = async () => {
    running.current = false;
    clearTimeout(timer.current);
    await cutPiece(true);
  };

  // metering is dBFS (about -160 silence … 0 loudest); 0–1 is easier to animate
  const level = state.metering == null ? 0 : Math.max(0, Math.min(1, (state.metering + 60) / 60));
  return { start, stop, level, isRecording: !!state.isRecording, durationMillis: state.durationMillis || 0 };
}
