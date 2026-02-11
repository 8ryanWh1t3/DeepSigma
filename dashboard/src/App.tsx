import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { AlertCircle, TrendingUp, Zap, Clock, Activity } from 'lucide-react';
import { generateMockEpisodes, generateMockDrifts, generateAgentMetrics, DecisionEpisode, DriftEvent, AgentMetrics } from './mockData';

export function App() {
    const [episodes, setEpisodes] = useState<DecisionEpisode[]>([]);
    const [drifts, setDrifts] = useState<DriftEvent[]>([]);
    const [metrics, setMetrics] = useState<AgentMetrics[]>([]);
    const [selectedView, setSelectedView] = useState<'overview' | 'episodes' | 'drift' | 'export'>('overview');
    const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
        const loadData = () => {
                setEpisodes(generateMockEpisodes(100));
                setDrifts(generateMockDrifts(100));
                setMetrics(generateAgentMetrics());
        };

                loadData();

                if (autoRefresh) {
                        const interval = setInterval(loadData, 5000);
                        return () => clearInterval(interval);
                }
  }, [autoRefresh]);

  const successRate = episodes.length > 0 
    ? ((episodes.filter(e => e.status === 'success').length / episodes.length) * 100).toFixed(1)
        : 0;

  const avgLatency = episodes.length > 0
      ? (episodes.reduce((sum, e) => sum + e.actualDuration, 0) / episodes.length).toFixed(0)
        : 0;

  const driftEvents = drifts.length;

  const metricsOverTime = episodes
      .sort((a, b) => a.timestamp - b.timestamp)
      .slice(-30)
      .map((ep, i) => ({
              time: new Date(ep.timestamp).toLocaleTimeString(),
              duration: Math.round(ep.actualDuration),
              deadline: Math.round(ep.deadline)
      }));

  const statusDistribution = [
    { name: 'Success', value: episodes.filter(e => e.status === 'success').length },
    { name: 'Timeout', value: episodes.filter(e => e.status === 'timeout').length },
    { name: 'Degraded', value: episodes.filter(e => e.status === 'degraded').length },
    { name: 'Failed', value: episodes.filter(e => e.status === 'failed').length }
      ];

  const driftDistribution = drifts.reduce((acc, d) => {
        const existing = acc.find(x => x.name === d.type);
        if (existing) existing.value++;
        else acc.push({ name: d.type, value: 1 });
        return acc;
  }, [] as Array<{name: string, value: number}>);

  const COLORS = ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  const handleExport = () => {
        const data = { episodes, drifts, metrics, timestamp: new Date().toISOString() };
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `overwatch-dashboard-${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
  };

  return (
        <div className="min-h-screen bg-slate-950 text-slate-100">
          {/* Header */}
              <header className="border-b border-slate-800 bg-slate-900 sticky top-0 z-50">
                      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                            <div className="text-2xl font-bold text-blue-400">Σ OVERWATCH</div>div>
                                            <div className="text-sm text-slate-400">Control Plane Dashboard</div>div>
                                </div>div>
                                <div className="flex items-center gap-4">
                                            <label className="flex items-center gap-2 text-sm">
                                                          <input
                                                                            type="checkbox"
                                                                            checked={autoRefresh}
                                                                            onChange={(e) => setAutoRefresh(e.target.checked)}
                                                                            className="rounded"
                                                                          />
                                                          Auto-Refresh (5s)
                                            </label>label>
                                            <div className="text-xs text-slate-500">Last update: {new Date().toLocaleTimeString()}</div>div>
                                </div>div>
                      </div>div>
              </header>header>
        
          {/* Navigation */}
              <nav className="border-b border-slate-800 bg-slate-900">
                      <div className="max-w-7xl mx-auto px-4 flex gap-1">
                        {(['overview', 'episodes', 'drift', 'export'] as const).map(view => (
                      <button
                                      key={view}
                                      onClick={() => setSelectedView(view)}
                                      className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
                                                        selectedView === view
                                                          ? 'border-blue-500 text-blue-400'
                                                          : 'border-transparent text-slate-400 hover:text-slate-300'
                                      }`}
                                    >
                        {view.charAt(0).toUpperCase() + view.slice(1)}
                      </button>button>
                    ))}
                      </div>div>
              </nav>nav>
        
          {/* Content */}
              <main className="max-w-7xl mx-auto p-6">
                {selectedView === 'overview' && (
                    <div className="space-y-6">
                      {/* KPI Cards */}
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                              <KPICard icon={<TrendingUp size={20} />} label="Success Rate" value={`${successRate}%`} trend="+2.5%" />
                                              <KPICard icon={<Clock size={20} />} label="Avg Latency" value={`${avgLatency}ms`} trend="-5%" />
                                              <KPICard icon={<Zap size={20} />} label="Drift Events" value={driftEvents.toString()} trend={`+${(driftEvents > 5 ? 1 : -1)}`} />
                                              <KPICard icon={<Activity size={20} />} label="Active Agents" value={metrics.length.toString()} trend="Stable" />
                                </div>div>
                    
                      {/* Charts */}
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                  {/* Latency Trend */}
                                              <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                                                              <h3 className="text-lg font-semibold mb-4">Deadline vs Actual Duration</h3>h3>
                                                              <ResponsiveContainer width="100%" height={300}>
                                                                                <LineChart data={metricsOverTime}>
                                                                                                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                                                                                    <XAxis dataKey="time" stroke="#64748b" />
                                                                                                    <YAxis stroke="#64748b" />
                                                                                                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
                                                                                                    <Legend />
                                                                                                    <Line type="monotone" dataKey="deadline" stroke="#60a5fa" name="Deadline" />
                                                                                                    <Line type="monotone" dataKey="duration" stroke="#ef4444" name="Actual Duration" />
                                                                                </LineChart>LineChart>
                                                              </ResponsiveContainer>ResponsiveContainer>
                                              </div>div>
                                
                                  {/* Status Distribution */}
                                              <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                                                              <h3 className="text-lg font-semibold mb-4">Decision Status Distribution</h3>h3>
                                                              <ResponsiveContainer width="100%" height={300}>
                                                                                <PieChart>
                                                                                                    <Pie data={statusDistribution} cx="50%" cy="50%" labelLine={false} label={({value}) => value} outerRadius={80} fill="#8884d8" dataKey="value">
                                                                                                      {statusDistribution.map((entry, index) => (
                                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                            ))}
                                                                                                      </Pie>Pie>
                                                                                                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
                                                                                </PieChart>PieChart>
                                                              </ResponsiveContainer>ResponsiveContainer>
                                              </div>div>
                                
                                  {/* Agent Metrics */}
                                              <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 lg:col-span-2">
                                                              <h3 className="text-lg font-semibold mb-4">Agent Performance Metrics</h3>h3>
                                                              <ResponsiveContainer width="100%" height={300}>
                                                                                <BarChart data={metrics}>
                                                                                                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                                                                                    <XAxis dataKey="agentName" stroke="#64748b" />
                                                                                                    <YAxis stroke="#64748b" />
                                                                                                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
                                                                                                    <Legend />
                                                                                                    <Bar dataKey="successRate" fill="#10b981" name="Success Rate %" />
                                                                                                    <Bar dataKey="avgLatency" fill="#f59e0b" name="Avg Latency (ms)" />
                                                                                </BarChart>BarChart>
                                                              </ResponsiveContainer>ResponsiveContainer>
                                              </div>div>
                                
                                  {/* Drift Distribution */}
                                              <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 lg:col-span-2">
                                                              <h3 className="text-lg font-semibold mb-4">Drift Events by Type</h3>h3>
                                                              <ResponsiveContainer width="100%" height={300}>
                                                                                <BarChart data={driftDistribution}>
                                                                                                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                                                                                    <XAxis dataKey="name" stroke="#64748b" />
                                                                                                    <YAxis stroke="#64748b" />
                                                                                                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
                                                                                                    <Bar dataKey="value" fill="#a855f7" name="Count" />
                                                                                </BarChart>BarChart>
                                                              </ResponsiveContainer>ResponsiveContainer>
                                              </div>div>
                                </div>div>
                    </div>div>
                      )}
              
                {selectedView === 'episodes' && <EpisodesView episodes={episodes} />}
                {selectedView === 'drift' && <DriftView drifts={drifts} />}
                {selectedView === 'export' && <ExportView onExport={handleExport} episodeCount={episodes.length} driftCount={drifts.length} />}
              </main>main>
        </div>div>
      );
}

