/*
 * DEEP SIGMA Liddell Lens 1.0.0 — dependency-free comparison engine.
 * Original Deep Sigma adaptation inspired by B. H. Liddell Hart.
 * No endorsement, causal finding, or validated military model is implied.
 * UMD: use require('./engine.js') in Node or window.LiddellLens in a browser.
 */
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.LiddellLens = factory();
  }
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const EFFORT_FIELDS = ['preparation', 'execution', 'review', 'clarification', 'rework'];
  const RUN_FIELDS = ['elapsed_minutes', 'effort_minutes', 'clarification_cycles',
    'unresolved_contradictions', 'closed', 'supported', 'authorized'];
  const ROOT_FIELDS = ['schema_version', 'data_kind', 'title', 'cases'];
  const CASE_FIELDS = ['case_id', 'baseline', 'cerpa'];
  const ARM_NAMES = ['baseline', 'cerpa'];

  function fail(path, message) {
    throw new Error(path + ': ' + message);
  }

  function checkObject(value, fields, path) {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) {
      fail(path, 'must be a plain JSON object');
    }
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== Object.prototype && prototype !== null) {
      fail(path, 'must be a plain JSON object');
    }
    for (const key of Reflect.ownKeys(value)) {
      if (typeof key !== 'string' || !fields.includes(key)) {
        fail(path + '.' + String(key), 'unknown field');
      }
      const descriptor = Object.getOwnPropertyDescriptor(value, key);
      if (!descriptor.enumerable || !Object.prototype.hasOwnProperty.call(descriptor, 'value')) {
        fail(path + '.' + key, 'must be an ordinary JSON data field');
      }
    }
    for (const key of fields) {
      if (!Object.prototype.hasOwnProperty.call(value, key)) {
        fail(path + '.' + key, 'missing required field');
      }
    }
  }

  function checkString(value, path) {
    if (typeof value !== 'string' || value.length === 0) {
      fail(path, 'must be a nonempty string');
    }
    if (value !== value.trim()) {
      fail(path, 'must already be trimmed');
    }
    if (Array.from(value).length > 200) {
      fail(path, 'must contain at most 200 Unicode code points');
    }
  }

  function checkNumber(value, maximum, integer, path) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > maximum) {
      fail(path, 'must be a finite number in [0, ' + maximum + ']');
    }
    if (integer && !Number.isInteger(value)) {
      fail(path, 'must be an integer');
    }
  }

  function checkRun(run, path) {
    checkObject(run, RUN_FIELDS, path);
    checkNumber(run.elapsed_minutes, 1000000000, false, path + '.elapsed_minutes');
    checkObject(run.effort_minutes, EFFORT_FIELDS, path + '.effort_minutes');
    for (const field of EFFORT_FIELDS) {
      checkNumber(run.effort_minutes[field], 1000000000, false, path + '.effort_minutes.' + field);
    }
    checkNumber(run.clarification_cycles, 1000000, true, path + '.clarification_cycles');
    checkNumber(run.unresolved_contradictions, 1000000, true, path + '.unresolved_contradictions');
    for (const field of ['closed', 'supported', 'authorized']) {
      if (typeof run[field] !== 'boolean') {
        fail(path + '.' + field, 'must be a boolean (true or false)');
      }
    }
  }

  /** Validate the exact version-1 input schema; throw a path-specific Error. */
  function validate(data) {
    checkObject(data, ROOT_FIELDS, '$');
    if (data.schema_version !== '1.0') {
      fail('$.schema_version', 'must equal "1.0"');
    }
    if (data.data_kind !== 'illustrative' && data.data_kind !== 'observed') {
      fail('$.data_kind', 'must be "illustrative" or "observed"');
    }
    checkString(data.title, '$.title');
    if (!Array.isArray(data.cases) || data.cases.length === 0 || data.cases.length > 10000) {
      fail('$.cases', 'must be a nonempty array containing at most 10000 cases');
    }
    // Reject sparse arrays and attached properties, which JSON arrays cannot preserve.
    for (const key of Reflect.ownKeys(data.cases)) {
      if (key === 'length') continue;
      if (typeof key !== 'string' || !/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= data.cases.length) {
        fail('$.cases.' + String(key), 'unknown array field');
      }
      const descriptor = Object.getOwnPropertyDescriptor(data.cases, key);
      if (!descriptor.enumerable || !Object.prototype.hasOwnProperty.call(descriptor, 'value')) {
        fail('$.cases[' + key + ']', 'must be an ordinary JSON array element');
      }
    }
    const ids = new Set();
    for (let index = 0; index < data.cases.length; index += 1) {
      const path = '$.cases[' + index + ']';
      if (!Object.prototype.hasOwnProperty.call(data.cases, index)) {
        fail(path, 'missing array element');
      }
      const item = data.cases[index];
      checkObject(item, CASE_FIELDS, path);
      checkString(item.case_id, path + '.case_id');
      if (ids.has(item.case_id)) {
        fail(path + '.case_id', 'must be unique');
      }
      ids.add(item.case_id);
      for (const arm of ARM_NAMES) checkRun(item[arm], path + '.' + arm);
    }
  }

  function isComplete(run) {
    return run.closed && run.supported && run.authorized;
  }

  function effortTotal(run) {
    return EFFORT_FIELDS.reduce(function (sum, field) { return sum + run.effort_minutes[field]; }, 0);
  }

  function percentSaved(baseline, saved) {
    if (baseline === 0) return null;
    const percentage = saved / baseline * 100;
    // Tiny, valid positive baselines can overflow a floating-point ratio.
    // Never let JSON.stringify silently disguise Infinity as a null result.
    if (!Number.isFinite(percentage)) {
      throw new Error('percentage exceeds finite range; use comparable numeric scales');
    }
    return percentage;
  }

  function difference(baseline, cerpa) {
    const saved = baseline - cerpa;
    return {baseline: baseline, cerpa: cerpa, saved: saved, percent_saved: percentSaved(baseline, saved)};
  }

  function emptyArm(caseCount) {
    return {
      case_count: caseCount,
      completed_supported_authorized: 0,
      completion_rate_pct: 0,
      total_effort_minutes: 0,
      effort_minutes: {preparation: 0, execution: 0, review: 0, clarification: 0, rework: 0},
      clarification_cycles: 0,
      unresolved_contradictions: 0
    };
  }

  /**
   * Compare all effort and outcomes, with elapsed means restricted to pairs
   * closed, supported, and authorized in both arms. Does not mutate input.
   * Unrounded outputs preserve negative savings; undefined percentages are null.
   */
  function analyze(data) {
    validate(data);
    const count = data.cases.length;
    const arms = {baseline: emptyArm(count), cerpa: emptyArm(count)};
    const excluded = [];
    const caseResults = [];
    let pairedCount = 0;
    let baselineElapsed = 0;
    let cerpaElapsed = 0;

    for (const item of data.cases) {
      const baselineComplete = isComplete(item.baseline);
      const cerpaComplete = isComplete(item.cerpa);
      const baselineEffort = effortTotal(item.baseline);
      const cerpaEffort = effortTotal(item.cerpa);
      for (const arm of ARM_NAMES) {
        const source = item[arm];
        const target = arms[arm];
        target.completed_supported_authorized += isComplete(source) ? 1 : 0;
        target.total_effort_minutes += effortTotal(source);
        for (const field of EFFORT_FIELDS) target.effort_minutes[field] += source.effort_minutes[field];
        target.clarification_cycles += source.clarification_cycles;
        target.unresolved_contradictions += source.unresolved_contradictions;
      }
      const paired = baselineComplete && cerpaComplete;
      if (paired) {
        pairedCount += 1;
        baselineElapsed += item.baseline.elapsed_minutes;
        cerpaElapsed += item.cerpa.elapsed_minutes;
      } else {
        excluded.push(item.case_id);
      }
      caseResults.push({
        case_id: item.case_id,
        baseline_complete: baselineComplete,
        cerpa_complete: cerpaComplete,
        baseline_effort_minutes: baselineEffort,
        cerpa_effort_minutes: cerpaEffort,
        effort_saved_minutes: baselineEffort - cerpaEffort,
        baseline_elapsed_minutes: item.baseline.elapsed_minutes,
        cerpa_elapsed_minutes: item.cerpa.elapsed_minutes,
        elapsed_saved_minutes: paired ? item.baseline.elapsed_minutes - item.cerpa.elapsed_minutes : null
      });
    }
    for (const arm of ARM_NAMES) {
      arms[arm].completion_rate_pct = arms[arm].completed_supported_authorized / count * 100;
    }

    const baselineMean = pairedCount ? baselineElapsed / pairedCount : null;
    const cerpaMean = pairedCount ? cerpaElapsed / pairedCount : null;
    const savedMean = pairedCount ? baselineMean - cerpaMean : null;
    const warnings = [
      'Recorded support and authority flags are human assessments; this tool does not verify evidence or authorization.'
    ];
    if (data.data_kind === 'illustrative') {
      warnings.push('ILLUSTRATIVE DATA: these results are examples, not measured Deep Sigma performance.');
    }
    if (excluded.length) {
      warnings.push('Elapsed-time comparison excludes cases without a closed, supported, authorized decision in both arms; inspect completion counts and excluded cases.');
    }
    warnings.push('Observed differences do not establish causation. Use comparable cases and include all preparation, review, and collection costs in the evaluation.');

    return {
      schema_version: '1.0',
      data_kind: data.data_kind,
      title: data.title,
      case_count: count,
      arms: arms,
      comparison: {
        total_effort_minutes: difference(arms.baseline.total_effort_minutes, arms.cerpa.total_effort_minutes),
        rework_minutes: difference(arms.baseline.effort_minutes.rework, arms.cerpa.effort_minutes.rework),
        clarification_cycles: difference(arms.baseline.clarification_cycles, arms.cerpa.clarification_cycles),
        unresolved_contradictions: difference(arms.baseline.unresolved_contradictions, arms.cerpa.unresolved_contradictions)
      },
      paired_elapsed: {
        case_count: pairedCount,
        excluded_case_ids: excluded,
        baseline_mean_minutes: baselineMean,
        cerpa_mean_minutes: cerpaMean,
        saved_mean_minutes: savedMean,
        percent_saved: pairedCount ? percentSaved(baselineMean, savedMean) : null
      },
      case_results: caseResults,
      warnings: warnings
    };
  }

  return Object.freeze({validate: validate, analyze: analyze});
}));
