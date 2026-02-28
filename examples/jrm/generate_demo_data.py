#!/usr/bin/env python3
"""Generate synthetic demo data for JRM.

Produces:
  - suricata_demo.jsonl  (5,000 Suricata EVE JSON lines)
  - copilot_demo.jsonl   (200 agent log records)

Usage:
  python examples/jrm/generate_demo_data.py [--output-dir examples/jrm]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _ts(base: datetime, offset_secs: int) -> str:
    return (base + timedelta(seconds=offset_secs)).strftime("%Y-%m-%dT%H:%M:%S.%f+0000")


def generate_suricata(output: Path, count: int = 5000, seed: int = 42) -> int:
    """Generate realistic Suricata EVE JSONL."""
    rng = random.Random(seed)
    base = datetime(2026, 2, 28, 10, 0, 0, tzinfo=timezone.utc)

    signatures = [
        {"sid": 2010935, "rev": 6, "msg": "ET MALWARE Generic Trojan RAT", "cat": "A Network Trojan was Detected", "sev": 1},
        {"sid": 2010935, "rev": 7, "msg": "ET MALWARE Generic Trojan RAT", "cat": "A Network Trojan was Detected", "sev": 1},
        {"sid": 2024897, "rev": 3, "msg": "ET INFO Observed DNS Query to .cloud TLD", "cat": "Potentially Bad Traffic", "sev": 3},
        {"sid": 2100498, "rev": 12, "msg": "GPL ATTACK_RESPONSE id check returned root", "cat": "Potentially Bad Traffic", "sev": 2},
        {"sid": 2019876, "rev": 1, "msg": "ET SCAN Nmap Scripting Engine User-Agent", "cat": "Web Application Attack", "sev": 2},
        {"sid": 2030001, "rev": 2, "msg": "ET POLICY External IP Lookup", "cat": "Potential Corporate Privacy Violation", "sev": 4},
    ]

    event_types = ["alert", "dns", "http", "flow", "tls", "fileinfo"]
    sensors = ["sensor-east-01", "sensor-west-01"]
    src_ips_v4 = [f"10.0.{rng.randint(0,255)}.{rng.randint(1,254)}" for _ in range(50)]
    dst_ips_v4 = [f"192.168.{rng.randint(0,5)}.{rng.randint(1,254)}" for _ in range(30)]
    src_ips_v6 = [f"fe80::{rng.randint(1, 0xffff):x}" for _ in range(10)]

    written = 0
    with open(output, "w") as f:
        for i in range(count):
            ts = _ts(base, i)
            etype = rng.choice(event_types)
            sensor = rng.choice(sensors)

            # FP burst: sig 2010935 fires heavily in middle portion
            if 1000 <= i <= 2000 and rng.random() < 0.6:
                etype = "alert"

            src = rng.choice(src_ips_v4 + src_ips_v6) if rng.random() < 0.15 else rng.choice(src_ips_v4)
            dst = rng.choice(dst_ips_v4)

            record: dict = {
                "timestamp": ts,
                "flow_id": rng.randint(10**9, 10**10),
                "event_type": etype,
                "src_ip": src,
                "src_port": rng.randint(1024, 65535),
                "dest_ip": dst,
                "dest_port": rng.choice([80, 443, 8080, 53, 22]),
                "proto": rng.choice(["TCP", "UDP"]),
                "host": sensor,
            }

            if etype == "alert":
                sig = rng.choice(signatures)
                record["alert"] = {
                    "action": "allowed",
                    "gid": 1,
                    "signature_id": sig["sid"],
                    "rev": sig["rev"],
                    "signature": sig["msg"],
                    "category": sig["cat"],
                    "severity": sig["sev"],
                }
            elif etype == "dns":
                record["dns"] = {
                    "type": "query",
                    "rrname": rng.choice(["malicious.example.com", "safe.example.org",
                                          "api.cloud-service.io", "updates.vendor.com"]),
                    "rrtype": "A",
                }
            elif etype == "http":
                record["http"] = {
                    "hostname": rng.choice(["example.com", "api.internal", "cdn.service.net"]),
                    "url": rng.choice(["/", "/api/data", "/login", "/admin", "/.env"]),
                    "http_method": rng.choice(["GET", "POST"]),
                    "status": rng.choice([200, 301, 403, 404, 500]),
                    "length": rng.randint(100, 50000),
                }
            elif etype == "tls":
                record["tls"] = {
                    "subject": "CN=example.com",
                    "issuerdn": "CN=DigiCert",
                    "ja3": {"hash": f"{rng.randint(0, 2**128):032x}"[:32]},
                }
            elif etype == "fileinfo":
                record["fileinfo"] = {
                    "filename": rng.choice(["payload.exe", "doc.pdf", "image.png", "data.csv"]),
                    "size": rng.randint(100, 10_000_000),
                    "sha256": f"{rng.randint(0, 2**256):064x}"[:64],
                }

            # Inject a few malformed lines
            if i in (2500, 3500, 4500):
                f.write("this is a malformed JSON line for demo\n")
                written += 1
                continue

            f.write(json.dumps(record) + "\n")
            written += 1

    return written


def generate_copilot(output: Path, count: int = 200, seed: int = 43) -> int:
    """Generate synthetic copilot/agent JSONL."""
    rng = random.Random(seed)
    base = datetime(2026, 2, 28, 10, 0, 0, tzinfo=timezone.utc)

    agents = ["agent-alpha", "agent-beta", "agent-gamma"]
    tools = ["query_logs", "deploy_patch", "lookup_ioc", "check_reputation",
             "block_domain", "scan_host", "create_ticket"]
    prompts = [
        "Analyze network traffic for anomalies",
        "Deploy security patch to affected hosts",
        "Correlate DNS queries with threat intelligence",
        "Review firewall rule changes",
        "Investigate failed login attempts",
    ]
    guardrails = [
        ["requires_approval", "production_change"],
        ["pii_detected"],
        ["data_exfil_risk"],
        ["rate_limit_exceeded"],
    ]

    written = 0
    with open(output, "w") as f:
        for i in range(count):
            ts = (base + timedelta(seconds=i * 5)).isoformat()
            agent = rng.choice(agents)

            record_type = rng.choices(
                ["prompt", "tool_call", "response", "guardrail"],
                weights=[0.2, 0.3, 0.3, 0.2],
            )[0]

            record: dict = {
                "type": record_type,
                "timestamp": ts,
                "agent_id": agent,
                "confidence": round(rng.uniform(0.3, 0.98), 2),
            }

            if record_type == "prompt":
                record["prompt"] = rng.choice(prompts)
                record["target"] = "system"
                record["model"] = rng.choice(["claude-opus-4-6", "claude-sonnet-4-6"])
            elif record_type == "tool_call":
                tool = rng.choice(tools)
                record["tool_calls"] = [{"name": tool, "args": {"target": "10.0.0." + str(rng.randint(1, 254))}}]
                record["target"] = tool
            elif record_type == "response":
                record["response"] = f"Analysis complete. Found {rng.randint(0, 50)} issues."
                record["target"] = "user"
            elif record_type == "guardrail":
                record["guardrail_flags"] = rng.choice(guardrails)
                record["target"] = rng.choice(tools)

            # Inject one malformed line
            if i == 100:
                f.write("this is a malformed agent log line\n")
                written += 1
                continue

            f.write(json.dumps(record) + "\n")
            written += 1

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate JRM demo data")
    parser.add_argument("--output-dir", default="examples/jrm", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    n_suri = generate_suricata(out_dir / "suricata_demo.jsonl")
    n_agent = generate_copilot(out_dir / "copilot_demo.jsonl")

    print(f"Generated {n_suri} Suricata EVE lines -> {out_dir / 'suricata_demo.jsonl'}")
    print(f"Generated {n_agent} Copilot agent lines -> {out_dir / 'copilot_demo.jsonl'}")


if __name__ == "__main__":
    main()
