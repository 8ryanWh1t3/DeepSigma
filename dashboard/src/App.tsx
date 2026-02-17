import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
    BarChart, Bar, LineChart, Line, AreaChart, Area, XAxis, YAxis,
    CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell,
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts';
import { AlertCircle, TrendingUp, Zap, Clock, Activity, Search, Download } from 'lucide-react';
import { generateMockEpisodes, generateMockDrifts, generateAgentMetrics, fetchRealEpisodes, fetchRealDrifts, fetchRealAgents, DecisionEpisode, DriftEvent, AgentMetrics } from './mockData';
import { IrisPanel } from './IrisPanel';

type ViewType = 'overview' | 'episodes' | 'drift' | 'iris' | 'export';
type SortField = 'agent' | 'status' | 'deadline' | 'duration' | 'freshness' | 'outcome';
type SortDir = 'asc' | 'desc';

const ttStyle = { backgroundColor: '#1e293b', border: '1px solid #475569', color: '#f1f5f9' };

function HealthGauge({ value }: { value: number }) {
    const color = value >= 90 ? '#10b981' : value >= 70 ? '#f59e0b' : '#ef4444';
    const label = value >= 90 ? 'Healthy' : value >= 70 ? 'Degraded' : 'Critical';
    const c = 2 * Math.PI * 40;
    const offset = c - (value / 100) * c;
    return (
          <div className="flex flex-col items-center gap-2">
                <svg width="100" height="100" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#334155" strokeWidth="8" />
                        <circle cx="50" cy="50" r="40" fill="none" stroke={color} strokeWidth="8"
                                    strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
                                    transform="rotate(-90 50 50)" style={{ transition: 'stroke-dashoffset 0.5s ease' }} />
                        <text x="50" y="46" textAnchor="middle" fill={color} fontSize="18" fontWeight="700">{value.toFixed(0)}</text>
                        <text x="50" y="62" textAnchor="middle" fill="#94a3b8" fontSize="10">{label}</text>
                </svg>
          </div>
        );
}

interface KPICardProps { icon: React.ReactNode; label: string; value: string; trend: string; trendUp?: boolean; }
function KPICard({ icon, label, value, trend, trendUp }: KPICardProps) {
    return (
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 hover:border-slate-700 transition-colors">
                <div className="flex items-center justify-between mb-2">
                        <span className="text-slate-400 text-sm">{label}</span>
                        <div className="text-blue-400">{icon}</div>
                </div>
                <div className="text-2xl font-bold mb-1">{value}</div>
                <div className={`text-xs ${trendUp === true ? 'text-green-400' : trendUp === false ? 'text-red-400' : 'text-slate-500'}`}>{trend}</div>
          </div>
        );
}

