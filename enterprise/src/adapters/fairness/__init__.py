"""Fairness monitoring adapter — hybrid connector for external fairness tools.

DeepSigma delegates fairness computation to external tools (AIF360, Fairlearn,
custom pipelines) and ingests their results as drift signals. This adapter
provides:

1. A schema for fairness audit events
2. Ingest functions that convert external fairness reports to DriftSignal
3. Connector hooks for popular fairness libraries
"""
