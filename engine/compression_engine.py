from primitives.compression import compress_claims


def apply_compression(episode: dict) -> dict:
    """Apply compression to the episode claims and store result."""

    if "claims" not in episode:
        episode["claims"] = []

    episode["compression"] = compress_claims(episode["claims"])
    return episode
