/* Credibility Engine Demo — Dashboard Application */

(function () {
  'use strict';

  /* ── Data Mode: "API" fetches from /api/*, "MOCK" uses local JSON ── */
  var DATA_MODE = "MOCK";

  /* ── Tenant + Role state ── */
  var currentTenant = "tenant-alpha";
  var currentRole = "exec";

  function apiBase() {
    return "/api/" + currentTenant + "/credibility";
  }

  function apiHeaders() {
    return {
      "X-Role": currentRole,
      "X-User": "demo"
    };
  }

  var API_MAP_FN = {
    credibility_snapshot: function () { return apiBase() + "/snapshot"; },
    claims_tier0: function () { return apiBase() + "/claims/tier0"; },
    drift_events_24h: function () { return apiBase() + "/drift/24h"; },
    correlation_map: function () { return apiBase() + "/correlation"; },
    ttl_timeline: function () { return null; },
    sync_integrity: function () { return apiBase() + "/sync"; },
    credibility_packet_example: function () { return apiBase() + "/snapshot"; }
  };

  const DATA = {};

  const FILES = [
    'credibility_snapshot',
    'claims_tier0',
    'drift_events_24h',
    'correlation_map',
    'ttl_timeline',
    'sync_integrity',
    'credibility_packet_example'
  ];

  /* ── Tenant/Role initialization ── */

  function initControls() {
    if (DATA_MODE !== "API") return;

    var controlsEl = document.getElementById('header-controls');
    controlsEl.style.display = 'flex';

    var tenantSelect = document.getElementById('tenant-select');
    var roleSelect = document.getElementById('role-select');

    // Fetch tenant list
    fetch("/api/tenants")
      .then(function (r) { return r.json(); })
      .then(function (tenants) {
        tenantSelect.innerHTML = tenants.map(function (t) {
          var sel = t.tenant_id === currentTenant ? ' selected' : '';
          return '<option value="' + t.tenant_id + '"' + sel + '>' +
            t.display_name + ' (' + t.tenant_id + ')</option>';
        }).join('');
      })
      .catch(function () {
        tenantSelect.innerHTML = '<option value="tenant-alpha">tenant-alpha</option>';
      });

    tenantSelect.addEventListener('change', function () {
      currentTenant = this.value;
      loadAll();
    });

    roleSelect.value = currentRole;
    roleSelect.addEventListener('change', function () {
      currentRole = this.value;
    });
  }

  /* ── Data loading ── */

  async function loadAll() {
    var results;
    if (DATA_MODE === "API") {
      results = await Promise.all(
        FILES.map(function (f) {
          var urlFn = API_MAP_FN[f];
          var url = urlFn ? urlFn() : null;
          if (!url) return fetch(f + '.json').then(function (r) { if (!r.ok) throw new Error(f); return r.json(); });
          return fetch(url, { headers: apiHeaders() }).then(function (r) { if (!r.ok) throw new Error(f); return r.json(); });
        })
      );
    } else {
      results = await Promise.all(
        FILES.map(function (f) {
          return fetch(f + '.json').then(function (r) { if (!r.ok) throw new Error(f); return r.json(); });
        })
      );
    }
    FILES.forEach((f, i) => { DATA[f] = results[i]; });
    render();
  }

  /* ── Render orchestrator ── */

  function render() {
    renderHeader();
    renderIndex();
    renderClaims();
    renderDrift();
    renderCorrelation();
    renderTTL();
    renderSync();
    bindPacketButton();
  }

  /* ── Header ── */

  function renderHeader() {
    const snap = DATA.credibility_snapshot;
    document.getElementById('current-tenant').textContent =
      snap.tenant_id || currentTenant;
    document.getElementById('last-updated').textContent =
      new Date(snap.last_updated).toLocaleString();
    document.getElementById('total-nodes').textContent =
      snap.total_nodes.toLocaleString();
    document.getElementById('total-regions').textContent = snap.regions;
    // Policy hash (v0.9.0)
    var policyEl = document.getElementById('policy-hash');
    if (policyEl && snap.policy_hash) {
      policyEl.textContent = snap.policy_hash.substring(0, 12) + '…';
      policyEl.title = snap.policy_hash;
    }
  }

  /* ── Credibility Index ── */

  function renderIndex() {
    const snap = DATA.credibility_snapshot;

    const scoreEl = document.getElementById('index-score');
    scoreEl.textContent = snap.index_score;
    scoreEl.style.color = bandColor(snap.index_score);

    const bandEl = document.getElementById('index-band');
    bandEl.textContent = snap.index_band;
    bandEl.className = 'badge badge-' + bandClass(snap.index_score);

    // Trend
    const trendEl = document.getElementById('index-trend');
    trendEl.innerHTML = snap.trend_points.map((p, i) => {
      const cls = i === snap.trend_points.length - 1 ? 'trend-point current' : 'trend-point';
      return '<span class="' + cls + '">' + snap.trend_labels[i] + ' ' + p + '</span>';
    }).join('');

    // Components
    const comp = snap.components;
    const compEl = document.getElementById('index-components');
    const entries = [
      ['Integrity', comp.tier_weighted_integrity],
      ['Drift', comp.drift_penalty],
      ['Correlation', comp.correlation_risk],
      ['Quorum', comp.quorum_margin],
      ['TTL', comp.ttl_expiration],
      ['Confirmation', comp.confirmation_bonus]
    ];
    compEl.innerHTML = entries.map(function (e) {
      var cls = e[1] >= 0 ? 'positive' : 'negative';
      var sign = e[1] >= 0 ? '+' : '';
      return '<span class="component-chip ' + cls + '">' + e[0] + ' ' + sign + e[1] + '</span>';
    }).join('');

    // Bands
    const bandsEl = document.getElementById('index-bands');
    bandsEl.innerHTML = snap.bands.map(function (b) {
      var active = snap.index_band === b.label;
      var color = bandColorForLabel(b.label);
      return '<div class="band-row' + (active ? ' active' : '') + '">' +
        '<span class="band-indicator" style="background:' + color + '"></span>' +
        '<span class="band-range">' + b.range + '</span>' +
        '<span>' + b.label + '</span>' +
        '</div>';
    }).join('');
  }

  /* ── Claims ── */

  function renderClaims() {
    const data = DATA.claims_tier0;
    document.getElementById('claims-count').textContent =
      data.claims.length + ' of ' + data.total_count;

    var html = '<table><thead><tr>' +
      '<th>ID</th><th>Status</th><th>Confidence</th>' +
      '<th>Quorum (K/N)</th><th>Margin</th><th>TTL</th>' +
      '<th>Corr Groups</th><th>OOB</th><th>Region</th>' +
      '</tr></thead><tbody>';

    data.claims.forEach(function (c) {
      var statusCls = c.status.toLowerCase();
      var marginCls = '';
      if (c.margin <= 1) marginCls = ' class="margin-critical"';
      else if (c.margin <= 2) marginCls = '';

      var confText = c.confidence !== null ? c.confidence.toFixed(2) : '—';
      var ttlText = c.ttl_remaining_minutes > 0
        ? c.ttl_remaining_minutes + 'min'
        : '<span style="color:var(--red);font-weight:600">EXPIRED</span>';

      var oobText = c.out_of_band_present
        ? '<span style="color:var(--green)">Yes</span>'
        : '<span style="color:var(--red)">No</span>';

      var corrText = c.correlation_groups_actual + '/' + c.correlation_groups_required;
      if (c.correlation_groups_actual < c.correlation_groups_required) {
        corrText = '<span style="color:var(--red);font-weight:600">' + corrText + '</span>';
      }

      html += '<tr>' +
        '<td><span class="status-dot ' + statusCls + '"></span>' + c.claim_id + '</td>' +
        '<td>' + c.status + '</td>' +
        '<td>' + confText + '</td>' +
        '<td>' + c.k_required + '/' + c.n_total + '</td>' +
        '<td' + marginCls + '>' + c.margin + '</td>' +
        '<td>' + ttlText + '</td>' +
        '<td>' + corrText + '</td>' +
        '<td>' + oobText + '</td>' +
        '<td>' + c.region + '</td>' +
        '</tr>';
    });

    html += '</tbody></table>';
    document.getElementById('claims-table').innerHTML = html;
  }

  /* ── Drift ── */

  function renderDrift() {
    var d = DATA.drift_events_24h;
    document.getElementById('drift-total').textContent = d.total_count + ' events';

    // Severity cards
    var sev = d.by_severity;
    document.getElementById('drift-severity').innerHTML =
      sevCard('low', sev.low) +
      sevCard('medium', sev.medium) +
      sevCard('high', sev.high) +
      sevCard('critical', sev.critical);

    // Category bars
    var cat = d.by_category;
    var maxCat = Math.max.apply(null, Object.values(cat));
    var catEl = document.getElementById('drift-categories');
    var catNames = {
      timing_entropy: 'Timing Entropy',
      correlation_drift: 'Correlation Drift',
      confidence_volatility: 'Confidence Volatility',
      ttl_compression: 'TTL Compression',
      external_mismatch: 'External Mismatch'
    };

    catEl.innerHTML = Object.keys(cat).map(function (k) {
      var pct = (cat[k] / maxCat * 100).toFixed(0);
      return '<div class="category-row">' +
        '<span class="category-name">' + catNames[k] + '</span>' +
        '<div class="category-bar-container">' +
        '<div class="category-bar" style="width:' + pct + '%"></div>' +
        '</div>' +
        '<span class="category-count">' + cat[k] + '</span>' +
        '</div>';
    }).join('');

    // Fingerprints
    var fpEl = document.getElementById('drift-fingerprints');
    fpEl.innerHTML = '<h3>Top Fingerprints</h3>' +
      d.top_fingerprints.map(function (fp) {
        var sevColor = fp.severity === 'high' || fp.severity === 'critical'
          ? 'var(--red)' : fp.severity === 'medium' ? 'var(--yellow)' : 'var(--text-muted)';
        return '<div class="fingerprint-item">' +
          '<span class="fp-desc">' +
          '<span style="color:' + sevColor + '">' + fp.fingerprint + '</span> — ' +
          fp.description + '</span>' +
          '<span class="fp-count">' + fp.recurrence_count + 'x</span>' +
          '</div>';
      }).join('');
  }

  function sevCard(level, count) {
    return '<div class="severity-card sev-' + level + '">' +
      '<span class="sev-count">' + count + '</span>' +
      '<span class="sev-label">' + level + '</span>' +
      '</div>';
  }

  /* ── Correlation ── */

  function renderCorrelation() {
    var data = DATA.correlation_map;
    var el = document.getElementById('correlation-clusters');

    el.innerHTML = data.clusters.map(function (c) {
      var cls = c.coefficient > data.thresholds.critical_min ? 'critical'
        : c.coefficient > data.thresholds.ok_max ? 'review' : 'ok';

      return '<div class="cluster-card ' + cls + '">' +
        '<div class="cluster-header">' +
        '<span class="cluster-label">' + c.label + '</span>' +
        '<span class="cluster-coeff ' + cls + '">' + c.coefficient.toFixed(2) + '</span>' +
        '</div>' +
        '<div class="cluster-meta">' +
        c.sources.length + ' sources / ' +
        c.claims_affected + ' claims / ' +
        c.regions.join(', ') +
        '</div>' +
        '</div>';
    }).join('');
  }

  /* ── TTL ── */

  function renderTTL() {
    var data = DATA.ttl_timeline;
    document.getElementById('ttl-expiring').textContent =
      data.expiring_within_window + ' in 4h';

    // Clustering alert
    var alertEl = document.getElementById('ttl-alert');
    if (data.clustering_warning) {
      alertEl.textContent = 'Clustering detected: ' + data.clustering_description;
      alertEl.classList.add('visible');
    }

    // Buckets with tier breakdown
    var maxBucket = Math.max.apply(null, data.upcoming_expirations.map(function (b) { return b.count; }));
    var bucketsEl = document.getElementById('ttl-buckets');

    bucketsEl.innerHTML = data.upcoming_expirations.map(function (b) {
      var tiers = b.by_tier;
      var total = b.count;
      var t0pct = (tiers['0'] / total * 100).toFixed(1);
      var t1pct = (tiers['1'] / total * 100).toFixed(1);
      var t2pct = (tiers['2'] / total * 100).toFixed(1);
      var t3pct = (tiers['3'] / total * 100).toFixed(1);
      var barWidth = (total / maxBucket * 100).toFixed(0);

      return '<div class="ttl-bucket">' +
        '<span class="bucket-label">' + b.bucket + '</span>' +
        '<div class="bucket-bar-container">' +
        '<div class="bucket-tiers" style="width:' + barWidth + '%">' +
        '<div class="bucket-tier tier-0" style="width:' + t0pct + '%"></div>' +
        '<div class="bucket-tier tier-1" style="width:' + t1pct + '%"></div>' +
        '<div class="bucket-tier tier-2" style="width:' + t2pct + '%"></div>' +
        '<div class="bucket-tier tier-3" style="width:' + t3pct + '%"></div>' +
        '</div>' +
        '</div>' +
        '<span class="bucket-count">' + total + '</span>' +
        '</div>';
    }).join('');

    // Tier 0 expirations
    var tier0El = document.getElementById('ttl-tier0');
    if (data.tier_0_expirations.length > 0) {
      tier0El.innerHTML = '<h3>Tier 0 Expirations</h3>' +
        data.tier_0_expirations.map(function (t) {
          var timeCls = t.ttl_remaining_minutes <= 0 ? 'expired'
            : t.ttl_remaining_minutes <= 60 ? 'warning' : '';
          var timeText = t.ttl_remaining_minutes <= 0 ? 'EXPIRED'
            : t.ttl_remaining_minutes + 'min';

          return '<div class="tier0-expiry">' +
            '<span class="tier0-claim">' + t.claim_id + ' / ' + t.evidence_id +
            ' (' + t.region + ')</span>' +
            '<span class="tier0-time ' + timeCls + '">' + timeText + '</span>' +
            '</div>';
        }).join('');
    }
  }

  /* ── Sync ── */

  function renderSync() {
    var data = DATA.sync_integrity;
    var el = document.getElementById('sync-regions');

    el.innerHTML = data.regions.map(function (r) {
      var cls = r.status.toLowerCase();
      return '<div class="sync-region ' + cls + '">' +
        '<div class="sync-region-header">' +
        '<span class="sync-region-name">' + r.region + '</span>' +
        '<span class="sync-status ' + cls + '">' + r.status + '</span>' +
        '</div>' +
        '<div class="sync-metrics">' +
        '<span>Skew: ' + r.time_skew_ms + 'ms</span>' +
        '<span>Lag: ' + r.watermark_lag_s + 's</span>' +
        '<span>Nodes: ' + r.sync_nodes_healthy + '/' + r.sync_nodes + '</span>' +
        '<span>Beacons: ' + r.beacons_healthy + '/' + r.beacons + '</span>' +
        (r.replay_flags_count > 0
          ? '<span style="color:var(--yellow)">Replays: ' + r.replay_flags_count + '</span>'
          : '') +
        '</div>' +
        (r.warning_detail
          ? '<div style="font-size:0.7rem;color:var(--yellow);margin-top:0.25rem">' +
            r.warning_detail + '</div>'
          : '') +
        '</div>';
    }).join('');

    // Federation
    var fed = data.federation;
    var fedEl = document.getElementById('sync-federation');
    fedEl.innerHTML =
      '<div class="sync-federation-header">Beacon Federation</div>' +
      '<span style="font-family:var(--font-mono);font-size:0.75rem">' +
      'Cross-region skew: ' + fed.cross_region_skew_ms + 'ms / ' +
      fed.max_acceptable_skew_ms + 'ms max — ' +
      '<span style="color:' + (fed.status === 'OK' ? 'var(--green)' : 'var(--yellow)') + '">' +
      fed.status + '</span></span>';
  }

  /* ── Credibility Packet ── */

  function bindPacketButton() {
    var genBtn = document.getElementById('btn-generate-packet');
    var sealBtn = document.getElementById('btn-seal-packet');
    var preview = document.getElementById('packet-preview');
    var statusEl = document.getElementById('packet-status');

    // Generate
    genBtn.onclick = function () {
      statusEl.style.display = 'none';
      if (DATA_MODE === "API") {
        fetch(apiBase() + "/packet/generate", {
          method: "POST",
          headers: apiHeaders()
        })
          .then(function (r) { return r.json(); })
          .then(function (pkt) {
            DATA.credibility_packet_example = pkt;
            renderPacketPreview(pkt, preview);
            statusEl.textContent = 'Packet generated (unsealed).';
            statusEl.className = 'packet-status info';
            statusEl.style.display = 'block';
          })
          .catch(function (err) {
            statusEl.textContent = 'Generate failed: ' + err.message;
            statusEl.className = 'packet-status error';
            statusEl.style.display = 'block';
          });
      } else {
        renderPacketPreview(DATA.credibility_packet_example, preview);
      }
    };

    // Seal
    sealBtn.onclick = function () {
      statusEl.style.display = 'none';
      if (DATA_MODE !== "API") {
        statusEl.textContent = 'Seal requires API mode.';
        statusEl.className = 'packet-status error';
        statusEl.style.display = 'block';
        return;
      }
      fetch(apiBase() + "/packet/seal", {
        method: "POST",
        headers: apiHeaders()
      })
        .then(function (r) {
          if (r.status === 403) {
            return r.json().then(function (body) {
              throw new Error(body.detail || 'Seal requires role: coherence_steward.');
            });
          }
          if (!r.ok) throw new Error('Seal failed (' + r.status + ')');
          return r.json();
        })
        .then(function (pkt) {
          DATA.credibility_packet_example = pkt;
          renderPacketPreview(pkt, preview);
          statusEl.textContent = 'Packet sealed by ' + currentRole + '.';
          statusEl.className = 'packet-status success';
          statusEl.style.display = 'block';
        })
        .catch(function (err) {
          statusEl.textContent = err.message;
          statusEl.className = 'packet-status error';
          statusEl.style.display = 'block';
        });
    };
  }

  function renderPacketPreview(pkt, preview) {
    var sealStatus = (pkt.seal && pkt.seal.sealed) ? 'YES' : 'NO';
    var sealHash = (pkt.seal && pkt.seal.seal_hash) ? pkt.seal.seal_hash : '—';
    var prevSealHash = (pkt.seal && pkt.seal.prev_seal_hash) ? pkt.seal.prev_seal_hash : '—';
    var policyHash = (pkt.seal && pkt.seal.policy_hash) || pkt.policy_hash || '—';
    var snapshotHash = (pkt.seal && pkt.seal.snapshot_hash) ? pkt.seal.snapshot_hash : '—';

    var text = '=== CREDIBILITY PACKET ===\n' +
      'Tenant: ' + (pkt.tenant_id || '—') + '\n' +
      'ID: ' + pkt.packet_id + '\n' +
      'Generated: ' + pkt.generated_at + '\n' +
      'Sealed: ' + sealStatus + '\n' +
      'Hash: ' + sealHash + '\n\n' +

      '--- CREDIBILITY INDEX ---\n' +
      'Score: ' + pkt.credibility_index.score + ' / 100\n' +
      'Band: ' + pkt.credibility_index.band + '\n\n' +

      '--- DLR SUMMARY ---\n' +
      'ID: ' + pkt.dlr_summary.dlr_id + '\n' +
      'Title: ' + pkt.dlr_summary.title + '\n' +
      'Decided by: ' + pkt.dlr_summary.decided_by + '\n' +
      'Key Findings:\n' +
      pkt.dlr_summary.key_findings.map(function (f) { return '  - ' + f; }).join('\n') + '\n\n' +

      '--- RS SUMMARY ---\n' +
      'ID: ' + pkt.rs_summary.rs_id + '\n' +
      'Assessment: ' + pkt.rs_summary.reasoning.overall_assessment + '\n' +
      'Primary Risk: ' + pkt.rs_summary.reasoning.primary_risk + '\n' +
      'Recommendation: ' + pkt.rs_summary.reasoning.recommendation + '\n\n' +

      '--- DS SUMMARY ---\n' +
      'ID: ' + pkt.ds_summary.ds_id + '\n' +
      'Active Signals: ' + pkt.ds_summary.active_signals + '\n' +
      'Critical: ' + pkt.ds_summary.critical_signal.category +
      ' (' + pkt.ds_summary.critical_signal.source + ')\n' +
      'Claims Affected: ' + pkt.ds_summary.critical_signal.claims_affected + '\n\n' +

      '--- MG SUMMARY ---\n' +
      'ID: ' + pkt.mg_summary.mg_id + '\n' +
      'Changes (24h): ' +
      pkt.mg_summary.changes_last_24h.nodes_added + ' nodes added, ' +
      pkt.mg_summary.changes_last_24h.patches_applied + ' patches, ' +
      pkt.mg_summary.changes_last_24h.seals_created + ' seals\n\n' +

      '--- SEAL ---\n' +
      'Sealed: ' + sealStatus + '\n' +
      'Hash: ' + sealHash + '\n' +
      'Prev Seal: ' + prevSealHash + '\n' +
      'Policy Hash: ' + policyHash + '\n' +
      'Snapshot Hash: ' + snapshotHash + '\n' +
      (pkt.seal && pkt.seal.sealed_at ? 'Sealed at: ' + pkt.seal.sealed_at + '\n' : '') +
      (pkt.seal && pkt.seal.role ? 'Role: ' + pkt.seal.role + '\n' : '') +
      (pkt.seal && pkt.seal.hash_chain_length ? 'Chain length: ' + pkt.seal.hash_chain_length + '\n' : '') +
      '\n--- GUARDRAILS ---\n' +
      pkt.guardrails.description;

    preview.textContent = text;
    preview.style.display = 'block';
  }

  /* ── Helpers ── */

  function bandColor(score) {
    if (score >= 95) return 'var(--green)';
    if (score >= 85) return 'var(--yellow)';
    if (score >= 70) return 'var(--red)';
    if (score >= 50) return 'var(--red)';
    return 'var(--red)';
  }

  function bandClass(score) {
    if (score >= 95) return 'stable';
    if (score >= 85) return 'minor';
    if (score >= 70) return 'elevated';
    if (score >= 50) return 'degraded';
    return 'compromised';
  }

  function bandColorForLabel(label) {
    switch (label) {
      case 'Stable': return 'var(--green)';
      case 'Minor Drift': return 'var(--yellow)';
      case 'Elevated Risk': return '#f0883e';
      case 'Structural Degradation': return 'var(--red)';
      case 'Compromised': return '#da3633';
      default: return 'var(--text-muted)';
    }
  }

  /* ── Boot ── */
  initControls();
  loadAll();

  /* ── Auto-refresh for simulation mode ── */
  setInterval(function () {
    loadAll().catch(function () { /* ignore refresh errors */ });
  }, 2000);
})();
