"""Run after installation: python examples/inspection_demo.py"""
from vinculum_folding import FoldWorld, NodeRef, audit, unfold
from vinculum_folding.demo import inspection_demo

if __name__ == "__main__":
    episode = inspection_demo()
    world = FoldWorld([episode])
    session = world.start(NodeRef(episode.episode_id, episode.revision, "summary"))
    session = world.follow(session, world.links(session.current)[0])
    assert session.current.node_id == "observation"
    assert world.back(session).current.node_id == "summary"
    assert world.replay(session.to_dict()) == session
    print("Traversal: summary -> observation -> back; replay verified")
    for finding in audit(episode).findings:
        if finding.code == "SCOPE_EXPANSION_REVIEW":
            print(finding.code, finding.message)
    print(unfold(episode, "summary-derivation")["fold"]["rationale"])
