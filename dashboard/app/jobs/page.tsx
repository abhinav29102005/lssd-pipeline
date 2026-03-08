'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import GlowCard from '@/components/GlowCard';
import JobTimeline from '@/components/JobTimeline';
import { motion } from 'framer-motion';
import { useState } from 'react';

const STATUS_COLORS: Record<string, string> = {
  pending: '#fbbf24',
  running: '#a78bfa',
  completed: '#34d399',
  failed: '#fb7185',
  cancelled: '#64748b',
  retry_wait: '#c084fc',
};

const STATUS_BG: Record<string, string> = {
  pending: 'rgba(251, 191, 36, 0.1)',
  running: 'rgba(167, 139, 250, 0.1)',
  completed: 'rgba(52, 211, 153, 0.1)',
  failed: 'rgba(251, 113, 133, 0.1)',
  cancelled: 'rgba(100, 116, 139, 0.1)',
  retry_wait: 'rgba(192, 132, 252, 0.1)',
};

export default function JobsPage() {
  const { data } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => api.jobs({ limit: 500 }),
  });
  const [filter, setFilter] = useState<string>('');

  const jobs = data?.jobs || [];
  const filtered = filter ? jobs.filter((j) => j.status === filter) : jobs;
  const statusCounts = jobs.reduce(
    (acc, j) => ({ ...acc, [j.status]: (acc[j.status] || 0) + 1 }),
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
          Job Queue
        </motion.h1>
        <p className="text-sm mt-2 font-medium" style={{ color: '#8b92b3' }}>
          {data?.total || 0} total jobs · <span className="text-[#a78bfa]">{statusCounts.running || 0} running</span>
        </p>
      </div>

      {/* Status filters */}
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={() => setFilter('')}
          className={`px-5 py-2 rounded-xl text-xs font-bold uppercase tracking-wide transition-all ${!filter
              ? 'bg-[#7c3aed] text-white shadow-glow'
              : 'bg-[#111631] text-[#8b92b3] border border-[rgba(124,58,237,0.1)] hover:border-[#7c3aed]'
            }`}
        >
          All ({jobs.length})
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

      {/* Job Timeline */}
      <JobTimeline jobs={jobs} />

      {/* Status Distribution */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {Object.entries(statusCounts).map(([status, count]) => (
          <GlowCard
            key={status}
            className="!p-5 text-center"
            glowColor={`${STATUS_COLORS[status]}33`}
          >
            <div className="text-3xl font-black font-mono" style={{ color: STATUS_COLORS[status], textShadow: `0 0 16px ${STATUS_COLORS[status]}44` }}>
              {count}
            </div>
            <div className="text-[10px] font-bold tracking-widest uppercase mt-2" style={{ color: '#8b92b3' }}>{status}</div>
          </GlowCard>
        ))}
      </div>

      {/* Job Table */}
      <GlowCard>
        <h2 className="text-sm font-bold tracking-wide text-[#e8eaf6] uppercase mb-4">
          Job Explorer — {filtered.length} jobs
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[#565d80] text-[10px] uppercase tracking-widest border-b border-[rgba(124,58,237,0.1)]">
                <th className="pb-3 font-bold">Job ID</th>
                <th className="pb-3 font-bold">Task Type</th>
                <th className="pb-3 font-bold">Status</th>
                <th className="pb-3 font-bold">Priority</th>
                <th className="pb-3 font-bold">CPU / Mem</th>
                <th className="pb-3 font-bold">Retries</th>
                <th className="pb-3 font-bold">Node</th>
                <th className="pb-3 font-bold">Submitted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(124,58,237,0.05)]">
              {filtered.slice(0, 100).map((job) => (
                <tr key={job.job_id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 font-mono text-[11px] text-[#c4b5fd] font-medium">
                    {job.job_id.slice(0, 8)}…
                  </td>
                  <td className="py-3 text-[#e8eaf6] font-medium text-[12px]">{job.task_type}</td>
                  <td className="py-3">
                    <span
                      className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider"
                      style={{
                        color: STATUS_COLORS[job.status] || '#8b92b3',
                        backgroundColor: STATUS_BG[job.status] || 'rgba(139, 146, 179, 0.1)',
                      }}
                    >
                      <span
                        className="w-1.5 h-1.5 rounded-full"
                        style={{
                          backgroundColor: STATUS_COLORS[job.status],
                          boxShadow: `0 0 6px ${STATUS_COLORS[job.status]}`,
                        }}
                      />
                      {job.status}
                    </span>
                  </td>
                  <td className="py-3 text-[#e8eaf6] font-mono font-bold text-[11px]">{job.priority}</td>
                  <td className="py-3 text-[#8b92b3] font-mono text-[10px]">
                    {job.required_cpu}c / {job.required_memory}MB
                  </td>
                  <td className="py-3">
                    {job.retry_count > 0 ? (
                      <span className="text-[#fbbf24] font-bold font-mono text-[11px]">{job.retry_count}</span>
                    ) : (
                      <span className="text-[#565d80] font-mono text-[11px]">0</span>
                    )}
                  </td>
                  <td className="py-3 font-mono text-[10px] text-[#565d80]">
                    {job.node_assigned || '—'}
                  </td>
                  <td className="py-3 text-[#565d80] text-[10px] font-mono">
                    {job.submission_time
                      ? new Date(job.submission_time).toLocaleTimeString()
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
