from deepsigma_contrast import ContrastEngine, episode_from_dict
import json
from pathlib import Path

base = Path(__file__).parent
prior = episode_from_dict(json.loads((base / "prior_episode.json").read_text()))
current = episode_from_dict(json.loads((base / "current_episode.json").read_text()))

result = ContrastEngine().compare(current_episode=current, prior_episode=prior)
print(json.dumps(result.to_dict(), indent=2, default=str))
