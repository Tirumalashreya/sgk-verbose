import React from 'react';
import { View, Text, Pressable } from 'react-native';
import { C, F } from '../theme';

function Item({ label, glyph, active, onPress, center, dark }) {
  if (center) {
    return (
      <Pressable onPress={onPress} style={{ alignItems: 'center', marginBottom: 2 }}>
        <View style={{
          width: 52, height: 52, borderRadius: 26,
          backgroundColor: dark ? C.saffron : C.saffron,
          alignItems: 'center', justifyContent: 'center',
          shadowColor: C.saffron, shadowOpacity: 0.55, shadowRadius: 12, shadowOffset: { width: 0, height: 8 }, elevation: 6,
        }}>
          <View style={{ width: 16, height: 16, borderRadius: 8, backgroundColor: '#fff4e2' }} />
        </View>
        <Text style={{ fontFamily: F.sansSemi, fontSize: 10.5, color: dark ? '#c9b78f' : C.maroon, marginTop: 6 }}>{label}</Text>
      </Pressable>
    );
  }
  const col = active
    ? (dark ? C.saffron : C.maroon)
    : (dark ? '#7a6a50' : '#b3a585');
  return (
    <Pressable onPress={onPress} style={{ alignItems: 'center', width: 64 }}>
      <Text style={{ fontSize: 19, color: col }}>{glyph}</Text>
      <Text style={{ fontFamily: F.sansSemi, fontSize: 10.5, color: col, marginTop: 5 }}>{label}</Text>
    </Pressable>
  );
}

export default function BottomNav({ screen, go, t, dark }) {
  return (
    <View style={{
      position: 'absolute', left: 0, right: 0, bottom: 0,
      paddingHorizontal: 30, paddingTop: 10, paddingBottom: 30,
      flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between',
      backgroundColor: dark ? 'rgba(15,11,8,0.95)' : C.paper,
      borderTopWidth: 1,
      borderTopColor: dark ? 'rgba(201,167,75,0.15)' : C.line,
    }}>
      <Item label={t('navLibrary')} glyph="❖" active={screen === 'library'} onPress={() => go('library')} dark={dark} />
      <Item label={t('navRecord')} center onPress={() => go('live')} dark={dark} />
      <Item label={t('navAsk')} glyph="✦" active={screen === 'ask'} onPress={() => go('ask')} dark={dark} />
    </View>
  );
}
