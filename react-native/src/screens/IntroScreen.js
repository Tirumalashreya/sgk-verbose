// Intro — the first moment: lamp-lit hall, the Acharya, one action.
import React from 'react';
import { View, Text, Image, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { palettes, F, T, S, ACHARYA_TE, ACHARYA, acharyaIntroPhoto } from '../theme';
import { Button, Enter } from '../ui/kit';
import Kolam from '../ui/Kolam';
import Deepam from '../ui/Deepam';

const c = palettes.hall;

export default function IntroScreen({ onDone, t, lang }) {
  const insets = useSafeAreaInsets();
  return (
    <View style={{ flex: 1, backgroundColor: c.bg }}>
      <Kolam color={c.kolam} />
      <LinearGradient colors={['rgba(18,13,9,0)', 'rgba(18,13,9,0.9)', c.bg]} locations={[0, 0.55, 1]} style={StyleSheet.absoluteFill} />
      <View style={[st.wrap, { paddingTop: insets.top + S.x4, paddingBottom: insets.bottom + S.xxl }]}>
        <Enter style={{ alignItems: 'center' }}>
          <View style={[st.ring, { borderColor: c.brass }]}>
            <Image source={acharyaIntroPhoto} style={st.portrait} accessibilityLabel={ACHARYA} />
          </View>
          <Text style={[T.caption, { color: c.brass, marginTop: S.xl }]}>{ACHARYA.toUpperCase()}</Text>
          <Text style={{ fontFamily: F.read, fontSize: 13, color: c.muted, marginTop: 4 }}>{ACHARYA_TE}</Text>
        </Enter>

        <Enter delay={180} style={{ alignItems: 'center' }}>
          <Deepam level={0.1} active size={150} />
        </Enter>

        <Enter delay={320} style={{ alignItems: 'center', gap: S.s }}>
          <Text style={[T.displayTe, { color: c.ink, fontSize: 44, lineHeight: 60 }]}>శ్రవణం</Text>
          <Text style={[T.display, { color: c.ink, fontSize: 22 }]}>Shravaṇam</Text>
          <Text style={{ fontFamily: F.read, fontSize: 16, lineHeight: 28, color: c.inkSoft, textAlign: 'center', marginTop: S.s }}>
            ప్రవచనంలోని ప్రతి మాట — భద్రంగా.
          </Text>
          <Text style={[T.body, { color: c.muted, textAlign: 'center' }]}>Every word of the pravachanam, kept.</Text>
          <Button c={c} label={t('begin')} onPress={onDone} style={{ marginTop: S.xxl, minWidth: 220 }} />
        </Enter>
      </View>
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: S.gutter },
  ring: { width: 132, height: 132, borderRadius: 66, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center' },
  portrait: { width: 120, height: 120, borderRadius: 60 },
});
