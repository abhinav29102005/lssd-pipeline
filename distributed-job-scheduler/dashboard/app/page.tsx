'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import dynamic from 'next/dynamic';
import AnimatedCounter from '@/components/AnimatedCounter';
import GlowCard from '@/components/GlowCard';
import MetricsCharts from '@/components/MetricsCharts';
import NodeGrid from '@/components/NodeGrid';
import { motion } from 'framer-motion';

const Cluster3D = dynamic(() => import('@/components/Cluster3D'), { ssr: false });

export default function OverviewPage() {
  const { data: status } = useQuery({
    queryKey: ['cluster-status'],
    queryFn: api.clusterStatus,
  });

  const { data: nodesData } = useQuery({
    queryKey: ['nodes'],
    queryFn: () => api.nodes(500),
  });

  const { data: metricsData } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => api.metrics(200),
  });

  const nodes = nodesData?.nodes || [];
  const metrics = metricsData?.metrics || [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <motion.h1
          className="text-4xl font-extrabold tracking-tight"
          style={{ color: '#e8eaf6', textShadow: '0 4px 20px rgba(124,58,237,0.3)' }}
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          Cluster Command Center
        </motion.h1>
        <p className="text-sm mt-2 font-medium" style={{ color: '#8b92b3' }}>
          Real-time monitoring · Distributed HPC Scheduler
        </p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-5">
        <AnimatedCounter
          value={status?.total_nodes || 0}
          label="Total Nodes"
          color="#c4b5fd"
        />
        <AnimatedCounter
          value={status?.active_nodes || 0}
          label="Active Nodes"
          color="#34d399"
        />
        <AnimatedCounter
          value={status?.failed_nodes || 0}
          label="Failed Nodes"
          color="#fb7185"
        />
        <AnimatedCounter
          value={status?.running_jobs || 0}
          label="Running Jobs"
          color="#a78bfa"
        />
        <AnimatedCounter
          value={status?.completed_jobs || 0}
          label="Completed"
          color="#34d399"
        />
        <AnimatedCounter
          value={status?.queue_size || 0}
          label="Queue Size"
          color="#fbbf24"
        />
        <AnimatedCounter
          value={(status?.cluster_utilization || 0) * 100}
          label="Utilization"
          suffix="%"
          precision={1}
          color="#22d3ee"
        />
      </div>

      {/* 3D Cluster Visualization */}
      {nodes.length > 0 && (
        <GlowCard className="!p-0 overflow-hidden" glowColor="rgba(6, 182, 212, 0.12)">
          <div className="p-5 border-b" style={{ borderColor: 'rgba(124,58,237,0.1)' }}>
            <h2 className="text-sm font-bold tracking-wide uppercase" style={{ color: '#e8eaf6' }}>
              3D Cluster Map <span style={{ color: '#6366f1' }}>— {nodes.length} Nodes</span>
            </h2>
          </div>
          <Cluster3D nodes={nodes} className="h-[450px]" />
        </GlowCard>
      )}

      {/* 2D Node Grid */}
      {nodes.length > 0 && (
        <GlowCard glowColor="rgba(124, 58, 237, 0.15)">
          <h2 className="text-sm font-bold tracking-wide uppercase mb-6" style={{ color: '#e8eaf6' }}>
            Node Grid Overview
          </h2>
          <NodeGrid nodes={nodes.slice(0, 200)} />
        </GlowCard>
      )}

      {/* Metrics Charts */}
      {metrics.length > 0 && <MetricsCharts metrics={metrics} />}
    </div>
  );
}
