// 2D deepam — fallback for the 3D lamp (no WebGL, or Reduce Motion). The flame
// grows, brightens and sways with the voice level (0–1).
import React, { useEffect, useRef } from 'react';
import { View, Animated, Easing } from 'react-native';
import Svg, { Defs, RadialGradient, LinearGradient, Stop, Path, Ellipse, Circle } from 'react-native-svg';

const AnimatedView = Animated.View;

export default function Deepam2D({ level = 0, active = false, size = 220, reduceMotion = false }) {
  const flicker = useRef(new Animated.Value(0)).current;
  const lvl = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (reduceMotion) return;
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(flicker, { toValue: 1, duration: 1300, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      Animated.timing(flicker, { toValue: 0, duration: 1100, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
    ]));
    loop.start();
    return () => loop.stop();
  }, [reduceMotion]);
  useEffect(() => {
    Animated.timing(lvl, { toValue: active ? level : 0, duration: 140, easing: Easing.out(Easing.quad), useNativeDriver: true }).start();
  }, [level, active]);

  const flameScale = Animated.add(0.85, Animated.add(Animated.multiply(lvl, 0.55), Animated.multiply(flicker, 0.06)));
  const sway = flicker.interpolate({ inputRange: [0, 1], outputRange: ['-3deg', '3deg'] });
  const glow = Animated.add(0.35, Animated.multiply(lvl, 0.6));
  const w = size, h = size;
  return (
    <View style={{ width: w, height: h, alignItems: 'center', justifyContent: 'flex-end' }} accessibilityRole="image" accessibilityLabel="Deepam">
      <AnimatedView style={{ position: 'absolute', top: 0, width: w, height: h * 0.8, opacity: glow }}>
        <Svg width={w} height={h * 0.8}>
          <Defs>
            <RadialGradient id="halo" cx="50%" cy="55%" r="50%">
              <Stop offset="0" stopColor="#F3C672" stopOpacity="0.55" />
              <Stop offset="0.5" stopColor="#E9922E" stopOpacity="0.16" />
              <Stop offset="1" stopColor="#E9922E" stopOpacity="0" />
            </RadialGradient>
          </Defs>
          <Circle cx={w / 2} cy={h * 0.44} r={w * 0.45} fill="url(#halo)" />
        </Svg>
      </AnimatedView>
      <AnimatedView style={{ position: 'absolute', top: h * 0.305, width: w * 0.22, height: h * 0.42, transformOrigin: 'bottom',
        transform: [{ scaleY: flameScale }, { rotate: sway }] }}>
        <Svg width="100%" height="100%" viewBox="0 0 40 80">
          <Defs>
            <LinearGradient id="flame" x1="0" y1="1" x2="0" y2="0">
              <Stop offset="0" stopColor="#FFF4D6" />
              <Stop offset="0.35" stopColor="#F3C672" />
              <Stop offset="0.75" stopColor="#E9922E" />
              <Stop offset="1" stopColor="#C2402F" stopOpacity="0.85" />
            </LinearGradient>
          </Defs>
          <Path d="M20 2C26 22 36 36 36 54a16 16 0 0 1-32 0C4 36 14 22 20 2z" fill="url(#flame)" />
          <Path d="M20 34c3 9 7 14 7 21a7 7 0 0 1-14 0c0-7 4-12 7-21z" fill="#FFF8E6" opacity="0.85" />
        </Svg>
      </AnimatedView>
      <Svg width={w * 0.78} height={h * 0.34} viewBox="0 0 160 70">
        <Defs>
          <LinearGradient id="brass" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#F3C672" />
            <Stop offset="0.45" stopColor="#D9A84E" />
            <Stop offset="1" stopColor="#8C6420" />
          </LinearGradient>
        </Defs>
        <Path d="M8 14c10 18 34 28 72 28s62-10 72-28c-8 4-16 6-24 6H32c-8 0-16-2-24-6z" fill="url(#brass)" />
        <Ellipse cx="80" cy="14" rx="72" ry="7" fill="#5C3F12" />
        <Ellipse cx="80" cy="13" rx="64" ry="4.5" fill="#2A1A08" />
        <Path d="M78.5 13c0-4 1-7 1.5-9 .5 2 1.5 5 1.5 9z" fill="#3A2510" />
        <Path d="M70 42h20l6 14H64z" fill="url(#brass)" />
        <Ellipse cx="80" cy="60" rx="34" ry="7" fill="url(#brass)" />
      </Svg>
    </View>
  );
}
