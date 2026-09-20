(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const MODE_NAMES = { baseline: 'Baseline', compensated: 'Compensated', full_control: 'Full control' };
  const MODE_NOTES = {
    baseline: 'Illustrative baseline adds a bounded concept-frequency term to the base score. This is a synthetic comparator, not a claim about any deployed model. Release checks are not applied.',
    compensated: 'A bounded rarity bonus applies only when relevance and quality meet policy thresholds. Mandatory claims remain protected. Release checks are not applied.',
    full_control: 'Selection is identical to Compensated. Evidence, review and authority checks are added as a separate simulation. HOLD does not remove a claim from review.'
  };
  const REASON_NAMES = {
    CONTRADICTION: 'A contradiction requires review', INSUFFICIENT_INDEPENDENT_SUPPORT: 'Too few declared independent supporting origins', MISSING_EVIDENCE_TYPES: 'Required evidence types are missing', MISSING_REVIEW: 'Review is missing', REVIEW_EXPIRED: 'Review has expired', REVIEW_REJECTED: 'Review was rejected', REVIEW_ROLE: 'Reviewer role is not permitted', REVIEW_VERSION: 'Review does not match the claim or policy version', MISSING_AUTHORITY: 'Authority is missing', AUTHORITY_EXPIRED: 'Authority has expired', AUTHORITY_REVOKED: 'Authority is revoked', AUTHORITY_ROLE: 'Authority role is not permitted', AUTHORITY_VERSION: 'Authority does not match the claim or policy version', AUTHORITY_USE: 'Authority does not cover the intended use', VERSION_MISMATCH: 'Evidence claim version does not match', FUTURE_EVIDENCE: 'Evidence is later than the scenario time', STALE_EVIDENCE: 'Evidence exceeds the allowed age', UNASSESSED_SUPPORT: 'Supporting evidence has not been assessed'
  };
  const ATTENTION_REASONS = {
    MANDATORY_REVIEW: 'Policy keeps this claim in the mandatory review lane.',
    DUPLICATE_REPORTS_COLLAPSED: 'Repeated copies share an originating event and do not add score.',
    NO_REPORT_OBSERVATIONS: 'No report observations are available; no rarity bonus is awarded.',
    RARITY_BONUS_APPLIED: 'The claim meets relevance and quality thresholds and receives a bounded rarity bonus.',
    RARITY_THRESHOLD_NOT_MET: 'Relevance or quality is below the policy threshold; no rarity bonus is awarded.',
    UNASSESSED_CONTRADICTION: 'An unassessed contradiction is preserved for review and causes a simulated hold.'
  };
  const localJS = window.location.protocol === 'file:';
  const state = { payload: null, result: null, mode: 'baseline', selected: null, request: 0, busy: false };

  function el(tag, className, content) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined && content !== null) node.textContent = String(content);
    return node;
  }
  function empty(node) { node.replaceChildren(); }
  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function badge(item) {
    return el('span', 'gate-badge ' + (item.gate.status === 'HOLD' ? 'hold' : 'eligible'), item.gate.status === 'HOLD' ? 'HOLD' : 'Simulated eligible');
  }
  function setBusy(value) {
    state.busy = value;
    ['import-button', 'reset-button', 'budget'].forEach(id => { $(id).disabled = value; });
    $('export-button').disabled = value || !state.result;
    $('review-panel').setAttribute('aria-busy', String(value));
  }
  function fail(error) {
    $('error').hidden = false;
    $('error').textContent = (state.result ? 'Scenario not changed. ' : 'Evaluation unavailable. ') + (error && error.message ? error.message : String(error));
    $('status').textContent = state.result ? 'The last successful evaluation remains displayed.' : 'No evaluation is displayed. Correct the input or evaluator error and retry.';
    if (state.payload) $('budget').value = state.payload.review_budget;
  }
  async function run(payload, statusText) {
    const request = ++state.request;
    setBusy(true);
    $('error').hidden = true;
    $('status').textContent = 'Evaluating the scenario…';
    try {
      let result;
      if (localJS) {
        if (!globalThis.DeepSigmaZipf || typeof globalThis.DeepSigmaZipf.evaluate !== 'function') throw new Error('JavaScript engine unavailable. Keep engine.js beside index.html.');
        result = globalThis.DeepSigmaZipf.evaluate(payload);
      } else {
        let response;
        try { response = await fetch('/api/evaluate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), cache: 'no-store' }); }
        catch (_) { throw new Error('The local Python evaluator could not be reached. Restart the server and retry. No JavaScript fallback was used.'); }
        let body;
        try { body = await response.json(); }
        catch (_) { throw new Error('The Python evaluator returned an unreadable response. No JavaScript fallback was used.'); }
        if (!response.ok) throw new Error(typeof body.error === 'string' ? body.error : typeof body.message === 'string' ? body.message : 'Python evaluation failed (HTTP ' + response.status + ').');
        result = body;
      }
      if (request !== state.request) return;
      state.payload = clone(payload);
      state.result = result;
      if (!state.selected || !result.items.some(item => item.id === state.selected)) state.selected = result.modes[state.mode].selected_ids[0] || result.items[0]?.id || null;
      $('budget').value = payload.review_budget;
      $('as-of').value = payload.as_of;
      render();
      $('status').textContent = statusText + ' · Policy ' + result.policy.id + ' v' + result.policy.version + ' · Explicit scenario time; no clock-dependent scoring.';
    } catch (error) { if (request === state.request) fail(error); }
    finally { if (request === state.request) setBusy(false); }
  }
  function selectClaim(id) { state.selected = id; renderQueue(); renderMandatory(); renderAllClaims(); renderDetail(); }
  function itemById(id) { return state.result.items.find(item => item.id === id); }
  function score(item) { return state.mode === 'baseline' ? item.baseline_score : item.compensated_score; }
  function render() { renderDiagnostics(); renderMetrics(); renderMode(); renderMandatory(); renderQueue(); renderAllClaims(); renderDetail(); }
  function renderDiagnostics() {
    const d = state.result.diagnostics;
    const stats = [
      [d.claims, 'Claims in scenario', d.mandatory_count + ' in the protected lane'],
      [d.report_count, 'Raw reports', 'Copies remain visible in provenance'],
      [d.unique_events, 'Unique report events', 'Declared origin + event identity'],
      [d.duplicate_reports, 'Duplicate reports collapsed', 'Copies cannot increase either score']
    ];
    empty($('diagnostics'));
    stats.forEach(([value, label, note]) => {
      const card = el('div', 'stat');
      card.append(el('div', 'stat-value', Number(value).toLocaleString('en-US')), el('div', 'stat-label', label), el('div', 'stat-note', note));
      $('diagnostics').append(card);
    });
  }
  const LABELS = ['rare_relevant_claim_ids', 'irrelevant_claim_ids', 'mandatory_claim_ids', 'gap_claim_ids'];
  function labelMetrics() {
    const labels = state.payload.labels;
    if (!labels || !LABELS.some(key => Array.isArray(labels[key]))) return null;
    const known = new Set(state.result.items.map(item => item.id));
    return Object.keys(MODE_NAMES).map(mode => {
      const selection = new Set(state.result.modes[mode].selected_ids);
      const values = LABELS.map(key => {
        if (!Array.isArray(labels[key])) return null;
        const ids = [...new Set(labels[key].filter(id => typeof id === 'string' && known.has(id)))];
        return { found: ids.filter(id => selection.has(id)).length, total: ids.length };
      });
      return { mode, values };
    });
  }
  function renderMetrics() {
    const metrics = labelMetrics();
    $('metrics-section').hidden = !metrics;
    empty($('metric-body'));
    if (!metrics) return;
    metrics.forEach(entry => {
      const row = el('tr', entry.mode === state.mode ? 'active' : '');
      row.append(el('td', '', MODE_NAMES[entry.mode]));
      entry.values.forEach(value => row.append(el('td', 'metric-num', value ? value.found + ' / ' + value.total : 'Not labeled')));
      $('metric-body').append(row);
    });
  }
  function renderMode() {
    document.querySelectorAll('[data-mode]').forEach(tab => {
      const selected = tab.dataset.mode === state.mode;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    $('review-panel').setAttribute('aria-labelledby', 'tab-' + state.mode);
    $('mode-note').textContent = MODE_NOTES[state.mode];
    $('gate-column-label').textContent = state.mode === 'full_control' ? 'Simulated gate' : 'Review';
  }
  function renderMandatory() {
    const ids = state.result.modes[state.mode].mandatory_ids;
    $('mandatory-count').textContent = ids.length;
    empty($('mandatory-list'));
    if (!ids.length) { $('mandatory-list').append(el('p', 'empty', 'No mandatory claims in this scenario.')); return; }
    ids.forEach(id => {
      const item = itemById(id);
      const button = el('button', 'mandatory-card' + (state.selected === id ? ' selected' : ''));
      button.setAttribute('aria-pressed', String(state.selected === id));
      const text = el('span'); text.append(el('strong', '', id), el('p', '', item.statement)); button.append(text);
      if (state.mode === 'full_control') button.append(badge(item));
      else button.append(el('span', 'gate-badge', 'Included'));
      button.addEventListener('click', () => selectClaim(id));
      $('mandatory-list').append(button);
    });
  }
  function renderQueue() {
    const ids = state.result.modes[state.mode].review_ids;
    $('queue-count').textContent = ids.length + ' / ' + state.payload.review_budget + ' budget';
    empty($('queue-body'));
    ids.forEach((id, index) => {
      const item = itemById(id);
      const row = el('tr', state.selected === id ? 'selected' : '');
      const claimCell = el('td');
      const button = el('button', 'claim-button'); button.setAttribute('aria-pressed', String(state.selected === id));
      button.append(el('span', 'rank', String(index + 1).padStart(2, '0')));
      const summary = el('span'); summary.append(el('strong', '', id), el('span', 'statement', item.statement)); button.append(summary);
      button.addEventListener('click', () => selectClaim(id)); claimCell.append(button);
      const scoreCell = el('td'); scoreCell.append(el('span', 'score-value', score(item)), el('span', 'small-note', state.mode === 'baseline' ? 'baseline' : '+' + item.rarity_bonus + ' rarity'));
      const reportsCell = el('td', '', item.report_count); reportsCell.append(el('span', 'small-note', item.independent_events + ' events'));
      const gateCell = el('td'); gateCell.append(state.mode === 'full_control' ? badge(item) : el('span', 'gate-badge', 'Selected'));
      row.append(claimCell, scoreCell, reportsCell, gateCell); $('queue-body').append(row);
    });
    if (!ids.length) { const row = el('tr'); const cell = el('td', 'empty', 'No nonmandatory claims in this scenario.'); cell.colSpan = 4; row.append(cell); $('queue-body').append(row); }
  }
  function renderAllClaims() {
    if (!state.result) return;
    empty($('all-claim-list'));
    const query = $('claim-search').value.trim().toLowerCase();
    const matches = state.result.items.filter(item => (item.id + ' ' + item.statement + ' ' + item.canonical_concept).toLowerCase().includes(query));
    matches.forEach(item => {
      const chip = el('button', 'claim-chip' + (item.id === state.selected ? ' selected' : ''), item.id);
      chip.title = item.statement; chip.setAttribute('aria-label', 'Inspect ' + item.id + ': ' + item.statement); chip.setAttribute('aria-pressed', String(item.id === state.selected));
      chip.addEventListener('click', () => selectClaim(item.id)); $('all-claim-list').append(chip);
    });
    if (!matches.length) $('all-claim-list').append(el('p', 'empty', 'No matching claims.'));
  }
  function block(title) { const section = el('section', 'detail-block'); section.append(el('h4', '', title)); return section; }
  function list(values, className) { const ul = el('ul', className); values.forEach(value => ul.append(el('li', '', value))); return ul; }
  function keyValues(entries) {
    const dl = el('dl', 'key-value-list');
    entries.forEach(([key, value]) => { const row = el('div'); row.append(el('dt', '', key), el('dd', '', value)); dl.append(row); }); return dl;
  }
  function renderDetail() {
    empty($('detail-body'));
    if (!state.selected) { $('detail-id').textContent = '—'; $('detail-body').append(el('p', 'empty', 'Select a claim to inspect its evidence.')); return; }
    const item = itemById(state.selected);
    const source = state.payload.claims.find(claim => claim.id === item.id);
    $('detail-id').textContent = item.id;
    $('detail-body').append(el('p', 'claim-statement', item.statement), el('p', 'detail-meta', 'Concept: ' + item.canonical_concept + ' · Claim v' + source.version + (item.mandatory ? ' · Mandatory' : '')));
    const selected = state.result.modes[state.mode].selected_ids.includes(item.id);
    $('detail-body').append(el('p', 'detail-meta', selected ? 'Included in the current review selection.' : 'Outside the current selection; still available for inspection.'));
    const scores = block('What drives attention');
    const grid = el('div', 'score-grid');
    [[item.base_score, 'Base score'], [item.baseline_score, 'Baseline score'], [item.compensated_score, 'Compensated score'], [item.report_count, 'Raw reports'], [item.independent_events, 'Claim report events'], [item.concept_events, 'Canonical concept events']].forEach(([value, label]) => { const cell = el('div', 'score-cell'); cell.append(el('div', 'value', value), el('div', 'label', label)); grid.append(cell); });
    scores.append(grid, el('p', 'score-inputs', 'Inputs: relevance ' + item.relevance + ' · consequence ' + item.consequence + ' · quality ' + item.quality + '. Rarity bonus: +' + item.rarity_bonus + ' (cap ' + state.payload.policy.rarity_cap + ').'), list(item.reasons.map(reason => ATTENTION_REASONS[reason] || reason), 'explanation-list'));
    $('detail-body').append(scores);

    const gate = el('section', 'detail-block'); const heading = el('div', 'gate-heading'); heading.append(el('h4', '', 'Simulated release check'), badge(item)); gate.append(heading);
    gate.append(el('p', 'gate-description', state.mode === 'full_control' ? 'This is a separate policy check, independent of the attention score.' : 'Diagnostic preview only. This mode does not apply a release check to its selection.'));
    if (item.gate.reasons.length) gate.append(list(item.gate.reasons.map(reason => (REASON_NAMES[reason] || reason) + ' [' + reason + ']'), 'gate-list'));
    else gate.append(el('p', 'gate-description', 'The supplied scenario metadata passes the configured checks. This is not authenticated approval or a finding of truth.'));
    gate.append(keyValues([
      ['Supporting origins', item.gate.independent_support_origins.join(', ') || 'None'],
      ['Origins required', state.payload.policy.min_independent_support],
      ['Missing types', item.gate.missing_evidence_types.join(', ') || 'None'],
      ['Intended use', state.payload.policy.intended_use]
    ]));
    $('detail-body').append(gate);

    const evidence = block('Evidence & declared provenance');
    evidence.append(el('p', 'provenance-note', 'Source IDs are scenario declarations, not authenticated proof of independent collection. Distinct copies or model outputs do not establish independent support.'));
    if (!source.evidence.length) evidence.append(el('p', 'empty', 'No evidence supplied. Missing information is a gap.'));
    source.evidence.forEach(record => {
      const card = el('div', 'source-card'); const top = el('div', 'source-top'); top.append(el('strong', '', record.id), el('span', 'source-state', record.stance)); card.append(top);
      card.append(el('div', '', record.kind + ' · Origin ' + record.origin_id), el('div', 'source-sub', 'Event ' + record.event_id + ' · Claim v' + record.claim_version), el('div', 'source-sub', record.observed_at + ' · ' + (record.support_assessed ? 'Assessed' : 'Unassessed')));
      const excluded = item.gate.excluded_evidence.find(entry => entry.id === record.id);
      if (excluded) card.append(el('div', 'source-exclusion', 'Excluded: ' + (REASON_NAMES[excluded.reason] || excluded.reason)));
      evidence.append(card);
    });
    const records = state.payload.reports.filter(report => report.claim_id === item.id);
    const origins = [...new Set(records.map(report => report.origin_id))].sort();
    const reportDetails = el('details'); reportDetails.append(el('summary', '', 'Report origins (' + origins.length + ')'));
    reportDetails.append(el('p', 'provenance-note', origins.length ? origins.join(', ') : 'No report observations. Evidence does not create report observations implicitly.'));
    evidence.append(reportDetails);
    const approvalDetails = el('details'); approvalDetails.append(el('summary', '', 'Supplied review & authority'));
    const review = source.review; const authority = source.authority;
    approvalDetails.append(keyValues([
      ['Reviewer', review ? review.reviewer_id + ' · ' + review.role : 'Not supplied'],
      ['Review decision', review ? review.decision + ' · expires ' + review.expires_at : 'Not supplied'],
      ['Review versions', review ? 'Claim ' + review.claim_version + ' / policy ' + review.policy_version : 'Not supplied'],
      ['Authority', authority ? authority.authority_id + ' · ' + authority.role : 'Not supplied'],
      ['Authority expiry', authority ? authority.expires_at + (authority.revoked ? ' · REVOKED' : '') : 'Not supplied'],
      ['Authority versions', authority ? 'Claim ' + authority.claim_version + ' / policy ' + authority.policy_version : 'Not supplied'],
      ['Authorized use', authority ? authority.intended_use : 'Not supplied']
    ]));
    evidence.append(approvalDetails); $('detail-body').append(evidence);
  }
  document.querySelectorAll('[data-mode]').forEach((tab, index, tabs) => {
    tab.addEventListener('click', () => { state.mode = tab.dataset.mode; if (state.result) render(); });
    tab.addEventListener('keydown', event => {
      let target;
      if (event.key === 'ArrowRight') target = (index + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') target = (index + tabs.length - 1) % tabs.length;
      else if (event.key === 'Home') target = 0;
      else if (event.key === 'End') target = tabs.length - 1;
      if (target !== undefined) { event.preventDefault(); tabs[target].focus(); tabs[target].click(); }
    });
  });
  $('claim-search').addEventListener('input', renderAllClaims);
  $('import-button').addEventListener('click', () => $('import-file').click());
  $('import-file').addEventListener('change', async event => {
    const file = event.target.files[0]; if (!file) return;
    try {
      if (file.size > 8 * 1024 * 1024) throw new Error('Import is limited to 8 MB.');
      const parsed = JSON.parse(await file.text());
      const payload = parsed && parsed.export_schema_version === '1.0' && parsed.input ? parsed.input : parsed;
      await run(payload, 'Imported scenario evaluated');
    } catch (error) { fail(error); }
    finally { event.target.value = ''; }
  });
  $('budget').addEventListener('change', () => {
    if (!state.payload || state.busy) return;
    const value = Number($('budget').value);
    if (!Number.isInteger(value) || value < 1 || value > 100) { fail(new Error('Review budget must be an integer from 1 to 100.')); return; }
    const payload = clone(state.payload); payload.review_budget = value; run(payload, 'Review budget updated');
  });
  $('reset-button').addEventListener('click', () => {
    if (!globalThis.DEEP_SIGMA_DEMO) { fail(new Error('Demo scenario unavailable. Keep demo.js beside index.html.')); return; }
    $('claim-search').value = ''; state.selected = null; run(clone(globalThis.DEEP_SIGMA_DEMO), 'Synthetic demo evaluated');
  });
  $('export-button').addEventListener('click', () => {
    if (!state.result) return;
    const bundle = { export_schema_version: '1.0', notice: 'Synthetic pilot. All release results are simulated and do not authorize an action.', engine: localJS ? 'JavaScript local' : 'Python localhost', input: state.payload, evaluation: state.result, evaluator_label_metrics: labelMetrics() };
    const blob = new Blob([JSON.stringify(bundle, null, 2) + '\n'], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const anchor = el('a'); anchor.href = url; anchor.download = 'deep_sigma_zipf_results.json'; document.body.append(anchor); anchor.click(); anchor.remove(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $('runtime-label').textContent = localJS ? 'JavaScript · Offline simulation' : 'Python · Localhost simulation';
  $('privacy-note').textContent = localJS ? 'No network requests. JavaScript runs on this device.' : 'Local Python evaluation. No LLM or external service.';
  if (globalThis.DEEP_SIGMA_DEMO) run(clone(globalThis.DEEP_SIGMA_DEMO), 'Synthetic demo evaluated');
  else { setBusy(false); fail(new Error('Demo scenario unavailable. Import a scenario or keep demo.js beside index.html.')); }
}());
