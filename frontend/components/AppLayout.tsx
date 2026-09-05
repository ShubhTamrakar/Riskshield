'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

const nav = [
  {
    section: 'Overview',
    items: [
      { label: 'Dashboard', href: '/', icon: HomeIcon },
    ],
  },
  {
    section: 'Operations',
    items: [
      { label: 'Transactions',    href: '/transactions',     icon: ListIcon },
      { label: 'Risk Alerts',     href: '/alerts',           icon: AlertIcon },
      { label: 'Customers',       href: '/customers',        icon: UsersIcon },
      { label: 'Investigation',   href: '/investigation',    icon: SearchIcon },
    ],
  },
  {
    section: 'Analysis',
    items: [
      { label: 'Simulation Lab',    href: '/simulation',     icon: FlaskIcon },
      { label: 'Model Performance', href: '/model',          icon: ChartIcon },
    ],
  },
  {
    section: 'System',
    items: [
      { label: 'Settings', href: '/settings', icon: GearIcon },
    ],
  },
];

export function AppLayout({ children, title }: { children: React.ReactNode; title: string }) {
  const pathname = usePathname();
  const [alertsCount, setAlertsCount] = useState<number | null>(null);

  useEffect(() => {
    const fetchSummary = () => {
      api.getDashboardSummary()
        .then(s => setAlertsCount(s.review))
        .catch(console.error);
    };
    
    fetchSummary();
    const intervalId = setInterval(fetchSummary, 2000);
    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-mark">
            <ShieldIcon />
          </div>
          <div>
            <div className="sidebar-logo-text">RiskShield</div>
            <div className="sidebar-logo-sub">Risk Operations</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          {nav.map(group => (
            <div key={group.section}>
              <div className="sidebar-section-label">{group.section}</div>
              {group.items.map(item => {
                const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
                
                let displayBadge = (item as any).badge;
                if (item.label === 'Risk Alerts' && alertsCount !== null && alertsCount > 0) {
                  displayBadge = alertsCount.toString();
                } else if (item.label === 'Risk Alerts' && alertsCount === 0) {
                  displayBadge = null;
                }

                return (
                  <Link key={item.href} href={item.href} className={`nav-item ${active ? 'active' : ''}`}>
                    <item.icon />
                    {item.label}
                    {displayBadge && <span className="nav-item-badge">{displayBadge}</span>}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div>RiskShield v1.0<br/><span style={{opacity: 0.7}}>Internal Operations</span></div>
        </div>
      </aside>

      <div className="main-content">
        <div className="topbar">
          <span className="topbar-title">{title}</span>
          <div className="topbar-right">
            <span style={{ fontSize: 12, color: 'var(--color-text-3)' }}>
              {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            </span>
            <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--color-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: 12, fontWeight: 600 }}>A</div>
          </div>
        </div>
        <div className="page-content">{children}</div>
      </div>
    </div>
  );
}

// ── Inline SVG icons ──────────────────────────────────────────────────────────
function ShieldIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>;
}
function HomeIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>;
}
function ListIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>;
}
function AlertIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>;
}
function UsersIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>;
}
function SearchIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>;
}
function FlaskIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><path d="M9 3h6v8l3 9H6L9 11V3z"/></svg>;
}
function ChartIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>;
}
function GearIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>;
}
