// 3D deepam (procedural, code-only — the img2threejs approach): a lathe-turned
// brass lamp, oil, wick and a shader flame whose height, sway and light follow
// the voice level. Phones render through expo-gl, web through a canvas.
import React, { useMemo, useRef } from 'react';
import { View } from 'react-native';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

// Brass profile (radius, height) turned around the y axis — base, stem, bowl, lip.
const PROFILE = [
  [0.0, 0.0], [0.52, 0.0], [0.56, 0.04], [0.5, 0.09], [0.2, 0.14], [0.11, 0.24], [0.1, 0.38],
  [0.16, 0.44], [0.42, 0.5], [0.72, 0.6], [0.9, 0.72], [0.98, 0.8], [0.96, 0.84], [0.86, 0.79],
  [0.62, 0.68], [0.3, 0.6], [0.0, 0.58],
];

const flameVertex = `
  uniform float uTime; uniform float uLevel;
  varying float vH; varying vec2 vXZ;
  void main() {
    vec3 p = position;
    float h = clamp((p.y + 1.0) * 0.5, 0.0, 1.0);          // 0 at base, 1 at tip
    float taper = mix(1.0, 0.08, pow(h, 1.35));
    p.xz *= taper;
    p.y = (p.y + 1.0) * (0.9 + uLevel * 0.85) - 0.05;
    float sway = sin(uTime * 3.1 + h * 2.6) * 0.06 + sin(uTime * 7.3) * 0.015;
    p.x += sway * h * (1.0 + uLevel * 1.5);
    p.z += cos(uTime * 2.4 + h * 2.0) * 0.03 * h;
    vH = h; vXZ = position.xz;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
  }`;

const flameFragment = `
  uniform float uLevel; uniform float uCore;
  varying float vH; varying vec2 vXZ;
  void main() {
    float r = length(vXZ);
    vec3 white = vec3(1.0, 0.97, 0.86);
    vec3 gold = vec3(0.98, 0.76, 0.40);
    vec3 orange = vec3(0.93, 0.50, 0.16);
    vec3 red = vec3(0.70, 0.20, 0.10);
    vec3 col = mix(white, gold, smoothstep(0.0, 0.35, vH));
    col = mix(col, orange, smoothstep(0.35, 0.7, vH));
    col = mix(col, red, smoothstep(0.75, 1.0, vH));
    col = mix(col, white, uCore * (1.0 - smoothstep(0.0, 0.55, r)));
    float alpha = (1.0 - smoothstep(0.6, 1.0, vH)) * (1.0 - smoothstep(0.75, 1.0, r));
    alpha *= mix(0.75, 1.0, uLevel);
    gl_FragColor = vec4(col, alpha);
  }`;

const glowFragment = `
  uniform float uLevel; varying vec2 vUv;
  void main() {
    float d = distance(vUv, vec2(0.5));
    float a = smoothstep(0.5, 0.0, d);
    a = pow(a, 2.2) * (0.35 + uLevel * 0.55);
    gl_FragColor = vec4(1.0, 0.70, 0.32, a);
  }`;
const glowVertex = `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;

function Lamp({ levelRef, activeRef }) {
  const light = useRef();
  const outer = useRef();
  const inner = useRef();
  const glow = useRef();
  const smooth = useRef(0);

  const lathe = useMemo(() => new THREE.LatheGeometry(PROFILE.map(([x, y]) => new THREE.Vector2(x, y)), 96), []);
  const uniforms = useMemo(() => ({
    outer: { uTime: { value: 0 }, uLevel: { value: 0 }, uCore: { value: 0 } },
    inner: { uTime: { value: 0 }, uLevel: { value: 0 }, uCore: { value: 1 } },
    glow: { uLevel: { value: 0 } },
  }), []);

  useFrame(({ clock, camera }) => {
    const t = clock.getElapsedTime();
    const target = activeRef.current ? levelRef.current : 0.06;
    smooth.current += (target - smooth.current) * 0.18;           // follow the voice, without jitter
    const lvl = smooth.current;
    for (const u of [uniforms.outer, uniforms.inner]) { u.uTime.value = t; u.uLevel.value = lvl; }
    uniforms.glow.uLevel.value = lvl;
    if (light.current) light.current.intensity = 2.2 + lvl * 5 + Math.sin(t * 9) * 0.25 + Math.sin(t * 13.7) * 0.15;
    if (glow.current) { glow.current.quaternion.copy(camera.quaternion); glow.current.scale.setScalar(1.6 + lvl * 1.2); }
  });

  return (
    <group position={[0, -0.55, 0]}>
      <mesh geometry={lathe}>
        <meshStandardMaterial color="#C9973E" metalness={0.85} roughness={0.3} side={THREE.DoubleSide} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.75, 0]}>
        <circleGeometry args={[0.86, 64]} />
        <meshStandardMaterial color="#2A1607" metalness={0.2} roughness={0.15} />
      </mesh>
      <mesh position={[0, 0.81, 0]}>
        <cylinderGeometry args={[0.022, 0.028, 0.13, 12]} />
        <meshStandardMaterial color="#2B1A0C" roughness={0.9} />
      </mesh>
      <group position={[0, 0.86, 0]} scale={[0.17, 0.32, 0.17]}>
        <mesh ref={outer}>
          <sphereGeometry args={[1, 40, 40]} />
          <shaderMaterial vertexShader={flameVertex} fragmentShader={flameFragment} uniforms={uniforms.outer}
            transparent depthWrite={false} blending={THREE.AdditiveBlending} />
        </mesh>
        <mesh ref={inner} scale={[0.55, 0.62, 0.55]}>
          <sphereGeometry args={[1, 32, 32]} />
          <shaderMaterial vertexShader={flameVertex} fragmentShader={flameFragment} uniforms={uniforms.inner}
            transparent depthWrite={false} blending={THREE.AdditiveBlending} />
        </mesh>
      </group>
      <mesh ref={glow} position={[0, 1.02, 0]}>
        <planeGeometry args={[1, 1]} />
        <shaderMaterial vertexShader={glowVertex} fragmentShader={glowFragment} uniforms={uniforms.glow}
          transparent depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
      <pointLight ref={light} position={[0, 1.15, 0.05]} color="#FFB45A" intensity={2.5} distance={5} decay={1.6} />
    </group>
  );
}

export default function Deepam3D({ level = 0, active = false, size = 280 }) {
  // Values read inside the render loop, so changing them never re-renders the canvas
  const levelRef = useRef(level);
  const activeRef = useRef(active);
  levelRef.current = level;
  activeRef.current = active;
  return (
    <View style={{ width: size, height: size }} accessibilityRole="image" accessibilityLabel="Deepam">
      <Canvas
        camera={{ position: [0, 0.75, 3.1], fov: 36 }}
        gl={{ antialias: true, alpha: true }}
        style={{ width: size, height: size, backgroundColor: 'transparent' }}
        onCreated={({ camera }) => camera.lookAt(0, 0.25, 0)}
      >
        <ambientLight color="#4A3420" intensity={0.55} />
        <directionalLight position={[-2.5, 3, 2.5]} color="#FFE2B0" intensity={1.1} />
        <directionalLight position={[2.5, 1.2, -2]} color="#B5652A" intensity={0.8} />
        <Lamp levelRef={levelRef} activeRef={activeRef} />
      </Canvas>
    </View>
  );
}
