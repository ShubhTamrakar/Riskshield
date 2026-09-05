import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'RiskShield — Risk Operations',
  description: 'Internal fraud & risk operations dashboard for real-time transaction analysis.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
