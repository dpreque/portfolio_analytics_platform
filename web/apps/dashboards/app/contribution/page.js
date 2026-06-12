// web/apps/dashboards/app/contribution/page.js
// ---------------------------------------------------------------------------
// Contribution dashboard: per-holding contribution to portfolio return over a
// period (weight at start x return over the period). Bar chart of top
// contributors/detractors + a sortable table. Single-period approximation.
// ---------------------------------------------------------------------------
'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { apiGet, pct } from '../../lib/api';
import SortableTable from '../../components/SortableTable';
import DateRangePicker from '../../components/DateRangePicker';

const PlotlyChart = dynamic(() => import('../../components/PlotlyChart'), { ssr: false });

const POS = '#047857';
const NEG = '#b91c1c';

export default function ContributionPage() {
  const [portfolios, setPortfolios] = useState([]);
  const [portfolioId, setPortfolioId] = useState('');
  const [dates, setDates] = useState([]);
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiGet('/api/portfolios')
      .then((rows) => {
        setPortfolios(rows);
        if (rows.length) setPortfolioId(String(rows[0].portfolio_id));
      })
      .catch((e) => setError(e.message));
  }, []);

  // load dates; default from = oldest snapshot, to = newest
  useEffect(() => {
    if (!portfolioId) return;
    apiGet(`/api/portfolios/${portfolioId}/dates`)
      .then((ds) => {
        setDates(ds);                 // ds is newest-first
        setTo(ds[0] || '');
        setFrom(ds[ds.length - 1] || '');
      })
      .catch((e) => setError(e.message));
  }, [portfolioId]);

  useEffect(() => {
    if (!portfolioId || !from || !to) return;
    setLoading(true);
    setError(null);
    apiGet(`/api/portfolios/${portfolioId}/contribution?from=${from}&to=${to}`)
      .then((d) => setData(d))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [portfolioId, from, to]);

  const holdings = data?.holdings || [];
  // bar chart: sort ascending so largest contributor sits at the top of a horizontal bar
  const barRows = [...holdings].sort((a, b) => a.contribution - b.contribution);
  const barTrace = {
    type: 'bar',
    orientation: 'h',
    y: barRows.map((h) => h.display_name),
    x: barRows.map((h) => h.contribution * 100),
    marker: { color: barRows.map((h) => (h.contribution >= 0 ? POS : NEG)) },
    hovertemplate: '%{y}: %{x:.3f}%<extra></extra>',
  };

  const columns = [
    { key: 'display_name', label: 'Security', align: 'left' },
    { key: 'asset_class', label: 'Class', align: 'left', render: (v) => <span className="tag">{v}</span> },
    { key: 'weight', label: 'Weight (start)', className: 'num', render: (v) => pct(v) },
    { key: 'return', label: 'Return', className: 'num', render: (v) => <span className={v >= 0 ? 'pos' : 'neg'}>{pct(v)}</span> },
    { key: 'contribution', label: 'Contribution', className: 'num', render: (v) => <span className={v >= 0 ? 'pos' : 'neg'}>{pct(v, 3)}</span> },
  ];

  const ret = data?.portfolio_return ?? 0;

  return (
    <div>
      <h1 className="page-title">Contribution</h1>
      <p className="page-sub">Per-holding contribution to portfolio return over a period (weight×return).</p>

      <div className="panel">
        <div className="controls">
          <div className="field">
            <label>Portfolio</label>
            <select value={portfolioId} onChange={(e) => setPortfolioId(e.target.value)} style={{ minWidth: 260 }}>
              {portfolios.map((p) => (
                <option key={p.portfolio_id} value={p.portfolio_id}>
                  {p.display_name} ({p.portfolio_type})
                </option>
              ))}
            </select>
          </div>
          <DateRangePicker
            from={from}
            to={to}
            onFromChange={setFrom}
            onToChange={setTo}
            min={dates[dates.length - 1]}
            max={dates[0]}
          />
        </div>
        <p className="muted" style={{ margin: '12px 0 0', fontSize: 12 }}>
          Single-period buy-and-hold approximation: beginning weights from the snapshot on/before “From”,
          returns from prices over the period. Intra-period rebalancing is ignored.
        </p>
      </div>

      {error && <div className="panel error">Error: {error}</div>}

      {data?.portfolio && (
        <div className="panel">
          <div className="metrics">
            <div className="metric">
              <span className="label">Portfolio</span>
              <span className="value">{data.portfolio.display_name}</span>
            </div>
            <div className="metric">
              <span className="label">Portfolio return</span>
              <span className={`value ${ret >= 0 ? 'pos' : 'neg'}`}>{pct(ret, 3)}</span>
            </div>
            <div className="metric">
              <span className="label">Period</span>
              <span className="value" style={{ fontSize: 15 }}>{data.period?.from} → {data.period?.to}</span>
            </div>
            <div className="metric">
              <span className="label">Weights as of</span>
              <span className="value" style={{ fontSize: 15 }}>{data.snapshot_date}</span>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, alignItems: 'start' }}>
        <div className="panel">
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Contribution by holding (%)</div>
          {loading ? <div className="loading">Loading…</div>
            : holdings.length ? <PlotlyChart data={[barTrace]} layout={{ margin: { l: 160, r: 20, t: 10, b: 40 }, xaxis: { title: '%', zeroline: true, zerolinecolor: '#9ca3af' } }} style={{ height: `${Math.max(360, holdings.length * 28)}px` }} />
            : <div className="muted">—</div>}
        </div>
        <div className="panel">
          {loading ? <div className="loading">Loading…</div>
            : holdings.length ? <SortableTable columns={columns} rows={holdings.map((h) => ({ ...h, __key: h.entity_id }))} initialSort="contribution" />
            : <div className="muted">No data.</div>}
        </div>
      </div>
    </div>
  );
}
