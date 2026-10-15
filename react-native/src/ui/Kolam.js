// A faint kolam (rangoli) dot-grid with interlacing loops — large dark surfaces only,
// never behind reading text (DESIGN.md §1).
import React from 'react';
import { StyleSheet } from 'react-native';
import Svg, { Defs, Pattern, Circle, Path, Rect } from 'react-native-svg';

export default function Kolam({ color, opacity = 1, style }) {
  return (
    <Svg width="100%" height="100%" style={[StyleSheet.absoluteFill, style]} pointerEvents="none" opacity={opacity}>
      <Defs>
        <Pattern id="kolam" width="44" height="44" patternUnits="userSpaceOnUse">
          <Circle cx="11" cy="11" r="1.4" fill={color} />
          <Circle cx="33" cy="33" r="1.4" fill={color} />
          <Path d="M11 11c6 0 11 5 11 11s5 11 11 11M33 11c-6 0-11 5-11 11s-5 11-11 11"
                stroke={color} strokeWidth="1" fill="none" />
        </Pattern>
      </Defs>
      <Rect width="100%" height="100%" fill="url(#kolam)" />
    </Svg>
  );
}
