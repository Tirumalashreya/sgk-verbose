// Cross-platform building blocks: one API for iOS, Android and web.
import { Alert, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as DocumentPicker from 'expo-document-picker';

export const isWeb = Platform.OS === 'web';

export const storage = {
  async get(key) {
    try { return await AsyncStorage.getItem(key); } catch { return null; }
  },
  async set(key, value) {
    try { await AsyncStorage.setItem(key, value); } catch {}
  },
};

/** Ask before something destructive. Resolves true when confirmed. */
export function confirm(title, message, confirmLabel = 'Delete') {
  if (isWeb) return Promise.resolve(window.confirm(`${title}\n\n${message}`));
  return new Promise((resolve) =>
    Alert.alert(title, message, [
      { text: 'Cancel', style: 'cancel', onPress: () => resolve(false) },
      { text: confirmLabel, style: 'destructive', onPress: () => resolve(true) },
    ], { cancelable: true, onDismiss: () => resolve(false) }));
}

/** Ask between two choices. Resolves true for `yesLabel`, false for `noLabel`. */
export function choose(title, message, yesLabel, noLabel) {
  if (isWeb) return Promise.resolve(window.confirm(`${title}\n\n${message}\n\nOK — ${yesLabel}\nCancel — ${noLabel}`));
  return new Promise((resolve) =>
    Alert.alert(title, message, [
      { text: noLabel, onPress: () => resolve(false) },
      { text: yesLabel, style: 'default', onPress: () => resolve(true) },
    ], { cancelable: true, onDismiss: () => resolve(false) }));
}

export function notify(title, message) {
  if (isWeb) window.alert(`${title}\n\n${message}`);
  else Alert.alert(title, message);
}

/** Let the user choose one audio file. Returns { name, uri, type, file? } or null. */
export async function pickAudioFile() {
  const result = await DocumentPicker.getDocumentAsync({
    type: ['audio/*', 'video/webm', 'video/mp4'],
    copyToCacheDirectory: true,
    multiple: false,
  });
  if (result.canceled || !result.assets?.length) return null;
  const a = result.assets[0];
  return { name: a.name || 'audio.mp3', uri: a.uri, type: a.mimeType || 'audio/mpeg', file: a.file };
}

/** A file reference in the shape FormData expects on this platform. */
export function formFile(f) {
  if (isWeb) return f.file || f.blob;
  return { uri: f.uri, name: f.name, type: f.type || 'audio/mpeg' };
}
