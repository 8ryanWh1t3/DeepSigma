# Dependency Locking

This repo uses pinned lockfiles in `requirements/locks/` for deterministic installs.

## Lockfiles
- `requirements/locks/base.txt` — runtime base deps
- `requirements/locks/dev-excel-local.txt` — contributor/CI set for `dev,excel,local`
- `requirements/locks/rdf.txt` — `rdf` extra (with transitive pins)
- `requirements/locks/azure.txt` — `azure` extra (with transitive pins)
- `requirements/locks/snowflake.txt` — `snowflake` extra (with transitive pins)
- `requirements/locks/openclaw.txt` — `openclaw` extra (with transitive pins)
- `requirements/locks/kpi.txt` — KPI workflow tooling (`matplotlib` stack)

## Deterministic installs
```bash
pip install -c requirements/locks/dev-excel-local.txt -e ".[dev,excel,local]"
pip install -c requirements/locks/rdf.txt -e ".[rdf]"
```

Optional extras:
```bash
pip install -c requirements/locks/azure.txt -e ".[azure]"
pip install -c requirements/locks/snowflake.txt -e ".[snowflake]"
pip install -c requirements/locks/openclaw.txt -e ".[openclaw]"
```

## Regenerate lockfiles
```bash
bash scripts/update_locks.sh
```

Lockfile updates should be committed with any dependency change.
