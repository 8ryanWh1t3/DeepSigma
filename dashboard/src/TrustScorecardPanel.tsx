import { useEffect, useCallback } from 'react';
import { useOverwatchStore } from './store';
import type { TrustScorecard } from './mockData';

const REFRESH_INTERVAL_MS = 30_000; // 30 seconds

function SLOBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${
      ok ? 'bg-green-900/50 text-green-400 border border-green-800' : 'bg-red-900/50 text-red-400 border border-red-800'
    }`}>
      {ok ? '✓' : '✗'} {label}
    </span>
  );
}

function MetricRow({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-slate-800">
      <span className="text-slate-400 text-sm">{label}</span>
      <span className="text-slate-200 font-mono text-sm">
        {value}{unit ? <span className="text-slate-500 ml-1">{unit}</span> : null}
      </span>
    </div>
  );
}

export function TrustScorecardPanel() {
  const scorecard = useOverwatchStore((s) => s.trustScorecard);
  const loading = useOverwatchStore((s) => s.trustScorecardLoading);
  const fetchScorecard = useOverwatchStore((s) => s.fetchTrustScorecard);
  const dataSource = useOverwatchStore((s) => s.connection.dataSource);

  const refresh = useCallback(() => { fetchScorecard(); }, [fetchScorecard]);

  // Fetch on mount + periodic refresh
  useEffect(() => {
    fetchScorecard();
    const timer = setInterval(fetchScorecard, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [fetchScorecard]);

  if (loading && !scorecard) {
    return (
      <div className="p-6 text-center text-slate-400">Loading Trust Scorecard...</div>
    );
  }

  if (!scorecard) {
    return (
      <div className="p-6">
        <div className="bg-slate-900 rounded-lg border border-slate-700 p-6 text-center">
          <h3 className="text-lg font-semibold text-slate-300 mb-2">Trust Scorecard</h3>
          <p className="text-slate-500">No scorecard data available.</p>
          <p className="text-slate-600 text-sm mt-2">
            Generate with: <code className="bg-slate-800 px-2 py-0.5 rounded">python -m tools.trust_scorecard --input golden_path_ci_out</code>
          </p>
        </div>
      </div>
    );
  }

  return <ScorecardContent scorecard={scorecard} dataSource={dataSource} onRefresh={refresh} loading={loading} />;
}

function ScorecardContent({ scorecard, dataSource, onRefresh, loading }: {
  scorecard: TrustScorecard;
  dataSource: string;
  onRefresh: () => void;
  loading: boolean;
}) {
  const m = scorecard.metrics;
  const slo = scorecard.slo_checks;
  const allSLOsPass = Object.values(slo).every(Boolean);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Trust Scorecard</h2>
          <p className="text-slate-500 text-sm">
            v{scorecard.scorecard_version} — {new Date(scorecard.timestamp).toLocaleString()}
            {dataSource === 'mock' && <span className="ml-2 text-slate-600">(mock data)</span>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onRefresh}
            disabled={loading}
            className="text-xs text-slate-400 hover:text-blue-400 transition-colors disabled:opacity-50"
          >
            {loading ? '↻ Refreshing...' : '↻ Refresh'}
          </button>
          <div className={`px-3 py-1.5 rounded-lg text-sm font-semibold ${
            allSLOsPass ? 'bg-green-900/50 text-green-400 border border-green-700' : 'bg-red-900/50 text-red-400 border border-red-700'
          }`}>
            {allSLOsPass ? 'ALL SLOs PASS' : 'SLO DEGRADED'}
          </div>
        </div>
      </div>

      {/* Score cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 text-center">
          <div className="text-slate-400 text-xs mb-1">Steps</div>
          <div className="text-2xl font-bold text-blue-400">{m.steps_completed}/{m.steps_total}</div>
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 text-center">
          <div className="text-slate-400 text-xs mb-1">Baseline</div>
          <div className="text-2xl font-bold text-amber-400">{m.baseline_score.toFixed(1)} ({m.baseline_grade})</div>
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 text-center">
          <div className="text-slate-400 text-xs mb-1">Patched</div>
          <div className="text-2xl font-bold text-green-400">{m.patched_score.toFixed(1)} ({m.patched_grade})</div>
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 text-center">
          <div className="text-slate-400 text-xs mb-1">IRIS</div>
          <div className="text-2xl font-bold text-purple-400">{m.iris_queries_resolved}/3</div>
        </div>
      </div>

      {/* SLO checks */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">SLO Checks</h3>
        <div className="flex flex-wrap gap-2">
          <SLOBadge ok={slo.iris_why_latency_ok} label="IRIS Latency ≤ 60s" />
          <SLOBadge ok={slo.all_steps_passed} label="All 7 Steps" />
          <SLOBadge ok={slo.schema_clean} label="Schema Clean" />
          <SLOBadge ok={slo.score_positive} label="Score > 0" />
        </div>
      </div>

      {/* Metrics detail */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Timing</h3>
          <MetricRow label="Total Elapsed" value={m.total_elapsed_ms.toFixed(1)} unit="ms" />
          <MetricRow label="IRIS WHY Latency" value={m.iris_why_latency_ms.toFixed(1)} unit="ms" />
          <MetricRow label="Drift Detection" value={m.drift_detect_latency_ms.toFixed(1)} unit="ms" />
          <MetricRow label="Patch" value={m.patch_latency_ms.toFixed(1)} unit="ms" />
          <MetricRow label="Ingest Rate" value={m.connector_ingest_records_per_sec.toFixed(1)} unit="rec/s" />
        </div>
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Quality</h3>
          <MetricRow label="Schema Failures" value={m.schema_validation_failures} />
          <MetricRow label="Drift Events" value={m.drift_events_detected} />
          <MetricRow label="Patch Applied" value={m.patch_applied ? 'Yes' : 'No'} />
          <MetricRow label="Baseline Grade" value={`${m.baseline_score.toFixed(1)} (${m.baseline_grade})`} />
          <MetricRow label="Patched Grade" value={`${m.patched_score.toFixed(1)} (${m.patched_grade})`} />
          {m.coverage_pct !== null && <MetricRow label="Coverage" value={m.coverage_pct.toFixed(1)} unit="%" />}
        </div>
      </div>
    </div>
  );
}
