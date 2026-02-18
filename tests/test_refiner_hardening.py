"""Tests for exhaust refiner hardening: entity_type, assumptions, alternatives, confidence calibration."""
from dashboard.server.models_exhaust import (
    DecisionEpisode,
    EpisodeEvent,
    EventType,
    Source,
    TruthItem,
)
from engine.exhaust_refiner import (
    _calibrate_confidence,
    _infer_entity_type,
    extract_reasoning,
    extract_truth,
)


def _make_episode(episode_id="ep-test", events=None):
    return DecisionEpisode(
        episode_id=episode_id,
        session_id="sess-1",
        events=events or [],
    )


def _make_event(event_type="metric", payload=None, episode_id="ep-test"):
    return EpisodeEvent(
        event_id="evt-1",
        episode_id=episode_id,
        event_type=EventType(event_type),
        source=Source.manual,
        payload=payload or {},
    )


class TestEntityTypeInference:
    def test_cpu_is_infrastructure(self):
        assert _infer_entity_type("cpu_usage") == "infrastructure"

    def test_latency_is_performance(self):
        assert _infer_entity_type("api_latency_p99") == "performance"

    def test_error_is_reliability(self):
        assert _infer_entity_type("error_rate") == "reliability"

    def test_revenue_is_business(self):
        assert _infer_entity_type("daily_revenue") == "business"

    def test_token_is_cost(self):
        assert _infer_entity_type("token_count") == "cost"

    def test_unknown_returns_empty(self):
        assert _infer_entity_type("foobar_xyz") == ""

    def test_case_insensitive(self):
        assert _infer_entity_type("CPU_Usage") == "infrastructure"

    def test_entity_type_in_extracted_truth(self):
        """extract_truth populates entity_type on metric truth items."""
        events = [_make_event("metric", {"name": "cpu_usage", "value": 75, "unit": "%"})]
        episode = _make_episode(events=events)
        items = extract_truth(episode)
        assert len(items) == 1
        assert items[0].entity_type == "infrastructure"

    def test_entity_type_empty_for_completion_claims(self):
        """Completion-derived claims have empty entity_type (no name to infer from)."""
        events = [_make_event("completion", {"text": "The system latency is 50ms on average"})]
        episode = _make_episode(events=events)
        items = extract_truth(episode)
        assert len(items) >= 1
        # Completion claims don't have entity/property set, so entity_type stays empty
        assert items[0].entity_type == ""


class TestConfidenceCalibration:
    def test_boost_with_certainty_words(self):
        assert _calibrate_confidence(0.6, "We observed the CPU spike") == 0.7

    def test_reduce_with_hedging_words(self):
        assert _calibrate_confidence(0.6, "The value is possibly incorrect") == 0.5

    def test_neutral_unchanged(self):
        assert _calibrate_confidence(0.6, "The value is 42") == 0.6

    def test_boost_capped_at_1(self):
        assert _calibrate_confidence(0.95, "confirmed and verified measurement") == 1.0

    def test_hedge_floored_at_01(self):
        assert _calibrate_confidence(0.15, "maybe it might be uncertain") == 0.1

    def test_both_cancel_out(self):
        """When both boost and hedge words present, returns base unchanged."""
        assert _calibrate_confidence(0.6, "We observed it but possibly wrong") == 0.6

    def test_calibration_in_truth_extraction(self):
        """Completion claims with certainty words get boosted confidence."""
        events = [_make_event("completion", {
            "text": "We confirmed the total count is 1500 items",
        })]
        episode = _make_episode(events=events)
        items = extract_truth(episode)
        assert len(items) >= 1
        # "confirmed" should boost from 0.6 to 0.7
        assert items[0].confidence == 0.7


class TestAssumptionExtraction:
    def test_assumptions_extracted(self):
        events = [_make_event("completion", {
            "text": (
                "I recommend deploying the new version.\n"
                "Assuming the load balancer can handle the traffic spike.\n"
                "Given that the canary deployment showed no errors."
            ),
        })]
        episode = _make_episode(events=events)
        items = extract_reasoning(episode)
        assert len(items) >= 1
        # At least one item should have assumptions
        has_assumptions = any(len(item.assumptions) > 0 for item in items)
        assert has_assumptions
        # Check specific assumption content
        all_assumptions = []
        for item in items:
            all_assumptions.extend(item.assumptions)
        assert any("load balancer" in a for a in all_assumptions)
        assert any("canary deployment" in a for a in all_assumptions)


class TestAlternativeExtraction:
    def test_alternatives_extracted(self):
        events = [_make_event("completion", {
            "text": (
                "We should use Redis for caching.\n"
                "Alternatively, we could use Memcached for simpler setup.\n"
                "Another option is to use the database query cache."
            ),
        })]
        episode = _make_episode(events=events)
        items = extract_reasoning(episode)
        assert len(items) >= 1
        has_alternatives = any(len(item.alternatives) > 0 for item in items)
        assert has_alternatives
        all_alternatives = []
        for item in items:
            all_alternatives.extend(item.alternatives)
        assert any("Memcached" in a for a in all_alternatives)


class TestRationaleEnrichment:
    def test_tool_rationale_from_context(self):
        """Tool invocations get rationale enriched from preceding completion."""
        events = [
            _make_event("completion", {
                "text": "Let me check the deployment status first",
            }, episode_id="ep-test"),
            _make_event("tool", {
                "name": "check_deploy",
                "input": {"target": "prod"},
            }, episode_id="ep-test"),
        ]
        # Need unique event_ids
        events[0].event_id = "evt-1"
        events[1].event_id = "evt-2"
        episode = _make_episode(events=events)
        items = extract_reasoning(episode)
        tool_items = [i for i in items if "check_deploy" in i.decision]
        assert len(tool_items) == 1
        # Rationale should include context from preceding completion
        assert "deployment status" in tool_items[0].rationale


class TestBackwardCompat:
    def test_entity_type_defaults_empty(self):
        """TruthItem with no entity_type still works (default empty string)."""
        item = TruthItem(claim="test claim")
        assert item.entity_type == ""

    def test_existing_truth_extraction_still_works(self):
        """Basic truth extraction produces valid items."""
        events = [_make_event("metric", {"name": "x", "value": 1})]
        episode = _make_episode(events=events)
        items = extract_truth(episode)
        assert len(items) == 1
        assert items[0].claim == "x = 1"
