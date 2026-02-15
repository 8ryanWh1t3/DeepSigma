import { useState, useMemo } from "react";

const concepts = [
  // Core Framework
  { name: "Coherence Ops", category: "Core Framework", posts: 142, repoStatus: "implemented", phase: "P0", inRepo: true, desc: "The operational framework — brand unified in P0" },
  { name: "Deep Sigma", category: "Core Framework", posts: 34, repoStatus: "implemented", phase: "P0", inRepo: true, desc: "Umbrella brand — README updated" },
  { name: "Σ OVERWATCH", category: "Core Framework", posts: 7, repoStatus: "implemented", phase: "P0", inRepo: true, desc: "Runtime engine — identity resolved in P0" },

  // PRIME Layer
  { name: "PRIME", category: "PRIME Layer", posts: 37, repoStatus: "implemented", phase: "P1", inRepo: true, desc: "Threshold Gate — prime.py + schema + tests" },
  { name: "Truth-Reasoning-Memory", category: "PRIME Layer", posts: 26, repoStatus: "implemented", phase: "P1", inRepo: true, desc: "Core invariants encoded in PRIME gate" },
  { name: "Threshold Gate", category: "PRIME Layer", posts: 25, repoStatus: "implemented", phase: "P1", inRepo: true, desc: "Gradient → decision conversion" },
  { name: "Confidence Bands", category: "PRIME Layer", posts: 1, repoStatus: "implemented", phase: "P1", inRepo: true, desc: "Part of PRIME schema spec" },
  { name: "Disconfirmers", category: "PRIME Layer", posts: 15, repoStatus: "implemented", phase: "P1", inRepo: true, desc: "Encoded in PRIME gate logic" },

  // Four Pillars
  { name: "DLR", category: "Four Pillars", posts: 121, repoStatus: "implemented", phase: "pre", inRepo: true, desc: "Decision Lineage Record — original repo pillar" },
  { name: "RS", category: "Four Pillars", posts: 59, repoStatus: "implemented", phase: "pre", inRepo: true, desc: "Reasoning Summary — original repo pillar" },
  { name: "DS", category: "Four Pillars", posts: 80, repoStatus: "implemented", phase: "pre", inRepo: true, desc: "Drift Scan — original repo pillar" },
  { name: "MG", category: "Four Pillars", posts: 80, repoStatus: "implemented", phase: "pre", inRepo: true, desc: "Memory Graph — original repo pillar" },

  // Operational Modes
  { name: "FranOPS", category: "Operational Modes", posts: 50, repoStatus: "planned", phase: "P3", inRepo: false, desc: "Franchise operations coherence mode" },
  { name: "IntelOps", category: "Operational Modes", posts: 40, repoStatus: "planned", phase: "P3", inRepo: false, desc: "Intelligence operations coherence mode" },
  { name: "ReflectionOps", category: "Operational Modes", posts: 28, repoStatus: "planned", phase: "P3", inRepo: false, desc: "Learning & improvement cycles mode" },

  // Instruments
  { name: "CTI", category: "Instruments", posts: 236, repoStatus: "partial", phase: "P4", inRepo: true, desc: "Exists in scoring internals, not exposed as named metric" },
  { name: "DAT", category: "Instruments", posts: 4, repoStatus: "planned", phase: "P4", inRepo: false, desc: "Dynamic Assertion Testing — not yet built" },
  { name: "DDR", category: "Instruments", posts: 8, repoStatus: "planned", phase: "P4", inRepo: false, desc: "Deep Dive Review tool — not yet built" },
  { name: "ITCO", category: "Instruments", posts: 4, repoStatus: "planned", phase: "P4", inRepo: false, desc: "Integrated Truth & Coherence Operations" },

  // Architecture
  { name: "IRIS", category: "Architecture", posts: 15, repoStatus: "planned", phase: "P2", inRepo: false, desc: "Operator query interface — next to build" },
  { name: "Temperature", category: "Architecture", posts: 3, repoStatus: "planned", phase: "P4", inRepo: false, desc: "System temperature regulation model" },
  { name: "AL6", category: "Architecture", posts: 1, repoStatus: "partial", phase: "P5", inRepo: true, desc: "6-dimension model — in repo, barely in content" },
  { name: "DTE", category: "Architecture", posts: 3, repoStatus: "partial", phase: "P5", inRepo: true, desc: "DTE contracts — in repo, barely in content" },
  { name: "Degrade Ladder", category: "Architecture", posts: 8, repoStatus: "partial", phase: "P5", inRepo: true, desc: "In repo, underexposed in content" },
  { name: "Policy Pack", category: "Architecture", posts: 2, repoStatus: "planned", phase: "P3", inRepo: false, desc: "Pre-configured policy bundles per mode" },
  { name: "Dimensional Resolution", category: "Architecture", posts: 4, repoStatus: "partial", phase: "pre", inRepo: true, desc: "Core principle, implicit in scoring" },

  // Metaphors
  { name: "Ferrari/Chassis", category: "Metaphors", posts: 5, repoStatus: "content-only", phase: "—", inRepo: false, desc: "Explanatory metaphor — no code analog" },
  { name: "Iceberg Model", category: "Metaphors", posts: 1, repoStatus: "content-only", phase: "—", inRepo: false, desc: "Enterprise AI stack metaphor" },
  { name: "Binary-to-Diamond", category: "Metaphors", posts: 9, repoStatus: "content-only", phase: "P1", inRepo: false, desc: "PRIME conceptual model — mermaid diagram planned" },
  { name: "MU-TH-UR", category: "Metaphors", posts: 1, repoStatus: "content-only", phase: "—", inRepo: false, desc: "Alien (1979) analogy for PRIME" },

  // Integration
  { name: "MCP Server", category: "Integration", posts: 2, repoStatus: "implemented", phase: "pre", inRepo: true, desc: "Adapter layer — built, underexposed" },
  { name: "OpenClaw", category: "Integration", posts: 0, repoStatus: "implemented", phase: "pre", inRepo: true, desc: "In repo, zero content coverage" },
  { name: "OpenTelemetry", category: "Integration", posts: 1, repoStatus: "implemented", phase: "pre", inRepo: true, desc: "In repo, almost zero content coverage" },
  { name: "RDF/Ontology", category: "Integration", posts: 97, repoStatus: "implemented", phase: "pre", inRepo: true, desc: "27-file RDF bundle with OWL/SHACL/SPARQL" },

  // Advanced
  { name: "Portfolio Mgmt", category: "Advanced", posts: 6, repoStatus: "planned", phase: "P5", inRepo: false, desc: "Cross-domain portfolio coherence" },
  { name: "Prompt Translator", category: "Advanced", posts: 1, repoStatus: "planned", phase: "P5", inRepo: false, desc: "Prompt → Coherence Ops compiler" },
  { name: "Supervisor", category: "Advanced", posts: 0, repoStatus: "implemented", phase: "pre", inRepo: true, desc: "In repo, zero content coverage" },
  { name: "Verifier Library", category: "Advanced", posts: 2, repoStatus: "implemented", phase: "pre", inRepo: true, desc: "In repo, minimal content coverage" },
  { name: "Replay Harness", category: "Advanced", posts: 5, repoStatus: "implemented", phase: "pre", inRepo: true, desc: "In repo, light content coverage" },
  { name: "Seal-Version-Patch", category: "Advanced", posts: 113, repoStatus: "implemented", phase: "pre", inRepo: true, desc: "Memory immutability pattern — deeply covered" },
];

