// Fills its parent with an image, cropped around a focal point (0–1, 0–1) —
// the same crop on iOS, Android and web.
import React, { useState } from 'react';
import { View, Image, StyleSheet } from 'react-native';

// `size` is the image's pixel size ({width, height}); pass it in, because web has
// no Image.resolveAssetSource to read it from the bundled asset.
export default function CoverImage({ source, size, focus = { x: 0.5, y: 0.35 }, accessibilityLabel }) {
  const [box, setBox] = useState(null);
  const { width: iw, height: ih } = size || Image.resolveAssetSource?.(source) || { width: 1, height: 1 };
  let style = null;
  if (box) {
    const scale = Math.max(box.w / iw, box.h / ih);
    const w = iw * scale, h = ih * scale;
    const clamp = (v, min) => Math.min(0, Math.max(min, v));
    style = {
      position: 'absolute', width: w, height: h,
      left: clamp(box.w / 2 - focus.x * w, box.w - w),
      top: clamp(box.h / 2 - focus.y * h, box.h - h),
    };
  }
  return (
    <View style={StyleSheet.absoluteFill} onLayout={(e) => setBox({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height })}
      accessibilityRole="image" accessibilityLabel={accessibilityLabel}>
      {style && <Image source={source} style={style} resizeMode="stretch" />}
    </View>
  );
}
