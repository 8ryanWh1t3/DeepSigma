"""Compile Deep Sigma AgentMissionContract objects to OpenShell policy YAML."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Set, Tuple

import yaml

from .models import (
    AccessMode,
    AgentMissionContract,
    EndpointPermission,
    PolicyDelta,
    PolicyProjection,
    canonical_hash,
    _safe_key,
)

# Conservative runtime paths based on OpenShell's documented default/baseline
# policy.  Mission-specific paths are appended, never inferred.
_BASE_READ_ONLY = [
    "/bin",
    "/usr",
    "/lib",
    "/proc",
    "/etc",
    "/var/log",
    "/dev/urandom",
]
_BASE_READ_WRITE = ["/tmp", "/dev/null"]


class OpenShellPolicyCompiler:
    """One-way projection from Deep Sigma mission semantics to enforcement."""

    def compile(self, contract: AgentMissionContract) -> PolicyProjection:
        contract.validate()

        filesystem = {
            "include_workdir": bool(contract.include_workdir),
            "read_only": _unique(_BASE_READ_ONLY + list(contract.read_only_paths)),
            "read_write": _unique(_BASE_READ_WRITE + list(contract.read_write_paths)),
        }
        policy: Dict[str, Any] = {
            "version": 1,
            "filesystem_policy": filesystem,
            "landlock": {"compatibility": "best_effort"},
        }

        if contract.process_user or contract.process_group:
            process: Dict[str, str] = {}
            if contract.process_user:
                process["run_as_user"] = contract.process_user
            if contract.process_group:
                process["run_as_group"] = contract.process_group
            policy["process"] = process

        if contract.endpoints:
            network: Dict[str, Any] = {}
            for permission in contract.endpoints:
                network[_safe_key(permission.name)] = self._compile_endpoint(permission)
            policy["network_policies"] = network

        static_surface = {
            "filesystem_policy": policy.get("filesystem_policy", {}),
            "landlock": policy.get("landlock", {}),
            "process": policy.get("process", {}),
        }
        dynamic_surface = {
            "network_policies": policy.get("network_policies", {}),
            "network_middlewares": policy.get("network_middlewares", {}),
        }
        yaml_text = yaml.safe_dump(policy, sort_keys=False, default_flow_style=False)
        return PolicyProjection(
            contract_id=contract.contract_id,
            contract_hash=contract.canonical_hash(),
            policy=policy,
            yaml_text=yaml_text,
            policy_hash=canonical_hash(policy),
            static_hash=canonical_hash(static_surface),
            dynamic_hash=canonical_hash(dynamic_surface),
        )

    def _compile_endpoint(self, permission: EndpointPermission) -> Dict[str, Any]:
        permission.validate()
        endpoint: Dict[str, Any] = {
            "host": permission.host,
            "port": int(permission.port),
        }
        if permission.protocol:
            endpoint["protocol"] = permission.protocol
        if permission.tls:
            endpoint["tls"] = permission.tls
        if permission.enforcement:
            endpoint["enforcement"] = permission.enforcement

        if permission.rules:
            rules: List[Dict[str, Any]] = []
            for rule in permission.rules:
                rules.append(
                    {
                        "allow" if rule.allow else "deny": {
                            "method": rule.method.upper(),
                            "path": rule.path,
                        }
                    }
                )
            endpoint["rules"] = rules
        elif permission.access:
            endpoint["access"] = permission.access

        result: Dict[str, Any] = {
            "name": permission.name,
            "endpoints": [endpoint],
            "binaries": [{"path": p} for p in _unique(permission.binaries)],
        }
        return result


def diff_policies(old: Dict[str, Any] | None, new: Dict[str, Any]) -> PolicyDelta:
    """Classify an OpenShell policy change for Deep Sigma governance.

    OpenShell has startup-time static controls and hot-reloadable dynamic network
    controls.  Deep Sigma additionally asks whether the proposed delta *expands*
    what the agent can touch, because expansion should normally require explicit
    authority/human review.
    """
    old = deepcopy(old or {"version": 1})
    new = deepcopy(new)

    static_keys = ("filesystem_policy", "landlock", "process")
    dynamic_keys = ("network_policies", "network_middlewares")
    static_changed = any(old.get(k, {}) != new.get(k, {}) for k in static_keys)
    dynamic_changed = any(old.get(k, {}) != new.get(k, {}) for k in dynamic_keys)

    reasons: List[str] = []
    expands = False

    old_fs = old.get("filesystem_policy", {}) or {}
    new_fs = new.get("filesystem_policy", {}) or {}
    old_ro, old_rw = set(old_fs.get("read_only", []) or []), set(old_fs.get("read_write", []) or [])
    new_ro, new_rw = set(new_fs.get("read_only", []) or []), set(new_fs.get("read_write", []) or [])

    added_rw = new_rw - old_rw
    if added_rw:
        expands = True
        reasons.append("filesystem_write_added:" + ",".join(sorted(added_rw)))
    promoted_rw = (new_rw & old_ro) - old_rw
    if promoted_rw:
        expands = True
        reasons.append("filesystem_promoted_to_write:" + ",".join(sorted(promoted_rw)))
    added_ro = new_ro - old_ro - old_rw
    if added_ro:
        expands = True
        reasons.append("filesystem_read_added:" + ",".join(sorted(added_ro)))
    if bool(new_fs.get("include_workdir")) and not bool(old_fs.get("include_workdir")):
        expands = True
        reasons.append("workdir_access_enabled")

    old_network = _network_capabilities(old.get("network_policies", {}) or {})
    new_network = _network_capabilities(new.get("network_policies", {}) or {})

    old_hosts = {(x[0], x[1], x[2]) for x in old_network}
    new_hosts = {(x[0], x[1], x[2]) for x in new_network}
    added_hosts = new_hosts - old_hosts
    if added_hosts:
        expands = True
        reasons.append(
            "network_endpoint_added:"
            + ",".join(f"{h}:{p}/{proto or 'tcp'}" for h, p, proto in sorted(added_hosts))
        )

    old_strength = _max_access_by_endpoint(old_network)
    new_strength = _max_access_by_endpoint(new_network)
    for endpoint, strength in new_strength.items():
        if strength > old_strength.get(endpoint, -1):
            expands = True
            if endpoint in old_strength:
                reasons.append(
                    f"network_access_expanded:{endpoint[0]}:{endpoint[1]}:{old_strength[endpoint]}->{strength}"
                )

    old_rules = _rule_set(old_network)
    new_rules = _rule_set(new_network)
    added_allow = {r for r in new_rules - old_rules if r[3] == "allow"}
    if added_allow:
        expands = True
        reasons.append(f"network_allow_rules_added:{len(added_allow)}")

    return PolicyDelta(
        static_changed=static_changed,
        dynamic_changed=dynamic_changed,
        expands_access=expands,
        reasons=reasons,
    )


def _network_capabilities(policies: Dict[str, Any]) -> List[Tuple[str, int, str, str, Tuple[Tuple[str, str, str], ...]]]:
    result: List[Tuple[str, int, str, str, Tuple[Tuple[str, str, str], ...]]] = []
    for body in policies.values():
        for endpoint in body.get("endpoints", []) or []:
            rules: List[Tuple[str, str, str]] = []
            for item in endpoint.get("rules", []) or []:
                for kind in ("allow", "deny"):
                    rule = item.get(kind)
                    if rule:
                        rules.append((kind, str(rule.get("method", "*")).upper(), str(rule.get("path", "/**"))))
            result.append(
                (
                    str(endpoint.get("host", "")),
                    int(endpoint.get("port", 0) or 0),
                    str(endpoint.get("protocol", "")),
                    str(endpoint.get("access", "")),
                    tuple(sorted(rules)),
                )
            )
    return result


def _access_strength(access: str) -> int:
    return {
        "": 0,
        AccessMode.READ_ONLY.value: 1,
        AccessMode.READ_WRITE.value: 2,
        AccessMode.FULL.value: 3,
    }.get(access, 2)


def _max_access_by_endpoint(items: Iterable[Tuple[str, int, str, str, tuple]]) -> Dict[Tuple[str, int, str], int]:
    out: Dict[Tuple[str, int, str], int] = {}
    for host, port, protocol, access, rules in items:
        key = (host, port, protocol)
        # Explicit allow rules are treated as scoped access, not zero access.
        strength = _access_strength(access)
        if rules and any(r[0] == "allow" for r in rules):
            strength = max(strength, 1)
        out[key] = max(out.get(key, -1), strength)
    return out


def _rule_set(items: Iterable[Tuple[str, int, str, str, tuple]]) -> Set[Tuple[str, int, str, str, str, str]]:
    out: Set[Tuple[str, int, str, str, str, str]] = set()
    for host, port, protocol, _access, rules in items:
        for kind, method, path in rules:
            out.add((host, port, protocol, kind, method, path))
    return out


def _unique(values: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    result: List[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


__all__ = ["OpenShellPolicyCompiler", "diff_policies"]
