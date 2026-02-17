import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
    BarChart, Bar, AreaChart, Area, XAxis, YAxis,
    CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell,
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts';
import { AlertCircle, TrendingUp, Zap, Clock, Activity, Search, Download, Sun, Moon, X, ChevronLeft, ChevronRight, Maximize2, Network } from 'lucide-react';
import { generateMockEpisodes, generateMockDrifts, generateAgentMetrics, DecisionEpisode, DriftEvent, AgentMetrics } from './mockData';
import { IrisPanel } from './IrisPanel';
import { CoherencePanel } from './CoherencePanel';

type ViewType = 'overview' | 'episodes' | 'drift' | 'iris' | 'coherence' | 'graph' | 'export';
type SortField = 'agent' | 'status' | 'deadline' | 'duration' | 'freshness' | 'outcome';
type SortDir = 'asc' | 'desc';

const ttStyle = { backgroundColor: '#1e293b', border: '1px solid #475569', color: '#f1f5f9' };
const ttStyleLight = { backgroundColor: '#f8fafc', border: '1px solid #cbd5e1', color: '#1e293b' };

interface Toast { id: string; message: string; severity: 'high' | 'medium' | 'low'; ts: number; }

function HealthGauge({ value }: { value: number }) {
    const color = value >= 90 ? '#10b981' : value >= 70 ? '#f59e0b' : '#ef4444';
    const label = value >= 90 ? 'Healthy' : value >= 70 ? 'Degraded' : 'Critical';
    const c = 2 * Math.PI * 40;
    const offset = c - (value / 100) * c;
    return (
        <div className="flex flex-col items-center gap-2">
            <svg width="100" height="100" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" fill="none" className="stroke-slate-300 dark:stroke-slate-700" strokeWidth="8" />
                <circle cx="50" cy="50" r="40" fill="none" stroke={color} strokeWidth="8"
                    strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
                    transform="rotate(-90 50 50)" style={{ transition: 'stroke-dashoffset 0.5s ease' }} />
                <text x="50" y="46" textAnchor="middle" fill={color} fontSize="18" fontWeight="700">{value.toFixed(0)}</text>
                <text x="50" y="62" textAnchor="middle" className="fill-slate-400" fontSize="10">{label}</text>
            </svg>
        </div>
    );
}

interface KPICardProps { icon: React.ReactNode; label: string; value: string; trend: string; trendUp?: boolean; }
function KPICard({ icon, label, value, trend, trendUp }: KPICardProps) {
    return (
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-4 hover:border-slate-300 dark:hover:border-slate-700 transition-colors shadow-sm dark:shadow-none">
            <div className="flex items-center justify-between mb-2">
                <span className="text-slate-500 dark:text-slate-400 text-sm">{label}</span>
                <div className="text-blue-500 dark:text-blue-400">{icon}</div>
            </div>
            <div className="text-2xl font-bold mb-1">{value}</div>
            <div className={`text-xs ${trendUp === true ? 'text-green-600 dark:text-green-400' : trendUp === false ? 'text-red-600 dark:text-red-400' : 'text-slate-400'}`}>{trend}</div>
        </div>
    );
}

