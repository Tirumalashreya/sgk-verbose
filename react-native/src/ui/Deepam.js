// The Live screen lamp: 3D when the device can draw it, 2D otherwise
// (no WebGL, or Reduce Motion — the 2D lamp also stays still then).
import React from 'react';
import { Platform } from 'react-native';
import Deepam2D from './Deepam2D';

let Deepam3D = null;
let hasGL = true;
if (Platform.OS === 'web') {
  try { hasGL = !!document.createElement('canvas').getContext('webgl'); } catch { hasGL = false; }
}
if (hasGL) {
  try { Deepam3D = require('./Deepam3D').default; } catch { Deepam3D = null; }
}

export default function Deepam(props) {
  if (Deepam3D && !props.reduceMotion && !props.flat) return <Deepam3D {...props} />;
  return <Deepam2D {...props} />;
}
