from __future__ import annotations

class QueryType:
    WHY = "WHY"

class ResolutionStatus:
    NOT_FOUND = "NOT_FOUND"

class IRISQuery:
    def __init__(self, query_type=QueryType.WHY, text=""):
        self.query_type = query_type
        self.text = text

class IRISResponse:
    def __init__(self, query_id, query_type, status, summary, warnings=None):
        self.query_id = query_id
        self.query_type = query_type
        self.status = status
        self.summary = summary
        self.warnings = list(warnings or [])

class IRISConfig:
    def __init__(self, response_time_target_ms=60_000):
        self.response_time_target_ms = response_time_target_ms

    def validate(self):
        issues = []
        if self.response_time_target_ms <= 0:
            issues.append("response_time_target_ms must be positive")
        return issues

class IRISEngine:
    def __init__(self, config=None):
        self.config = config or IRISConfig()
        issues = self.config.validate()
        if issues:
            raise ValueError("Invalid IRISConfig: " + "; ".join(issues))

    def resolve(self, query):
        return IRISResponse(
            query_id="stub",
            query_type=query.query_type,
            status=ResolutionStatus.NOT_FOUND,
            summary="IRIS stub resolver (no artefacts wired)",
            warnings=["IRIS engine is not wired to DLR/RS/DS/MG"],
        )
