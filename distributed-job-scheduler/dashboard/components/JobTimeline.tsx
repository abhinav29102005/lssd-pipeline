'use client';

import { motion } from 'framer-motion';
import type { Job } from '@/lib/api';

const STATUS_COLORS: Record<string, string> = {
  pending: '#fbbf24',
  running: '#a78bfa',
  completed: '#34d399',
  failed: '#fb7185',
  cancelled: '#64748b',
  retry_wait: '#c084fc',
};

interface JobTimelineProps {
  jobs: Job[];
  className?: string;
}

export default function JobTimeline({ jobs, className = '' }: JobTimelineProps) {
  const completedJobs = jobs
    .filter((j) => j.start_time && j.completion_time)
    .slice(0, 50);

  if (completedJobs.length === 0) {
    return (
      <div className={`glass-card p-8 text-center text-[#565d80] font-medium ${className}`}>
        No completed jobs to display on the timeline.
      </div>
    );
  }

  const times = completedJobs.flatMap((j) => [
    new Date(j.start_time!).getTime(),
    new Date(j.completion_time!).getTime(),
  ]);
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);
  const range = maxTime - minTime || 1;

  // Group by node
  const byNode = new Map<string, Job[]>();
  for (const job of completedJobs) {
    const node = job.node_assigned || 'unassigned';
    if (!byNode.has(node)) byNode.set(node, []);
    byNode.get(node)!.push(job);
  }

  const nodeRows = Array.from(byNode.entries()).slice(0, 20);
  const rowHeight = 32;
  const barHeight = 20;
  const svgHeight = nodeRows.length * rowHeight + 40;

  return (
    <div className={`glass-card p-6 overflow-x-auto ${className}`}>
      <h3 className="text-sm font-bold tracking-wide uppercase text-[#e8eaf6] mb-4">
        Job Execution Timeline
      </h3>
      <svg width="100%" height={svgHeight} viewBox={`0 0 900 ${svgHeight}`}>
        {/* Background gridlines */}
        {Array.from({ length: 6 }, (_, i) => {
          const x = (i / 5) * 860 + 40;
          return (
            <line
              key={i}
              x1={x}
              y1={20}
              x2={x}
              y2={svgHeight - 20}
              stroke="rgba(124, 58, 237, 0.08)"
              strokeDasharray="4,4"
            />
          );
        })}

        {nodeRows.map(([node, nodeJobs], rowIdx) => {
          const y = rowIdx * rowHeight + 30;

          return (
            <g key={node}>
              {/* Node label (clipped) */}
              <text
                x={0}
                y={y + barHeight / 2 + 4}
                fill="#565d80"
                fontSize={10}
                fontFamily="JetBrains Mono, monospace"
                fontWeight="500"
              >
                {node.length > 14 ? node.slice(0, 14) + '…' : node}
              </text>

              {/* Job bars */}
              {nodeJobs.map((job) => {
                const start = new Date(job.start_time!).getTime();
                const end = new Date(job.completion_time!).getTime();
                const x = ((start - minTime) / range) * 780 + 110;
                const w = Math.max(3, ((end - start) / range) * 780);
                const color = STATUS_COLORS[job.status] || '#565d80';

                return (
                  <g key={job.job_id}>
                    <rect
                      x={x}
                      y={y}
                      width={w}
                      height={barHeight}
                      rx={4}
                      fill={color}
                      opacity={0.8}
                      style={{ filter: `drop-shadow(0 0 4px ${color}66)` }}
                    >
                      <title>
                        {job.job_id.slice(0, 8)} · {job.task_type} · {job.status}
                        {job.retry_count > 0 ? ` · ${job.retry_count} retries` : ''}
                      </title>
                    </rect>
                    {job.retry_count > 0 && (
                      <text
                        x={x + w / 2}
                        y={y + barHeight / 2 + 3}
                        fill="#05060b"
                        fontSize={9}
                        fontFamily="Inter"
                        fontWeight={800}
                        textAnchor="middle"
                      >
                        R{job.retry_count}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex gap-6 mt-4 justify-center text-[10px] font-bold tracking-wider uppercase">
        {Object.entries(STATUS_COLORS).map(([s, c]) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className="w-3 h-2.5 rounded-sm"
              style={{ backgroundColor: c, boxShadow: `0 0 8px ${c}66` }}
            />
            <span style={{ color: '#8b92b3' }}>{s}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
