'use client';

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { Metric } from '@/lib/api';

const COLORS = {
  primary: '#7c3aed', // accent
  success: '#34d399', // neon.green
  warning: '#fbbf24', // neon.yellow
  danger: '#fb7185', // neon.red
  info: '#22d3ee', // neon.cyan
  purple: '#a78bfa', // accent.light
};

function formatTime(ts: string) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

const tooltipStyle = {
  backgroundColor: 'rgba(12, 16, 33, 0.95)',
  border: '1px solid rgba(124, 58, 237, 0.2)',
  borderRadius: '12px',
  color: '#e8eaf6',
  fontSize: '12px',
  boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
};

interface MetricsChartsProps {
  metrics: Metric[];
  className?: string;
}

export default function MetricsCharts({ metrics, className = '' }: MetricsChartsProps) {
  const data = [...metrics].reverse().map((m) => ({
    ...m,
    utilization_pct: +(m.cluster_utilization * 100).toFixed(1),
    time: formatTime(m.timestamp),
  }));

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Cluster Utilization */}
      <div className="glass-card-hover p-6">
        <h3 className="text-sm font-bold tracking-wide uppercase text-[#e8eaf6] mb-4">
          Cluster Utilization %
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="utilGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.info} stopOpacity={0.3} />
                <stop offset="95%" stopColor={COLORS.info} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(124,58,237,0.06)" />
            <XAxis dataKey="time" tick={{ fill: '#565d80', fontSize: 10 }} />
            <YAxis domain={[0, 100]} tick={{ fill: '#565d80', fontSize: 10 }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Area
              type="monotone"
              dataKey="utilization_pct"
              stroke={COLORS.info}
              strokeWidth={2}
              fill="url(#utilGrad)"
              name="Utilization %"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Job Throughput */}
      <div className="glass-card-hover p-6">
        <h3 className="text-sm font-bold tracking-wide uppercase text-[#e8eaf6] mb-4">
          Job Activity
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(124,58,237,0.06)" />
            <XAxis dataKey="time" tick={{ fill: '#565d80', fontSize: 10 }} />
            <YAxis tick={{ fill: '#565d80', fontSize: 10 }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11, color: '#8b92b3', fontWeight: 600 }} />
            <Line
              type="monotone"
              dataKey="running_jobs"
              stroke={COLORS.purple}
              strokeWidth={2}
              dot={false}
              name="Running"
            />
            <Line
              type="monotone"
              dataKey="completed_jobs"
              stroke={COLORS.success}
              strokeWidth={2}
              dot={false}
              name="Completed"
            />
            <Line
              type="monotone"
              dataKey="queue_size"
              stroke={COLORS.warning}
              strokeWidth={2}
              dot={false}
              name="Queue"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Node Health */}
      <div className="glass-card-hover p-6">
        <h3 className="text-sm font-bold tracking-wide uppercase text-[#e8eaf6] mb-4">
          Node Health Over Time
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="activeGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.success} stopOpacity={0.2} />
                <stop offset="95%" stopColor={COLORS.success} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="failedGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.danger} stopOpacity={0.2} />
                <stop offset="95%" stopColor={COLORS.danger} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(124,58,237,0.06)" />
            <XAxis dataKey="time" tick={{ fill: '#565d80', fontSize: 10 }} />
            <YAxis tick={{ fill: '#565d80', fontSize: 10 }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11, color: '#8b92b3', fontWeight: 600 }} />
            <Area
              type="monotone"
              dataKey="active_nodes"
              stroke={COLORS.success}
              fill="url(#activeGrad)"
              strokeWidth={2}
              name="Active"
            />
            <Area
              type="monotone"
              dataKey="failed_nodes"
              stroke={COLORS.danger}
              fill="url(#failedGrad)"
              strokeWidth={2}
              name="Failed"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
