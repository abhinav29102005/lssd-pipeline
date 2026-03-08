'use client';

import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useRef, useMemo } from 'react';
import * as THREE from 'three';
import type { Node } from '@/lib/api';

const STATUS_COLORS: Record<string, string> = {
  available: '#34d399', // neon.green
  busy: '#fbbf24', // neon.yellow
  failed: '#fb7185', // neon.red
  draining: '#22d3ee', // neon.cyan
};

function NodeCube({
  position,
  color,
  label,
  jobs,
}: {
  position: [number, number, number];
  color: string;
  label: string;
  jobs: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const scale = 0.8 + Math.min(jobs, 5) * 0.05;

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.002;
      // Subtle floating animation
      meshRef.current.position.y =
        position[1] + Math.sin(state.clock.elapsedTime * 0.5 + position[0]) * 0.05;
    }
  });

  return (
    <mesh ref={meshRef} position={position} scale={[scale, scale, scale]}>
      <boxGeometry args={[0.6, 0.6, 0.6]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.6}
        metalness={0.8}
        roughness={0.2}
        transparent
        opacity={0.9}
      />
    </mesh>
  );
}

function ClusterGrid({ nodes }: { nodes: Node[] }) {
  const cols = Math.ceil(Math.sqrt(nodes.length));

  const cubes = useMemo(() => {
    return nodes.map((node, i) => {
      const row = Math.floor(i / cols);
      const col = i % cols;
      const x = (col - cols / 2) * 1.0;
      const z = (row - cols / 2) * 1.0;
      const color = STATUS_COLORS[node.status] || '#565d80';

      return (
        <NodeCube
          key={node.node_id}
          position={[x, 0, z]}
          color={color}
          label={node.node_id}
          jobs={node.current_jobs}
        />
      );
    });
  }, [nodes, cols]);

  return <>{cubes}</>;
}

interface Cluster3DProps {
  nodes: Node[];
  className?: string;
}

export default function Cluster3D({ nodes, className = '' }: Cluster3DProps) {
  return (
    <div className={`relative rounded-2xl overflow-hidden ${className}`}>
      <Canvas
        camera={{ position: [0, 12, 18], fov: 50 }}
        style={{ height: '100%', background: 'transparent' }}
        gl={{ alpha: true, antialias: true }}
      >
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 15, 10]} intensity={2} color="#a78bfa" />
        <pointLight position={[-10, 10, -10]} intensity={1.5} color="#06b6d4" />
        <directionalLight position={[0, 20, 0]} intensity={0.5} color="#7c3aed" />

        <ClusterGrid nodes={nodes} />

        <OrbitControls
          enableZoom={true}
          enablePan={true}
          autoRotate
          autoRotateSpeed={0.5}
          maxPolarAngle={Math.PI / 2.2}
          minDistance={5}
          maxDistance={40}
        />

        {/* Subtle ground plane matching the void background */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.5, 0]}>
          <planeGeometry args={[50, 50]} />
          <meshStandardMaterial
            color="#05060b"
            transparent
            opacity={0.6}
            metalness={0.9}
            roughness={0.1}
          />
        </mesh>
      </Canvas>

      {/* Legend overlay */}
      <div className="absolute bottom-4 left-4 flex gap-4 text-[10px] font-bold tracking-wider uppercase">
        {Object.entries(STATUS_COLORS).map(([status, color]) => (
          <div key={status} className="flex items-center gap-2">
            <div
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: color, boxShadow: `0 0 10px ${color}` }}
            />
            <span style={{ color: '#8b92b3' }}>{status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
