// web/apps/dashboards/app/prices/page.js
// ---------------------------------------------------------------------------
// Price Viewer (by source): a security's price history, one line per source.
// Range comes from the global header (period). Keeps the Bloomberg-style hover
// tooltip + crosshair + x-axis date tag, adds a KPI bar and a source-comparison
// table below the chart.
//
// NOTE on sources: price sources are bloomberg / sbs / scraper (FMS is a
// *positions* source, not a price source). The source-comparison table pairs
// the Bloomberg and SBS series (price + cumulative return each); securities
// without an SBS series show blanks in the SBS columns.
// ---------------------------------------------------------------------------
'use client';

import { useEffect, useState, useMemo, useRef } from 'react';
import dynamic from 'next/dynamic';
import { apiGet, pct, num } from '../../lib/api';
import { downloadCsv } from '../../lib/csv';
import { useDashboard } from '../../components/DashboardProvider';
import KpiBar from '../../components/KpiBar';
import SecuritySearch from '../../components/SecuritySearch';
import { chartTheme } from '../../lib/theme';

const PlotlyChart = dynamic(() => import('../../components/PlotlyChart'), { ssr: false });

const SOURCE_COLOR = { bloomberg: '#5B8CFF', sbs: '#2DD4A0', scraper: '#F5A623', fms: '#A78BFA' };

// Highlight a row's Return Difference when |Bloomberg return − SBS return| exceeds this.
const RETURN_DIFF_THRESHOLD = 0.005; // 0.50%

const fmtPrice = (v) => (v == null ? '—' : v.toFixed(2));
const fmtReturn = (v) => (v == null ? '—' : `${v >= 0 ? '+' : ''}${(v * 100).toFixed(2)}%`);
const retClass = (v) => (v == null ? '' : v >= 0 ? 'pos' : 'neg');

// Source-comparison table columns (Date is always shown and is NOT toggleable).
// CMP_COLUMNS drives the chooser dropdown; CMP_GROUPS drives the grouped header.
const CMP_STORAGE_KEY = 'priceTableColumns';
const CMP_COLUMNS = [
  { key: 'bPrice', label: 'Bloomberg Price' },
  { key: 'bRet', label: 'Bloomberg Return' },
  { key: 'sPrice', label: 'SBS Price' },
  { key: 'sRet', label: 'SBS Return' },
  { key: 'diff', label: 'Return Difference' },
];
const CMP_GROUPS = [
  { label: 'Bloomberg', cols: [
    { key: 'bPrice', label: 'Price', width: 120, type: 'price' },
    { key: 'bRet', label: 'Return', width: 110, type: 'ret' },
  ] },
  { label: 'SBS', cols: [
    { key: 'sPrice', label: 'Price', width: 120, type: 'price' },
    { key: 'sRet', label: 'Return', width: 110, type: 'ret' },
  ] },
  { label: 'Comparison', cols: [
    { key: 'diff', label: 'Return Diff', width: 130, type: 'diff' },
  ] },
];
const CMP_VAL = { bPrice: (r) => r.bPrice, bRet: (r) => r.bRet, sPrice: (r) => r.sPrice, sRet: (r) => r.sRet, diff: (r) => r.diff };

const NBSP = String.fromCharCode(160);
const labelCell = (t) => { const b = `${t}:`; return b + NBSP.repeat(Math.max(1, 8 - b.length)); };
const hoverTemplate = (color) =>
  `<span style="color:#8892A4">${labelCell('Source')}</span><b><span style="color:${color}">%{customdata[2]}</span></b><br>` +
  `<span style="color:#8892A4">${labelCell('Date')}</span>%{customdata[0]}<br>` +
  `<span style="color:#8892A4">${labelCell('Return')}</span>%{customdata[1]:+.2f}%<br>` +
  `<span style="color:#8892A4">${labelCell('Price')}</span>%{customdata[3]:,.4f}<extra></extra>`;
