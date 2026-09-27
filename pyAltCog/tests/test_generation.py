from pyaltcog.generation import TemplateHypothesisGenerator
from pyaltcog.models import AlternativeKind, ExceptionClusterCard


def test_template_generator_covers_all_kinds():
    cluster = ExceptionClusterCard(
        id="ECC-1", stream_id="S", signal_ids=["FSR-1"], created_at="t",
        centroid_terms=["handoff", "identity", "reset"],
    )
    drafts = TemplateHypothesisGenerator().generate(cluster, "random noise")
    assert {d.kind for d in drafts} == set(AlternativeKind)
    assert all("random noise" in d.rationale for d in drafts)
