from deep_sigma_p2pc2 import AuthorityEnvelope, CerpaEngine, Scope
from deep_sigma_p2pc2.models import MissionObject
from deep_sigma_p2pc2.reconcile import Reconciler
from deep_sigma_p2pc2.world import WorldModel


def test_cerpa_patch_requires_patch_and_apply_scope():
    world = WorldModel()
    world.ingest(MissionObject.observation(entity_id="e", value="A", origin_peer="a"))
    world.ingest(MissionObject.observation(entity_id="e", value="B", origin_peer="b"))
    conflict = Reconciler().detect(world)[0]

    from deep_sigma_p2pc2.authority import AuthorityEngine
    auth = AuthorityEngine()
    auth.install(AuthorityEnvelope(
        authority_id="cmd",
        issuer="HQ",
        subject="reviewer",
        scopes={Scope.PATCH, Scope.APPLY},
    ))

    cerpa = CerpaEngine(auth)
    case = cerpa.open(conflict)
    cerpa.review(case.case_id, reviewer="reviewer", rationale="resolve contradiction")
    cerpa.propose_patch(
        case.case_id,
        author="reviewer",
        value="A",
        authority_id="cmd",
        rationale="validated evidence",
    )
    applied = cerpa.apply(case.case_id, actor="reviewer")
    assert applied.value == "A"
    assert applied.version == 2
