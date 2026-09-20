/* Deep Sigma Zipf pilot 1.0.0. Dependency-free deterministic evaluation.
 * A local simulation only: metadata is supplied by the caller, not authenticated.
 */
(function (root) {
  "use strict";

  class ValidationError extends Error {
    constructor(message) {
      super(message);
      this.name = "ValidationError";
    }
  }

  const ID = /^[A-Za-z0-9_.:-]{1,80}$/;
  const CONCEPT = /^[A-Za-z0-9 _-]{1,80}$/;
  const UTC = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$/;
  // Match Python str.strip() whitespace semantics for cross-language validation.
  const BLANK = /^[\u0009-\u000D\u001C-\u0020\u0085\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000]*$/;
  const MAX_INTEGER = Number.MAX_SAFE_INTEGER;
  const DAY = 86400000;
  const own = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
  const fail = (path, description) => { throw new ValidationError(path + ": " + description); };
  const cpLength = value => Array.from(value).length;
  const asciiCompare = (a, b) => a < b ? -1 : a > b ? 1 : 0;
  // Python strings sort by Unicode code points, rather than UTF-16 code units.
  function codePointCompare(a, b) {
    const aa = Array.from(a), bb = Array.from(b);
    for (let i = 0; i < Math.min(aa.length, bb.length); i++) {
      const delta = aa[i].codePointAt(0) - bb[i].codePointAt(0);
      if (delta) return delta;
    }
    return aa.length - bb.length;
  }
  function object(value, path) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) fail(path, "must be an object");
    return value;
  }
  function field(obj, key, path) {
    if (!own(obj, key)) fail(path + "." + key, "required field missing");
    return obj[key];
  }
  function array(value, path, min, max) {
    if (!Array.isArray(value) || value.length < min || value.length > max) fail(path, "must be an array with " + min + ".." + max + " entries");
    return value;
  }
  function integer(value, path, min, max) {
    if (typeof value !== "number" || !Number.isSafeInteger(value) || value < min || value > max) fail(path, "must be an integer in " + min + ".." + max);
    return value;
  }
  function boolean(value, path) {
    if (typeof value !== "boolean") fail(path, "must be a boolean");
    return value;
  }
  function identity(value, path) {
    if (typeof value !== "string" || (!ID.test(value) || ID.exec(value)[0] !== value)) fail(path, "must be an ASCII identifier of 1..80 characters");
    return value;
  }
  function generic(value, path) {
    if (typeof value !== "string" || cpLength(value) < 1 || cpLength(value) > 80 || BLANK.test(value) || /[\x00-\x1F\x7F]/.test(value)) fail(path, "must be a nonblank string of 1..80 characters without control characters");
    return value;
  }
  function concept(value, path) {
    if (typeof value !== "string" || (!CONCEPT.test(value) || CONCEPT.exec(value)[0] !== value)) fail(path, "must be a concept string of 1..80 permitted ASCII characters");
    const normalized = value.trim().toLowerCase().replace(/ +/g, " ");
    if (!normalized) fail(path, "must not be blank");
    return normalized;
  }
  function choice(value, path, options) {
    if (!options.includes(value)) fail(path, "must be one of " + options.join(", "));
    return value;
  }
  function timestamp(value, path) {
    if (typeof value !== "string") fail(path, "must be a UTC timestamp YYYY-MM-DDTHH:MM:SSZ");
    const match = UTC.exec(value);
    if (!match || match[0] !== value) fail(path, "must be a UTC timestamp YYYY-MM-DDTHH:MM:SSZ");
    const [year, month, day, hour, minute, second] = match.slice(1).map(Number);
    if (year < 1 || month < 1 || month > 12 || day < 1 || day > 31 || hour > 23 || minute > 59 || second > 59) fail(path, "must be a real UTC calendar timestamp");
    const date = new Date(0);
    date.setUTCFullYear(year, month - 1, day);
    date.setUTCHours(hour, minute, second, 0);
    if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) fail(path, "must be a real UTC calendar timestamp");
    return date.getTime();
  }
  function stringArray(value, path, allowEmpty) {
    const result = array(value, path, allowEmpty ? 0 : 1, MAX_INTEGER).map((entry, i) => generic(entry, path + "[" + i + "]"));
    if (new Set(result).size !== result.length) fail(path, "entries must be unique");
    return result;
  }
  function required(obj, key, path, validator, ...args) {
    return validator(field(obj, key, path), path + "." + key, ...args);
  }
  function validate(payload) {
    object(payload, "input");
    if (field(payload, "schema_version", "input") !== "1.0") fail("input.schema_version", "must equal 1.0");
    const asOf = required(payload, "as_of", "input", timestamp);
    const reviewBudget = required(payload, "review_budget", "input", integer, 1, 100);
    const p = required(payload, "policy", "input", object);
    const policy = {
      id: required(p, "id", "policy", identity),
      version: required(p, "version", "policy", integer, 1, MAX_INTEGER),
      rarity_cap: required(p, "rarity_cap", "policy", integer, 0, 30),
      min_relevance: required(p, "min_relevance", "policy", integer, 0, 100),
      min_quality: required(p, "min_quality", "policy", integer, 0, 100),
      min_independent_support: required(p, "min_independent_support", "policy", integer, 1, 10),
      required_evidence_types: required(p, "required_evidence_types", "policy", stringArray, false),
      max_evidence_age_days: required(p, "max_evidence_age_days", "policy", integer, 1, 3650),
      reviewer_roles: required(p, "reviewer_roles", "policy", stringArray, false),
      authority_roles: required(p, "authority_roles", "policy", stringArray, false),
      intended_use: required(p, "intended_use", "policy", generic)
    };
    const rawAliases = required(payload, "aliases", "input", object);
    const aliases = new Map();
    Object.entries(rawAliases).forEach(([key, value]) => {
      const norm = concept(key, "aliases key");
      if (aliases.has(norm)) fail("aliases", "duplicate normalized alias key");
      aliases.set(norm, concept(value, "aliases." + key));
    });
    aliases.forEach((value) => {
      if (aliases.has(value)) fail("aliases", "chained or cyclic aliases are not allowed");
    });
    const canonical = value => aliases.has(value) ? aliases.get(value) : value;
    const owners = new Map();
    const eventKey = (origin, event) => JSON.stringify([origin, event]);
    function registerEvent(origin, event, claim, path) {
      const key = eventKey(origin, event);
      if (owners.has(key) && owners.get(key) !== claim) fail(path, "source event reused across different claims");
      owners.set(key, claim);
      return key;
    }
    function reviewOrAuthority(value, path, authority) {
      if (value === null) return null;
      object(value, path);
      const answer = {
        role: required(value, "role", path, generic),
        claim_version: required(value, "claim_version", path, integer, 1, MAX_INTEGER),
        policy_version: required(value, "policy_version", path, integer, 1, MAX_INTEGER),
        expires_at: required(value, "expires_at", path, timestamp)
      };
      if (authority) {
        answer.authority_id = required(value, "authority_id", path, identity);
        answer.intended_use = required(value, "intended_use", path, generic);
        answer.revoked = required(value, "revoked", path, boolean);
      } else {
        answer.reviewer_id = required(value, "reviewer_id", path, identity);
        answer.decision = required(value, "decision", path, choice, ["approved", "rejected"]);
      }
      return answer;
    }
    const claimIds = new Set();
    const claims = required(payload, "claims", "input", array, 1, 1000).map((raw, index) => {
      const path = "claims[" + index + "]";
      object(raw, path);
      const id = required(raw, "id", path, identity);
      if (claimIds.has(id)) fail(path + ".id", "duplicate claim identifier");
      claimIds.add(id);
      const statement = field(raw, "statement", path);
      if (typeof statement !== "string" || cpLength(statement) < 1 || cpLength(statement) > 2000) fail(path + ".statement", "must be a string of 1..2000 characters");
      const claim = {
        id,
        version: required(raw, "version", path, integer, 1, MAX_INTEGER),
        concept: canonical(required(raw, "concept", path, concept)),
        statement,
        relevance: required(raw, "relevance", path, integer, 0, 100),
        consequence: required(raw, "consequence", path, integer, 0, 100),
        quality: required(raw, "quality", path, integer, 0, 100),
        contradiction: required(raw, "contradiction", path, boolean),
        mandatory: required(raw, "mandatory", path, boolean),
        required_evidence_types: required(raw, "required_evidence_types", path, stringArray, true),
        review: reviewOrAuthority(field(raw, "review", path), path + ".review", false),
        authority: reviewOrAuthority(field(raw, "authority", path), path + ".authority", true)
      };
      const evidenceIds = new Set(), identities = new Map();
      claim.evidence = required(raw, "evidence", path, array, 0, MAX_INTEGER).map((e, ei) => {
        const ep = path + ".evidence[" + ei + "]";
        object(e, ep);
        const evidence = {
          id: required(e, "id", ep, identity),
          origin_id: required(e, "origin_id", ep, identity),
          event_id: required(e, "event_id", ep, identity),
          kind: required(e, "kind", ep, generic),
          stance: required(e, "stance", ep, choice, ["supports", "contradicts", "neutral"]),
          claim_version: required(e, "claim_version", ep, integer, 1, MAX_INTEGER),
          observed_at: required(e, "observed_at", ep, timestamp),
          support_assessed: required(e, "support_assessed", ep, boolean)
        };
        if (evidenceIds.has(evidence.id)) fail(ep + ".id", "duplicate evidence identifier within claim");
        evidenceIds.add(evidence.id);
        const key = registerEvent(evidence.origin_id, evidence.event_id, id, ep);
        const signature = JSON.stringify([evidence.kind, evidence.stance, evidence.claim_version, evidence.observed_at, evidence.support_assessed]);
        if (identities.has(key) && identities.get(key) !== signature) fail(ep, "conflicting metadata for the same evidence event");
        identities.set(key, signature);
        return evidence;
      });
      return claim;
    });
    const reportIds = new Set();
    const reports = required(payload, "reports", "input", array, 0, 50000).map((r, ri) => {
      const path = "reports[" + ri + "]";
      object(r, path);
      const report = {
        id: required(r, "id", path, identity),
        claim_id: required(r, "claim_id", path, identity),
        origin_id: required(r, "origin_id", path, identity),
        event_id: required(r, "event_id", path, identity)
      };
      if (reportIds.has(report.id)) fail(path + ".id", "duplicate report identifier");
      reportIds.add(report.id);
      if (!claimIds.has(report.claim_id)) fail(path + ".claim_id", "unknown claim identifier");
      report.key = registerEvent(report.origin_id, report.event_id, report.claim_id, path);
      return report;
    });
    return {asOf, asOfText: payload.as_of, reviewBudget, policy, claims, reports};
  }

  function gate(claim, policy, asOf) {
    const excluded = [], origins = new Set(), kinds = new Set();
    let contradiction = claim.contradiction, unassessedContradiction = false;
    claim.evidence.forEach(e => {
      let reason = null;
      if (e.claim_version !== claim.version) reason = "VERSION_MISMATCH";
      else if (e.observed_at > asOf) reason = "FUTURE_EVIDENCE";
      else if (asOf - e.observed_at > policy.max_evidence_age_days * DAY) reason = "STALE_EVIDENCE";
      else if (e.stance === "supports" && !e.support_assessed) reason = "UNASSESSED_SUPPORT";
      if (reason) {
        excluded.push({id: e.id, reason});
        return;
      }
      if (e.stance === "supports") {
        origins.add(e.origin_id);
        kinds.add(e.kind);
      } else if (e.stance === "contradicts") {
        contradiction = true;
        if (!e.support_assessed) unassessedContradiction = true;
      }
    });
    excluded.sort((a, b) => asciiCompare(a.id, b.id));
    const requiredTypes = new Set(policy.required_evidence_types.concat(claim.required_evidence_types));
    const missing = Array.from(requiredTypes).filter(kind => !kinds.has(kind)).sort(codePointCompare);
    const reasons = [];
    if (contradiction) reasons.push("CONTRADICTION");
    if (origins.size < policy.min_independent_support) reasons.push("INSUFFICIENT_INDEPENDENT_SUPPORT");
    if (missing.length) reasons.push("MISSING_EVIDENCE_TYPES");
    const review = claim.review;
    if (review === null) reasons.push("MISSING_REVIEW");
    else {
      if (review.expires_at <= asOf) reasons.push("REVIEW_EXPIRED");
      if (review.decision === "rejected") reasons.push("REVIEW_REJECTED");
      if (!policy.reviewer_roles.includes(review.role)) reasons.push("REVIEW_ROLE");
      if (review.claim_version !== claim.version || review.policy_version !== policy.version) reasons.push("REVIEW_VERSION");
    }
    const authority = claim.authority;
    if (authority === null) reasons.push("MISSING_AUTHORITY");
    else {
      if (authority.expires_at <= asOf) reasons.push("AUTHORITY_EXPIRED");
      if (authority.revoked) reasons.push("AUTHORITY_REVOKED");
      if (!policy.authority_roles.includes(authority.role)) reasons.push("AUTHORITY_ROLE");
      if (authority.claim_version !== claim.version || authority.policy_version !== policy.version) reasons.push("AUTHORITY_VERSION");
      if (authority.intended_use !== policy.intended_use) reasons.push("AUTHORITY_USE");
    }
    return {
      result: {
        status: reasons.length ? "HOLD" : "ELIGIBLE",
        simulated: true,
        reasons,
        independent_support_origins: Array.from(origins).sort(asciiCompare),
        missing_evidence_types: missing,
        excluded_evidence: excluded
      },
      unassessedContradiction
    };
  }

  function evaluate(payload) {
    const {asOf, asOfText, reviewBudget, policy, claims, reports} = validate(payload);
    const byId = new Map(claims.map(c => [c.id, c]));
    const rawCounts = new Map(), events = new Map(), conceptCounts = new Map();
    const seen = new Set();
    reports.forEach(r => {
      rawCounts.set(r.claim_id, (rawCounts.get(r.claim_id) || 0) + 1);
      if (seen.has(r.key)) return;
      seen.add(r.key);
      events.set(r.claim_id, (events.get(r.claim_id) || 0) + 1);
      const canonical = byId.get(r.claim_id).concept;
      conceptCounts.set(canonical, (conceptCounts.get(canonical) || 0) + 1);
    });
    const total = seen.size;
    const items = claims.map(claim => {
      const count = rawCounts.get(claim.id) || 0;
      const independent = events.get(claim.id) || 0;
      const df = conceptCounts.get(claim.concept) || 0;
      const base = Math.floor((45 * claim.relevance + 35 * claim.consequence + 20 * claim.quality) / 100);
      let logarithm = 0;
      for (let n = 1 + df; n >= 2; n = Math.floor(n / 2)) logarithm++;
      const threshold = claim.relevance >= policy.min_relevance && claim.quality >= policy.min_quality;
      const bonus = threshold && independent >= 1 && df >= 1 && total > 1 ? Math.floor(policy.rarity_cap * (total - df) / (total - 1)) : 0;
      const evaluatedGate = gate(claim, policy, asOf);
      const reasons = [];
      if (claim.mandatory) reasons.push("MANDATORY_REVIEW");
      if (count > independent) reasons.push("DUPLICATE_REPORTS_COLLAPSED");
      if (independent === 0) reasons.push("NO_REPORT_OBSERVATIONS");
      if (bonus > 0) reasons.push("RARITY_BONUS_APPLIED");
      if (!threshold) reasons.push("RARITY_THRESHOLD_NOT_MET");
      if (evaluatedGate.unassessedContradiction) reasons.push("UNASSESSED_CONTRADICTION");
      return {
        id: claim.id,
        statement: claim.statement,
        canonical_concept: claim.concept,
        mandatory: claim.mandatory,
        relevance: claim.relevance,
        consequence: claim.consequence,
        quality: claim.quality,
        base_score: base,
        baseline_score: base + (independent >= 1 ? Math.min(20, 4 * logarithm) : 0),
        rarity_bonus: bonus,
        compensated_score: base + bonus,
        report_count: count,
        independent_events: independent,
        concept_events: df,
        reasons,
        gate: evaluatedGate.result
      };
    }).sort((a, b) => asciiCompare(a.id, b.id));
    const mandatory = items.filter(item => item.mandatory).map(item => item.id);
    const rank = scoreKey => items.filter(item => !item.mandatory).sort((a, b) => b[scoreKey] - a[scoreKey] || b.consequence - a.consequence || asciiCompare(a.id, b.id)).slice(0, reviewBudget).map(item => item.id);
    function mode(reviewIds, applied) {
      return {mandatory_ids: mandatory.slice(), review_ids: reviewIds.slice(), selected_ids: mandatory.concat(reviewIds), gate_applied: applied};
    }
    const baseline = rank("baseline_score"), compensated = rank("compensated_score");
    return {
      schema_version: "1.0",
      as_of: asOfText,
      policy: {id: policy.id, version: policy.version},
      items,
      modes: {
        baseline: mode(baseline, false),
        compensated: mode(compensated, false),
        full_control: mode(compensated, true)
      },
      diagnostics: {
        report_count: reports.length,
        unique_events: total,
        duplicate_reports: reports.length - total,
        claims: claims.length,
        mandatory_count: mandatory.length,
        review_budget: reviewBudget
      }
    };
  }
  const api = {evaluate, ValidationError};
  root.DeepSigmaZipf = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
