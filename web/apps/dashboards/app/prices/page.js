// web/apps/dashboards/app/prices/page.js
// ---------------------------------------------------------------------------
// Price Viewer (by source): pick a security + date range, overlay one price line
// per source so cross-source dispersion is visible at a glance.
//
// Hover UX is modelled on institutional charting (Bloomberg-style): a dark,
// multi-line tooltip (Source / Date / Return / Price) snapped to the exact data
// point, with a dotted crosshair across both axes. All of it is native Plotly
// (hovertemplate + customdata + axis spikes) -- no custom DOM/JS.
// ---------------------------------------------------------------------------
'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { apiGet } from '../../lib/api';
import DateRangePicker from '../../components/DateRangePicker';

const PlotlyChart = dynamic(() => import('../../components/PlotlyChart'), { ssr: false });

const SOURCE_COLOR = {
  bloomberg: '#1d4ed8',
  sbs: '#047857',
  scraper: '#b45309',
  fms: '#7c3aed',
};

// Pad a tooltip label to a fixed column with non-breaking spaces so values line
// up under the monospace hover font (normal spaces collapse in SVG text).
const NBSP = String.fromCharCode(160);
const labelCell = (text) => {
  const base = `${text}:`;
  return base + NBSP.repeat(Math.max(1, 8 - base.length));
};

// Multi-line hover panel: Source / Date / Return / Price. The source value is
// tinted to match its line; labels are muted, values bright. customdata carries
// [date, return%, SOURCE, price] for the exact point being inspected.
const hoverTemplate = (color) =>
  `<span style="color:#94a3b8">${labelCell('Source')}</span>` +
  `<b><span style="color:${color}">%{customdata[2]}</span></b><br>` +
  `<span style="color:#94a3b8">${labelCell('Date')}</span>%{customdata[0]}<br>` +
  `<span style="color:#94a3b8">${labelCell('Return')}</span>%{customdata[1]:+.2f}%<br>` +
  `<span style="color:#94a3b8">${labelCell('Price')}</span>%{customdata[3]:,.4f}` +
  `<extra></extra>`;

// Shared crosshair/spike config for both axes -- dotted line that snaps to the
// nearest data point, so the highlighted observation is unambiguous.
const SPIKE = {
  showspikes: true,
  spikemode: 'across',
  spikesnap: 'hovered data',
  spikethickness: 1,
  spikedash: 'dot',
  spikecolor: '#94a3b8',
  gridcolor: '#eef2f7',
};

export default function PricesPage() {
  const [securities, setSecurities] = useState([]);
  const [entityId, setEntityId] = useState('');
  const [from, setFrom] = useState('2026-03-01');
  const [to, setTo] = useState('2026-06-10');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [hoverDate, setHoverDate] = useState(null); // x value of the inspected point

  // load the security picker once
  useEffect(() => {
    apiGet('/api/securities?limit=500')
      .then((rows) => {
        setSecurities(rows);
        if (rows.length) setEntityId(String(rows[0].entity_id));
      })
      .catch((e) => setError(e.message));
  }, []);

  // (re)load prices whenever the selection changes
  useEffect(() => {
    if (!entityId) return;
    setLoading(true);
    setError(null);
    apiGet(`/api/prices?entity_id=${entityId}&from=${from}&to=${to}`)
      .then((d) => setData(d))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [entityId, from, to]);

  const traces = (data?.series || []).map((s) => {
    const color = SOURCE_COLOR[s.source] || '#374151';
    // Return is the cumulative % change from the first valid point in the window.
    const firstValid = s.points.find((p) => p.price != null);
    const base = firstValid ? firstValid.price : null;
    return {
      x: s.points.map((p) => p.date),
      y: s.points.map((p) => p.price),
      customdata: s.points.map((p) => [
        p.date,                                       // exact ISO date of the point
        base ? (p.price / base - 1) * 100 : 0,        // cumulative return over window (%)
        s.source.toUpperCase(),                       // source label
        p.price,                                      // price
      ]),
      type: 'scatter',
      mode: 'lines',
      name: s.source,
      line: { color, width: 2 },
      hovertemplate: hoverTemplate(color),
      hoverlabel: { bordercolor: color }, // source-matched accent edge on the panel
    };
  });

  const entity = data?.entity;

  // Bloomberg-style x-axis date tag: a translucent box pinned to the x-axis that
  // follows the inspected point. Implemented as a paper-anchored annotation
  // repositioned on hover (Plotly has no native axis-spike label box).
  const handleHover = (e) => {
    const pt = e?.points?.[0];
    if (pt) setHoverDate(pt.customdata?.[0] ?? pt.x);
  };
  const handleUnhover = () => setHoverDate(null);

  const dateTag = hoverDate
    ? [{
        x: hoverDate,
        xref: 'x',
        y: 0,
        yref: 'paper',
        yanchor: 'top',
        yshift: -6,
        text: hoverDate,
        showarrow: false,
        bgcolor: 'rgba(15, 23, 42, 0.85)',
        bordercolor: '#334155',
        borderwidth: 1,
        borderpad: 4,
        font: {
          family: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
          size: 11,
          color: '#e2e8f0',
        },
      }]
    : [];

  return (
    <div>
      <h1 className="page-title">Price Viewer</h1>
      <p className="page-sub">Daily prices for one security, one line per source.</p>

      <div className="panel">
        <div className="controls">
          <div className="field">
            <label>Security</label>
            <select value={entityId} onChange={(e) => setEntityId(e.target.value)} style={{ minWidth: 280 }}>
              {securities.map((s) => (
                <option key={s.entity_id} value={s.entity_id}>
                  {s.display_name} {s.ticker ? `(${s.ticker})` : ''}
                </option>
              ))}
            </select>
          </div>
          <DateRangePicker from={from} to={to} onFromChange={setFrom} onToChange={setTo} />
        </div>
      </div>

      {error && <div className="panel error">Error: {error}</div>}

      {entity && (
        <div className="panel">
          <div className="metrics">
            <div className="metric">
              <span className="label">Security</span>
              <span className="value">{entity.display_name}</span>
            </div>
            <div className="metric">
              <span className="label">Asset class</span>
              <span className="value"><span className="tag">{entity.asset_class}</span></span>
            </div>
            <div className="metric">
              <span className="label">ISIN</span>
              <span className="value" style={{ fontSize: 15 }}>{entity.isin || '—'}</span>
            </div>
            <div className="metric">
              <span className="label">Currency</span>
              <span className="value" style={{ fontSize: 15 }}>{entity.base_currency}</span>
            </div>
          </div>
        </div>
      )}

      <div className="panel">
        {loading ? (
          <div className="loading">Loading…</div>
        ) : traces.length ? (
          <PlotlyChart
            data={traces}
            onHover={handleHover}
            onUnhover={handleUnhover}
            layout={{
              hovermode: 'closest',
              hoverdistance: 30,
              margin: { l: 60, r: 20, t: 30, b: 64 },
              annotations: dateTag,
              xaxis: { title: '', hoverformat: '%Y-%m-%d', ...SPIKE },
              yaxis: { title: entity?.base_currency || 'Price', zeroline: false, ...SPIKE },
            }}
          />
        ) : (
          <div className="muted">No price data for this selection.</div>
        )}
      </div>
    </div>
  );
}
