'use client';

import { useState, useEffect } from 'react';
import { Radio } from 'lucide-react';

export function LiveClock() {
  const [time, setTime] = useState<{ utc: string; wib: string } | null>(null);

  useEffect(() => {
    function update() {
      const now = new Date();
      const utc = now.toUTCString().slice(17, 25) + ' UTC';
      const wib = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Asia/Jakarta',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }).format(now) + ' WIB';
      setTime({ utc, wib });
    }

    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="hidden items-center gap-3 border-l border-edge pl-3 lg:flex">
      <div className="flex items-center gap-1.5 rounded-full bg-surface-overlay px-3 py-1 text-[11px] font-mono border border-edge text-ink-muted">
        <Radio size={12} className="text-emerald-500 animate-pulse" aria-hidden="true" />
        <span className="text-ink font-semibold tabular-nums">{time?.wib ?? '--:--:-- WIB'}</span>
        <span className="text-ink-faint">·</span>
        <span className="tabular-nums">{time?.utc ?? '--:--:-- UTC'}</span>
      </div>
    </div>
  );
}