function EpisodeModal({ episode, onClose }: { episode: DecisionEpisode | null; onClose: () => void }) {
    if (!episode) return null;
    const sc = episode.status === 'success' ? 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300'
        : episode.status === 'timeout' ? 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300'
        : episode.status === 'degraded' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300'
        : 'bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-300';
    const fields = [
        { label: 'Episode ID', value: episode.episodeId },
        { label: 'Agent', value: episode.agentName },
        { label: 'Status', value: episode.status, badge: sc },
        { label: 'Deadline', value: episode.deadline.toFixed(0) + 'ms' },
        { label: 'Actual Duration', value: episode.actualDuration.toFixed(0) + 'ms' },
        { label: 'Freshness', value: episode.freshness.toFixed(2) + '%' },
        { label: 'Data Age', value: episode.dataAge.toFixed(0) + 'ms' },
        { label: 'Distance', value: episode.distance.toFixed(3) },
        { label: 'Variability', value: episode.variability.toFixed(3) },
        { label: 'Drag', value: episode.drag.toFixed(3) },
        { label: 'AL6 Score', value: episode.al6Score.toFixed(2) },
        { label: 'Decision', value: episode.decision },
        { label: 'Verification', value: episode.verification },
        { label: 'Outcome', value: episode.outcome },
        { label: 'Action Contract', value: episode.actionContract },
    ];
    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-y-auto m-4" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between p-5 border-b border-slate-200 dark:border-slate-700">
                    <h3 className="text-lg font-semibold flex items-center gap-2"><Maximize2 size={18} className="text-blue-500" /> Episode Detail</h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"><X size={20} /></button>
                </div>
                <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {fields.map(f => (
                        <div key={f.label} className={f.label === 'Episode ID' || f.label === 'Action Contract' ? 'sm:col-span-2' : ''}>
                            <div className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">{f.label}</div>
                            {f.badge ? <span className={`px-2 py-1 rounded text-xs font-medium ${f.badge}`}>{f.value}</span>
                            : <div className="text-sm font-mono break-all">{f.value}</div>}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

function EpisodesView({ episodes }: { episodes: DecisionEpisode[] }) {
    const [search, setSearch] = useState('');
    const [sortField, setSortField] = useState<SortField>('agent');
    const [sortDir, setSortDir] = useState<SortDir>('asc');
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [selectedEpisode, setSelectedEpisode] = useState<DecisionEpisode | null>(null);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const toggleSort = (field: SortField) => {
        if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        else { setSortField(field); setSortDir('asc'); }
    };
    const sortIcon = (field: SortField) => sortField === field ? (sortDir === 'asc' ? ' \u2191' : ' \u2193') : '';
    const filtered = useMemo(() => {
        let data = [...episodes];
        if (statusFilter !== 'all') data = data.filter(e => e.status === statusFilter);
        if (search) { const q = search.toLowerCase(); data = data.filter(e => e.agentName.toLowerCase().includes(q) || e.episodeId.toLowerCase().includes(q)); }
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
    const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    const safePage = Math.min(page, totalPages);
    const paged = filtered.slice((safePage - 1) * pageSize, safePage * pageSize);
    useEffect(() => { setPage(1); }, [search, statusFilter, pageSize]);
    return (
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6 shadow-sm dark:shadow-none">
            <EpisodeModal episode={selectedEpisode} onClose={() => setSelectedEpisode(null)} />
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                <h3 className="text-lg font-semibold">Recent Decision Episodes</h3>
                <div className="flex items-center gap-3 flex-wrap">
                    <div className="relative">
                        <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input type="text" placeholder="Search..." value={search} onChange={e => setSearch(e.target.value)}
                            className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded pl-7 pr-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 w-40" />
                    </div>
                    <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded px-2 py-1.5 text-sm focus:outline-none">
                        <option value="all">All Status</option><option value="success">Success</option><option value="timeout">Timeout</option><option value="degraded">Degraded</option><option value="failed">Failed</option>
                    </select>
                    <select value={pageSize} onChange={e => setPageSize(Number(e.target.value))} className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded px-2 py-1.5 text-sm focus:outline-none">
                        <option value={10}>10/pg</option><option value={20}>20/pg</option><option value={50}>50/pg</option><option value={100}>100/pg</option>
                    </select>
                </div>
            </div>
            <div className="text-xs text-slate-500 mb-2">Showing {paged.length} of {filtered.length} episodes (page {safePage}/{totalPages})</div>
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead className="border-b border-slate-300 dark:border-slate-700">
                        <tr>
                            <th className="text-left py-2 px-3 text-slate-600 dark:text-slate-300">Episode ID</th>
                            {(['agent','status','deadline','duration','freshness','outcome'] as SortField[]).map(f => (
                                <th key={f} className="text-left py-2 px-3 text-slate-600 dark:text-slate-300 cursor-pointer hover:text-blue-500" onClick={() => toggleSort(f)}>{f.charAt(0).toUpperCase()+f.slice(1)}{sortIcon(f)}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {paged.map(ep => (
                            <tr key={ep.episodeId} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer" onClick={() => setSelectedEpisode(ep)}>
                                <td className="py-2 px-3 font-mono text-xs text-slate-400">{ep.episodeId.slice(0,15)}...</td>
                                <td className="py-2 px-3">{ep.agentName}</td>
                                <td className="py-2 px-3"><span className={`px-2 py-1 rounded text-xs font-medium ${ep.status==='success'?'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300':ep.status==='timeout'?'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300':ep.status==='degraded'?'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300':'bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-300'}`}>{ep.status}</span></td>
                                <td className="py-2 px-3">{ep.deadline.toFixed(0)}ms</td>
                                <td className="py-2 px-3">{ep.actualDuration.toFixed(0)}ms</td>
                                <td className="py-2 px-3"><div className="flex items-center gap-2"><div className="w-16 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden"><div className="h-full rounded-full" style={{width:`${ep.freshness}%`,background:ep.freshness>97?'#10b981':ep.freshness>95?'#f59e0b':'#ef4444'}} /></div><span className="text-xs">{ep.freshness.toFixed(1)}%</span></div></td>
                                <td className="py-2 px-3">{ep.outcome}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-200 dark:border-slate-700">
                <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={safePage <= 1} className="flex items-center gap-1 px-3 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-700 disabled:opacity-30 hover:bg-slate-100 dark:hover:bg-slate-800"><ChevronLeft size={14}/> Prev</button>
                <div className="flex items-center gap-1">{Array.from({length: Math.min(5, totalPages)}, (_, i) => { const s = Math.max(1, Math.min(safePage - 2, totalPages - 4)); const p = s + i; if (p > totalPages) return null; return <button key={p} onClick={() => setPage(p)} className={`w-8 h-8 rounded text-sm font-medium ${p===safePage?'bg-blue-600 text-white':'hover:bg-slate-100 dark:hover:bg-slate-800'}`}>{p}</button>; })}</div>
                <button onClick={() => setPage(p => Math.min(totalPages, p+1))} disabled={safePage >= totalPages} className="flex items-center gap-1 px-3 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-700 disabled:opacity-30 hover:bg-slate-100 dark:hover:bg-slate-800">Next <ChevronRight size={14}/></button>
            </div>
        </div>
    );
}

function DriftView({ drifts }: { drifts: DriftEvent[] }) {
    const [severityFilter, setSeverityFilter] = useState<string>('all');
    const filtered = useMemo(() => { let d = drifts.slice(-30).reverse(); if (severityFilter !== 'all') d = d.filter(x => x.severity === severityFilter); return d; }, [drifts, severityFilter]);
    const counts = useMemo(() => ({ high: drifts.filter(d => d.severity === 'high').length, medium: drifts.filter(d => d.severity === 'medium').length, low: drifts.filter(d => d.severity === 'low').length }), [drifts]);
    return (
        <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-center"><div className="text-2xl font-bold text-red-600 dark:text-red-400">{counts.high}</div><div className="text-xs text-red-500 dark:text-red-300">High Severity</div></div>
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 text-center"><div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{counts.medium}</div><div className="text-xs text-yellow-600 dark:text-yellow-300">Medium Severity</div></div>
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 text-center"><div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{counts.low}</div><div className="text-xs text-blue-500 dark:text-blue-300">Low Severity</div></div>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6 shadow-sm dark:shadow-none">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold flex items-center gap-2"><AlertCircle size={20} className="text-yellow-500" /> Drift Events</h3>
                    <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)} className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded px-2 py-1 text-sm">
                        <option value="all">All</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
                    </select>
                </div>
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                    {filtered.map(drift => (
                        <div key={drift.driftId} className={`p-3 rounded border transition-colors ${drift.severity==='high'?'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700':''}  ${drift.severity==='medium'?'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700':''} ${drift.severity==='low'?'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700':''}`}>
                            <div className="flex items-start justify-between">
                                <div>
                                    <div className="font-semibold capitalize">{drift.type} Drift</div>
                                    <div className="text-xs text-slate-400 font-mono mt-1">{drift.episodeId.slice(0,20)}...</div>
                                    <div className="text-sm text-slate-600 dark:text-slate-300 mt-2">{drift.patchHint}</div>
                                    <div className="text-xs text-slate-400 mt-1">{new Date(drift.timestamp).toLocaleTimeString()}</div>
                                </div>
                                <span className={`px-2 py-1 rounded text-xs font-medium whitespace-nowrap ${drift.severity==='high'?'bg-red-200 text-red-800 dark:bg-red-900 dark:text-red-200':drift.severity==='medium'?'bg-yellow-200 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200':'bg-blue-200 text-blue-800 dark:bg-blue-900 dark:text-blue-200'}`}>{drift.severity}</span>
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
        if (fmt==='json') { const data = JSON.stringify({episodes,drifts,metrics,timestamp:new Date().toISOString()},null,2); dl(data,'application/json',`overwatch-${d}.json`); }
        else { const hdr='id,agent,status,deadline,duration,freshness,outcome\n'; const rows=episodes.map(e=>`${e.episodeId},${e.agentName},${e.status},${e.deadline.toFixed(0)},${e.actualDuration.toFixed(0)},${e.freshness.toFixed(1)},${e.outcome}`).join('\n'); dl(hdr+rows,'text/csv',`overwatch-episodes-${d}.csv`); }
    };
    const dl = (c:string,t:string,n:string) => { const b=new Blob([c],{type:t});const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download=n;a.click();URL.revokeObjectURL(u); };
    return (
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6 shadow-sm dark:shadow-none">
            <h3 className="text-lg font-semibold mb-4">Export Dashboard Data</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                {[{l:'Decision Episodes',v:episodes.length},{l:'Drift Events',v:drifts.length},{l:'Agents Tracked',v:metrics.length},{l:'Data Points',v:episodes.length*7+drifts.length*4}].map(s=>(
                    <div key={s.l} className="p-4 bg-slate-100 dark:bg-slate-800 rounded-lg"><div className="text-sm text-slate-500 dark:text-slate-400">{s.l}</div><div className="text-2xl font-bold">{s.v}</div></div>
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

/* ── Memory Graph Visualization ──────────────────────────────── */
interface GraphNode { id: string; kind: string; label: string; x: number; y: number; vx: number; vy: number; }
interface GraphEdge { source: string; target: string; kind: string; }

function MemoryGraphView() {
    const svgRef = useRef<SVGSVGElement>(null);
    const [nodes, setNodes] = useState<GraphNode[]>([]);
    const [edges, setEdges] = useState<GraphEdge[]>([]);
    const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
    const [zoom, setZoom] = useState(1);
    const [pan, setPan] = useState({ x: 0, y: 0 });
    const dragging = useRef<{ node: string; startX: number; startY: number } | null>(null);
    const panning = useRef<{ startX: number; startY: number; startPanX: number; startPanY: number } | null>(null);
    const animRef = useRef<number>(0);

    const kindColor: Record<string, string> = { episode: '#60a5fa', action: '#34d399', drift: '#f87171', patch: '#a78bfa', evidence: '#fbbf24' };

    useEffect(() => {
        const kinds = [
            { kind: 'episode', count: 12, prefix: 'ep' },
            { kind: 'action', count: 15, prefix: 'act' },
            { kind: 'drift', count: 8, prefix: 'dft' },
            { kind: 'patch', count: 4, prefix: 'ptc' },
            { kind: 'evidence', count: 7, prefix: 'ev' },
        ];
        const ns: GraphNode[] = [];
        const cx = 400, cy = 300;
        kinds.forEach(({ kind, count, prefix }) => {
            for (let i = 0; i < count; i++) {
                const angle = (Math.PI * 2 * i) / count + Math.random() * 0.5;
                const radius = 80 + Math.random() * 180;
                ns.push({ id: `${prefix}-${i}`, kind, label: `${prefix}-${i}`, x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius, vx: 0, vy: 0 });
            }
        });
        const es: GraphEdge[] = [];
        const edgeTypes = ['produced', 'triggered', 'resolved_by', 'evidence_of', 'recurrence'];
        for (let i = 0; i < 50; i++) {
            const src = ns[Math.floor(Math.random() * ns.length)];
            const tgt = ns[Math.floor(Math.random() * ns.length)];
            if (src.id !== tgt.id) es.push({ source: src.id, target: tgt.id, kind: edgeTypes[Math.floor(Math.random() * edgeTypes.length)] });
        }
        setNodes(ns);
        setEdges(es);
    }, []);

    useEffect(() => {
        let running = true;
        const tick = () => {
            if (!running) return;
            setNodes(prev => {
                const next = prev.map(n => ({ ...n }));
                for (let i = 0; i < next.length; i++) {
                    for (let j = i + 1; j < next.length; j++) {
                        const dx = next[j].x - next[i].x;
                        const dy = next[j].y - next[i].y;
                        const dist = Math.max(1, Math.sqrt(dx * dx + dy * dy));
                        const force = 800 / (dist * dist);
                        const fx = (dx / dist) * force;
                        const fy = (dy / dist) * force;
                        next[i].vx -= fx; next[i].vy -= fy;
                        next[j].vx += fx; next[j].vy += fy;
                    }
                }
                edges.forEach(e => {
                    const s = next.find(n => n.id === e.source);
                    const t = next.find(n => n.id === e.target);
                    if (s && t) {
                        const dx = t.x - s.x, dy = t.y - s.y;
                        const dist = Math.max(1, Math.sqrt(dx * dx + dy * dy));
                        const force = (dist - 100) * 0.01;
                        const fx = (dx / dist) * force, fy = (dy / dist) * force;
                        s.vx += fx; s.vy += fy; t.vx -= fx; t.vy -= fy;
                    }
                });
                next.forEach(n => {
                    const cx = 400, cy = 300;
                    n.vx += (cx - n.x) * 0.001;
                    n.vy += (cy - n.y) * 0.001;
                    n.vx *= 0.9; n.vy *= 0.9;
                    if (!dragging.current || dragging.current.node !== n.id) {
                        n.x += n.vx; n.y += n.vy;
                    }
                });
                return next;
            });
            animRef.current = requestAnimationFrame(tick);
        };
        animRef.current = requestAnimationFrame(tick);
        return () => { running = false; cancelAnimationFrame(animRef.current); };
    }, [edges]);

    const handleWheel = (e: React.WheelEvent) => { e.preventDefault(); setZoom(z => Math.max(0.3, Math.min(3, z - e.deltaY * 0.001))); };
    const handleMouseDown = (e: React.MouseEvent, nodeId?: string) => {
        if (nodeId) { dragging.current = { node: nodeId, startX: e.clientX, startY: e.clientY }; }
        else { panning.current = { startX: e.clientX, startY: e.clientY, startPanX: pan.x, startPanY: pan.y }; }
    };
    const handleMouseMove = (e: React.MouseEvent) => {
        if (dragging.current) {
            const dx = (e.clientX - dragging.current.startX) / zoom;
            const dy = (e.clientY - dragging.current.startY) / zoom;
            setNodes(prev => prev.map(n => n.id === dragging.current!.node ? { ...n, x: n.x + dx, y: n.y + dy, vx: 0, vy: 0 } : n));
            dragging.current.startX = e.clientX; dragging.current.startY = e.clientY;
        } else if (panning.current) {
            setPan({ x: panning.current.startPanX + e.clientX - panning.current.startX, y: panning.current.startPanY + e.clientY - panning.current.startY });
        }
    };
    const handleMouseUp = () => { dragging.current = null; panning.current = null; };

    return (
        <div className="space-y-4">
            <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6 shadow-sm dark:shadow-none">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold flex items-center gap-2"><Network size={20} className="text-purple-500" /> Memory Graph (MG) Visualization</h3>
                    <div className="flex items-center gap-3">
                        <div className="flex gap-2">{Object.entries(kindColor).map(([k, c]) => (<span key={k} className="flex items-center gap-1 text-xs"><span className="w-3 h-3 rounded-full inline-block" style={{background: c}} />{k}</span>))}</div>
                        <span className="text-xs text-slate-400">Zoom: {(zoom*100).toFixed(0)}%</span>
                    </div>
                </div>
                <svg ref={svgRef} width="100%" height="500" viewBox="0 0 800 600" className="bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-700 cursor-grab active:cursor-grabbing"
                    onWheel={handleWheel} onMouseDown={e => handleMouseDown(e)} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
                    <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                        {edges.map((e, i) => {
                            const s = nodes.find(n => n.id === e.source);
                            const t = nodes.find(n => n.id === e.target);
                            if (!s || !t) return null;
                            return <line key={i} x1={s.x} y1={s.y} x2={t.x} y2={t.y} className="stroke-slate-300 dark:stroke-slate-700" strokeWidth={0.5} strokeOpacity={0.6} />;
                        })}
                        {nodes.map(n => (
                            <g key={n.id} transform={`translate(${n.x}, ${n.y})`} onMouseDown={e => { e.stopPropagation(); handleMouseDown(e, n.id); }} onClick={() => setSelectedNode(n)} className="cursor-pointer">
                                <circle r={n.id === selectedNode?.id ? 10 : 7} fill={kindColor[n.kind] || '#94a3b8'} stroke={n.id === selectedNode?.id ? '#fff' : 'none'} strokeWidth={2} opacity={0.9} />
                                <text y={-12} textAnchor="middle" className="fill-slate-500 dark:fill-slate-400" fontSize={8} opacity={0.8}>{n.label}</text>
                            </g>
                        ))}
                    </g>
                </svg>
                {selectedNode && (
                    <div className="mt-3 p-3 bg-slate-100 dark:bg-slate-800 rounded-lg flex items-center justify-between">
                        <div><span className="font-semibold">{selectedNode.label}</span> <span className="text-xs text-slate-400 ml-2">({selectedNode.kind})</span></div>
                        <div className="text-xs text-slate-400">Edges: {edges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id).length}</div>
                    </div>
                )}
            </div>
        </div>
    );
}

/* ── Toast Container ─────────────────────────────────────────── */
function ToastContainer({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
    return (
        <div className="fixed top-20 right-4 z-[90] space-y-2 max-w-sm">
            {toasts.map(t => (
                <div key={t.id} className={`flex items-start gap-3 p-3 rounded-lg border shadow-lg animate-slide-in ${t.severity==='high'?'bg-red-50 dark:bg-red-900/80 border-red-200 dark:border-red-700':t.severity==='medium'?'bg-yellow-50 dark:bg-yellow-900/80 border-yellow-200 dark:border-yellow-700':'bg-blue-50 dark:bg-blue-900/80 border-blue-200 dark:border-blue-700'}`}>
                    <AlertCircle size={16} className={`mt-0.5 flex-shrink-0 ${t.severity==='high'?'text-red-500':t.severity==='medium'?'text-yellow-500':'text-blue-500'}`} />
                    <div className="flex-1 text-sm">{t.message}</div>
                    <button onClick={() => onDismiss(t.id)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 flex-shrink-0"><X size={14}/></button>
                </div>
            ))}
        </div>
    );
}

/* ── Main App ────────────────────────────────────────────────── */
export function App() {
    const [episodes, setEpisodes] = useState<DecisionEpisode[]>([]);
    const [drifts, setDrifts] = useState<DriftEvent[]>([]);
    const [metrics, setMetrics] = useState<AgentMetrics[]>([]);
    const [selectedView, setSelectedView] = useState<ViewType>('overview');
    const [autoRefresh, setAutoRefresh] = useState(true);
    const [lastUpdate, setLastUpdate] = useState('');
    const [darkMode, setDarkMode] = useState(true);
    const [toasts, setToasts] = useState<Toast[]>([]);
    const prevDriftCount = useRef(0);

    const addToast = useCallback((message: string, severity: Toast['severity']) => {
        const id = Math.random().toString(36).slice(2);
        setToasts(prev => [...prev.slice(-4), { id, message, severity, ts: Date.now() }]);
        setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 6000);
    }, []);

    const loadData = useCallback(() => {
        const newEpisodes = generateMockEpisodes(100);
        const newDrifts = generateMockDrifts(100);
        setEpisodes(newEpisodes);
        setDrifts(newDrifts);
        setMetrics(generateAgentMetrics());
        setLastUpdate(new Date().toLocaleTimeString());
        const highDrifts = newDrifts.filter(d => d.severity === 'high');
        if (highDrifts.length > prevDriftCount.current) {
            const newCount = highDrifts.length - prevDriftCount.current;
            addToast(`${newCount} new high-severity drift event${newCount > 1 ? 's' : ''} detected!`, 'high');
        }
        prevDriftCount.current = highDrifts.length;
    }, [addToast]);

    useEffect(() => { loadData(); if (autoRefresh) { const id=setInterval(loadData,5000); return ()=>clearInterval(id); } }, [autoRefresh, loadData]);

    useEffect(() => {
        if (darkMode) document.documentElement.classList.add('dark');
        else document.documentElement.classList.remove('dark');
    }, [darkMode]);

    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement || e.target instanceof HTMLTextAreaElement) return;
            const views: ViewType[] = ['overview','episodes','drift','iris','coherence','graph','export'];
            if (e.key >= '1' && e.key <= '7') setSelectedView(views[parseInt(e.key)-1]);
            if (e.key === 'r' || e.key === 'R') loadData();
            if (e.key === 't' || e.key === 'T') setDarkMode(d => !d);
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [loadData]);

    const successRate = episodes.length > 0 ? ((episodes.filter(e => e.status === 'success').length / episodes.length) * 100).toFixed(1) : '0';
    const avgLatency = episodes.length > 0 ? (episodes.reduce((s, e) => s + e.actualDuration, 0) / episodes.length).toFixed(0) : '0';
    const systemHealth = useMemo(() => {
        if (!episodes.length) return 100;
        const sr = episodes.filter(e => e.status === 'success').length / episodes.length;
        return Math.max(0, Math.min(100, sr * 100 - drifts.filter(d => d.severity === 'high').length * 5));
    }, [episodes, drifts]);
    const metricsOverTime = useMemo(() => [...episodes].sort((a, b) => a.timestamp - b.timestamp).slice(-30).map(ep => ({ time: new Date(ep.timestamp).toLocaleTimeString(), duration: Math.round(ep.actualDuration), deadline: Math.round(ep.deadline) })), [episodes]);
    const statusDist = useMemo(() => [{ name: 'Success', value: episodes.filter(e => e.status === 'success').length }, { name: 'Timeout', value: episodes.filter(e => e.status === 'timeout').length }, { name: 'Degraded', value: episodes.filter(e => e.status === 'degraded').length }, { name: 'Failed', value: episodes.filter(e => e.status === 'failed').length }], [episodes]);
    const driftDist = useMemo(() => drifts.reduce((acc, d) => { const ex = acc.find(x => x.name === d.type); if (ex) ex.value++; else acc.push({ name: d.type, value: 1 }); return acc; }, [] as Array<{ name: string; value: number }>), [drifts]);
    const radarData = useMemo(() => metrics.map(m => ({ agent: m.agentName.replace('Agent ', ''), success: m.successRate, freshness: m.averageFreshness, latency: 100 - (m.avgLatency / 5) })), [metrics]);
    const COLORS = ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
    const currentTT = darkMode ? ttStyle : ttStyleLight;

    const viewLabels: Record<ViewType, string> = { overview: 'Overview', episodes: 'Episodes', drift: 'Drift', iris: 'IRIS', coherence: 'Coherence', graph: 'Graph', export: 'Export' };

    return (
        <div className={`min-h-screen transition-colors duration-200 ${darkMode ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
            <ToastContainer toasts={toasts} onDismiss={id => setToasts(prev => prev.filter(t => t.id !== id))} />
            <header className={`border-b sticky top-0 z-50 ${darkMode ? 'border-slate-800 bg-slate-900' : 'border-slate-200 bg-white shadow-sm'}`}>
                <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between flex-wrap gap-3">
                    <div className="flex items-center gap-3">
                        <div className="text-2xl font-bold text-blue-500">{'\u03A3'} OVERWATCH</div>
                        <div className="text-sm text-slate-400">Control Plane Dashboard</div>
                    </div>
                    <div className="flex items-center gap-4">
                        <button onClick={() => setDarkMode(d => !d)} className={`p-2 rounded-lg border transition-colors ${darkMode ? 'border-slate-700 hover:bg-slate-800' : 'border-slate-200 hover:bg-slate-100'}`} title="Toggle theme (T)">
                            {darkMode ? <Sun size={16} className="text-yellow-400" /> : <Moon size={16} className="text-slate-600" />}
                        </button>
                        <label className="flex items-center gap-2 text-sm cursor-pointer">
                            <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} className="rounded accent-blue-500" />
                            Auto-Refresh
                        </label>
                        <button onClick={loadData} className={`text-xs hover:text-blue-500 transition-colors ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>{'\u21BB'} Refresh</button>
                        <div className="text-xs text-slate-500">Updated: {lastUpdate}</div>
                    </div>
                </div>
            </header>

            <nav className={`border-b ${darkMode ? 'border-slate-800 bg-slate-900' : 'border-slate-200 bg-white'}`}>
                <div className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto">
                    {(['overview','episodes','drift','iris','coherence','graph','export'] as ViewType[]).map((view, i) => (
                        <button key={view} onClick={() => setSelectedView(view)}
                            className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 whitespace-nowrap ${selectedView === view ? 'border-blue-500 text-blue-500' : `border-transparent ${darkMode ? 'text-slate-400 hover:text-slate-300' : 'text-slate-500 hover:text-slate-700'}`}`}>
                            <span className="text-xs text-slate-500 mr-1">{i + 1}</span>{viewLabels[view]}
                        </button>
                    ))}
                </div>
            </nav>

            <main className="max-w-7xl mx-auto p-6">
                {selectedView === 'overview' && (
                    <div className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                            <KPICard icon={<TrendingUp size={20} />} label="Success Rate" value={`${successRate}%`} trend="+2.5% from baseline" trendUp={true} />
                            <KPICard icon={<Clock size={20} />} label="Avg Latency" value={`${avgLatency}ms`} trend="-5% improvement" trendUp={true} />
                            <KPICard icon={<Zap size={20} />} label="Drift Events" value={drifts.length.toString()} trend={`${drifts.filter(d => d.severity === 'high').length} high severity`} trendUp={false} />
                            <KPICard icon={<Activity size={20} />} label="Active Agents" value={metrics.length.toString()} trend="All operational" trendUp={true} />
                            <div className={`rounded-lg border p-4 flex flex-col items-center justify-center transition-colors shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800 hover:border-slate-700 shadow-none' : 'bg-white border-slate-200 hover:border-slate-300'}`}>
                                <div className="text-slate-400 text-sm mb-1">System Health</div>
                                <HealthGauge value={systemHealth} />
                            </div>
                        </div>
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div className={`rounded-lg border p-6 shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800 shadow-none' : 'bg-white border-slate-200'}`}>
                                <h3 className="text-lg font-semibold mb-4">Deadline vs Actual Duration</h3>
                                <ResponsiveContainer width="100%" height={300}>
                                    <AreaChart data={metricsOverTime}>
                                        <defs>
                                            <linearGradient id="gDL" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3} /><stop offset="95%" stopColor="#60a5fa" stopOpacity={0} /></linearGradient>
                                            <linearGradient id="gDR" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} /><stop offset="95%" stopColor="#ef4444" stopOpacity={0} /></linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" stroke={darkMode ? '#334155' : '#e2e8f0'} />
                                        <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                                        <YAxis stroke="#64748b" />
                                        <Tooltip contentStyle={currentTT} />
                                        <Legend />
                                        <Area type="monotone" dataKey="deadline" stroke="#60a5fa" fill="url(#gDL)" name="Deadline" />
                                        <Area type="monotone" dataKey="duration" stroke="#ef4444" fill="url(#gDR)" name="Actual" />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                            <div className={`rounded-lg border p-6 shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800 shadow-none' : 'bg-white border-slate-200'}`}>
                                <h3 className="text-lg font-semibold mb-4">Decision Status Distribution</h3>
                                <ResponsiveContainer width="100%" height={300}>
                                    <PieChart>
                                        <Pie data={statusDist} cx="50%" cy="50%" outerRadius={90} innerRadius={50} dataKey="value" label={({ name, value }) => `${name}: ${value}`} paddingAngle={2}>
                                            {statusDist.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
                                        </Pie>
                                        <Tooltip contentStyle={currentTT} />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                            <div className={`rounded-lg border p-6 shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800 shadow-none' : 'bg-white border-slate-200'}`}>
                                <h3 className="text-lg font-semibold mb-4">Agent Comparison Radar</h3>
                                <ResponsiveContainer width="100%" height={300}>
                                    <RadarChart data={radarData}>
                                        <PolarGrid stroke={darkMode ? '#334155' : '#e2e8f0'} />
                                        <PolarAngleAxis dataKey="agent" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                                        <PolarRadiusAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                                        <Radar name="Success %" dataKey="success" stroke="#10b981" fill="#10b981" fillOpacity={0.2} />
                                        <Radar name="Freshness %" dataKey="freshness" stroke="#60a5fa" fill="#60a5fa" fillOpacity={0.2} />
                                        <Tooltip contentStyle={currentTT} /><Legend />
                                    </RadarChart>
                                </ResponsiveContainer>
                            </div>
                            <div className={`rounded-lg border p-6 shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800 shadow-none' : 'bg-white border-slate-200'}`}>
                                <h3 className="text-lg font-semibold mb-4">Agent Performance</h3>
                                <ResponsiveContainer width="100%" height={300}>
                                    <BarChart data={metrics}>
                                        <CartesianGrid strokeDasharray="3 3" stroke={darkMode ? '#334155' : '#e2e8f0'} />
                                        <XAxis dataKey="agentName" stroke="#64748b" tick={{ fontSize: 11 }} />
                                        <YAxis stroke="#64748b" />
                                        <Tooltip contentStyle={currentTT} /><Legend />
                                        <Bar dataKey="successRate" fill="#10b981" name="Success %" radius={[4, 4, 0, 0]} />
                                        <Bar dataKey="avgLatency" fill="#f59e0b" name="Latency (ms)" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                            <div className={`rounded-lg border p-6 lg:col-span-2 shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800 shadow-none' : 'bg-white border-slate-200'}`}>
                                <h3 className="text-lg font-semibold mb-4">Drift Events by Type</h3>
                                <ResponsiveContainer width="100%" height={280}>
                                    <BarChart data={driftDist} layout="vertical">
                                        <CartesianGrid strokeDasharray="3 3" stroke={darkMode ? '#334155' : '#e2e8f0'} />
                                        <XAxis type="number" stroke="#64748b" />
                                        <YAxis type="category" dataKey="name" stroke="#64748b" width={80} />
                                        <Tooltip contentStyle={currentTT} />
                                        <Bar dataKey="value" fill="#a855f7" name="Count" radius={[0, 4, 4, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                )}
                {selectedView === 'episodes' && <EpisodesView episodes={episodes} />}
                {selectedView === 'drift' && <DriftView drifts={drifts} />}
                {selectedView === 'iris' && <IrisPanel />}
                {selectedView === 'coherence' && <CoherencePanel />}
                {selectedView === 'graph' && <MemoryGraphView />}
                {selectedView === 'export' && <ExportView episodes={episodes} drifts={drifts} metrics={metrics} />}
            </main>

            <div className={`fixed bottom-4 right-4 text-xs bg-opacity-80 px-3 py-1.5 rounded border ${darkMode ? 'text-slate-600 bg-slate-900/80 border-slate-800' : 'text-slate-400 bg-white/80 border-slate-200'}`}>
                1-7 views {'\u00B7'} R refresh {'\u00B7'} T theme
            </div>
        </div>
    );
                                                                                            }