// Structural spike config only; colors are injected by PlotlyChart from the theme.
const SPIKE = {
  showspikes: true, spikemode: 'across', spikesnap: 'hovered data',
  spikethickness: 1, spikedash: 'dot',
};

export default function PricesPage() {
  const { range } = useDashboard();
  const [selected, setSelected] = useState(null);
  const [entityId, setEntityId] = useState('');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [hoverDate, setHoverDate] = useState(null);
  const [hidden, setHidden] = useState(() => new Set()); // sources toggled off via the legend

  useEffect(() => {
    if (!entityId) return;
    setLoading(true); setError(null);
    apiGet(`/api/prices?entity_id=${entityId}&from=${range.from}&to=${range.to}`)
      .then(setData).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [entityId, range.from, range.to]);

  // reset legend hide-state when the security changes (fresh data / fresh legend)
  useEffect(() => { setHidden(new Set()); }, [entityId]);

  const entity = data?.entity;
  const series = data?.series || [];

  const traces = series.map((s) => {
    const color = SOURCE_COLOR[s.source] || '#8892A4';
    const firstValid = s.points.find((p) => p.price != null);
    const base = firstValid ? firstValid.price : null;
    const isHidden = hidden.has(s.source);
    const trace = {
      x: s.points.map((p) => p.date),
      y: s.points.map((p) => p.price),
      customdata: s.points.map((p) => [p.date, base ? (p.price / base - 1) * 100 : 0, s.source.toUpperCase(), p.price]),
      type: 'scatter', mode: 'lines', name: s.source,
      line: { color, width: 2 },
      hovertemplate: hoverTemplate(color),
      hoverlabel: { bordercolor: color },
      visible: isHidden ? 'legendonly' : true,
    };
    // A 'legendonly' trace is hidden visually but still participates in hover —
    // its tooltip would surface over the visible lines. Exclude it from hover too.
    if (isHidden) trace.hoverinfo = 'skip';
    return trace;
  });

  // KPI inputs: prefer bloomberg as the primary series
  const primary = series.find((s) => s.source === 'bloomberg') || series[0];
  const lastPt = primary?.points?.[primary.points.length - 1];
  const firstPt = primary?.points?.find((p) => p.price != null);
  const periodRet = (firstPt && lastPt && firstPt.price) ? lastPt.price / firstPt.price - 1 : null;
  const latest = series.map((s) => s.points[s.points.length - 1]?.price).filter((v) => v != null);
  const spread = latest.length > 1 ? (Math.max(...latest) - Math.min(...latest)) / (latest.reduce((a, b) => a + b, 0) / latest.length) : 0;

  const kpis = [
    { label: 'Security', value: entity?.ticker || entity?.display_name || '—', meta: entity?.display_name || '' },
    { label: 'Latest Price', value: lastPt ? num(lastPt.price, 4) : '—', meta: lastPt ? `${primary.source} · ${lastPt.date}` : '' },
    { label: 'Period Return', value: periodRet != null ? pct(periodRet) : '—', tone: periodRet >= 0 ? 'pos' : 'neg', meta: 'window' },
    { label: 'Sources', value: series.length <= 1 ? 'Single' : (spread > 0.0025 ? 'Diverge' : 'Agree'), meta: `${series.length} src · ${(spread * 100).toFixed(2)}% spread` },
  ];

  // x-axis date tag (paper-anchored annotation, follows the hovered point)
  const handleHover = (e) => { const pt = e?.points?.[0]; if (pt) setHoverDate(pt.customdata?.[0] ?? pt.x); };
  const handleUnhover = () => setHoverDate(null);

  // Legend interaction: we OWN visibility in state (keyed by source) so the toggle —
  // and the matching hoverinfo:'skip' — survives this page's frequent hover re-renders.
  // Returning false also suppresses Plotly's default toggle (state is the source of truth).
  const toggleSource = (src) => setHidden((prev) => {
    const next = new Set(prev);
    next.has(src) ? next.delete(src) : next.add(src);
    return next;
  });
  const isolateSource = (src) => setHidden((prev) => {
    const others = series.map((s) => s.source).filter((s) => s !== src);
    const alreadyIsolated = !prev.has(src) && others.every((s) => prev.has(s));
    return alreadyIsolated ? new Set() : new Set(others); // double-click: isolate, or restore all
  });
  const handleLegendClick = (e) => { const src = series[e?.curveNumber]?.source; if (src) toggleSource(src); return false; };
  const handleLegendDoubleClick = (e) => { const src = series[e?.curveNumber]?.source; if (src) isolateSource(src); return false; };
  const ct = chartTheme();
  const dateTag = hoverDate ? [{
    x: hoverDate, xref: 'x', y: 0, yref: 'paper', yanchor: 'top', yshift: -6,
    text: hoverDate, showarrow: false,
    bgcolor: ct.panel, bordercolor: ct.border, borderwidth: 1, borderpad: 4,
    font: { family: "var(--font-plex), 'IBM Plex Mono', monospace", size: 11, color: ct.text },
  }] : [];

  // source-comparison table: pair the Bloomberg and SBS series (price + cumulative
  // return each), with a Return-Difference column. SBS may be absent -> blank cells.
  const bbgSeries = series.find((s) => s.source === 'bloomberg');
  const sbsSeries = series.find((s) => s.source === 'sbs');
  const cmpRows = useMemo(() => {
    if (!bbgSeries) return [];
    const baseB = bbgSeries.points.find((p) => p.price != null)?.price ?? null;
    const sbsMap = sbsSeries ? new Map(sbsSeries.points.map((p) => [p.date, p.price])) : null;
    const baseS = sbsSeries ? (sbsSeries.points.find((p) => p.price != null)?.price ?? null) : null;
    return bbgSeries.points.map((p) => {
      const bPrice = p.price;
      const bRet = baseB ? bPrice / baseB - 1 : null;
      const sPrice = sbsMap ? (sbsMap.get(p.date) ?? null) : null;
      const sRet = (sPrice != null && baseS) ? sPrice / baseS - 1 : null;
      const diff = (bRet != null && sRet != null) ? bRet - sRet : null;
      return { date: p.date, bPrice, bRet, sPrice, sRet, diff };
    }).reverse();
  }, [data]); // eslint-disable-line react-hooks/exhaustive-deps

  // comparison-table column visibility (persisted) + the chooser dropdown
  const [cmpVisible, setCmpVisible] = useState(() => new Set(CMP_COLUMNS.map((c) => c.key)));
  const [cmpChooser, setCmpChooser] = useState(false);
  const cmpToolsRef = useRef(null);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(CMP_STORAGE_KEY) || 'null');
      if (Array.isArray(saved)) setCmpVisible(new Set(saved));
    } catch { /* ignore */ }
  }, []);

  // close the dropdown when clicking outside it
  useEffect(() => {
    if (!cmpChooser) return undefined;
    const onDoc = (e) => { if (cmpToolsRef.current && !cmpToolsRef.current.contains(e.target)) setCmpChooser(false); };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [cmpChooser]);

  const toggleCmpCol = (key) => setCmpVisible((prev) => {
    const next = new Set(prev);
    next.has(key) ? next.delete(key) : next.add(key);
    try { localStorage.setItem(CMP_STORAGE_KEY, JSON.stringify([...next])); } catch { /* ignore */ }
    return next;
  });

  // visible groups (drop fully-hidden groups so colspans + dividers stay correct)
  const cmpGroups = CMP_GROUPS
    .map((g) => ({ label: g.label, cols: g.cols.filter((c) => cmpVisible.has(c.key)) }))
    .filter((g) => g.cols.length > 0);

  const exportCmpCsv = () => {
    const cols = cmpGroups.flatMap((g) => g.cols);
    const headers = ['Date', ...cols.map((c) => CMP_COLUMNS.find((x) => x.key === c.key)?.label || c.key)];
    const rows = cmpRows.map((r) => [r.date, ...cols.map((c) => {
      const v = CMP_VAL[c.key](r);
      if (v == null) return '';
      return c.type === 'price' ? v.toFixed(2) : (v * 100).toFixed(2);
    })]);
    downloadCsv(`${entity?.ticker || 'security'}_prices_${range.from}_${range.to}`, headers, rows);
  };

  return (
    <div>
      <h1 className="page-title">Price Viewer</h1>
      <p className="page-sub">Daily prices for one security, one line per source.</p>

      <KpiBar tiles={kpis} />

      <div className="panel">
        <div className="controls">
          <SecuritySearch
            value={selected}
            onSelect={(s) => { setSelected(s); setEntityId(s ? String(s.entity_id) : ''); }}
          />
        </div>
      </div>

      {error && <div className="panel error">Error: {error}</div>}

      <div className="panel">
        {loading ? (
          <div className="loading">Loading…</div>
        ) : traces.length ? (
          <PlotlyChart
            data={traces}
            onHover={handleHover}
            onUnhover={handleUnhover}
            onLegendClick={handleLegendClick}
            onLegendDoubleClick={handleLegendDoubleClick}
            layout={{
              hovermode: 'closest', hoverdistance: 10,
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

      <div className="panel">
        <div className="panel-title">Source comparison</div>
        {cmpRows.length ? (
          <>
            <div className="table-tools">
              <div />
              <div className="right" ref={cmpToolsRef}>
                <button className="btn" onClick={exportCmpCsv} title="Export visible columns as CSV">↓ CSV</button>
                <button className="btn" onClick={() => setCmpChooser((v) => !v)} title="Show / hide columns">⊞ Columns</button>
                {cmpChooser && (
                  <div className="col-chooser">
                    {CMP_COLUMNS.map((c) => (
                      <label className="row" key={c.key}>
                        <input type="checkbox" checked={cmpVisible.has(c.key)} onChange={() => toggleCmpCol(c.key)} />
                        {c.label}
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="cmp-wrap">
              <table className="cmp-table">
                <colgroup>
                  <col style={{ width: 110 }} />
                  {cmpGroups.flatMap((g) => g.cols.map((c) => <col key={c.key} style={{ width: c.width }} />))}
                </colgroup>
                <thead>
                  <tr className="cmp-grp">
                    <th rowSpan={2} className="cmp-date">Date</th>
                    {cmpGroups.map((g, gi) => (
                      <th key={g.label} colSpan={g.cols.length} className={gi > 0 ? 'cmp-div' : ''}>{g.label}</th>
                    ))}
                  </tr>
                  <tr className="cmp-col">
                    {cmpGroups.flatMap((g, gi) => g.cols.map((c, ci) => (
                      <th key={c.key} className={gi > 0 && ci === 0 ? 'cmp-div' : ''}>{c.label}</th>
                    )))}
                  </tr>
                </thead>
                <tbody>
                  {cmpRows.map((r) => (
                    <tr key={r.date}>
                      <td className="cmp-date num">{r.date}</td>
                      {cmpGroups.flatMap((g, gi) => g.cols.map((c, ci) => {
                        const divider = gi > 0 && ci === 0 ? 'cmp-div' : '';
                        const v = CMP_VAL[c.key](r);
                        if (c.type === 'price') {
                          return <td key={c.key} className={`num ${divider}`}>{fmtPrice(v)}</td>;
                        }
                        if (c.type === 'ret') {
                          return <td key={c.key} className={`num ${retClass(v)} ${divider}`}>{fmtReturn(v)}</td>;
                        }
                        const hot = v != null && Math.abs(v) > RETURN_DIFF_THRESHOLD;
                        return <td key={c.key} className={`num ${retClass(v)} ${divider} ${hot ? 'cmp-hot' : ''}`}>{fmtReturn(v)}</td>;
                      }))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="muted">No Bloomberg price series to compare.</div>
        )}
      </div>
    </div>
  );
}