interface KPICardProps {
    icon: React.ReactNode;
    label: string;
    value: string;
    trend: string;
}

function KPICard({ icon, label, value, trend }: KPICardProps) {
    return (
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
                <div className="flex items-center justify-between mb-2">
                        <span className="text-slate-400 text-sm">{label}</span>span>
                        <div className="text-blue-400">{icon}</div>div>
                </div>div>
                <div className="text-2xl font-bold mb-1">{value}</div>div>
                <div className="text-xs text-slate-500">{trend}</div>div>
          </div>div>
        );
}

function EpisodesView({ episodes }: { episodes: DecisionEpisode[] }) {
    return (
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 overflow-x-auto">
                <h3 className="text-lg font-semibold mb-4">Recent Decision Episodes</h3>h3>
                <table className="w-full text-sm">
                        <thead className="border-b border-slate-700">
                                  <tr>
                                              <th className="text-left py-2 px-3 text-slate-300">Episode ID</th>th>
                                              <th className="text-left py-2 px-3 text-slate-300">Agent</th>th>
                                              <th className="text-left py-2 px-3 text-slate-300">Status</th>th>
                                              <th className="text-left py-2 px-3 text-slate-300">Deadline</th>th>
                                              <th className="text-left py-2 px-3 text-slate-300">Duration</th>th>
                                              <th className="text-left py-2 px-3 text-slate-300">Freshness</th>th>
                                              <th className="text-left py-2 px-3 text-slate-300">Outcome</th>th>
                                  </tr>tr>
                        </thead>thead>
                        <tbody>
                          {episodes.slice(-20).reverse().map(ep => (
                        <tr key={ep.episodeId} className="border-b border-slate-800 hover:bg-slate-800">
                                      <td className="py-2 px-3 font-mono text-xs text-slate-400">{ep.episodeId.slice(0, 15)}...</td>td>
                                      <td className="py-2 px-3">{ep.agentName}</td>td>
                                      <td className="py-2 px-3">
                                                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                                            ep.status === 'success' ? 'bg-green-900 text-green-200' :
                                            ep.status === 'timeout' ? 'bg-red-900 text-red-200' :
                                            ep.status === 'degraded' ? 'bg-yellow-900 text-yellow-200' :
                                            'bg-purple-900 text-purple-200'
                        }`}>
                                                        {ep.status}
                                                      </span>span>
                                      </td>td>
                                      <td className="py-2 px-3">{ep.deadline.toFixed(0)}ms</td>td>
                                      <td className="py-2 px-3">{ep.actualDuration.toFixed(0)}ms</td>td>
                                      <td className="py-2 px-3">{ep.freshness.toFixed(1)}%</td>td>
                                      <td className="py-2 px-3">{ep.outcome}</td>td>
                        </tr>tr>
                      ))}
                        </tbody>tbody>
                </table>table>
          </div>div>
        );
}

function DriftView({ drifts }: { drifts: DriftEvent[] }) {
    return (
          <div className="space-y-4">
                <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                  <AlertCircle size={20} className="text-yellow-500" />
                                  Drift Events
                        </h3>h3>
                        <div className="space-y-3 max-h-[600px] overflow-y-auto">
                          {drifts.slice(-20).reverse().map(drift => (
                        <div key={drift.driftId} className={`p-3 rounded border ${
                                        drift.severity === 'high' ? 'bg-red-900/20 border-red-700' :
                                        drift.severity === 'medium' ? 'bg-yellow-900/20 border-yellow-700' :
                                        'bg-blue-900/20 border-blue-700'
                        }`}>
                                      <div className="flex items-start justify-between">
                                                      <div>
                                                                        <div className="font-semibold capitalize">{drift.type} Drift</div>div>
                                                                        <div className="text-xs text-slate-400 font-mono mt-1">{drift.episodeId.slice(0, 20)}...</div>div>
                                                                        <div className="text-sm text-slate-300 mt-2">{drift.patchHint}</div>div>
                                                      </div>div>
                                                      <span className={`px-2 py-1 rounded text-xs font-medium whitespace-nowrap ${
                                            drift.severity === 'high' ? 'bg-red-900 text-red-200' :
                                            drift.severity === 'medium' ? 'bg-yellow-900 text-yellow-200' :
                                            'bg-blue-900 text-blue-200'
                        }`}>
                                                        {drift.severity}
                                                      </span>span>
                                      </div>div>
                        </div>div>
                      ))}
                        </div>div>
                </div>div>
          </div>div>
        );
}

function ExportView({ onExport, episodeCount, driftCount }: { onExport: () => void, episodeCount: number, driftCount: number }) {
    return (
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                <h3 className="text-lg font-semibold mb-4">Export Dashboard Data</h3>h3>
                <div className="grid grid-cols-2 gap-4 mb-6">
                        <div className="p-4 bg-slate-800 rounded">
                                  <div className="text-sm text-slate-400">Decision Episodes</div>div>
                                  <div className="text-2xl font-bold">{episodeCount}</div>div>
                        </div>div>
                        <div className="p-4 bg-slate-800 rounded">
                                  <div className="text-sm text-slate-400">Drift Events</div>div>
                                  <div className="text-2xl font-bold">{driftCount}</div>div>
                        </div>div>
                </div>div>
                <button
                          onClick={onExport}
                          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded transition-colors"
                        >
                        Export as JSON
                </button>button>
                <p className="text-xs text-slate-500 mt-4">
                        Exports all decision episodes, drift events, and agent metrics as a JSON file for further analysis.
                </p>p>
          </div>div>
        );
}</div>
