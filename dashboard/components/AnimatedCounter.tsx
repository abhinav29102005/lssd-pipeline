'use client';

import { motion, useSpring, useTransform } from 'framer-motion';
import { useEffect, useRef } from 'react';

interface AnimatedCounterProps {
  value: number;
  label: string;
  suffix?: string;
  precision?: number;
  color?: string;
  delta?: number;
}

export default function AnimatedCounter({
  value,
  label,
  suffix = '',
  precision = 0,
  color = '#a78bfa',
  delta,
}: AnimatedCounterProps) {
  const spring = useSpring(0, { stiffness: 80, damping: 20 });
  const display = useTransform(spring, (v) =>
    precision > 0 ? v.toFixed(precision) : Math.round(v).toLocaleString()
  );
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    spring.set(value);
  }, [value, spring]);

  useEffect(() => {
    const unsubscribe = display.on('change', (v) => {
      if (ref.current) ref.current.textContent = v + suffix;
    });
    return () => unsubscribe();
  }, [display, suffix]);

  return (
    <div className="glass-card-hover p-5 relative overflow-hidden group">
      {/* Subtle corner glow */}
      <div className="absolute -top-8 -right-8 w-20 h-20 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500"
        style={{ background: `radial-gradient(circle, ${color}22 0%, transparent 70%)` }}
      />

      <p className="text-[10px] font-bold uppercase tracking-[0.15em] mb-3"
        style={{ color: '#565d80' }}
      >
        {label}
      </p>
      <div className="flex items-end gap-2">
        <motion.span
          ref={ref}
          className="text-3xl font-extrabold font-mono tabular-nums"
          style={{ color, textShadow: `0 0 20px ${color}44` }}
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
        >
          0{suffix}
        </motion.span>
        {delta !== undefined && delta !== 0 && (
          <motion.span
            className="text-xs font-bold mb-1 font-mono"
            style={{
              color: delta > 0 ? '#34d399' : '#fb7185',
              textShadow: delta > 0
                ? '0 0 8px rgba(52, 211, 153, 0.4)'
                : '0 0 8px rgba(251, 113, 133, 0.4)',
            }}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {delta > 0 ? '↑' : '↓'} {Math.abs(delta)}
          </motion.span>
        )}
      </div>
    </div>
  );
}
