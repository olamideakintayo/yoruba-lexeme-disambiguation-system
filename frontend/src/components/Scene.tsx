import { Canvas, useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';

function ToneParticles() {
  const group = useRef<THREE.Group>(null);
  const marks = useMemo(() => ['á', 'à', 'ẹ', 'ọ', 'ṣ', 'gb', 'ń', 'ā'], []);

  useFrame(({ clock }) => {
    if (group.current) {
      group.current.rotation.y = Math.sin(clock.elapsedTime * 0.18) * 0.25;
      group.current.rotation.x = Math.cos(clock.elapsedTime * 0.12) * 0.08;
    }
  });

  return (
    <group ref={group}>
      {marks.map((mark, index) => {
        const angle = (index / marks.length) * Math.PI * 2;
        const radius = 2.4 + (index % 2) * 0.55;
        return (
          <mesh key={mark} position={[Math.cos(angle) * radius, Math.sin(angle) * 1.2, Math.sin(angle) * radius]}>
            <boxGeometry args={[0.18 + mark.length * 0.08, 0.18, 0.18]} />
            <meshStandardMaterial color={index % 2 === 0 ? '#2a9d8f' : '#e9c46a'} roughness={0.35} />
          </mesh>
        );
      })}
      <mesh>
        <torusKnotGeometry args={[0.75, 0.08, 120, 12]} />
        <meshStandardMaterial color="#264653" metalness={0.2} roughness={0.4} />
      </mesh>
    </group>
  );
}

export function Scene() {
  return (
    <div className="scene" aria-hidden="true">
      <Canvas camera={{ position: [0, 0, 6], fov: 45 }}>
        <ambientLight intensity={0.7} />
        <directionalLight position={[3, 4, 5]} intensity={1.2} />
        <ToneParticles />
      </Canvas>
    </div>
  );
}
