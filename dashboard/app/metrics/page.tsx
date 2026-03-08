'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import MetricsCharts from '@/components/MetricsCharts';
import AnimatedCounter from '@/components/AnimatedCounter';
import { motion } from 'framer-motion';

export default function MetricsPage() {
  const { data: status } = useQuery({
    queryKey: ['cluster-status'],
    queryFn: api.clusterStatus,
  });

  const { data: metricsData } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => api.metrics(500),
  });

  const metrics = metricsData?.metrics || [];

  return (
    <div className="space-y-8">
      <div>
        <motion.h1
          className="text-4xl font-extrabold tracking-tight"
          style={{ color: '#e8eaf6', textShadow: '0 4px 20px rgba(124,58,237,0.3)' }}
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          Cluster Metrics
        </motion.h1>
        <p className="text-sm mt-2 font-medium" style={{ color: '#8b92b3' }}>
          Historical performance data · {metrics.length} snapshots
        </p>
      </div>

      {/* Live KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
        <AnimatedCounter
          value={(status?.cluster_utilization || 0) * 100}
          label="Utilization"
          suffix="%"
          precision={1}
          color="#22d3ee"
        />
        <AnimatedCounter
          value={status?.running_jobs || 0}
          label="Running Jobs"
          color="#a78bfa"
        />
        <AnimatedCounter
          value={status?.queue_size || 0}
          label="Queue Depth"
          color="#fbbf24"
        />
        <AnimatedCounter
          value={status?.completed_jobs || 0}
          label="Total Completed"
          color="#34d399"
        />
      </div>

      {/* Charts */}
      {metrics.length > 0 ? (
        <MetricsCharts metrics={metrics} />
      ) : (
        <div className="glass-card p-12 text-center text-[#565d80] font-medium tracking-wide">
          Waiting for metrics data…
        </div>
      )}
    </div>
  );
}
