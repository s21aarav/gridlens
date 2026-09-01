import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';

export const metadata: Metadata = {
  title: 'GridLens — Agentic Power-System Event Investigation & Engineering Copilot',
  description: 'Evidence-constrained AI copilot for substation protection event diagnosis and root cause analysis.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex flex-col bg-grid-bg text-grid-text selection:bg-grid-cyan selection:text-slate-900">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto p-6">
          {children}
        </main>
        <footer className="border-t border-grid-border py-4 px-6 text-center text-xs text-grid-muted font-mono bg-grid-surface">
          GridLens Substation Copilot • Orion Grid Substation OGS-01 • Industrial Protection Investigation Architecture
        </footer>
      </body>
    </html>
  );
}
