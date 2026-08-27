import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Aero-Flare — Wildfire Intelligence Dashboard',
  description: 'Real-time wildfire detection, triage, and spread prediction for Indonesia.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex h-screen flex-col overflow-hidden">
        <nav className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-800 bg-slate-950 px-5 text-white shadow-sm">
          {/* Logo mark */}
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-orange-500 text-white text-xs font-black shadow-lg shadow-orange-500/20">
            AF
          </span>
          <span className="text-sm font-bold tracking-tight">Aero-Flare</span>
          <span className="hidden border-l border-slate-700 pl-3 text-xs text-slate-400 sm:inline">Wildfire Intelligence</span>

          <div className="ml-auto flex items-center gap-1 text-xs text-slate-400">
            <a href="/" className="rounded-md px-3 py-1.5 transition-colors hover:bg-white/10 hover:text-white">
              Dashboard
            </a>
            <a href="/events" className="rounded-md px-3 py-1.5 transition-colors hover:bg-white/10 hover:text-white">
              Events
            </a>
          </div>
        </nav>

        <main className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto">{children}</main>
      </body>
    </html>
  );
}
