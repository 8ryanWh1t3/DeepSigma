#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TARGET_MILESTONE = os.getenv("TARGET_MILESTONE", "v2.1.0 (DISR Architecture)")
PROJECT_OWNER = os.getenv("PROJECT_OWNER", "8ryanWh1t3")
PROJECT_NUMBER = int(os.getenv("PROJECT_NUMBER", "2"))
STATUS_NAME = os.getenv("PROJECT_STATUS_DEFAULT", "Todo")

LANE_LABEL_TO_OPTION = {
    "lane:epic": "Epic",
    "lane:provider-layer": "Provider Layer",
    "lane:authority": "Authority",
    "lane:telemetry": "Telemetry",
    "lane:policy": "Policy",
    "lane:recovery-scale": "Recovery & Scale",
    "lane:benchmarks": "Benchmarks",
    "lane:automation-gate": "Automation Gate",
    "lane:audit-pack": "Audit Pack",
}


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def gh_graphql(query: str, vars_map: dict[str, str | int | None]) -> dict:
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in vars_map.items():
        if isinstance(value, int):
            cmd.extend(["-F", f"{key}={value}"])
        elif value is None:
            cmd.extend(["-f", f"{key}=null"])
        else:
            cmd.extend(["-f", f"{key}={value}"])
    raw = run(cmd)
    return json.loads(raw)


def gh_issue_comment(repo: str, number: int, body: str) -> None:
    run(
        [
            "gh",
            "api",
            f"repos/{repo}/issues/{number}/comments",
            "-f",
            f"body={body}",
        ]
    )


def get_project_meta() -> dict:
    query = """
query($owner:String!, $number:Int!) {
  user(login:$owner) {
    projectV2(number:$number) {
      id
      fields(first:50) {
        nodes {
          ... on ProjectV2FieldCommon { id name }
          ... on ProjectV2SingleSelectField {
            id
            name
            options { id name }
          }
        }
      }
    }
  }
}
"""
    data = gh_graphql(query, {"owner": PROJECT_OWNER, "number": PROJECT_NUMBER})
    proj = data["data"]["user"]["projectV2"]
    if not proj:
        raise RuntimeError("Project not found")

    status_field = None
    lane_field = None
    for field in proj["fields"]["nodes"]:
        if field.get("name") == "Status":
            status_field = field
        if field.get("name") == "Lane":
            lane_field = field

    if not status_field or not lane_field:
        raise RuntimeError("Missing Status or Lane field in project")

    status_option_id = next(
        (opt["id"] for opt in status_field.get("options", []) if opt["name"] == STATUS_NAME),
        None,
    )
    if not status_option_id:
        raise RuntimeError(f"Status option '{STATUS_NAME}' not found")

    lane_option_ids = {opt["name"]: opt["id"] for opt in lane_field.get("options", [])}

    return {
        "project_id": proj["id"],
        "status_field_id": status_field["id"],
        "status_option_id": status_option_id,
        "lane_field_id": lane_field["id"],
        "lane_option_ids": lane_option_ids,
    }


def find_project_item_id(project_id: str, issue_number: int) -> str | None:
    query = """
query($project:ID!, $cursor:String) {
  node(id:$project) {
    ... on ProjectV2 {
      items(first:100, after:$cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          content {
            __typename
            ... on Issue { number }
          }
        }
      }
    }
  }
}
"""
    cursor: str | None = None
    while True:
        data = gh_graphql(query, {"project": project_id, "cursor": cursor})
        items = data["data"]["node"]["items"]
        for node in items["nodes"]:
            content = node.get("content") or {}
            if content.get("__typename") == "Issue" and content.get("number") == issue_number:
                return node["id"]
        if not items["pageInfo"]["hasNextPage"]:
            return None
        cursor = items["pageInfo"]["endCursor"]


def add_issue_to_project(project_id: str, issue_node_id: str) -> str | None:
    mutation = """
mutation($project:ID!, $content:ID!) {
  addProjectV2ItemById(input:{projectId:$project, contentId:$content}) {
    item { id }
  }
}
"""
    try:
        data = gh_graphql(mutation, {"project": project_id, "content": issue_node_id})
        return data["data"]["addProjectV2ItemById"]["item"]["id"]
    except subprocess.CalledProcessError:
        return None


def update_single_select(project_id: str, item_id: str, field_id: str, option_id: str) -> None:
    mutation = """
mutation($project:ID!, $item:ID!, $field:ID!, $option:String!) {
  updateProjectV2ItemFieldValue(input:{
    projectId:$project,
    itemId:$item,
    fieldId:$field,
    value:{singleSelectOptionId:$option}
  }) {
    projectV2Item { id }
  }
}
"""
    gh_graphql(
        mutation,
        {"project": project_id, "item": item_id, "field": field_id, "option": option_id},
    )


def main() -> int:
    event_path = os.getenv("GITHUB_EVENT_PATH")
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not event_path or not Path(event_path).exists():
        print("Missing GITHUB_EVENT_PATH")
        return 1

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    issue = event.get("issue")
    if not issue:
        print("No issue in event payload")
        return 0

    issue_number = issue["number"]
    issue_node_id = issue["node_id"]
    labels = {label["name"] for label in issue.get("labels", [])}
    milestone = issue.get("milestone")
    milestone_title = milestone["title"] if milestone else None

    if milestone_title != TARGET_MILESTONE:
        print(f"Skipping issue #{issue_number}: milestone is not '{TARGET_MILESTONE}'")
        return 0

    lane_labels = [name for name in labels if name in LANE_LABEL_TO_OPTION]
    if len(lane_labels) != 1:
        if repo:
            msg = (
                f"Intake gate failed for #{issue_number}: add exactly one `lane:*` label.\n\n"
                "Allowed labels:\n"
                "- `lane:epic`\n"
                "- `lane:provider-layer`\n"
                "- `lane:authority`\n"
                "- `lane:telemetry`\n"
                "- `lane:policy`\n"
                "- `lane:recovery-scale`\n"
                "- `lane:benchmarks`\n"
                "- `lane:automation-gate`\n"
                "- `lane:audit-pack`\n"
            )
            gh_issue_comment(repo, issue_number, msg)
        print(f"Lane label validation failed for #{issue_number}: {lane_labels}")
        return 1

    lane_option_name = LANE_LABEL_TO_OPTION[lane_labels[0]]

    meta = get_project_meta()
    lane_option_id = meta["lane_option_ids"].get(lane_option_name)
    if not lane_option_id:
        raise RuntimeError(f"Lane option not found: {lane_option_name}")

    item_id = add_issue_to_project(meta["project_id"], issue_node_id)
    if not item_id:
        item_id = find_project_item_id(meta["project_id"], issue_number)
    if not item_id:
        raise RuntimeError(f"Could not resolve project item for issue #{issue_number}")

    update_single_select(
        meta["project_id"], item_id, meta["status_field_id"], meta["status_option_id"]
    )
    update_single_select(meta["project_id"], item_id, meta["lane_field_id"], lane_option_id)

    print(f"Issue #{issue_number} synced to project: status={STATUS_NAME}, lane={lane_option_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
