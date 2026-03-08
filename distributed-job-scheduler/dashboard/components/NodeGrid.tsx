'use client';

import { motion } from 'framer-motion';
import type { Node } from '@/lib/api';

const STATUS_COLORS: Record<string, string> = {
  available: '#34d399',
  busy: '#fbbf24',
  failed: '#fb7185',
  draining: '#22d3ee',
};

const STATUS_BG: Record<string, string> = {
  available: 'rgba(52, 211, 153, 0.15)',
  busy: 'rgba(251, 191, 36, 0.15)',
  failed: 'rgba(251, 113, 133, 0.15)',
  draining: 'rgba(34, 211, 238, 0.15)',
};

interface NodeGridProps {
  nodes: Node[];
  className?: string;
}

export default function NodeGrid({ nodes, className = '' }: NodeGridProps) {
  return (
    <div className={className}>
      <div className="grid grid-cols-10 sm:grid-cols-12 md:grid-cols-16 lg:grid-cols-20 gap-1.5">
        {nodes.map((node, i) => {
          const color = STATUS_COLORS[node.status] || '#565d80';
          const bg = STATUS_BG[node.status] || 'rgba(86, 93, 128, 0.15)';

          return (
            <motion.div
              key={node.node_id}
              className="relative group cursor-pointer"
              initial={{ opacity: 0, scale: 0.6 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: Math.min(i * 0.003, 0.5), duration: 0.3 }}
              whileHover={{ scale: 1.3, zIndex: 10 }}
            >
              <div
                className="w-full aspect-square rounded-md border transition-all duration-200"
                style={{
                  backgroundColor: bg,
                  borderColor: `${color}44`,
                  boxShadow: `0 0 8px ${color}22`,
                }}
              />
              <div
                className="absolute inset-0 rounded-md opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ boxShadow: `0 0 16px ${color}66` }}
              />

              {/* Tooltip */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20">
                <div className="glass-card px-4 py-3 text-xs whitespace-nowrap min-w-[140px] shadow-glow">
                  <div className="font-bold text-[#e8eaf6] mb-1">{node.node_id}</div>
                  <div className="text-[#8b92b3] font-mono text-[10px] mb-2">
                    {node.cpu_cores} CPU · {node.memory_mb} MB
                  </div>
                  <div style={{ color, textShadow: `0 0 8px ${color}55` }} className="font-bold capitalize flex items-center justify-between">
                    <span>{node.status}</span>
                    <span className="text-[#e8eaf6]">{node.current_jobs} jobs</span>
                  </div>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex gap-6 mt-6 justify-center">
        {Object.entries(STATUS_COLORS).map(([status, color]) => (
          <div key={status} className="flex items-center gap-2 text-[10px] font-bold tracking-wider uppercase">
            <div
              className="w-3 h-3 rounded-sm shadow-glow"
              style={{ backgroundColor: STATUS_BG[status], border: `1px solid ${color}` }}
            />
            <span style={{ color: '#8b92b3' }}>{status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
