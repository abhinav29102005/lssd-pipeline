'use client';

import { api, SubmitJobPayload } from '@/lib/api';
import GlowCard from '@/components/GlowCard';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';

const TASK_TYPES = [
  { value: 'compute_pi', label: 'Compute Pi', desc: 'Monte Carlo π estimation' },
  { value: 'matrix_multiplication', label: 'Matrix Multiply', desc: 'Dense matrix product' },
  { value: 'monte_carlo_simulation', label: 'Monte Carlo Sim', desc: 'Statistical simulation' },
  { value: 'data_processing', label: 'Data Processing', desc: 'Tabular ETL pipeline' },
];

export default function SubmitPage() {
  const [form, setForm] = useState<SubmitJobPayload>({
    task_type: 'compute_pi',
    required_cpu: 2,
    required_memory: 1024,
    priority: 10,
    execution_time: 5.0,
  });
  const [result, setResult] = useState<{ id: string; ok: boolean } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [batchCount, setBatchCount] = useState(1);

  const submit = async () => {
    setSubmitting(true);
    setResult(null);
    try {
      if (batchCount <= 1) {
        const res = await api.submitJob(form);
        setResult({ id: res.job_id, ok: true });
      } else {
        // Submit batch sequentially
        const ids: string[] = [];
        for (let i = 0; i < batchCount; i++) {
          const res = await api.submitJob({
            ...form,
            priority: Math.max(1, form.priority + Math.floor(Math.random() * 10) - 5),
            execution_time: +(form.execution_time + Math.random() * 2).toFixed(1),
          });
          ids.push(res.job_id);
        }
        setResult({ id: `${ids.length} jobs submitted`, ok: true });
      }
    } catch {
      setResult({ id: 'Submission failed', ok: false });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <motion.h1
          className="text-4xl font-extrabold tracking-tight"
          style={{ color: '#e8eaf6', textShadow: '0 4px 20px rgba(124,58,237,0.3)' }}
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          Submit Job
        </motion.h1>
        <p className="text-sm mt-2 font-medium" style={{ color: '#8b92b3' }}>
          Submit HPC workloads to the distributed scheduling cluster
        </p>
      </div>

      <GlowCard glowColor="rgba(124, 58, 237, 0.2)">
        <div className="space-y-8">
          {/* Task Type */}
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-widest text-[#565d80] mb-4">
              Task Type
            </label>
            <div className="grid grid-cols-2 gap-4">
              {TASK_TYPES.map((t) => (
                <motion.button
                  key={t.value}
                  onClick={() => setForm({ ...form, task_type: t.value })}
                  className={`p-5 rounded-2xl text-left border transition-all ${form.task_type === t.value
                      ? 'border-[#7c3aed] bg-[#7c3aed]/10 shadow-glow'
                      : 'border-[rgba(124,58,237,0.1)] bg-[#111631] hover:border-[#7c3aed]/50 hover:bg-[#161d3f]'
                    }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div
                    className={`text-sm font-bold ${form.task_type === t.value ? 'text-[#c4b5fd]' : 'text-[#e8eaf6]'
                      }`}
                  >
                    {t.label}
                  </div>
                  <div className="text-xs text-[#8b92b3] mt-1">{t.desc}</div>
                </motion.button>
              ))}
            </div>
          </div>

          {/* Resource Requirements */}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-widest text-[#565d80] mb-3">
                CPU Cores
              </label>
              <input
                type="number"
                min={1}
                max={32}
                value={form.required_cpu}
                onChange={(e) => setForm({ ...form, required_cpu: +e.target.value })}
                className="w-full bg-[#080a14] border border-[rgba(124,58,237,0.2)] rounded-xl px-4 py-3 text-[#e8eaf6] font-mono text-sm focus:outline-none focus:border-[#7c3aed] focus:shadow-glow transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-widest text-[#565d80] mb-3">
                Memory (MB)
              </label>
              <input
                type="number"
                min={128}
                max={65536}
                step={256}
                value={form.required_memory}
                onChange={(e) => setForm({ ...form, required_memory: +e.target.value })}
                className="w-full bg-[#080a14] border border-[rgba(124,58,237,0.2)] rounded-xl px-4 py-3 text-[#e8eaf6] font-mono text-sm focus:outline-none focus:border-[#7c3aed] focus:shadow-glow transition-all"
              />
            </div>
          </div>

          {/* Priority & Execution Time */}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-widest text-[#565d80] mb-3">
                Priority (1–100)
              </label>
              <input
                type="range"
                min={1}
                max={100}
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: +e.target.value })}
                className="w-full accent-[#7c3aed]"
              />
              <div className="text-right text-xs font-mono font-bold text-[#c4b5fd] mt-1">{form.priority}</div>
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-widest text-[#565d80] mb-3">
                Execution Time (s)
              </label>
              <input
                type="number"
                min={0.1}
                max={600}
                step={0.5}
                value={form.execution_time}
                onChange={(e) => setForm({ ...form, execution_time: +e.target.value })}
                className="w-full bg-[#080a14] border border-[rgba(124,58,237,0.2)] rounded-xl px-4 py-3 text-[#e8eaf6] font-mono text-sm focus:outline-none focus:border-[#7c3aed] focus:shadow-glow transition-all"
              />
            </div>
          </div>

          {/* Batch Count */}
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-widest text-[#565d80] mb-3">
              Batch Submission
            </label>
            <div className="flex gap-3">
              {[1, 10, 50, 100, 500].map((n) => (
                <button
                  key={n}
                  onClick={() => setBatchCount(n)}
                  className={`px-4 py-2 rounded-xl text-xs font-bold tracking-wide transition-all ${batchCount === n
                      ? 'bg-[#7c3aed] text-white shadow-glow'
                      : 'bg-[#111631] text-[#8b92b3] border border-[rgba(124,58,237,0.1)] hover:border-[#7c3aed]'
                    }`}
                >
                  {n === 1 ? 'Single' : `×${n}`}
                </button>
              ))}
            </div>
          </div>

          {/* Submit Button */}
          <motion.button
            onClick={submit}
            disabled={submitting}
            className="w-full py-4 rounded-xl text-white font-bold text-sm bg-[linear-gradient(135deg,#7c3aed_0%,#06b6d4_100%)] hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed shadow-glow transition-all mt-4"
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
          >
            {submitting ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Submitting Protocol…
              </span>
            ) : (
              `INITIATE ${batchCount > 1 ? `${batchCount} JOBS` : 'JOB'} SUBMISSION`
            )}
          </motion.button>
        </div>
      </GlowCard>

      {/* Result Toast */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`glass-card p-5 ${result.ok ? 'border-[#34d399]/50 shadow-[0_0_20px_rgba(52,211,153,0.15)] bg-[#34d399]/5'
                : 'border-[#fb7185]/50 shadow-[0_0_20px_rgba(251,113,133,0.15)] bg-[#fb7185]/5'
              }`}
          >
            <div className="flex items-center gap-4">
              <span className="text-2xl">{result.ok ? '⚡' : '⚠️'}</span>
              <div>
                <div className={`text-sm font-bold uppercase tracking-wider ${result.ok ? 'text-[#34d399]' : 'text-[#fb7185]'}`}>
                  {result.ok ? 'Submission Accepted' : 'Submission Failed'}
                </div>
                <div className="text-[11px] text-[#8b92b3] font-mono mt-1">{result.id}</div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