const TOTAL_POSTS = 284;

const statusColors = {
  "implemented": "#00e5a0",
  "partial": "#ffb84d",
  "planned": "#38bdf8",
  "content-only": "#a78bfa",
};

const statusLabels = {
  "implemented": "SHIPPED",
  "partial": "PARTIAL",
  "planned": "PLANNED",
  "content-only": "NARRATIVE",
};

const categoryOrder = [
  "Core Framework", "PRIME Layer", "Four Pillars", "Operational Modes",
  "Instruments", "Architecture", "Metaphors", "Integration", "Advanced"
];

const phaseColors = {
  "pre": "#5a6d8a",
  "P0": "#ff4d6a",
  "P1": "#ffb84d",
  "P2": "#38bdf8",
  "P3": "#a78bfa",
  "P4": "#06d6a0",
  "P5": "#f472b6",
  "—": "#333",
};

export default function GapDashboard() {
  const [sortBy, setSortBy] = useState("category");
  const [filterStatus, setFilterStatus] = useState("all");
  const [hoveredConcept, setHoveredConcept] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);

  const maxPosts = Math.max(...concepts.map(c => c.posts));

  const sorted = useMemo(() => {
    let filtered = [...concepts];
    if (filterStatus !== "all") filtered = filtered.filter(c => c.repoStatus === filterStatus);
    if (selectedCategory) filtered = filtered.filter(c => c.category === selectedCategory);

    if (sortBy === "posts-desc") return filtered.sort((a, b) => b.posts - a.posts);
    if (sortBy === "posts-asc") return filtered.sort((a, b) => a.posts - b.posts);
    if (sortBy === "gap") return filtered.sort((a, b) => {
      const gapA = a.posts > 10 && !a.inRepo ? 2 : (!a.inRepo ? 1 : (a.posts < 3 && a.inRepo ? -1 : 0));
      const gapB = b.posts > 10 && !b.inRepo ? 2 : (!b.inRepo ? 1 : (b.posts < 3 && b.inRepo ? -1 : 0));
      return gapB - gapA;
    });
    return filtered;
  }, [sortBy, filterStatus, selectedCategory]);

  // Compute summary stats
  const stats = useMemo(() => {
    const shipped = concepts.filter(c => c.repoStatus === "implemented").length;
    const partial = concepts.filter(c => c.repoStatus === "partial").length;
    const planned = concepts.filter(c => c.repoStatus === "planned").length;
    const narrative = concepts.filter(c => c.repoStatus === "content-only").length;

    const highPostNoCode = concepts.filter(c => c.posts >= 10 && !c.inRepo);
    const inRepoLowContent = concepts.filter(c => c.inRepo && c.posts <= 2);
    const totalContentCoverage = concepts.reduce((s, c) => s + c.posts, 0);

    return { shipped, partial, planned, narrative, highPostNoCode, inRepoLowContent, totalContentCoverage };
  }, []);

  const getGapType = (c) => {
    if (c.posts >= 10 && !c.inRepo) return { label: "CONTENT > CODE", color: "#ff4d6a", bg: "#ff4d6a18" };
    if (c.inRepo && c.posts <= 2) return { label: "CODE > CONTENT", color: "#38bdf8", bg: "#38bdf818" };
    if (c.repoStatus === "partial") return { label: "PARTIAL GAP", color: "#ffb84d", bg: "#ffb84d18" };
    if (c.inRepo && c.posts > 2) return { label: "ALIGNED", color: "#00e5a0", bg: "#00e5a018" };
    return { label: "LOW SIGNAL", color: "#5a6d8a", bg: "#5a6d8a18" };
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#06090f",
      color: "#e2e8f0",
      fontFamily: "'Söhne', 'Helvetica Neue', sans-serif",
      padding: "32px 24px",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Instrument+Sans:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0d1420; }
        ::-webkit-scrollbar-thumb { background: #1a2740; border-radius: 3px; }
        @keyframes slideIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
      `}</style>

      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        {/* HEADER */}
        <div style={{ marginBottom: 36 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 6 }}>
            <span style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.65rem", color: "#00e5a0", letterSpacing: "0.15em", fontWeight: 500 }}>DEEP SIGMA</span>
            <span style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.55rem", color: "#5a6d8a" }}>COHERENCE OPS GAP ANALYSIS</span>
          </div>
          <h1 style={{ fontFamily: "'Instrument Sans', sans-serif", fontSize: "1.8rem", fontWeight: 700, color: "#e2e8f0", lineHeight: 1.15, letterSpacing: "-0.02em" }}>
            Content × Code<span style={{ color: "#5a6d8a" }}> — </span><span style={{ color: "#00e5a0" }}>Coverage Map</span>
          </h1>
          <p style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.72rem", color: "#5a6d8a", marginTop: 8, lineHeight: 1.6, maxWidth: 700 }}>
            284 LinkedIn posts mapped against repository implementation status across {concepts.length} framework concepts.
            Surfaces two critical gap types: narrative promises without code, and shipped code without content exposure.
          </p>
        </div>

        {/* STAT CARDS */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 10, marginBottom: 28 }}>
          {[
            { v: stats.shipped, l: "Shipped", c: "#00e5a0" },
            { v: stats.partial, l: "Partial", c: "#ffb84d" },
            { v: stats.planned, l: "Planned", c: "#38bdf8" },
            { v: stats.narrative, l: "Narrative", c: "#a78bfa" },
            { v: stats.highPostNoCode.length, l: "Content > Code", c: "#ff4d6a" },
            { v: stats.inRepoLowContent.length, l: "Code > Content", c: "#38bdf8" },
          ].map((s, i) => (
            <div key={i} style={{
              background: "#0d1420", border: `1px solid #1a2740`, borderRadius: 10,
              padding: "14px 12px", textAlign: "center",
              animation: `slideIn 0.4s ease ${i * 0.06}s both`,
            }}>
              <div style={{ fontFamily: "'DM Mono', monospace", fontSize: "1.5rem", fontWeight: 500, color: s.c }}>{s.v}</div>
              <div style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.55rem", color: "#5a6d8a", letterSpacing: "0.08em", marginTop: 3 }}>{s.l}</div>
            </div>
          ))}
        </div>

        {/* CRITICAL GAPS CALLOUT */}
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 28,
        }}>
          <div style={{ background: "#ff4d6a08", border: "1px solid #ff4d6a22", borderRadius: 10, padding: 16 }}>
            <div style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.6rem", color: "#ff4d6a", letterSpacing: "0.12em", fontWeight: 500, marginBottom: 10 }}>
              CONTENT PROMISES WITHOUT CODE
            </div>
            {stats.highPostNoCode.map(c => (
              <div key={c.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "5px 0", borderBottom: "1px solid #ff4d6a0a" }}>
                <span style={{ fontFamily: "'Instrument Sans', sans-serif", fontSize: "0.78rem", color: "#e2e8f0" }}>{c.name}</span>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.65rem", color: "#ff4d6a" }}>{c.posts} posts</span>
                  <span style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.55rem", color: "#5a6d8a", background: `${phaseColors[c.phase]}18`, padding: "2px 6px", borderRadius: 4 }}>{c.phase}</span>
                </div>
              </div>
            ))}
          </div>
          <div style={{ background: "#38bdf808", border: "1px solid #38bdf822", borderRadius: 10, padding: 16 }}>
            <div style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.6rem", color: "#38bdf8", letterSpacing: "0.12em", fontWeight: 500, marginBottom: 10 }}>
              SHIPPED CODE WITHOUT CONTENT EXPOSURE
            </div>
            {stats.inRepoLowContent.map(c => (
              <div key={c.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "5px 0", borderBottom: "1px solid #38bdf80a" }}>
                <span style={{ fontFamily: "'Instrument Sans', sans-serif", fontSize: "0.78rem", color: "#e2e8f0" }}>{c.name}</span>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.65rem", color: "#38bdf8" }}>{c.posts} posts</span>
                  <span style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.55rem", color: "#5a6d8a" }}>{c.desc.split("—")[0].trim()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CONTROLS */}
        <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 4 }}>
            {["all", "implemented", "partial", "planned", "content-only"].map(s => (
              <button key={s} onClick={() => setFilterStatus(s)} style={{
                fontFamily: "'DM Mono', monospace", fontSize: "0.62rem", fontWeight: 500,
                color: filterStatus === s ? "#e2e8f0" : "#5a6d8a",
                background: filterStatus === s ? "#1a2740" : "transparent",
                border: `1px solid ${filterStatus === s ? "#253550" : "#1a274066"}`,
                padding: "5px 10px", borderRadius: 6, cursor: "pointer",
                transition: "all 0.15s",
              }}>
                {s === "all" ? "ALL" : (statusLabels[s] || s.toUpperCase())}
              </button>
            ))}
          </div>
          <div style={{ borderLeft: "1px solid #1a2740", paddingLeft: 10, display: "flex", gap: 4 }}>
            {["category", "posts-desc", "posts-asc", "gap"].map(s => (
              <button key={s} onClick={() => setSortBy(s)} style={{
                fontFamily: "'DM Mono', monospace", fontSize: "0.62rem", fontWeight: 500,
                color: sortBy === s ? "#e2e8f0" : "#5a6d8a",
                background: sortBy === s ? "#1a2740" : "transparent",
                border: `1px solid ${sortBy === s ? "#253550" : "#1a274066"}`,
                padding: "5px 10px", borderRadius: 6, cursor: "pointer",
                transition: "all 0.15s",
              }}>
                {s === "category" ? "BY CATEGORY" : s === "posts-desc" ? "POSTS ↓" : s === "posts-asc" ? "POSTS ↑" : "BY GAP"}
              </button>
            ))}
          </div>
          {selectedCategory && (
            <button onClick={() => setSelectedCategory(null)} style={{
              fontFamily: "'DM Mono', monospace", fontSize: "0.62rem",
              color: "#ff4d6a", background: "#ff4d6a12", border: "1px solid #ff4d6a33",
              padding: "5px 10px", borderRadius: 6, cursor: "pointer",
            }}>
              ✕ {selectedCategory}
            </button>
          )}
        </div>

        {/* CATEGORY PILLS */}
        <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
          {categoryOrder.map(cat => {
            const catConcepts = concepts.filter(c => c.category === cat);
            const avg = Math.round(catConcepts.reduce((s, c) => s + c.posts, 0) / catConcepts.length);
            const shipped = catConcepts.filter(c => c.repoStatus === "implemented").length;
            return (
              <button key={cat} onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)} style={{
                fontFamily: "'DM Mono', monospace", fontSize: "0.6rem",
                color: selectedCategory === cat ? "#e2e8f0" : "#8b9cb8",
                background: selectedCategory === cat ? "#111d2e" : "#0d1420",
                border: `1px solid ${selectedCategory === cat ? "#253550" : "#1a2740"}`,
                padding: "6px 10px", borderRadius: 8, cursor: "pointer",
                display: "flex", alignItems: "center", gap: 6,
              }}>
                {cat}
                <span style={{ color: "#00e5a0", fontSize: "0.55rem" }}>{shipped}/{catConcepts.length}</span>
              </button>
            );
          })}
        </div>

        {/* MAIN TABLE */}
        <div style={{ background: "#0d1420", border: "1px solid #1a2740", borderRadius: 12, overflow: "hidden" }}>
          {/* Header row */}
          <div style={{
            display: "grid", gridTemplateColumns: "170px 60px 1fr 90px 50px 110px",
            gap: 0, padding: "10px 16px", borderBottom: "1px solid #1a2740",
            background: "#111d2e",
          }}>
            {["CONCEPT", "POSTS", "CONTENT COVERAGE", "STATUS", "PHASE", "GAP TYPE"].map(h => (
              <div key={h} style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.55rem", color: "#5a6d8a", letterSpacing: "0.1em", fontWeight: 500 }}>{h}</div>
            ))}
          </div>

          {/* Rows */}
          {sorted.map((c, i) => {
            const gap = getGapType(c);
            const barWidth = maxPosts > 0 ? (c.posts / maxPosts) * 100 : 0;
            const pct = ((c.posts / TOTAL_POSTS) * 100).toFixed(1);
            const isHovered = hoveredConcept === c.name;

            return (
              <div key={c.name}
                onMouseEnter={() => setHoveredConcept(c.name)}
                onMouseLeave={() => setHoveredConcept(null)}
                style={{
                  display: "grid", gridTemplateColumns: "170px 60px 1fr 90px 50px 110px",
                  gap: 0, padding: "10px 16px",
                  borderBottom: "1px solid #1a274044",
                  background: isHovered ? "#111d2e" : "transparent",
                  transition: "background 0.15s",
                  animation: `slideIn 0.3s ease ${i * 0.02}s both`,
                  cursor: "default",
                }}>
                {/* Name */}
                <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
                  <span style={{ fontFamily: "'Instrument Sans', sans-serif", fontSize: "0.8rem", fontWeight: 600, color: "#e2e8f0" }}>{c.name}</span>
                  {isHovered && (
                    <span style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.58rem", color: "#5a6d8a", marginTop: 2 }}>{c.desc}</span>
                  )}
                </div>

                {/* Post count */}
                <div style={{ display: "flex", alignItems: "center" }}>
                  <span style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.78rem", fontWeight: 500, color: c.posts === 0 ? "#333" : c.posts < 5 ? "#5a6d8a" : "#e2e8f0" }}>
                    {c.posts}
                  </span>
                </div>

                {/* Bar */}
                <div style={{ display: "flex", alignItems: "center", gap: 8, paddingRight: 12 }}>
                  <div style={{ flex: 1, height: 14, background: "#1a2740", borderRadius: 3, overflow: "hidden", position: "relative" }}>
                    <div style={{
                      height: "100%", width: `${barWidth}%`,
                      background: `linear-gradient(90deg, ${statusColors[c.repoStatus]}44, ${statusColors[c.repoStatus]}88)`,
                      borderRadius: 3,
                      transition: "width 0.6s ease",
                    }} />
                  </div>
                  <span style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.55rem", color: "#5a6d8a", minWidth: 32, textAlign: "right" }}>{pct}%</span>
                </div>

                {/* Status */}
                <div style={{ display: "flex", alignItems: "center" }}>
                  <span style={{
                    fontFamily: "'DM Mono', monospace", fontSize: "0.55rem", fontWeight: 500,
                    color: statusColors[c.repoStatus],
                    background: `${statusColors[c.repoStatus]}14`,
                    border: `1px solid ${statusColors[c.repoStatus]}28`,
                    padding: "2px 7px", borderRadius: 4,
                  }}>
                    {statusLabels[c.repoStatus]}
                  </span>
                </div>

                {/* Phase */}
                <div style={{ display: "flex", alignItems: "center" }}>
                  <span style={{
                    fontFamily: "'DM Mono', monospace", fontSize: "0.58rem", fontWeight: 500,
                    color: phaseColors[c.phase] || "#5a6d8a",
                  }}>{c.phase}</span>
                </div>

                {/* Gap type */}
                <div style={{ display: "flex", alignItems: "center" }}>
                  <span style={{
                    fontFamily: "'DM Mono', monospace", fontSize: "0.52rem", fontWeight: 500,
                    color: gap.color, background: gap.bg,
                    padding: "2px 7px", borderRadius: 4,
                    animation: gap.label === "CONTENT > CODE" ? "pulse 3s ease infinite" : "none",
                  }}>
                    {gap.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* PHASE LEGEND */}
        <div style={{
          display: "flex", gap: 12, justifyContent: "center", marginTop: 20, flexWrap: "wrap",
        }}>
          {[
            { p: "pre", l: "Pre-existing" },
            { p: "P0", l: "P0 Brand" },
            { p: "P1", l: "P1 PRIME" },
            { p: "P2", l: "P2 IRIS" },
            { p: "P3", l: "P3 Modes" },
            { p: "P4", l: "P4 CTI/DAT" },
            { p: "P5", l: "P5 Bridge" },
          ].map(x => (
            <div key={x.p} style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: phaseColors[x.p] }} />
              <span style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.58rem", color: "#5a6d8a" }}>{x.l}</span>
            </div>
          ))}
        </div>

        {/* FOOTER */}
        <div style={{ textAlign: "center", padding: "28px 0 0", marginTop: 24, borderTop: "1px solid #1a2740" }}>
          <div style={{ fontFamily: "'DM Mono', monospace", fontSize: "0.58rem", color: "#5a6d8a", letterSpacing: "0.12em" }}>
            DEEP SIGMA · COHERENCE OPS · GAP ANALYSIS · {TOTAL_POSTS} POSTS × {concepts.length} CONCEPTS
          </div>
        </div>
      </div>
    </div>
  );
}
