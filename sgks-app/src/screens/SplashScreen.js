import React from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  ImageBackground, Dimensions, StatusBar,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors } from '../theme/colors';

const { height } = Dimensions.get('window');
const GURU_IMAGE = require('../../assets/guru.jpg');

export default function SplashScreen({ navigation }) {
  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />

      <ImageBackground source={GURU_IMAGE} style={styles.image} resizeMode="cover">
        {/* Warm pastel veil over the guru photo */}
        <LinearGradient
          colors={['rgba(255,248,240,0.0)', 'rgba(255,240,220,0.35)', 'rgba(255,230,200,0.82)', '#FFF3E4']}
          locations={[0, 0.35, 0.65, 1]}
          style={StyleSheet.absoluteFillObject}
        />

        <Text style={styles.bgOm}>ॐ</Text>

        <View style={styles.topBrand}>
          <Text style={styles.lotusTop}>❀</Text>
        </View>

        <View style={styles.bottomContent}>
          <View style={styles.goldLine} />

          <Text style={styles.brandSgks}>Sgks</Text>
          <Text style={styles.brandLive}>LIVE NOTES</Text>

          <View style={styles.goldLine} />

          <Text style={styles.taglineEn}>AI that listens. Wisdom that stays.</Text>
          <Text style={styles.taglineTe}>ప్రవచనం వినండి. జ్ఞానాన్ని నిలుపుకోండి.</Text>

          <View style={styles.symbolRow}>
            <Text style={styles.symbol}>🪷</Text>
            <Text style={styles.symbolOm}>ॐ</Text>
            <Text style={styles.symbol}>🪷</Text>
          </View>

          <TouchableOpacity
            style={styles.beginBtn}
            onPress={() => navigation.replace('Main')}
          >
            <LinearGradient
              colors={['#D4A017', '#A87800']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.beginGradient}
            >
              <Text style={styles.beginText}>Begin  ❀</Text>
            </LinearGradient>
          </TouchableOpacity>

          <View style={styles.langRow}>
            <TouchableOpacity style={[styles.langBtn, styles.langActive]}>
              <Text style={styles.langActiveText}>ENGLISH</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.langBtn}>
              <Text style={styles.langText}>తెలుగు</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ImageBackground>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFF3E4' },
  image: { flex: 1, justifyContent: 'space-between' },
  bgOm: {
    position: 'absolute',
    fontSize: 300,
    color: colors.gold,
    opacity: 0.06,
    top: height * 0.1,
    alignSelf: 'center',
  },
  topBrand: { alignItems: 'center', paddingTop: 60 },
  lotusTop: { fontSize: 32, color: colors.gold },
  bottomContent: {
    paddingHorizontal: 28,
    paddingBottom: 50,
    alignItems: 'center',
  },
  goldLine: {
    width: 80,
    height: 1.5,
    backgroundColor: colors.gold,
    opacity: 0.8,
    marginVertical: 12,
  },
  brandSgks: {
    fontSize: 56,
    fontWeight: '800',
    color: colors.text,
    letterSpacing: 4,
    textShadowColor: colors.gold,
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 12,
  },
  brandLive: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.gold,
    letterSpacing: 8,
    marginTop: -6,
  },
  taglineEn: {
    fontSize: 15,
    color: colors.text,
    textAlign: 'center',
    marginTop: 16,
    fontStyle: 'italic',
    opacity: 0.85,
  },
  taglineTe: {
    fontSize: 13,
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: 4,
    marginBottom: 8,
  },
  symbolRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    marginVertical: 20,
  },
  symbol: { fontSize: 22 },
  symbolOm: { fontSize: 26, color: colors.gold },
  beginBtn: { width: '100%', borderRadius: 100, overflow: 'hidden', marginBottom: 16 },
  beginGradient: {
    paddingVertical: 18,
    alignItems: 'center',
    borderRadius: 100,
  },
  beginText: { color: '#FFF', fontSize: 17, fontWeight: '700', letterSpacing: 1 },
  langRow: { flexDirection: 'row', gap: 12 },
  langBtn: {
    paddingHorizontal: 24,
    paddingVertical: 11,
    borderRadius: 100,
    borderWidth: 1.5,
    borderColor: colors.gold,
  },
  langActive: { backgroundColor: 'rgba(196,144,15,0.15)' },
  langActiveText: { color: colors.gold, fontWeight: '700', fontSize: 14 },
  langText: { color: colors.textMuted, fontWeight: '600', fontSize: 14 },
});
