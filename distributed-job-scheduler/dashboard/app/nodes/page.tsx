'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import NodeGrid from '@/components/NodeGrid';
import GlowCard from '@/components/GlowCard';
import { motion } from 'framer-motion';
import { useState } from 'react';

const STATUS_COLORS: Record<string, string> = {
  available: '#34d399',
  busy: '#fbbf24',
  failed: '#fb7185',
  draining: '#22d3ee',
};

const STATUS_BG: Record<string, string> = {
  available: 'rgba(52, 211, 153, 0.1)',
  busy: 'rgba(251, 191, 36, 0.1)',
  failed: 'rgba(251, 113, 133, 0.1)',
  draining: 'rgba(34, 211, 238, 0.1)',
};

export default function NodesPage() {
  const { data } = useQuery({
    queryKey: ['nodes'],
    queryFn: () => api.nodes(1000),
  });
  const [filter, setFilter] = useState<string>('');

  const nodes = data?.nodes || [];
  const filtered = filter ? nodes.filter((n) => n.status === filter) : nodes;
  const statusCounts = nodes.reduce(
    (acc, n) => ({ ...acc, [n.status]: (acc[n.status] || 0) + 1 }),
    {} as Record<string, number>
  );

  return (
    <div className="space-y-8">
      <div>
        <motion.h1
          className="text-4xl font-extrabold tracking-tight"
          style={{ color: '#e8eaf6', textShadow: '0 4px 20px rgba(124,58,237,0.3)' }}
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          Node Health
        </motion.h1>
        <p className="text-sm mt-2 font-medium" style={{ color: '#8b92b3' }}>
          Monitor all {nodes.length} compute nodes in the cluster
        </p>
      </div>

      {/* Status summary cards */}
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={() => setFilter('')}
          className={`px-5 py-2 rounded-xl text-xs font-bold uppercase tracking-wide transition-all ${!filter
              ? 'bg-[#7c3aed] text-white shadow-glow'
              : 'bg-[#111631] text-[#8b92b3] border border-[rgba(124,58,237,0.1)] hover:border-[#7c3aed]'
            }`}
        >
          All ({nodes.length})
        </button>
        {Object.entries(statusCounts).map(([status, count]) => (
          <button
            key={status}
            onClick={() => setFilter(filter === status ? '' : status)}
            className={`px-5 py-2 rounded-xl text-xs font-bold uppercase tracking-wide transition-all ${filter === status
                ? 'border shadow-glow'
                : 'bg-[#111631] border border-[rgba(124,58,237,0.1)] hover:bg-[#161d3f]'
              }`}
            style={{
              color: STATUS_COLORS[status] || '#8b92b3',
              backgroundColor: filter === status ? STATUS_BG[status] : undefined,
              borderColor: filter === status ? STATUS_COLORS[status] : undefined,
            }}
          >
            {status} ({count})
          </button>
        ))}
      </div>

      {/* Node Grid */}
      <GlowCard glowColor="rgba(34, 211, 238, 0.15)">
        <h2 className="text-sm font-bold tracking-wide uppercase text-[#e8eaf6] mb-6">
          Node Grid — {filtered.length} nodes
        </h2>
        <NodeGrid nodes={filtered} />
      </GlowCard>

      {/* Detailed Table */}
      <GlowCard>
        <h2 className="text-sm font-bold tracking-wide uppercase text-[#e8eaf6] mb-4">Node Details</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[#565d80] text-[10px] uppercase tracking-widest border-b border-[rgba(124,58,237,0.1)]">
                <th className="pb-3 font-bold">Node ID</th>
                <th className="pb-3 font-bold">Status</th>
                <th className="pb-3 font-bold">CPU</th>
                <th className="pb-3 font-bold">Memory</th>
                <th className="pb-3 font-bold">Jobs</th>
                <th className="pb-3 font-bold">Last Heartbeat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(124,58,237,0.05)]">
              {filtered.slice(0, 100).map((node) => (
                <tr key={node.node_id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 font-mono text-[11px] text-[#c4b5fd] font-medium">{node.node_id}</td>
                  <td className="py-3">
                    <span
                      className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider"
                      style={{
                        color: STATUS_COLORS[node.status] || '#8b92b3',
                        backgroundColor: STATUS_BG[node.status] || 'rgba(139, 146, 179, 0.1)',
                      }}
                    >
                      <span
                        className="w-1.5 h-1.5 rounded-full"
                        style={{
                          backgroundColor: STATUS_COLORS[node.status],
                          boxShadow: `0 0 6px ${STATUS_COLORS[node.status]}`,
                        }}
                      />
                      {node.status}
                    </span>
                  </td>
                  <td className="py-3 text-[#e8eaf6] font-mono text-[11px]">{node.cpu_cores} cores</td>
                  <td className="py-3 text-[#e8eaf6] font-mono text-[11px]">{(node.memory_mb / 1024).toFixed(0)} GB</td>
                  <td className="py-3 text-[#34d399] font-mono font-bold text-[11px]">{node.current_jobs}</td>
                  <td className="py-3 text-[#565d80] font-mono text-[10px]">
                    {node.last_heartbeat
                      ? new Date(node.last_heartbeat).toLocaleTimeString()
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlowCard>
    </div>
  );
}
