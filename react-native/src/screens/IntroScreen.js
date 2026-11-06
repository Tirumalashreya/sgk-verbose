// Intro — the Acharya's photo fills the whole page; SGK'S Notes, recording waves, one action.
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { palettes, F, T, S, ACHARYA, ACHARYA_TE, acharyaIntroPhoto } from '../theme';
import { Button, Enter } from '../ui/kit';
import Waveform from '../ui/Waveform';
import CoverImage from '../ui/CoverImage';

const c = palettes.hall;

export default function IntroScreen({ onDone, t }) {
  const insets = useSafeAreaInsets();
  return (
    <View style={st.page}>
      <CoverImage source={acharyaIntroPhoto} size={{ width: 1280, height: 854 }} focus={{ x: 0.48, y: 0.3 }} accessibilityLabel={ACHARYA} />
      {/* darken only the lower part so the text reads over the photo */}
      <LinearGradient colors={['rgba(14,11,31,0)', 'rgba(14,11,31,0.55)', 'rgba(14,11,31,0.94)', c.bg]}
        locations={[0, 0.5, 0.74, 1]} style={StyleSheet.absoluteFill} />
      <View style={[st.content, { paddingBottom: insets.bottom + S.x3 }]}>
        <Enter style={{ alignItems: 'center' }}>
          <Waveform color={c.brassBright} accent={c.kumkumText} height={52} />
        </Enter>
        <Enter delay={150} style={{ alignItems: 'center', marginTop: S.xxl }}>
          <Text style={[T.display, st.title, { color: c.ink }]}>SGK'S Notes</Text>
          <Text style={[T.caption, { color: c.brass, marginTop: S.m }]}>{ACHARYA.toUpperCase()}</Text>
          <Text style={{ fontFamily: F.read, fontSize: 13.5, color: c.inkSoft, marginTop: 4 }}>{ACHARYA_TE}</Text>
          <Text style={[T.body, { color: c.inkSoft, textAlign: 'center', marginTop: S.l }]}>Every word of the pravachanam, kept.</Text>
          <Button c={c} label={t('begin')} onPress={onDone} style={{ marginTop: S.xxl, minWidth: 240 }} />
        </Enter>
      </View>
    </View>
  );
}

const st = StyleSheet.create({
  page: { flex: 1, backgroundColor: c.bg },
  content: { flex: 1, justifyContent: 'flex-end', alignItems: 'center', paddingHorizontal: S.gutter },
  title: { fontSize: 42, lineHeight: 50, letterSpacing: 1 },
});
