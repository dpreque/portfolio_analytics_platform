// web/apps/dashboards/app/page.js
import Link from 'next/link';

const CARDS = [
  { href: '/prices/', title: 'Price Viewer', desc: 'Compare a security’s price history across sources (Bloomberg, SBS, scraper).' },
  { href: '/positioning/', title: 'Positioning', desc: 'Portfolio holdings on a date with weights and asset-class / currency breakdowns.' },
  { href: '/contribution/', title: 'Contribution', desc: 'Per-holding contribution to portfolio return over a period.' },
];

export default function Home() {
  return (
    <div>
      <h1 className="page-title">Portfolio Analytics</h1>
      <p className="page-sub">Investment analytics dashboards — reference data.</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
        {CARDS.map((c) => (
          <Link key={c.href} href={c.href} className="panel" style={{ display: 'block' }}>
            <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 6, color: 'var(--accent)' }}>{c.title}</div>
            <div className="muted">{c.desc}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
