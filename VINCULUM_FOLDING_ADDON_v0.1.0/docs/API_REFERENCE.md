# Public API

```python
from vinculum_folding import (
    FoldEpisode, FoldWorld, NodeRef, EpisodeJournal,
    from_pipeline, host_pair_results,
    audit, project, unfold, compare, review_input,
    export_bundle, verify_bundle, episode_template, unassessed_lenses,
)
```

| Call | Result / boundary |
|---|---|
| `FoldEpisode.from_dict(data)` | Validated immutable snapshot; input copied |
| `FoldEpisode.load(path)` | Bounded strict UTF-8 JSON load |
| `episode.to_dict()` | Independent mutable copy, not a mutable view of the episode |
| `episode.digest` | Full snapshot SHA-256, not source authentication |
| `episode.revise(recorded_at=..., **changes)` | New revision, same mission/episode identity, predecessor digest retained |
| `from_pipeline(run, episode_id=..., mission_id=..., title=..., recorded_at=...)` | Exact retained host capture plus typed aspect/fold projections |
| `host_pair_results(episode)` | Original host pair result dictionary; never a new JIT result |
| `audit(episode).to_dict()` | Structural findings, aspect inventory, lens assessment counts and declared source groups |
| `project(episode)` | Read-only host UI data contract |
| `unfold(episode, fold_id)` | Both endpoints, evidence, JIT, original host pair result where present |
| `compare(before, after)` | Revision content changes; no truth/authority winner |
| `review_input(episode)` | Non-executing DRAFT_REVIEW_INPUT |
| `export_bundle(episode, new_directory)` | New sidecar bundle; never overwrites an existing directory |
| `verify_bundle(directory)` | Reproduces the retained episode/projections and checks unsigned hashes |
| `FoldWorld(episodes)` | Fixed collection keyed by episode and revision |
| `world.start(NodeRef(...))` | Immutable traversal session |
| `world.links(ref)` | Recorded adjacent links, including unresolved external targets |
| `world.follow(session, step)` | New focus with recorded return path; does not mutate the world |
| `world.back(session)` | Prior focus or unchanged origin |
| `world.replay(session.to_dict())` | Exact-world replay; refuses a stale or invalid trail |
| `world.neighborhood(ref, depth=1, max_nodes=1000)` | Bounded relationship reach with truncation/missing-target disclosure |
| `EpisodeJournal.create(new_path)` | Explicit writer creation; rejects existing paths |
| `EpisodeJournal.open(path, read_only=True)` | Read-only by default; refuses missing/invalid journals |
| `journal.append(snapshot)` | Transactional next-revision append; rejects stale writers |
| `journal.get(id, revision=None)` | Exact historical revision or stored latest |
| `journal.verify(id, expected_tip=None)` | Internal content continuity; optional independently expected tip check |

`FoldError` is the validation error type. Filesystem failures may also raise
`OSError`; the CLI reports either as exit code 2. No API establishes trusted
operational authority. `revise()` and journal append are data preparation and
storage, not COMPOSER or CERPA commands.

See `examples/generated-inspection/episode.json` for the complete JSON contract
example. `model.validate_episode` is the executable validation specification.
