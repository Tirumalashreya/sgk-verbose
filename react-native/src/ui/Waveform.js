// Recording waves: bars that rise and fall like a live voice (static with Reduce Motion).
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, Animated, Easing, AccessibilityInfo } from 'react-native';

export default function Waveform({ color = '#F3C672', accent = '#E9922E', bars = 28, height = 56, barWidth = 4, gap = 4 }) {
  const values = useMemo(() => Array.from({ length: bars }, () => new Animated.Value(0.3)), [bars]);
  const [reduce, setReduce] = useState(false);
  const loops = useRef([]);
  useEffect(() => { AccessibilityInfo.isReduceMotionEnabled?.().then(setReduce); }, []);
  useEffect(() => {
    if (reduce) return undefined;
    loops.current = values.map((v, i) => {
      const peak = 0.35 + 0.65 * Math.abs(Math.sin(i * 0.55)) * (0.6 + Math.random() * 0.4);
      const dur = 420 + ((i * 97) % 380);
      const loop = Animated.loop(Animated.sequence([
        Animated.timing(v, { toValue: peak, duration: dur, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
        Animated.timing(v, { toValue: 0.18 + Math.random() * 0.15, duration: dur * 0.9, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      ]));
      setTimeout(() => loop.start(), (i * 53) % 400);
      return loop;
    });
    return () => loops.current.forEach((l) => l.stop());
  }, [reduce]);
  return (
    <View style={{ height, flexDirection: 'row', alignItems: 'center', gap }} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {values.map((v, i) => (
        <Animated.View key={i} style={{
          width: barWidth, height, borderRadius: barWidth / 2,
          backgroundColor: i % 5 === 2 ? accent : color,
          transform: [{ scaleY: reduce ? 0.2 + 0.6 * Math.abs(Math.sin(i * 0.55)) : v }],
        }} />
      ))}
    </View>
  );
}
