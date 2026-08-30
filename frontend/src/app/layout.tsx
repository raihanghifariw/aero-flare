import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { Flame, Satellite } from 'lucide-react';
import { NavLinks } from '@/components/layout/NavLinks';
import { LiveClock } from '@/components/layout/LiveClock';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Aero-Flare — Wildfire Intelligence & Telemetry Platform',
  description: 'Real-time satellite wildfire detection, VLM multimodal triage, and spread prediction for Indonesia.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="flex h-screen flex-col overflow-hidden bg-surface font-sans text-ink">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-edge bg-surface-raised px-4 sm:px-6 shadow-sm z-30">
          <div className="flex items-center gap-3.5">
            <a
              href="/"
              className="flex items-center gap-2.5 rounded-full transition-transform focus-visible:ring-2 focus-visible:ring-brand/70"
            >
              <div className="relative flex h-9 w-9 items-center justify-center rounded-2xl bg-brand text-white shadow-md shadow-brand/20">
                <Flame size={18} strokeWidth={2.5} aria-hidden="true" />
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="text-base font-extrabold tracking-tight text-ink">Aero-Flare</span>
                  <span className="rounded-full bg-brand/10 px-2 py-0.5 text-[10px] font-semibold text-brand border border-brand/20">
                    LIVE OPS
                  </span>
                </div>
                <span className="text-[11px] font-medium text-ink-muted hidden sm:block">
                  NASA FIRMS · AI Wildfire Intelligence
                </span>
              </div>
            </a>

            <div className="hidden items-center gap-1.5 border-l border-edge pl-3 text-xs text-ink-faint md:flex">
              <Satellite size={13} className="text-brand" aria-hidden="true" />
              <span className="text-[11px] font-medium text-ink-muted">MODIS / VIIRS Active</span>
            </div>

            <LiveClock />
          </div>

          <div className="flex items-center gap-3">
            <NavLinks />
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto">{children}</main>
      </body>
    </html>
  );
}

