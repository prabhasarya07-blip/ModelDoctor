/* ────────────────────────────────────────
   NeuralBackground — 3D Animated Neural Network
   Three.js powered — DNA helix, particles,
   floating nodes connected by neural links
   Replaces the old CSS-only background
   ──────────────────────────────────────── */

"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

/* ─── Floating Particle Field ─── */
function ParticleField() {
  const ref = useRef<THREE.Points>(null);
  const geoRef = useRef<THREE.BufferGeometry>(null!);
  const COUNT = 300;
  const initialized = useRef(false);

  const positions = useMemo(() => {
    const pos = new Float32Array(COUNT * 3);
    for (let i = 0; i < COUNT; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 30;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 20;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 15 - 5;
    }
    return pos;
  }, []);

  const colors = useMemo(() => {
    const col = new Float32Array(COUNT * 3);
    const palette = [
      new THREE.Color("#4285F4"),
      new THREE.Color("#00DEB4"),
      new THREE.Color("#A855F7"),
    ];
    for (let i = 0; i < COUNT; i++) {
      const c = palette[Math.floor(Math.random() * 3)];
      col[i * 3] = c.r;
      col[i * 3 + 1] = c.g;
      col[i * 3 + 2] = c.b;
    }
    return col;
  }, []);

  useFrame((state) => {
    if (!ref.current) return;
    const geo = ref.current.geometry;
    if (!initialized.current) {
      geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
      initialized.current = true;
    }
    const posAttr = geo.getAttribute("position") as THREE.BufferAttribute;
    if (!posAttr) return;
    const t = state.clock.elapsedTime;
    for (let i = 0; i < COUNT; i++) {
      const ix = i * 3;
      posAttr.array[ix + 1] += Math.sin(t * 0.3 + posAttr.array[ix] * 0.2) * 0.003;
    }
    posAttr.needsUpdate = true;
    ref.current.rotation.y = t * 0.015;
  });

  return (
    <points ref={ref}>
      <bufferGeometry ref={geoRef} />
      <pointsMaterial
        size={0.06}
        vertexColors
        transparent
        opacity={0.6}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}

/* ─── DNA Helix ─── */
function DNAHelix() {
  const groupRef = useRef<THREE.Group>(null);
  const POINTS = 50;
  const RADIUS = 1.5;
  const HEIGHT = 10;
  const TURNS = 3;

  const { strand1, strand2, connections } = useMemo(() => {
    const s1: [number, number, number][] = [];
    const s2: [number, number, number][] = [];
    const conn: { mid: [number, number, number]; q: THREE.Quaternion; len: number }[] = [];

    for (let i = 0; i < POINTS; i++) {
      const t = i / POINTS;
      const y = t * HEIGHT - HEIGHT / 2;
      const angle = t * Math.PI * 2 * TURNS;
      const x1 = Math.cos(angle) * RADIUS;
      const z1 = Math.sin(angle) * RADIUS;
      const x2 = Math.cos(angle + Math.PI) * RADIUS;
      const z2 = Math.sin(angle + Math.PI) * RADIUS;
      s1.push([x1, y, z1]);
      s2.push([x2, y, z2]);

      if (i % 4 === 0) {
        const from = new THREE.Vector3(x1, y, z1);
        const to = new THREE.Vector3(x2, y, z2);
        const mid = new THREE.Vector3().addVectors(from, to).multiplyScalar(0.5);
        const dir = new THREE.Vector3().subVectors(to, from);
        const len = dir.length();
        const q = new THREE.Quaternion();
        q.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
        conn.push({ mid: [mid.x, mid.y, mid.z], q, len });
      }
    }
    return { strand1: s1, strand2: s2, connections: conn };
  }, []);

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.003;
      groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.2) * 0.4;
    }
  });

  return (
    <group ref={groupRef} position={[5, 0, -3]}>
      {strand1.map((pos, i) => (
        <mesh key={`a${i}`} position={pos}>
          <sphereGeometry args={[0.08, 8, 8]} />
          <meshStandardMaterial color="#4285F4" emissive="#4285F4" emissiveIntensity={0.6} transparent opacity={0.8} />
        </mesh>
      ))}
      {strand2.map((pos, i) => (
        <mesh key={`b${i}`} position={pos}>
          <sphereGeometry args={[0.08, 8, 8]} />
          <meshStandardMaterial color="#00DEB4" emissive="#00DEB4" emissiveIntensity={0.6} transparent opacity={0.8} />
        </mesh>
      ))}
      {connections.map((c, i) => (
        <mesh key={`c${i}`} position={c.mid} quaternion={c.q}>
          <cylinderGeometry args={[0.02, 0.02, c.len, 4]} />
          <meshStandardMaterial color="#A855F7" emissive="#A855F7" emissiveIntensity={0.3} transparent opacity={0.4} />
        </mesh>
      ))}
    </group>
  );
}

