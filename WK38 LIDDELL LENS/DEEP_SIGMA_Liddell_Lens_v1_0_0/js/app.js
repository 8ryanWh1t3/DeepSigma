(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const number = new Intl.NumberFormat('en-US', {maximumFractionDigits: 2});
  const fmt = (value) => value === null ? 'N/A' : number.format(Object.is(value, -0) ? 0 : value);
  const pageSize = 25;
  let currentData = null;
  let currentResult = null;
  let page = 0;
  let importSequence = 0;
  const exportIds = ['export-input', 'export-json', 'export-csv'];

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function percentDetail(percent) {
    return percent === null ? 'N/A · zero baseline or no eligible pair' : fmt(percent) + '% saved versus baseline';
  }

  function clearResults() {
    currentData = null;
    currentResult = null;
    page = 0;
    $('results').hidden = true;
    $('evaluation-title').textContent = 'No valid evaluation loaded';
    $('case-summary').textContent = '';
    ['cases-body', 'friction-body', 'effort-breakdown', 'warnings'].forEach((id) => $(id).replaceChildren());
    exportIds.forEach((id) => { $(id).disabled = true; });
  }

  function showError(error) {
    clearResults();
    $('error-message').textContent = error && error.message ? error.message : String(error);
    $('error-box').hidden = false;
    $('data-banner').textContent = 'No results displayed. A valid input file is required.';
    $('error-box').focus();
  }

  function analyze(data, origin) {
    try {
      const result = window.LiddellLens.analyze(data);
      currentData = data;
      currentResult = result;
      page = 0;
      $('excluded-only').checked = false;
      $('error-box').hidden = true;
      $('error-message').textContent = '';
      render(result, origin);
      exportIds.forEach((id) => { $(id).disabled = false; });
    } catch (error) {
      showError(error);
    }
  }

  function render(result, origin) {
    $('results').hidden = false;
    $('evaluation-title').textContent = result.title;
    $('case-summary').textContent = fmt(result.case_count) + ' matched case' + (result.case_count === 1 ? '' : 's') + ' · ' + origin;
    const banner = $('data-banner');
    banner.replaceChildren();
    if (result.data_kind === 'illustrative') {
      banner.append(element('strong', 'ILLUSTRATIVE DATA'), document.createTextNode(' — An example for exploring the method. These results are not measured Deep Sigma performance.'));
    } else {
      banner.append(element('strong', 'OBSERVED DATA · USER-SUPPLIED'), document.createTextNode(' — Values and completion flags are recorded assessments. The tool does not independently verify them or establish causation.'));
    }

    const effort = result.comparison.total_effort_minutes;
    const rework = result.comparison.rework_minutes;
    const paired = result.paired_elapsed;
    $('effort-saving').textContent = fmt(effort.saved);
    $('effort-percent').textContent = percentDetail(effort.percent_saved);
    $('rework-saving').textContent = fmt(rework.saved);
    $('rework-percent').textContent = percentDetail(rework.percent_saved);
    $('elapsed-saving').textContent = fmt(paired.saved_mean_minutes);
    $('elapsed-percent').textContent = percentDetail(paired.percent_saved);
    $('paired-count').textContent = fmt(paired.case_count) + ' of ' + fmt(result.case_count) + ' cases qualify in both arms. Other cases are excluded from timing only.';
    for (const arm of ['baseline', 'cerpa']) {
      const values = result.arms[arm];
      $(arm + '-completion').textContent = fmt(values.completed_supported_authorized) + ' / ' + fmt(values.case_count);
      $(arm + '-rate').textContent = fmt(values.completion_rate_pct) + '% of all cases';
    }
    $('baseline-elapsed').textContent = fmt(paired.baseline_mean_minutes) + (paired.baseline_mean_minutes === null ? '' : ' min');
    $('cerpa-elapsed').textContent = fmt(paired.cerpa_mean_minutes) + (paired.cerpa_mean_minutes === null ? '' : ' min');
    const excluded = paired.excluded_case_ids;
    $('excluded-summary').textContent = excluded.length ? fmt(excluded.length) + ' case' + (excluded.length === 1 ? ' is' : 's are') + ' excluded from paired timing. All remain in effort and count measures.' : 'Every case qualifies for paired timing.';
    $('excluded-details').hidden = excluded.length === 0;
    $('excluded-details').open = false;
    $('excluded-ids').textContent = excluded.join(' · ');
    renderBreakdown(result);
    renderFriction(result);
    renderCases();
    const warnings = $('warnings');
    warnings.replaceChildren(...result.warnings.map((warning) => element('li', warning)));
  }

  function renderBreakdown(result) {
    const stages = ['preparation', 'execution', 'review', 'clarification', 'rework'];
    const baseline = result.arms.baseline.effort_minutes;
    const cerpa = result.arms.cerpa.effort_minutes;
    const max = Math.max(...stages.flatMap((stage) => [baseline[stage], cerpa[stage]]));
    const container = $('effort-breakdown');
    container.replaceChildren();
    for (const stage of stages) {
      const row = element('div');
      const heading = element('div', undefined, 'stage-heading');
      const label = stage.charAt(0).toUpperCase() + stage.slice(1);
      heading.append(element('strong', label), element('span', fmt(baseline[stage]) + ' / ' + fmt(cerpa[stage])));
      const pair = element('div', undefined, 'bar-pair');
      pair.setAttribute('role', 'img');
      pair.setAttribute('aria-label', label + ': baseline ' + fmt(baseline[stage]) + ', CERPA ' + fmt(cerpa[stage]) + ' person-minutes.');
      for (const arm of ['baseline', 'cerpa']) {
        const track = element('div', undefined, 'bar-track');
        const bar = element('div', undefined, 'bar ' + arm);
        bar.style.width = (max === 0 ? 0 : result.arms[arm].effort_minutes[stage] / max * 100) + '%';
        track.append(bar);
        pair.append(track);
      }
      row.append(heading, pair);
      container.append(row);
    }
    $('effort-totals').textContent = fmt(result.arms.baseline.total_effort_minutes) + ' baseline / ' + fmt(result.arms.cerpa.total_effort_minutes) + ' CERPA';
  }

  function renderFriction(result) {
    const body = $('friction-body');
    body.replaceChildren();
    for (const [key, label] of [['clarification_cycles', 'Clarification cycles'], ['unresolved_contradictions', 'Unresolved contradictions']]) {
      const values = result.comparison[key];
      const row = element('tr');
      row.append(element('td', label), element('td', fmt(values.baseline)), element('td', fmt(values.cerpa)), element('td', fmt(values.saved)));
      body.append(row);
    }
  }

  function renderCases() {
    if (!currentResult) return;
    let rows = currentResult.case_results;
    if ($('excluded-only').checked) rows = rows.filter((row) => !row.baseline_complete || !row.cerpa_complete);
    const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
    page = Math.max(0, Math.min(page, totalPages - 1));
    const start = page * pageSize;
    const displayed = rows.slice(start, start + pageSize);
    const body = $('cases-body');
    body.replaceChildren();
    for (const values of displayed) {
      const row = element('tr');
      const caseHeader = element('th', values.case_id);
      caseHeader.scope = 'row';
      row.append(caseHeader);
      row.append(element('td', values.baseline_complete ? 'Yes' : 'No'), element('td', values.cerpa_complete ? 'Yes' : 'No'));
      for (const key of ['baseline_effort_minutes', 'cerpa_effort_minutes', 'effort_saved_minutes', 'baseline_elapsed_minutes', 'cerpa_elapsed_minutes']) row.append(element('td', fmt(values[key])));
      row.append(element('td', values.elapsed_saved_minutes === null ? 'Excluded' : fmt(values.elapsed_saved_minutes), values.elapsed_saved_minutes === null ? 'excluded-cell' : undefined));
      body.append(row);
    }
    if (!rows.length) {
      const row = element('tr');
      const cell = element('td', 'No cases are excluded from paired timing.', 'empty-row');
      cell.colSpan = 9;
      row.append(cell);
      body.append(row);
    }
    $('page-summary').textContent = rows.length ? 'Showing ' + fmt(start + 1) + '–' + fmt(start + displayed.length) + ' of ' + fmt(rows.length) + ' cases' : '0 excluded cases';
    $('prev-page').disabled = page === 0;
    $('next-page').disabled = page >= totalPages - 1;
  }

  function download(content, filename, type) {
    const blob = new Blob([content], {type});
    const url = URL.createObjectURL(blob);
    const anchor = element('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function csvCell(value) {
    if (value === null) return '';
    let str = String(value);
    // Protect spreadsheet users from formula execution in imported string fields.
    if (typeof value === 'string' && (/^[\t\r\n]/.test(str) || /^[\s\u0000-\u001f]*[=+\-@]/.test(str))) str = "'" + str;
    return '"' + str.replace(/"/g, '""') + '"';
  }

  $('export-json').addEventListener('click', () => {
    if (currentResult) download(JSON.stringify(currentResult, null, 2) + '\n', 'liddell_lens_results.json', 'application/json');
  });
  $('export-input').addEventListener('click', () => {
    if (currentData) download(JSON.stringify(currentData, null, 2) + '\n', 'liddell_lens_input.json', 'application/json');
  });
  $('export-csv').addEventListener('click', () => {
    if (!currentResult) return;
    const keys = ['case_id', 'baseline_complete', 'cerpa_complete', 'baseline_effort_minutes', 'cerpa_effort_minutes', 'effort_saved_minutes', 'baseline_elapsed_minutes', 'cerpa_elapsed_minutes', 'elapsed_saved_minutes'];
    const rows = [keys.map(csvCell).join(',')].concat(currentResult.case_results.map((row) => keys.map((key) => csvCell(row[key])).join(',')));
    download(rows.join('\r\n') + '\r\n', 'liddell_lens_cases.csv', 'text/csv;charset=utf-8');
  });
  $('download-template').addEventListener('click', () => {
    const emptyRun = () => ({elapsed_minutes: 0, effort_minutes: {preparation: 0, execution: 0, review: 0, clarification: 0, rework: 0}, clarification_cycles: 0, unresolved_contradictions: 0, closed: false, supported: false, authorized: false});
    const data = {schema_version: '1.0', data_kind: 'illustrative', title: 'Template only — replace every placeholder before use', cases: [{case_id: 'CASE-001', baseline: emptyRun(), cerpa: emptyRun()}]};
    download(JSON.stringify(data, null, 2) + '\n', 'liddell_lens_blank_template.json', 'application/json');
  });
  $('excluded-only').addEventListener('change', () => { page = 0; renderCases(); });
  $('prev-page').addEventListener('click', () => { page -= 1; renderCases(); });
  $('next-page').addEventListener('click', () => { page += 1; renderCases(); });
  $('file-input').addEventListener('change', (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    const sequence = ++importSequence;
    clearResults();
    $('error-box').hidden = true;
    $('data-banner').textContent = 'Reading local file…';
    $('example-select').value = '';
    const reader = new FileReader();
    reader.onload = () => {
      if (sequence !== importSequence) return;
      try {
        const data = JSON.parse(String(reader.result).replace(/^\uFEFF/, ''));
        analyze(data, file.name);
      } catch (error) {
        showError(new Error('JSON input: ' + error.message));
      }
    };
    reader.onerror = () => {
      if (sequence === importSequence) showError(new Error('The local file could not be read. Choose the file again.'));
    };
    reader.readAsText(file);
    event.target.value = '';
  });

  const examples = Array.isArray(window.LiddellExamples) ? window.LiddellExamples : [];
  const select = $('example-select');
  select.replaceChildren();
  const placeholder = element('option', 'Choose an illustrative example');
  placeholder.value = '';
  placeholder.disabled = true;
  select.append(placeholder);
  examples.forEach((example, index) => {
    const option = element('option', example.label);
    option.value = String(index);
    select.append(option);
  });
  select.addEventListener('change', () => {
    importSequence += 1;
    const index = Number(select.value);
    if (Number.isInteger(index) && examples[index]) analyze(examples[index].data, 'built-in example');
  });
  if (!window.LiddellLens || typeof window.LiddellLens.analyze !== 'function') {
    showError(new Error('The local analysis engine is missing. Keep index.html, css, and js together in the extracted folder.'));
  } else if (examples.length) {
    select.value = '0';
    analyze(examples[0].data, 'built-in example');
  } else {
    clearResults();
    $('data-banner').textContent = 'Import a JSON file to start, or download the blank template.';
  }
})();