function EpisodesView({ episodes }: { episodes: DecisionEpisode[] }) {
    const [search, setSearch] = useState('');
    const [sortField, setSortField] = useState<SortField>('agent');
    const [sortDir, setSortDir] = useState<SortDir>('asc');
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const toggleSort = (field: SortField) => {
          if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
          else { setSortField(field); setSortDir('asc'); }
    };
    const sortIcon = (field: SortField) => sortField === field ? (sortDir === 'asc' ? ' \u2191' : ' \u2193') : '';
    const filtered = useMemo(() => {
          let data = episodes.slice(-50);
          if (statusFilter !== 'all') data = data.filter(e => e.status === statusFilter);
          if (search) {
                  const q = search.toLowerCase();
                  data = data.filter(e => e.agentName.toLowerCase().includes(q) || e.episodeId.toLowerCase().includes(q));
          }
          data.sort((a, b) => {
                  let cmp = 0;
                  switch (sortField) {
                    case 'agent': cmp = a.agentName.localeCompare(b.agentName); break;
                    case 'status': cmp = a.status.localeCompare(b.status); break;
                    case 'deadline': cmp = a.deadline - b.deadline; break;
                    case 'duration': cmp = a.actualDuration - b.actualDuration; break;
                    case 'freshness': cmp = a.freshness - b.freshness; break;
                    case 'outcome': cmp = a.outcome.localeCompare(b.outcome); break;
                  }
                  return sortDir === 'desc' ? -cmp : cmp;
          });
          return data;
    }, [episodes, search, sortField, sortDir, statusFilter]);
    return (
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                        <h3 className="text-lg font-semibold">Recent Decision Episodes</h3>
                        <div className="flex items-center gap-3">
                                  <div className="relative">
                                              <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-500" />
                                              <input type="text" placeholder="Search..." value={search} onChange={e => setSearch(e.target.value)}
                                                              className="bg-slate-800 border border-slate-700 rounded pl-7 pr-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500 w-40" />
                                  </div>
                                  <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                                                className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200 focus:outline-none">
                                              <option value="all">All Status</option><option value="success">Success</option>
                                              <option value="timeout">Timeout</option><option value="degraded">Degraded</option><option value="failed">Failed</option>
                                  </select>
                        </div>
                </div>
                <div className="text-xs text-slate-500 mb-2">Showing {filtered.length} episodes</div>
                <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                                  <thead className="border-b border-slate-700">
                                              <tr>
                                                            <th className="text-left py-2 px-3 text-slate-300">Episode ID</th>
                                                {(['agent','status','deadline','duration','freshness','outcome'] as SortField[]).map(f => (
                            <th key={f} className="text-left py-2 px-3 text-slate-300 cursor-pointer hover:text-blue-400" onClick={() => toggleSort(f)}>
                              {f.charAt(0).toUpperCase()+f.slice(1)}{sortIcon(f)}
                            </th>
                          ))}
                                              </tr>
                                  </thead>
                                  <tbody>
                                    {filtered.map(ep => (
                          <tr key={ep.episodeId} className="border-b border-slate-800 hover:bg-slate-800 transition-colors">
                                          <td className="py-2 px-3 font-mono text-xs text-slate-400">{ep.episodeId.slice(0,15)}...</td>
                                          <td className="py-2 px-3">{ep.agentName}</td>
                                          <td className="py-2 px-3"><span className={`px-2 py-1 rounded text-xs font-medium ${ep.status==='success'?'bg-green-900/50 text-green-300':ep.status==='timeout'?'bg-red-900/50 text-red-300':ep.status==='degraded'?'bg-yellow-900/50 text-yellow-300':'bg-purple-900/50 text-purple-300'}`}>{ep.status}</span></td>
                                          <td className="py-2 px-3">{ep.deadline.toFixed(0)}ms</td>
                                          <td className="py-2 px-3">{ep.actualDuration.toFixed(0)}ms</td>
                                          <td className="py-2 px-3">
                                                            <div className="flex items-center gap-2">
                                                                                <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                                                                                                      <div className="h-full rounded-full" style={{width:`${ep.freshness}%`,background:ep.freshness>97?'#10b981':ep.freshness>95?'#f59e0b':'#ef4444'}} />
                                                                                  </div>
                                                                                <span className="text-xs">{ep.freshness.toFixed(1)}%</span>
                                                            </div>
                                          </td>
                                          <td className="py-2 px-3">{ep.outcome}</td>
                          </tr>
                        ))}
                                  </tbody>
                        </table>
                </div>
          </div>
        );
}

