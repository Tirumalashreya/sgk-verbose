// Bottom navigation with the raised Record control (the one allowed shadow).
import React from 'react';
import { View, Text, Pressable, StyleSheet, Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import Icon from './Icon';
import { F, S } from '../theme';

const isTelugu = (s) => /[ఀ-౿]/.test(s || '');

export default function NavBar({ c, t, screen, go }) {
  const insets = useSafeAreaInsets();
  const nav = t('nav');
  const Item = ({ id, icon, label, style }) => {
    const active = screen === id || (id === 'history' && screen === 'reading');
    return (
      <Pressable onPress={() => go(id)} accessibilityRole="tab" accessibilityState={{ selected: active }} accessibilityLabel={label}
        style={[st.item, style]} hitSlop={6}>
        <Icon name={icon} size={23} color={active ? c.brass : c.muted} strokeWidth={active ? 2 : 1.75} />
        <Text style={{ fontFamily: isTelugu(label) ? F.readMed : F.uiSemi, fontSize: isTelugu(label) ? 11.5 : 11, color: active ? c.brass : c.muted, marginTop: 3 }}>{label}</Text>
      </Pressable>
    );
  };
  return (
    <View style={[st.bar, { backgroundColor: c.surface, borderTopColor: c.line, paddingBottom: Math.max(insets.bottom, 10) }]}>
      {/* Left wing: Home in slot 1, Notes in slot 2 (where History was) */}
      <View style={st.leftWing}>
        <Item id="home" icon="home" label={nav.home} style={st.leftItem} />
        <Item id="history" icon="book" label={nav.notes} style={st.leftItem} />
      </View>

      {/* Center: Record (Mic) pinned in exact 50% middle */}
      <Pressable onPress={() => go('live')} accessibilityRole="button" accessibilityLabel={nav.record} style={st.recordWrap}>
        <LinearGradient colors={[c.kumkum, c.kumkumDeep]} style={[st.record, { borderColor: c.bg }]}>
          <Icon name="mic" size={26} color={c.onFill} />
        </LinearGradient>
        <Text style={{ fontFamily: isTelugu(nav.record) ? F.readMed : F.uiSemi, fontSize: 11, color: screen === 'live' ? c.brass : c.muted, marginTop: 2 }}>{nav.record}</Text>
      </Pressable>

      {/* Right wing: Ask */}
      <View style={st.rightWing}>
        <Item id="ask" icon="search" label={nav.ask} style={st.rightItem} />
      </View>
    </View>
  );
}

const st = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    borderTopWidth: StyleSheet.hairlineWidth,
    paddingTop: 8,
    paddingHorizontal: S.s,
  },
  leftWing: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-around',
  },
  leftItem: {
    flex: 1,
    maxWidth: 76,
  },
  recordWrap: {
    width: 72,
    alignItems: 'center',
    marginTop: -26,
  },
  record: {
    width: 60,
    height: 60,
    borderRadius: 30,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    ...Platform.select({
      ios: { shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 10, shadowOffset: { width: 0, height: 6 } },
      android: { elevation: 8 },
      default: {},
    }),
  },
  rightWing: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-around',
  },
  rightItem: {
    flex: 1,
    maxWidth: 76,
  },
  item: {
    alignItems: 'center',
    justifyContent: 'flex-end',
    minHeight: 48,
  },
});
