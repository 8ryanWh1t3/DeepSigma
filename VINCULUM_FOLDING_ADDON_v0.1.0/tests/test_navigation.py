import copy
import dataclasses
import pytest
from vinculum_folding import FoldEpisode, FoldError, FoldWorld, NavigationSession, NodeRef


def test_traverse_back_replay(episode):
    w = FoldWorld([episode])
    root = w.start(NodeRef(episode.episode_id, 1, "summary"))
    session = w.follow(root, w.links(root.current)[0])
    assert session.current.node_id == "observation"
    assert w.back(session) == root
    assert w.back(root) == root
    assert w.replay(session.to_dict()) == session
    assert episode.digest == w._episodes[(episode.episode_id, 1)].digest


def test_world_order_determinism(episode):
    newer = episode.revise(recorded_at="2026-10-03T12:00:00-04:00")
    assert FoldWorld([episode, newer]).digest == FoldWorld([newer, episode]).digest
    with pytest.raises(FoldError): FoldWorld([episode, episode])


def test_stale_world(episode):
    w = FoldWorld([episode]); root = w.start(NodeRef(episode.episode_id, 1, "summary"))
    other = FoldWorld([episode, episode.revise(recorded_at="2026-10-03T12:00:00-04:00")])
    with pytest.raises(FoldError): other.back(root)
    with pytest.raises(FoldError): other.replay(root.to_dict())


def test_nonadjacent_step(episode):
    w = FoldWorld([episode]); root = w.start(NodeRef(episode.episode_id, 1, "summary"))
    wrong = w.links(NodeRef(episode.episode_id, 1, "count"))[0]
    with pytest.raises(FoldError): w.follow(root, wrong)


def test_cross_episode_missing_then_loaded(episode, data):
    data["external_links"] = [{"id": "cross", "from_node": "summary", "to_episode_id": "OTHER",
        "to_revision": 1, "to_node": "observation", "relation": "DEPENDS_ON", "rationale": "declared test dependency"}]
    source = FoldEpisode(data)
    w = FoldWorld([source]); root = w.start(NodeRef(source.episode_id, 1, "summary"))
    step = next(s for s in w.links(root.current) if s.link_id == "cross")
    assert not step.resolved
    with pytest.raises(FoldError): w.follow(root, step)
    assert w.neighborhood(root.current)["unresolved_targets"]
    other = episode.to_dict(); other["episode_id"] = "OTHER"; other["mission_id"] = "OTHER-MISSION"
    world = FoldWorld([source, FoldEpisode(other)])
    root = world.start(NodeRef(source.episode_id, 1, "summary"))
    step = next(s for s in world.links(root.current) if s.link_id == "cross")
    session = world.follow(root, step)
    assert session.current.episode_id == "OTHER"
    assert world.back(session) == root
    assert world.replay(session.to_dict()) == session


def test_neighborhood_cycles_and_capacity(episode):
    w = FoldWorld([episode]); ref = NodeRef(episode.episode_id, 1, "summary")
    result = w.neighborhood(ref, depth=100)
    assert len(result["nodes"]) == 4
    assert not result["capacity_truncated"]
    assert w.neighborhood(ref, depth=10, max_nodes=2)["capacity_truncated"]


@pytest.mark.parametrize("kwargs", [{"depth": -1}, {"depth": True}, {"depth": 101}, {"max_nodes": 0}, {"max_nodes": True}])
def test_neighborhood_capacity_validation(episode, kwargs):
    w = FoldWorld([episode])
    with pytest.raises(FoldError): w.neighborhood(NodeRef(episode.episode_id, 1, "summary"), **kwargs)


def test_trail_tampering(episode):
    w = FoldWorld([episode]); root = w.start(NodeRef(episode.episode_id, 1, "summary"))
    session = w.follow(root, w.links(root.current)[0])
    trail = session.to_dict(); trail["steps"][0]["reverse"] = True
    with pytest.raises(FoldError): w.replay(trail)
    trail = session.to_dict(); trail["steps"][0]["execute"] = "APPLY"
    with pytest.raises(FoldError): w.replay(trail)
    corrupt = dataclasses.replace(session, trail=session.trail[::-1])
    with pytest.raises(FoldError): w.back(corrupt)


def test_exported_node_is_copy(episode):
    w = FoldWorld([episode]); ref = NodeRef(episode.episode_id, 1, "summary")
    w.node(ref)["value"]["text"] = "mutated"
    assert w.node(ref)["value"]["text"] != "mutated"
