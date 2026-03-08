'use client';

import { motion } from 'framer-motion';
import { ReactNode } from 'react';

interface GlowCardProps {
  children: ReactNode;
  className?: string;
  glowColor?: string;
}

export default function GlowCard({
  children,
  className = '',
  glowColor = 'rgba(124, 58, 237, 0.12)',
}: GlowCardProps) {
  return (
    <motion.div
      className={`glass-card-hover p-6 relative overflow-hidden ${className}`}
      whileHover={{
        boxShadow: `0 8px 40px ${glowColor}, inset 0 1px 0 rgba(255,255,255,0.04)`,
      }}
      transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
    >
      {children}
    </motion.div>
  );
}
