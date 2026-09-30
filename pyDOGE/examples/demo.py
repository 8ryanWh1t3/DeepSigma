from pathlib import Path
import json

from pydoge import WorkSystem

HERE = Path(__file__).resolve().parent
ws = WorkSystem.load(HERE / "agency.json")

print("=== WHY DOES W2 EXIST? ===")
print(json.dumps(ws.explain("W2"), indent=2))

print("\n=== BLAST RADIUS OF W1 ===")
print(json.dumps(ws.calculate_blast_radius("W1"), indent=2))

print("\n=== WORK-FIRST OPTIMIZATION ===")
print(json.dumps(ws.optimize(), indent=2))
