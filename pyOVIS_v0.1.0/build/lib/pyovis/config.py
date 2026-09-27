from dataclasses import dataclass

DEFAULT_MODEL = "ATH-MaaS/Ovis-Omni-Embedding-3B"
DEFAULT_QUERY_INSTRUCTION = "Represent this query for semantic retrieval."
DEFAULT_CANDIDATE_INSTRUCTION = "Represent this candidate for semantic retrieval."


@dataclass(frozen=True)
class Settings:
    model: str = DEFAULT_MODEL
    query_instruction: str = DEFAULT_QUERY_INSTRUCTION
    candidate_instruction: str = DEFAULT_CANDIDATE_INSTRUCTION
    residual_threshold: float = 0.45
