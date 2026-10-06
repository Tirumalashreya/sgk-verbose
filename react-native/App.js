import React, { useState, useEffect } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useFonts, Marcellus_400Regular } from '@expo-google-fonts/marcellus';
import {
  HankenGrotesk_400Regular, HankenGrotesk_500Medium,
  HankenGrotesk_600SemiBold, HankenGrotesk_700Bold,
} from '@expo-google-fonts/hanken-grotesk';
import { NotoSerifDevanagari_500Medium, NotoSerifDevanagari_600SemiBold } from '@expo-google-fonts/noto-serif-devanagari';
import { NotoSerifTelugu_400Regular, NotoSerifTelugu_500Medium } from '@expo-google-fonts/noto-serif-telugu';

import { C } from './src/theme';
import { makeT } from './src/i18n';
import { getSessions } from './src/services/api';
import TopNav from './src/components/TopNav';
import LibraryScreen from './src/screens/LibraryScreen';
import LiveScreen from './src/screens/LiveScreen';
import DiscourseScreen from './src/screens/DiscourseScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import AskScreen from './src/screens/AskScreen';
import IntroScreen from './src/screens/IntroScreen';

export default function App() {
  const [screen, setScreen] = useState('library');
  const [lang, setLang] = useState('en');
  const [showIntro, setShowIntro] = useState(false);

  useEffect(() => {
    try {
      const seen = localStorage.getItem('shravanam_intro_shown');
      if (!seen) setShowIntro(true);
    } catch {}
  }, []);

  const handleIntroDone = () => {
    try { localStorage.setItem('shravanam_intro_shown', '1'); } catch {}
    setShowIntro(false);
  };
  const [sessionUrl, setSessionUrl] = useState(null);
  const [sessionData, setSessionData] = useState(null);
  const [pendingUpload, setPendingUpload] = useState(null);
  // In-flight file upload {name, status: uploading|processing|done|error, startedAt, knownCount}.
  // Lives here so it survives switching screens.
  const [upload, setUpload] = useState(null);

  // Notice when the uploaded file's session lands, whichever screen is open
  useEffect(() => {
    if (upload?.status !== 'processing') return;
    const id = setInterval(async () => {
      try {
        const sessions = (await getSessions()).sessions || [];
        const newest = sessions[sessions.length - 1];
        if (sessions.length > upload.knownCount && (newest?.notes || newest?.transcript)) {
          setUpload(u => (u ? { ...u, status: 'done' } : u));
        }
      } catch {}
    }, 8000);
    return () => clearInterval(id);
  }, [upload?.status]);
  const t = makeT(lang);

  const [fontsLoaded] = useFonts({
    Marcellus_400Regular,
    HankenGrotesk_400Regular, HankenGrotesk_500Medium,
    HankenGrotesk_600SemiBold, HankenGrotesk_700Bold,
    NotoSerifDevanagari_500Medium, NotoSerifDevanagari_600SemiBold,
    NotoSerifTelugu_400Regular, NotoSerifTelugu_500Medium,
  });

  if (!fontsLoaded) {
    return (
      <View style={{ flex: 1, backgroundColor: C.paper, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color={C.maroon} />
      </View>
    );
  }

  const go = (s, params) => {
    if (params?.url) setSessionUrl(params.url);
    if (params?.session) setSessionData(params.session);
    if (params?.upload) setPendingUpload(params.upload);
    setScreen(s);
  };

  const dark = screen === 'live';
  const shared = { go, t, lang, setLang, sessionUrl, sessionData,
                   pendingUpload, clearPendingUpload: () => setPendingUpload(null),
                   upload, setUpload };

  if (showIntro) {
    return (
      <SafeAreaProvider>
        <IntroScreen onDone={handleIntroDone} />
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <View style={{ flex: 1, backgroundColor: dark ? C.darkBg : C.paper }}>
        <StatusBar style={dark ? 'light' : 'dark'} />
        <TopNav screen={screen} go={go} t={t} dark={dark} />
        {screen === 'library'  && <LibraryScreen  {...shared} />}
        {screen === 'live'     && <LiveScreen     {...shared} />}
        {screen === 'discourse'&& <DiscourseScreen {...shared} />}
        {screen === 'history'  && <HistoryScreen  {...shared} />}
        {screen === 'ask'      && <AskScreen      {...shared} />}
      </View>
    </SafeAreaProvider>
  );
}