function DriftView({ drifts }: { drifts: DriftEvent[] }) {
    const [severityFilter, setSeverityFilter] = useState<string>('all');
    const filtered = useMemo(() => {
          let data = drifts.slice(-30).reverse();
          if (severityFilter !== 'all') data = data.filter(d => d.severity === severityFilter);
          return data;
    }, [drifts, severityFilter]);
    const counts = useMemo(() => ({
          high: drifts.filter(d => d.severity === 'high').length,
          medium: drifts.filter(d => d.severity === 'medium').length,
          low: drifts.filter(d => d.severity === 'low').length,
    }), [drifts]);
    return (
          <div className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-center">
                                  <div className="text-2xl font-bold text-red-400">{counts.high}</div>
                                  <div className="text-xs text-red-300">High Severity</div>
                        </div>
                        <div className="bg-yellow-900/20 border border-yellow-800 rounded-lg p-4 text-center">
                                  <div className="text-2xl font-bold text-yellow-400">{counts.medium}</div>
                                  <div className="text-xs text-yellow-300">Medium Severity</div>
                        </div>
                        <div className="bg-blue-900/20 border border-blue-800 rounded-lg p-4 text-center">
                                  <div className="text-2xl font-bold text-blue-400">{counts.low}</div>
                                  <div className="text-xs text-blue-300">Low Severity</div>
                        </div>
                </div>
                <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                        <div className="flex items-center justify-between mb-4">
                                  <h3 className="text-lg font-semibold flex items-center gap-2"><AlertCircle size={20} className="text-yellow-500" /> Drift Events</h3>
                                  <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}
                                                className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200">
                                              <option value="all">All</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
                                  </select>
                        </div>
                        <div className="space-y-3 max-h-[600px] overflow-y-auto">
                          {filtered.map(drift => (
                        <div key={drift.driftId} className={`p-3 rounded border transition-colors ${drift.severity==='high'?'bg-red-900/20 border-red-700 hover:bg-red-900/30':drift.severity==='medium'?'bg-yellow-900/20 border-yellow-700 hover:bg-yellow-900/30':'bg-blue-900/20 border-blue-700 hover:bg-blue-900/30'}`}>
                                      <div className="flex items-start justify-between">
                                                      <div>
                                                                        <div className="font-semibold capitalize">{drift.type} Drift</div>
                                                                        <div className="text-xs text-slate-400 font-mono mt-1">{drift.episodeId.slice(0,20)}...</div>
                                                                        <div className="text-sm text-slate-300 mt-2">{drift.patchHint}</div>
                                                                        <div className="text-xs text-slate-500 mt-1">{new Date(drift.timestamp).toLocaleTimeString()}</div>
                                                      </div>
                                                      <span className={`px-2 py-1 rounded text-xs font-medium whitespace-nowrap ${drift.severity==='high'?'bg-red-900 text-red-200':drift.severity==='medium'?'bg-yellow-900 text-yellow-200':'bg-blue-900 text-blue-200'}`}>{drift.severity}</span>
                                      </div>
                        </div>
                      ))}
                        </div>
                </div>
          </div>
        );
}

function ExportView({ episodes, drifts, metrics }: { episodes: DecisionEpisode[]; drifts: DriftEvent[]; metrics: AgentMetrics[] }) {
    const doExport = (fmt: 'json'|'csv') => {
          const d = new Date().toISOString().slice(0,10);
          if (fmt==='json') {
                  const data = JSON.stringify({episodes,drifts,metrics,timestamp:new Date().toISOString()},null,2);
                  dl(data,'application/json',`overwatch-${d}.json`);
          } else {
                  const hdr='id,agent,status,deadline,duration,freshness,outcome\n';
                  const rows=episodes.map(e=>`${e.episodeId},${e.agentName},${e.status},${e.deadline.toFixed(0)},${e.actualDuration.toFixed(0)},${e.freshness.toFixed(1)},${e.outcome}`).join('\n');
                  dl(hdr+rows,'text/csv',`overwatch-episodes-${d}.csv`);
          }
    };
    const dl = (c:string,t:string,n:string) => {
          const b=new Blob([c],{type:t});const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download=n;a.click();URL.revokeObjectURL(u);
    };
    return (
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                <h3 className="text-lg font-semibold mb-4">Export Dashboard Data</h3>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                  {[{l:'Decision Episodes',v:episodes.length},{l:'Drift Events',v:drifts.length},{l:'Agents Tracked',v:metrics.length},{l:'Data Points',v:episodes.length*7+drifts.length*4}].map(s=>(
                      <div key={s.l} className="p-4 bg-slate-800 rounded-lg"><div className="text-sm text-slate-400">{s.l}</div><div className="text-2xl font-bold">{s.v}</div></div>
                    ))}
                </div>
                <div className="flex gap-3">
                        <button onClick={()=>doExport('json')} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded transition-colors flex items-center gap-2"><Download size={16}/>Export JSON</button>
                        <button onClick={()=>doExport('csv')} className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2 px-4 rounded transition-colors flex items-center gap-2"><Download size={16}/>Export CSV</button>
                </div>
                <p className="text-xs text-slate-500 mt-4">Exports all decision episodes, drift events, and agent metrics for offline analysis.</p>
          </div>
        );
}

