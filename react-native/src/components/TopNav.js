import React from 'react';
import { View, Text, Pressable, Image } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { C, F, acharyaPhoto } from '../theme';

export default function TopNav({ screen, go, t, dark }) {
  const insets = useSafeAreaInsets();

  const bg = dark ? '#0f0b08' : C.paper;
  const border = dark ? 'rgba(201,167,75,0.2)' : C.line;
  const logo = dark ? '#e8d9b5' : C.ink;
  const muted = dark ? '#7a6a50' : C.muted;

  const NavItem = ({ id, label }) => {
    const active = screen === id;
    const col = active ? (dark ? C.saffron : C.maroon) : muted;
    return (
      <Pressable
        onPress={() => go(id)}
        style={{
          paddingHorizontal: 14, paddingVertical: 6, borderRadius: 99,
          backgroundColor: active ? (dark ? 'rgba(224,132,59,0.15)' : 'rgba(122,46,37,0.08)') : 'transparent',
        }}
      >
        <Text style={{ fontFamily: F.sansSemi, fontSize: 13, color: col }}>{label}</Text>
      </Pressable>
    );
  };

  return (
    <View style={{
      paddingTop: insets.top + 4,
      paddingBottom: 8,
      paddingHorizontal: 18,
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      backgroundColor: bg,
      borderBottomWidth: 1,
      borderBottomColor: border,
    }}>
      {/* Logo */}
      <Pressable onPress={() => go('library')} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <Image source={acharyaPhoto} style={{ width: 30, height: 30, borderRadius: 15, borderWidth: 1, borderColor: '#cdb27a' }} />
        <Text style={{ fontFamily: F.sansSemi, fontSize: 16, color: logo }}>SGKS Notes</Text>
      </Pressable>

      {/* Nav items */}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 2 }}>
        <NavItem id="library" label="Home" />
        <NavItem id="live" label="Live" />
        <NavItem id="history" label="History" />
        <NavItem id="ask" label="Ask" />
      </View>
    </View>
  );
}
