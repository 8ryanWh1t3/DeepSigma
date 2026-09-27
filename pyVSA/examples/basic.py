from deep_sigma_vsa import VoiceSemanticAdapter


text = (
    "We can probably cover the eastern sector with the current systems, "
    "but I'm concerned about the gap near the river."
)

packet = VoiceSemanticAdapter().from_transcript(text, speaker_id="commander-01")

print("=== JSON ===")
print(packet.to_json(indent=2))
print("\n=== RESONATOR ===")
print(packet.to_resonator_payload())
print("\n=== PATHFINDER ===")
print(packet.to_pathfinder_payload())
print("\n=== CERPA ===")
print(packet.to_cerpa_candidates())
