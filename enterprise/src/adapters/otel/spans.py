"""Canonical span names and attribute keys for DeepSigma OTel telemetry.

All span names and attribute keys MUST be registered here.
The CI test ``test_otel_span_registry`` enforces that every
``start_as_current_span`` and ``set_attribute`` call in the
exporter references a value from this module.

Namespace convention: ``deepsigma.<resource>.<field>``

Span names use short resource labels (no ``deepsigma.`` prefix)
because they appear as top-level trace names in observability UIs.
Attribute keys use the ``deepsigma.`` namespace to avoid collisions
with vendor or OTel semantic convention attributes.
"""

from __future__ import annotations


# ── Span Names ───────────────────────────────────────────────────
# These are the first argument to tracer.start_as_current_span().

SPAN_DECISION_EPISODE = "decision_episode"
SPAN_PHASE_PREFIX = "phase"           # actual span: "phase.{name}"
SPAN_DRIFT_EVENT = "drift_event"
SPAN_COHERENCE_EVAL = "coherence_evaluation"
SPAN_TOOL_CALL = "tool_call"
SPAN_LLM_COMPLETION = "llm.completion"

# Event names (added to spans via add_event)
EVENT_DEGRADE_TRIGGERED = "degrade_triggered"

ALL_SPAN_NAMES: frozenset[str] = frozenset({
    SPAN_DECISION_EPISODE,
    SPAN_DRIFT_EVENT,
    SPAN_COHERENCE_EVAL,
    SPAN_TOOL_CALL,
    SPAN_LLM_COMPLETION,
    # phase.* are dynamic — validated by prefix check
})

SPAN_PHASE_NAMES: frozenset[str] = frozenset({
    "context", "plan", "act", "verify",
})


# ── Attribute Keys ───────────────────────────────────────────────
# Every set_attribute key used in the exporter.

# Episode attributes
ATTR_EPISODE_ID = "deepsigma.episode.id"
ATTR_EPISODE_DECISION_TYPE = "deepsigma.episode.decision_type"
ATTR_EPISODE_DEGRADE_STEP = "deepsigma.episode.degrade_step"

# Phase attributes
ATTR_PHASE_NAME = "deepsigma.phase.name"
ATTR_PHASE_DURATION_MS = "deepsigma.phase.duration_ms"

# Drift attributes
ATTR_DRIFT_ID = "deepsigma.drift.id"
ATTR_DRIFT_TYPE = "deepsigma.drift.type"
ATTR_DRIFT_SEVERITY = "deepsigma.drift.severity"
ATTR_DRIFT_EPISODE_ID = "deepsigma.drift.episode_id"

# Coherence attributes
ATTR_COHERENCE_SCORE = "deepsigma.coherence.score"
ATTR_COHERENCE_GRADE = "deepsigma.coherence.grade"
ATTR_COHERENCE_DIMENSION_PREFIX = "deepsigma.coherence"  # .{dim_name}

# Degrade event attributes
ATTR_DEGRADE_STEP = "deepsigma.degrade.step"

# Tool call attributes
ATTR_TOOL_NAME = "deepsigma.tool.name"
ATTR_TOOL_VERSION = "deepsigma.tool.version"
ATTR_TOOL_STATUS = "deepsigma.tool.status"
ATTR_TOOL_DURATION_MS = "deepsigma.tool.duration_ms"

# LLM call attributes
ATTR_LLM_MODEL = "deepsigma.llm.model"
ATTR_LLM_PROMPT_TOKENS = "deepsigma.llm.prompt_tokens"
ATTR_LLM_COMPLETION_TOKENS = "deepsigma.llm.completion_tokens"
ATTR_LLM_TOTAL_TOKENS = "deepsigma.llm.total_tokens"
ATTR_LLM_LATENCY_MS = "deepsigma.llm.latency_ms"

ALL_ATTRIBUTE_KEYS: frozenset[str] = frozenset({
    ATTR_EPISODE_ID,
    ATTR_EPISODE_DECISION_TYPE,
    ATTR_EPISODE_DEGRADE_STEP,
    ATTR_PHASE_NAME,
    ATTR_PHASE_DURATION_MS,
    ATTR_DRIFT_ID,
    ATTR_DRIFT_TYPE,
    ATTR_DRIFT_SEVERITY,
    ATTR_DRIFT_EPISODE_ID,
    ATTR_COHERENCE_SCORE,
    ATTR_COHERENCE_GRADE,
    ATTR_DEGRADE_STEP,
    ATTR_TOOL_NAME,
    ATTR_TOOL_VERSION,
    ATTR_TOOL_STATUS,
    ATTR_TOOL_DURATION_MS,
    ATTR_LLM_MODEL,
    ATTR_LLM_PROMPT_TOKENS,
    ATTR_LLM_COMPLETION_TOKENS,
    ATTR_LLM_TOTAL_TOKENS,
    ATTR_LLM_LATENCY_MS,
    # coherence.{dim} are dynamic — validated by prefix check
})


# ── Metric Names ─────────────────────────────────────────────────

METRIC_EPISODES_TOTAL = "sigma.episodes.total"
METRIC_EPISODE_LATENCY_MS = "sigma.episode.latency_ms"
METRIC_DRIFT_TOTAL = "sigma.drift.total"
METRIC_COHERENCE_SCORE = "sigma.coherence.score"
METRIC_TOOL_LATENCY_MS = "sigma.tool.latency_ms"
METRIC_LLM_LATENCY_MS = "sigma.llm.latency_ms"
METRIC_LLM_TOKENS_TOTAL = "sigma.llm.tokens.total"

ALL_METRIC_NAMES: frozenset[str] = frozenset({
    METRIC_EPISODES_TOTAL,
    METRIC_EPISODE_LATENCY_MS,
    METRIC_DRIFT_TOTAL,
    METRIC_COHERENCE_SCORE,
    METRIC_TOOL_LATENCY_MS,
    METRIC_LLM_LATENCY_MS,
    METRIC_LLM_TOKENS_TOTAL,
})
