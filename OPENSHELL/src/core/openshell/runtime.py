"""OpenShell runtime adapters.

The CLI adapter is deliberately primary because NVIDIA documents policy create,
get, set, update and prove operations there.  The optional SDK probe exposes the
official Python SDK for health and exec without guessing undocumented policy APIs.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

import yaml


class OpenShellRuntimeError(RuntimeError):
    pass


class OpenShellRuntime(Protocol):
    def sandbox_exists(self, name: str) -> bool: ...
    def get_base_policy(self, name: str) -> Optional[Dict[str, Any]]: ...
    def create_sandbox(self, name: str, policy_yaml: str, command: List[str], image: Optional[str] = None) -> Dict[str, Any]: ...
    def apply_policy(self, name: str, policy_yaml: str, *, wait: bool = True) -> Dict[str, Any]: ...
    def exec(self, name: str, argv: List[str]) -> Dict[str, Any]: ...
    def delete(self, name: str) -> Dict[str, Any]: ...


@dataclass
class CommandResult:
    argv: List[str]
    returncode: int
    stdout: str
    stderr: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "argv": self.argv,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


class OpenShellCliRuntime:
    """Production-friendly adapter over the documented ``openshell`` CLI."""

    def __init__(self, binary: str = "openshell", *, workspace: Optional[str] = None) -> None:
        self.binary = binary
        self.workspace = workspace

    def available(self) -> bool:
        return shutil.which(self.binary) is not None

    def sandbox_exists(self, name: str) -> bool:
        result = self._run(["sandbox", "get", name], check=False)
        return result.returncode == 0

    def get_base_policy(self, name: str) -> Optional[Dict[str, Any]]:
        if not self.sandbox_exists(name):
            return None
        result = self._run(["policy", "get", name, "--base"])
        return _extract_yaml_mapping(result.stdout)

    def create_sandbox(
        self,
        name: str,
        policy_yaml: str,
        command: List[str],
        image: Optional[str] = None,
    ) -> Dict[str, Any]:
        with _policy_file(policy_yaml) as path:
            args = ["sandbox", "create", "--name", name, "--policy", str(path)]
            if image:
                args += ["--from", image]
            if self.workspace:
                args += ["--workspace", self.workspace]
            args += ["--"] + list(command)
            return self._run(args).to_dict()

    def apply_policy(self, name: str, policy_yaml: str, *, wait: bool = True) -> Dict[str, Any]:
        with _policy_file(policy_yaml) as path:
            args = ["policy", "set", name, "--policy", str(path)]
            if wait:
                args.append("--wait")
            return self._run(args).to_dict()

    def prove_policy(self, policy_yaml: str) -> Dict[str, Any]:
        with _policy_file(policy_yaml) as path:
            result = self._run(["policy", "prove", "--policy", str(path)])
            return result.to_dict()

    def exec(self, name: str, argv: List[str]) -> Dict[str, Any]:
        return self._run(["sandbox", "exec", "-n", name, "--"] + list(argv)).to_dict()

    def delete(self, name: str) -> Dict[str, Any]:
        return self._run(["sandbox", "delete", name]).to_dict()

    def _run(self, args: List[str], *, check: bool = True) -> CommandResult:
        if not self.available():
            raise OpenShellRuntimeError(
                f"OpenShell CLI not found: {self.binary!r}. Install NVIDIA OpenShell first."
            )
        proc = subprocess.run(
            [self.binary] + args,
            text=True,
            capture_output=True,
            check=False,
        )
        result = CommandResult(
            argv=[self.binary] + args,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
        if check and proc.returncode != 0:
            raise OpenShellRuntimeError(
                f"OpenShell command failed ({proc.returncode}): {' '.join(result.argv)}\n{proc.stderr.strip()}"
            )
        return result


class OpenShellSdkProbe:
    """Small wrapper around NVIDIA's official Python SDK.

    It intentionally does not invent policy-management methods that are not part
    of the documented Python SDK examples.  Use OpenShellCliRuntime for policy
    lifecycle and this class for health/exec automation when desired.
    """

    def __init__(self, *, workspace: str = "default") -> None:
        self.workspace = workspace

    def health(self) -> Dict[str, Any]:
        SandboxClient = _sandbox_client()
        with SandboxClient.from_active_cluster() as client:
            health = client.health()
            return {"version": getattr(health, "version", None)}

    def exec(self, sandbox_name: str, argv: List[str]) -> Dict[str, Any]:
        SandboxClient = _sandbox_client()
        with SandboxClient.from_active_cluster() as client:
            result = client.exec(sandbox_name, list(argv), workspace=self.workspace)
            return {
                "stdout": getattr(result, "stdout", ""),
                "stderr": getattr(result, "stderr", ""),
                "returncode": getattr(result, "returncode", getattr(result, "exit_code", None)),
            }


def _sandbox_client():
    try:
        from openshell import SandboxClient
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise OpenShellRuntimeError(
            "NVIDIA OpenShell Python SDK is not installed. On Python 3.11+, install with: pip install openshell"
        ) from exc
    return SandboxClient


class _policy_file:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.path: Optional[Path] = None

    def __enter__(self) -> Path:
        fd, raw = tempfile.mkstemp(prefix="deepsigma-openshell-", suffix=".yaml")
        Path(raw).write_text(self.payload, encoding="utf-8")
        # mkstemp fd is no longer needed after Path.write_text opens the file itself.
        import os
        os.close(fd)
        self.path = Path(raw)
        return self.path

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.path:
            self.path.unlink(missing_ok=True)


def _extract_yaml_mapping(text: str) -> Dict[str, Any]:
    """Extract a YAML policy mapping from CLI output that may include headers."""
    # Prefer the first 'version:' line because ``policy get`` may print revision
    # metadata before the YAML body.
    idx = text.find("version:")
    candidate = text[idx:] if idx >= 0 else text
    data = yaml.safe_load(candidate) or {}
    if not isinstance(data, dict):
        raise OpenShellRuntimeError("OpenShell policy output did not contain a YAML mapping")
    return data


__all__ = [
    "OpenShellCliRuntime",
    "OpenShellRuntime",
    "OpenShellRuntimeError",
    "OpenShellSdkProbe",
]
