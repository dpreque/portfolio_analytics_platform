// web/apps/dashboards/app/positioning/page.js
// ---------------------------------------------------------------------------
// Positioning dashboard: pick a portfolio + date range, show enriched holdings
// (sortable) and an asset-class / currency weight breakdown chart.
//
// Positioning is point-in-time, so the shared date range drives it via its END
// date: holdings are shown "as of" the latest snapshot on/before the range end
// (the backend snaps to it). The range From bounds the picker for consistency
// with the other dashboards.
// ---------------------------------------------------------------------------
'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { apiGet, pct, num } from '../../lib/api';
import SortableTable from '../../components/SortableTable';
import DateRangePicker from '../../components/DateRangePicker';

const PlotlyChart = dynamic(() => import('../../components/PlotlyChart'), { ssr: false });

const ASSET_COLOR = {
  equity: '#1d4ed8',
  bond: '#047857',
  fund: '#b45309',
  cash: '#6b7280',
};

export default function PositioningPage() {
  const [portfolios, setPortfolios] = useState([]);
  const [portfolioId, setPortfolioId] = useState('');
  const [dates, setDates] = useState([]);          // available snapshots (newest first), for bounds/defaults
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');                // range END drives the "as of" snapshot
  const [data, setData] = useState(null);
  const [breakdown, setBreakdown] = useState('asset_class'); // asset_class | currency
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  // load portfolio picker once
  useEffect(() => {
    apiGet('/api/portfolios')
      .then((rows) => {
        setPortfolios(rows);
        if (rows.length) setPortfolioId(String(rows[0].portfolio_id));
      })
      .catch((e) => setError(e.message));
  }, []);

  // load available dates when portfolio changes; default range = oldest..newest snapshot
  useEffect(() => {
    if (!portfolioId) return;
    apiGet(`/api/portfolios/${portfolioId}/dates`)
      .then((ds) => {
        setDates(ds);
        setTo(ds[0] || '');
        setFrom(ds[ds.length - 1] || '');
      })
      .catch((e) => setError(e.message));
  }, [portfolioId]);

  // load holdings as of the range end (backend snaps to latest snapshot <= `to`)
  useEffect(() => {
    if (!portfolioId || !to) return;
    setLoading(true);
    setError(null);
    apiGet(`/api/portfolios/${portfolioId}/holdings?date=${to}`)
      .then((d) => setData(d))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [portfolioId, to]);

  const holdings = data?.holdings || [];
  const buckets = breakdown === 'asset_class'
    ? data?.summary?.by_asset_class || []
    : data?.summary?.by_currency || [];

  const pieTrace = {
    type: 'pie',
    labels: buckets.map((b) => b.key),
    values: buckets.map((b) => b.weight),
    marker: breakdown === 'asset_class'
      ? { colors: buckets.map((b) => ASSET_COLOR[b.key] || '#9ca3af') }
      : undefined,
    textinfo: 'label+percent',
    hole: 0.45,
    sort: false,
  };

  const columns = [
    { key: 'display_name', label: 'Security', align: 'left' },
    { key: 'asset_class', label: 'Class', align: 'left', render: (v) => <span className="tag">{v}</span> },
    { key: 'sector', label: 'Sector', align: 'left', render: (v) => v || '—' },
    { key: 'source', label: 'Source', align: 'left' },
    { key: 'quantity', label: 'Quantity', className: 'num', render: (v) => num(v, 0) },
    { key: 'market_value', label: 'Market value', className: 'num', render: (v) => num(v, 0) },
    { key: 'weight', label: 'Weight', className: 'num', render: (v) => pct(v) },
  ];

  return (
    <div>
      <h1 className="page-title">Positioning</h1>
      <p className="page-sub">Portfolio holdings as of the range end (latest snapshot on/before), with weight breakdown.</p>

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
          <div className="field">
            <label>Breakdown</label>
            <select value={breakdown} onChange={(e) => setBreakdown(e.target.value)}>
              <option value="asset_class">By asset class</option>
              <option value="currency">By currency</option>
            </select>
          </div>
        </div>
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
              <span className="label">Total market value</span>
              <span className="value">{num(data.total_market_value, 0)} {data.portfolio.base_currency}</span>
            </div>
            <div className="metric">
              <span className="label">Holdings</span>
              <span className="value">{holdings.length}</span>
            </div>
            <div className="metric">
              <span className="label">Snapshot</span>
              <span className="value" style={{ fontSize: 15 }}>{data.reference_date}</span>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 20, alignItems: 'start' }}>
        <div className="panel">
          {loading ? <div className="loading">Loading…</div>
            : holdings.length ? <SortableTable columns={columns} rows={holdings.map((h) => ({ ...h, __key: h.entity_id }))} initialSort="weight" />
            : <div className="muted">No holdings.</div>}
        </div>
        <div className="panel">
          <div style={{ fontWeight: 600, marginBottom: 8 }}>
            Weight by {breakdown === 'asset_class' ? 'asset class' : 'currency'}
          </div>
          {buckets.length ? <PlotlyChart data={[pieTrace]} layout={{ showlegend: false }} style={{ height: '360px' }} />
            : <div className="muted">—</div>}
        </div>
      </div>
    </div>
  );
}
