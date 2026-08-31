import React, { useEffect, useRef } from 'react';
import { View, Text, Image, Pressable, Animated, StyleSheet, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { C, F, acharyaIntroPhoto } from '../theme';
import Waveform from '../components/Waveform';

const { width, height } = Dimensions.get('window');

export default function IntroScreen({ onDone }) {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(20)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 1000, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 0, duration: 900, useNativeDriver: true }),
    ]).start();
  }, []);

  return (
    <View style={{ flex: 1 }}>
      {/* Full-screen photo — covers everything */}
      <Image
        source={acharyaIntroPhoto}
        style={StyleSheet.absoluteFill}
        resizeMode="cover"
      />

      {/* Top scrim — subtle dark for OM text readability */}
      <LinearGradient
        colors={['rgba(0,0,0,0.35)', 'transparent']}
        style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 140 }}
      />

      {/* Bottom scrim — gentle fade only at bottom 45% */}
      <LinearGradient
        colors={['transparent', 'rgba(8,4,1,0.60)', 'rgba(8,4,1,0.85)']}
        locations={[0, 0.5, 1]}
        style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: height * 0.45 }}
      />

      {/* Top: OM + app name */}
      <Animated.View style={[styles.topContent, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
        <Text style={styles.om}>ॐ</Text>
        <Text style={styles.appTag}>SGKS · LIVE NOTES</Text>
      </Animated.View>

      {/* Bottom: waveform + text + button */}
      <Animated.View style={[styles.bottomContent, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
        <Waveform />
        <Text style={styles.taglineEn}>AI that listens.{'\n'}Wisdom that stays.</Text>
        <Text style={styles.taglineTe}>ప్రవచనం వినండి.{'\n'}జ్ఞానాన్ని నిలుపుకోండి.</Text>
        <Pressable onPress={onDone} style={styles.btn}>
          <Text style={styles.btnText}>Continue  →</Text>
        </Pressable>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  topContent: {
    position: 'absolute', top: 52, left: 0, right: 0,
    alignItems: 'center',
  },
  om: { fontSize: 26, color: '#fff', opacity: 0.92 },
  appTag: {
    fontFamily: F.sansSemi, fontSize: 10.5,
    color: 'rgba(255,255,255,0.75)', letterSpacing: 3.5, marginTop: 5,
  },
  bottomContent: {
    position: 'absolute', bottom: 36, left: 24, right: 24,
  },
  taglineEn: {
    fontFamily: F.serif, fontSize: 26, color: '#fff',
    textAlign: 'center', lineHeight: 36, marginTop: 18,
  },
  taglineTe: {
    fontFamily: F.telugu, fontSize: 15,
    color: 'rgba(255,228,170,0.88)',
    textAlign: 'center', marginTop: 8, lineHeight: 26,
  },
  btn: {
    marginTop: 28, backgroundColor: C.saffron,
    borderRadius: 50, paddingVertical: 17,
    alignItems: 'center', justifyContent: 'center',
  },
  btnText: { fontFamily: F.sansSemi, fontSize: 17, color: '#fff' },
});
