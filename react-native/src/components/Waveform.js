import React, { useEffect, useRef } from 'react';
import { View, Animated } from 'react-native';
import { C } from '../theme';

// Live audio equaliser — 28 bars looping on the Animated API (native driver).
export default function Waveform() {
  const bars = useRef(Array.from({ length: 28 }, () => new Animated.Value(0.3))).current;

  useEffect(() => {
    const anims = bars.map((b, i) => {
      const dur = 360 + (i % 6) * 70;
      return Animated.loop(
        Animated.sequence([
          Animated.delay(i * 40),
          Animated.timing(b, { toValue: 1, duration: dur, useNativeDriver: true }),
          Animated.timing(b, { toValue: 0.28, duration: dur, useNativeDriver: true }),
        ])
      );
    });
    anims.forEach((a) => a.start());
    return () => anims.forEach((a) => a.stop());
  }, []);

  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', height: 46 }}>
      {bars.map((b, i) => (
        <Animated.View
          key={i}
          style={{
            width: 3,
            height: 38,
            marginHorizontal: 1.5,
            borderRadius: 2,
            backgroundColor: C.saffron,
            transform: [{ scaleY: b }],
          }}
        />
      ))}
    </View>
  );
}
