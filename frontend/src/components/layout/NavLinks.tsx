'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Flame } from 'lucide-react';

const NAV_ITEMS = [
  { href: '/', label: 'Live Map', icon: LayoutDashboard },
  { href: '/events', label: 'Incidents Explorer', icon: Flame },
] as const;

export function NavLinks() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-1.5 bg-surface-overlay p-1 rounded-full border border-edge" aria-label="Main navigation">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={isActive ? 'page' : undefined}
            className={`relative flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold tracking-tight transition-all ${
              isActive
                ? 'bg-brand text-white shadow-sm'
                : 'text-ink-muted hover:text-ink hover:bg-white/60'
            }`}
          >
            <Icon size={13} className={isActive ? 'text-white' : 'text-ink-faint'} aria-hidden="true" />
            <span>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