export function App() {
    const [episodes, setEpisodes] = useState<DecisionEpisode[]>([]);
    const [drifts, setDrifts] = useState<DriftEvent[]>([]);
    const [metrics, setMetrics] = useState<AgentMetrics[]>([]);
    const [selectedView, setSelectedView] = useState<ViewType>('overview');
    const [autoRefresh, setAutoRefresh] = useState(true);
    const [lastUpdate, setLastUpdate] = useState('');
    const [dataSource, setDataSource] = useState<'api' | 'mock'>('mock');

    const loadData = useCallback(async () => {
          // Try the real API first; fall back to mock data if offline
          const [realEps, realDrifts, realAgents] = await Promise.all([
                  fetchRealEpisodes(), fetchRealDrifts(), fetchRealAgents(),
          ]);
          if (realEps && realEps.length > 0) {
                  setEpisodes(realEps);
                  setDrifts(realDrifts ?? generateMockDrifts(20));
                  setMetrics(realAgents ?? generateAgentMetrics());
                  setDataSource('api');
          } else {
                  setEpisodes(generateMockEpisodes(100));
                  setDrifts(generateMockDrifts(100));
                  setMetrics(generateAgentMetrics());
                  setDataSource('mock');
          }
          setLastUpdate(new Date().toLocaleTimeString());
    }, []);
  
    useEffect(() => {
          loadData();
          if (autoRefresh) {
                  const id=setInterval(loadData,5000);
                  return ()=>clearInterval(id);
          }
    }, [autoRefresh, loadData]);
  
    useEffect(() => {
          const handler = (e: KeyboardEvent) => {
                  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
                  const views: ViewType[] = ['overview','episodes','drift','iris','export'];
                  if (e.key>='1'&&e.key<='5') setSelectedView(views[parseInt(e.key)-1]);
                  if (e.key==='r') loadData();
          };
          window.addEventListener('keydown', handler);
          return () => window.removeEventListener('keydown', handler);
    }, [loadData]);
  
    const successRate = episodes.length>0 ? ((episodes.filter(e=>e.status==='success').length/episodes.length)*100).toFixed(1) : '0';
    const avgLatency = episodes.length>0 ? (episodes.reduce((s,e)=>s+e.actualDuration,0)/episodes.length).toFixed(0) : '0';
    const systemHealth = useMemo(() => {
          if (!episodes.length) return 100;
          const sr = episodes.filter(e=>e.status==='success').length/episodes.length;
          return Math.max(0, Math.min(100, sr*100 - drifts.filter(d=>d.severity==='high').length*5));
    }, [episodes, drifts]);
  
    const metricsOverTime = useMemo(() => episodes.sort((a,b)=>a.timestamp-b.timestamp).slice(-30).map(ep=>({
          time:new Date(ep.timestamp).toLocaleTimeString(),
          duration:Math.round(ep.actualDuration),
          deadline:Math.round(ep.deadline)
    })), [episodes]);
  
    const statusDist = useMemo(() => [
      {name:'Success',value:episodes.filter(e=>e.status==='success').length},
      {name:'Timeout',value:episodes.filter(e=>e.status==='timeout').length},
      {name:'Degraded',value:episodes.filter(e=>e.status==='degraded').length},
      {name:'Failed',value:episodes.filter(e=>e.status==='failed').length}
        ], [episodes]);
  
    const driftDist = useMemo(() => drifts.reduce((acc,d) => {
          const ex=acc.find(x=>x.name===d.type);
          if(ex) ex.value++; else acc.push({name:d.type,value:1});
          return acc;
    }, [] as Array<{name:string;value:number}>), [drifts]);
  
    const radarData = useMemo(() => metrics.map(m=>({
          agent:m.agentName.replace('Agent',''),
          success:m.successRate,
          freshness:m.averageFreshness,
          latency:100-(m.avgLatency/5)
    })), [metrics]);
  
    const COLORS = ['#10b981','#f59e0b','#ef4444','#8b5cf6'];
  
    return (
          <div className="min-h-screen bg-slate-950 text-slate-100">
                <header className="border-b border-slate-800 bg-slate-900 sticky top-0 z-50">
                        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between flex-wrap gap-3">
                                  <div className="flex items-center gap-3">
                                              <div className="text-2xl font-bold text-blue-400">{'\u03A3'} OVERWATCH</div>
                                              <div className="text-sm text-slate-400">Control Plane Dashboard</div>
                                  </div>
                                  <div className="flex items-center gap-4">
                                              <label className="flex items-center gap-2 text-sm cursor-pointer">
                                                            <input type="checkbox" checked={autoRefresh} onChange={e=>setAutoRefresh(e.target.checked)} className="rounded accent-blue-500" />
                                                            Auto-Refresh (5s)
                                              </label>
                                              <button onClick={loadData} className="text-xs text-slate-400 hover:text-blue-400 transition-colors">{'\u21BB'} Refresh</button>
                                              <div className="text-xs text-slate-500">Updated: {lastUpdate}</div>
                                              <div className={`text-xs px-1.5 py-0.5 rounded font-mono ${dataSource === 'api' ? 'bg-green-900 text-green-300' : 'bg-slate-800 text-slate-500'}`}>{dataSource === 'api' ? '● live' : '○ mock'}</div>
                                  </div>
                        </div>
                </header>
          
                <nav className="border-b border-slate-800 bg-slate-900">
                        <div className="max-w-7xl mx-auto px-4 flex gap-1">
                          {(['overview','episodes','drift','iris','export'] as const).map((view,i) => (
                        <button key={view} onClick={()=>setSelectedView(view)}
                                        className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 ${selectedView===view?'border-blue-500 text-blue-400':'border-transparent text-slate-400 hover:text-slate-300'}`}>
                                      <span className="text-xs text-slate-600 mr-1">{i+1}</span>{view === 'iris' ? 'IRIS' : view.charAt(0).toUpperCase()+view.slice(1)}
                        </button>
                      ))}
                        </div>
                </nav>
          
                <main className="max-w-7xl mx-auto p-6">
                  {selectedView==='overview' && (
                      <div className="space-y-6">
                                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                                                <KPICard icon={<TrendingUp size={20}/>} label="Success Rate" value={`${successRate}%`} trend="+2.5% from baseline" trendUp={true} />
                                                <KPICard icon={<Clock size={20}/>} label="Avg Latency" value={`${avgLatency}ms`} trend="-5% improvement" trendUp={true} />
                                                <KPICard icon={<Zap size={20}/>} label="Drift Events" value={drifts.length.toString()} trend={`${drifts.filter(d=>d.severity==='high').length} high severity`} trendUp={false} />
                                                <KPICard icon={<Activity size={20}/>} label="Active Agents" value={metrics.length.toString()} trend="All operational" trendUp={true} />
                                                <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 flex flex-col items-center justify-center hover:border-slate-700 transition-colors">
                                                                <div className="text-slate-400 text-sm mb-1">System Health</div>
                                                                <HealthGauge value={systemHealth} />
                                                </div>
                                  </div>
                                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                                <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                                                                <h3 className="text-lg font-semibold mb-4">Deadline vs Actual Duration</h3>
                                                                <ResponsiveContainer width="100%" height={300}>
                                                                                  <AreaChart data={metricsOverTime}>
                                                                                                      <defs>
                                                                                                                            <linearGradient id="gDL" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3}/><stop offset="95%" stopColor="#60a5fa" stopOpacity={0}/></linearGradient>
                                                                                                                            <linearGradient id="gDR" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/><stop offset="95%" stopColor="#ef4444" stopOpacity={0}/></linearGradient>
                                                                                                        </defs>
                                                                                                      <CartesianGrid strokeDasharray="3 3" stroke="#334155"/>
                                                                                                      <XAxis dataKey="time" stroke="#64748b" tick={{fontSize:10}}/>
                                                                                                      <YAxis stroke="#64748b"/>
                                                                                                      <Tooltip contentStyle={ttStyle}/>
                                                                                                      <Legend/>
                                                                                                      <Area type="monotone" dataKey="deadline" stroke="#60a5fa" fill="url(#gDL)" name="Deadline"/>
                                                                                                      <Area type="monotone" dataKey="duration" stroke="#ef4444" fill="url(#gDR)" name="Actual"/>
                                                                                    </AreaChart>
                                                                </ResponsiveContainer>
                                                </div>
                                                <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                                                                <h3 className="text-lg font-semibold mb-4">Decision Status Distribution</h3>
                                                                <ResponsiveContainer width="100%" height={300}>
                                                                                  <PieChart>
                                                                                                      <Pie data={statusDist} cx="50%" cy="50%" outerRadius={90} innerRadius={50} dataKey="value"
                                                                                                                              label={({name,value})=>`${name}: ${value}`} paddingAngle={2}>
                                                                                                        {statusDist.map((_,i)=><Cell key={i} fill={COLORS[i]}/>)}
                                                                                                        </Pie>
                                                                                                      <Tooltip contentStyle={ttStyle}/>
                                                                                    </PieChart>
                                                                </ResponsiveContainer>
                                                </div>
                                                <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                                                                <h3 className="text-lg font-semibold mb-4">Agent Comparison Radar</h3>
                                                                <ResponsiveContainer width="100%" height={300}>
                                                                                  <RadarChart data={radarData}>
                                                                                                      <PolarGrid stroke="#334155"/>
                                                                                                      <PolarAngleAxis dataKey="agent" tick={{fill:'#94a3b8',fontSize:12}}/>
                                                                                                      <PolarRadiusAxis tick={{fill:'#64748b',fontSize:10}}/>
                                                                                                      <Radar name="Success %" dataKey="success" stroke="#10b981" fill="#10b981" fillOpacity={0.2}/>
                                                                                                      <Radar name="Freshness %" dataKey="freshness" stroke="#60a5fa" fill="#60a5fa" fillOpacity={0.2}/>
                                                                                                      <Tooltip contentStyle={ttStyle}/><Legend/>
                                                                                    </RadarChart>
                                                                </ResponsiveContainer>
                                                </div>
                                                <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                                                                <h3 className="text-lg font-semibold mb-4">Agent Performance</h3>
                                                                <ResponsiveContainer width="100%" height={300}>
                                                                                  <BarChart data={metrics}>
                                                                                                      <CartesianGrid strokeDasharray="3 3" stroke="#334155"/>
                                                                                                      <XAxis dataKey="agentName" stroke="#64748b" tick={{fontSize:11}}/>
                                                                                                      <YAxis stroke="#64748b"/>
                                                                                                      <Tooltip contentStyle={ttStyle}/><Legend/>
                                                                                                      <Bar dataKey="successRate" fill="#10b981" name="Success %" radius={[4,4,0,0]}/>
                                                                                                      <Bar dataKey="avgLatency" fill="#f59e0b" name="Latency (ms)" radius={[4,4,0,0]}/>
                                                                                    </BarChart>
                                                                </ResponsiveContainer>
                                                </div>
                                                <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 lg:col-span-2">
                                                                <h3 className="text-lg font-semibold mb-4">Drift Events by Type</h3>
                                                                <ResponsiveContainer width="100%" height={280}>
                                                                                  <BarChart data={driftDist} layout="vertical">
                                                                                                      <CartesianGrid strokeDasharray="3 3" stroke="#334155"/>
                                                                                                      <XAxis type="number" stroke="#64748b"/>
                                                                                                      <YAxis type="category" dataKey="name" stroke="#64748b" width={80}/>
                                                                                                      <Tooltip contentStyle={ttStyle}/>
                                                                                                      <Bar dataKey="value" fill="#a855f7" name="Count" radius={[0,4,4,0]}/>
                                                                                    </BarChart>
                                                                </ResponsiveContainer>
                                                </div>
                                  </div>
                      </div>
                        )}
                  {selectedView==='episodes' && <EpisodesView episodes={episodes}/>}
                  {selectedView==='drift' && <DriftView drifts={drifts}/>}
                  {selectedView==='iris' && <IrisPanel />}
                  {selectedView==='export' && <ExportView episodes={episodes} drifts={drifts} metrics={metrics}/>}
                </main>
          
                <div className="fixed bottom-4 right-4 text-xs text-slate-600 bg-slate-900/80 px-3 py-1.5 rounded border border-slate-800">
                        Press 1-5 to switch views {'\u00B7'} R to refresh
                </div>
          </div>
        );
}