'use client';

import './globals.css';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchInterval: 3000, staleTime: 2000 },
  },
});

const NAV_ITEMS = [
  { href: '/', label: 'Overview', icon: '⚡' },
  { href: '/nodes', label: 'Nodes', icon: '🖥️' },
  { href: '/jobs', label: 'Jobs', icon: '📋' },
  { href: '/metrics', label: 'Metrics', icon: '📊' },
  { href: '/submit', label: 'Submit', icon: '🚀' },
];

function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 border-r flex flex-col z-50"
      style={{
        background: 'linear-gradient(180deg, #080a14 0%, #0c1021 50%, #080a14 100%)',
        borderColor: 'rgba(124, 58, 237, 0.08)',
      }}
    >
      {/* Logo */}
      <div className="p-6 border-b" style={{ borderColor: 'rgba(124, 58, 237, 0.08)' }}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, #7c3aed 0%, #06b6d4 100%)',
              boxShadow: '0 4px 15px rgba(124, 58, 237, 0.3)',
            }}
          >
            <span className="text-lg font-black text-white">⚡</span>
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight" style={{ color: '#e8eaf6' }}>
              Cluster HQ
            </h1>
            <p className="text-[10px] font-semibold tracking-widest uppercase"
              style={{ color: '#565d80' }}
            >
              HPC Scheduler
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-0.5 mt-2">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          return (
            <Link key={item.href} href={item.href}>
              <motion.div
                className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-200"
                style={{
                  background: active
                    ? 'linear-gradient(135deg, rgba(124, 58, 237, 0.15), rgba(6, 182, 212, 0.05))'
                    : 'transparent',
                  color: active ? '#c4b5fd' : '#8b92b3',
                  border: active ? '1px solid rgba(124, 58, 237, 0.2)' : '1px solid transparent',
                }}
                whileHover={{
                  x: 4,
                  color: '#e8eaf6',
                  backgroundColor: active ? undefined : 'rgba(124, 58, 237, 0.06)',
                }}
                whileTap={{ scale: 0.97 }}
              >
                <span className="text-base">{item.icon}</span>
                {item.label}
                {active && (
                  <motion.div
                    layoutId="nav-dot"
                    className="ml-auto w-1.5 h-1.5 rounded-full"
                    style={{
                      background: '#7c3aed',
                      boxShadow: '0 0 8px rgba(124, 58, 237, 0.6)',
                    }}
                  />
                )}
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t" style={{ borderColor: 'rgba(124, 58, 237, 0.06)' }}>
        <div className="flex items-center gap-2 justify-center">
          <div className="w-1.5 h-1.5 rounded-full animate-pulse"
            style={{ background: '#34d399', boxShadow: '0 0 6px rgba(52, 211, 153, 0.5)' }}
          />
          <span className="text-[10px] font-medium" style={{ color: '#565d80' }}>
            v2.0 · Live
          </span>
        </div>
      </div>
    </aside>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <title>Cluster Command Center — Distributed HPC Scheduler</title>
        <meta name="description" content="Real-time monitoring dashboard for a distributed HPC job scheduling platform with 100-1000 compute nodes." />
      </head>
      <body className="bg-grid">
        <QueryClientProvider client={queryClient}>
          <Sidebar />
          <main className="ml-64 min-h-screen">
            <AnimatePresence mode="wait">
              <motion.div
                key={typeof window !== 'undefined' ? window.location.pathname : 'init'}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
                className="p-8"
              >
                {children}
              </motion.div>
            </AnimatePresence>
          </main>
        </QueryClientProvider>
      </body>
    </html>
  );
}
