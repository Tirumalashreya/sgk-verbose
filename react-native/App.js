import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, BackHandler, useColorScheme } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useFonts, Marcellus_400Regular } from '@expo-google-fonts/marcellus';
import { HankenGrotesk_400Regular, HankenGrotesk_500Medium, HankenGrotesk_600SemiBold, HankenGrotesk_700Bold } from '@expo-google-fonts/hanken-grotesk';
import { NotoSerifDevanagari_500Medium } from '@expo-google-fonts/noto-serif-devanagari';
import { NotoSerifTelugu_400Regular, NotoSerifTelugu_500Medium } from '@expo-google-fonts/noto-serif-telugu';
import { NotoSerifTamil_500Medium } from '@expo-google-fonts/noto-serif-tamil';
import { Suravaram_400Regular } from '@expo-google-fonts/suravaram';

import { useTheme, palettes } from './src/theme';
import { makeT } from './src/i18n';
import { getSessions } from './src/services/api';
import { storage } from './src/services/platform';
import NavBar from './src/ui/NavBar';
import IntroScreen from './src/screens/IntroScreen';
import HomeScreen from './src/screens/HomeScreen';
import LiveScreen from './src/screens/LiveScreen';
import ReadingScreen from './src/screens/ReadingScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import AskScreen from './src/screens/AskScreen';

SplashScreen.preventAutoHideAsync().catch(() => {});

const WITH_NAV = new Set(['home', 'history', 'ask', 'reading']);

export default function App() {
  const [fontsLoaded] = useFonts({
    Marcellus_400Regular, Suravaram_400Regular,
    HankenGrotesk_400Regular, HankenGrotesk_500Medium, HankenGrotesk_600SemiBold, HankenGrotesk_700Bold,
    NotoSerifTelugu_400Regular, NotoSerifTelugu_500Medium, NotoSerifDevanagari_500Medium, NotoSerifTamil_500Medium,
  });
  const [ready, setReady] = useState(false);
  const [showIntro, setShowIntro] = useState(false);
  const [lang, setLangState] = useState('te');
  const [stack, setStack] = useState(['home']);
  const [params, setParams] = useState({});
  // In-flight upload { name, status: uploading|processing|error, startedAt } — lives here so it
  // survives switching screens; a running upload is never started twice.
  const [upload, setUpload] = useState(null);
  const c = useTheme();
  const screen = stack[stack.length - 1];
  const t = makeT(lang);

  useEffect(() => {
    (async () => {
      const [seen, savedLang] = await Promise.all([storage.get('intro_seen'), storage.get('lang')]);
      if (!seen) setShowIntro(true);
      if (savedLang) setLangState(savedLang);
      setReady(true);
    })();
  }, []);
  useEffect(() => { if (fontsLoaded && ready) SplashScreen.hideAsync().catch(() => {}); }, [fontsLoaded, ready]);

  const setLang = (l) => { setLangState(l); storage.set('lang', l); };

  const go = useCallback((s, p = {}) => {
    setParams((prev) => ({ ...prev, ...p }));
    setStack((st) => (s === 'home' ? ['home'] : st[st.length - 1] === s ? st : [...st, s]));
  }, []);
  const stackRef = useRef(stack);
  stackRef.current = stack;
  /** Step back one screen. Returns false when already at the first screen. */
  const back = useCallback(() => {
    if (stackRef.current.length <= 1) return false;
    setStack(stackRef.current.slice(0, -1));
    return true;
  }, []);

  // Android hardware back: step back through screens
  const backRef = useRef(back);
  backRef.current = back;
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => backRef.current());
    return () => sub.remove();
  }, []);

  // Finish a running upload even if the Live screen was left
  useEffect(() => {
    if (upload?.status !== 'processing') return undefined;
    const base = upload.name.replace(/\.[^.]+$/, '');
    const id = setInterval(async () => {
      try {
        const list = (await getSessions()).sessions || [];
        if (list.some((s) => s.title === base && new Date(s.created_at + 'Z') >= new Date(upload.startedAt - 60000))) setUpload(null);
      } catch {}
    }, 8000);
    return () => clearInterval(id);
  }, [upload?.status]);

  if (!fontsLoaded || !ready) return null;   // splash screen stays up

  if (showIntro) {
    return (
      <SafeAreaProvider>
        <StatusBar style="light" />
        <IntroScreen t={t} lang={lang} onDone={() => { setShowIntro(false); storage.set('intro_seen', '1'); }} />
      </SafeAreaProvider>
    );
  }

  const shared = {
    go, back, t, lang, setLang, upload, setUpload,
    pendingUpload: params.upload, clearPendingUpload: () => setParams((p) => ({ ...p, upload: null })),
    pendingLink: params.link, clearPendingLink: () => setParams((p) => ({ ...p, link: null })),
  };
  const immersive = screen === 'live';

  return (
    <SafeAreaProvider>
      <StatusBar style={immersive || c.mode === 'hall' ? 'light' : 'dark'} />
      <View style={{ flex: 1, backgroundColor: immersive ? palettes.hall.bg : c.bg }}>
        <View style={{ flex: 1 }}>
          {screen === 'home' && <HomeScreen {...shared} />}
          {screen === 'live' && <LiveScreen {...shared} />}
          {screen === 'reading' && <ReadingScreen {...shared} session={params.session} />}
          {screen === 'history' && <HistoryScreen {...shared} />}
          {screen === 'ask' && <AskScreen {...shared} />}
        </View>
        {WITH_NAV.has(screen) && <NavBar c={c} t={t} screen={screen} go={go} />}
      </View>
    </SafeAreaProvider>
  );
}
