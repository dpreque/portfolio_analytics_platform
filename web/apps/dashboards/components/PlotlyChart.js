// web/apps/dashboards/components/PlotlyChart.js
// ---------------------------------------------------------------------------
// Client-only Plotly wrapper. plotly.js touches `window` at module load, so this
// file is always imported via next/dynamic({ ssr: false }) -- never server-side.
// Uses the prebuilt dist-min bundle + react-plotly.js factory (no source build).
// ---------------------------------------------------------------------------
'use client';

import createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';

const Plot = createPlotlyComponent(Plotly);

const BASE_LAYOUT = {
  margin: { l: 60, r: 20, t: 30, b: 50 },
  font: { family: 'system-ui, sans-serif', size: 12, color: '#1f2937' },
  paper_bgcolor: 'white',
  plot_bgcolor: 'white',
  legend: { orientation: 'h', y: -0.2 },
  hovermode: 'closest',
  // Institutional-style hover label: dark panel, monospace numerals, left-aligned.
  // Per-trace bordercolor (set on each trace) gives a source-matched accent edge.
  hoverlabel: {
    bgcolor: '#0f172a',
    bordercolor: '#1e293b',
    font: {
      family: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
      size: 12,
      color: '#e2e8f0',
    },
    align: 'left',
    namelength: -1,
  },
};

export default function PlotlyChart({ data, layout = {}, style, onHover, onUnhover }) {
  return (
    <Plot
      data={data}
      layout={{ ...BASE_LAYOUT, ...layout }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%', height: '420px', ...style }}
      useResizeHandler
      onHover={onHover}
      onUnhover={onUnhover}
    />
  );
}