/* ─── Neural Network Nodes ─── */
function NeuralNodes() {
  const groupRef = useRef<THREE.Group>(null);

  const nodes = useMemo(() => {
    const n: { pos: [number, number, number]; color: string; size: number }[] = [];
    // 3 layers of neural network nodes
    for (let layer = 0; layer < 3; layer++) {
      const count = [4, 6, 3][layer];
      const x = -6 + layer * 3;
      for (let j = 0; j < count; j++) {
        const y = (j - count / 2) * 1.5;
        n.push({
          pos: [x, y, -4],
          color: ["#4285F4", "#00DEB4", "#A855F7"][layer],
          size: 0.15 + Math.random() * 0.08,
        });
      }
    }
    return n;
  }, []);

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.4) * 0.2;
    }
  });

  return (
    <group ref={groupRef} position={[-2, 0, -2]}>
      {nodes.map((node, i) => (
        <mesh key={i} position={node.pos}>
          <sphereGeometry args={[node.size, 12, 12]} />
          <meshStandardMaterial
            color={node.color}
            emissive={node.color}
            emissiveIntensity={0.4}
            transparent
            opacity={0.6}
          />
        </mesh>
      ))}
    </group>
  );
}

/* ─── Wireframe Torus ─── */
function FloatingTorus() {
  const ref = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.x = state.clock.elapsedTime * 0.1;
      ref.current.rotation.z = state.clock.elapsedTime * 0.05;
    }
  });

  return (
    <mesh ref={ref} position={[0, 0, -8]}>
      <torusKnotGeometry args={[3, 0.5, 100, 12]} />
      <meshStandardMaterial
        color="#0A0A14"
        emissive="#4285F4"
        emissiveIntensity={0.06}
        wireframe
        transparent
        opacity={0.1}
      />
    </mesh>
  );
}

/* ─── Main 3D Scene ─── */
function Scene() {
  return (
    <>
      <ambientLight intensity={0.2} />
      <pointLight position={[10, 8, 10]} intensity={0.8} color="#4285F4" />
      <pointLight position={[-8, -5, 5]} intensity={0.5} color="#00DEB4" />
      <pointLight position={[0, 8, -8]} intensity={0.3} color="#A855F7" />

      <ParticleField />
      <DNAHelix />
      <NeuralNodes />
      <FloatingTorus />
    </>
  );
}

/* ─── Exported Component ─── */
export default function NeuralBackground() {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none">
      {/* Fallback base gradient (shows while Three.js loads) */}
      <div className="absolute inset-0 bg-void" />

      {/* 3D Canvas */}
      <Canvas
        camera={{ position: [0, 0, 10], fov: 55 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
        style={{ background: "transparent" }}
      >
        <Scene />
      </Canvas>

      {/* Edge fades for readability */}
      <div className="absolute inset-0 bg-gradient-to-b from-void via-transparent to-void pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-void via-transparent to-void opacity-40 pointer-events-none" />
    </div>
  );
}
