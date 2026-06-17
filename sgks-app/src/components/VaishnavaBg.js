import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors } from '../theme/colors';

const { height } = Dimensions.get('window');

function LotusDecor({ size = 200, opacity = 0.07, top, bottom, left, right }) {
  return (
    <Text style={[styles.lotusDecor, { fontSize: size, opacity, top, bottom, left, right }]}>
      ❀
    </Text>
  );
}

function OmDecor({ size = 120, opacity = 0.06, top, bottom, left, right }) {
  return (
    <Text style={[styles.omDecor, { fontSize: size, opacity, top, bottom, left, right }]}>
      ॐ
    </Text>
  );
}

function ChakraDecor({ size = 100, opacity = 0.06, top, bottom, left, right }) {
  return (
    <Text style={[styles.omDecor, { fontSize: size, opacity, top, bottom, left, right }]}>
      ☸
    </Text>
  );
}

export default function VaishnavaBg({ children, style }) {
  return (
    <LinearGradient
      colors={['#FFF8F0', '#FFF3E4', '#FFECD5', '#FFF8F0']}
      locations={[0, 0.3, 0.7, 1]}
      style={[styles.container, style]}
    >
      <LotusDecor size={280} opacity={0.07} top={-60} right={-80} />
      <OmDecor size={160} opacity={0.06} top={height * 0.2} left={-40} />
      <ChakraDecor size={200} opacity={0.055} top={height * 0.45} right={-50} />
      <LotusDecor size={220} opacity={0.06} bottom={100} left={-60} />
      <OmDecor size={100} opacity={0.06} bottom={180} right={20} />

      {/* Gold shimmer lines */}
      <View style={[styles.shimmer, { top: height * 0.3 }]} />
      <View style={[styles.shimmer, { top: height * 0.6, opacity: 0.04 }]} />

      {children}
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  lotusDecor: {
    position: 'absolute',
    color: colors.gold,
    fontWeight: '100',
  },
  omDecor: {
    position: 'absolute',
    color: colors.gold,
  },
  shimmer: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 1,
    backgroundColor: colors.gold,
    opacity: 0.1,
  },
});
