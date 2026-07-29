import shutil
import subprocess
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings


class ToolNotInstalledError(RuntimeError):
    def __init__(self, binary: str):
        super().__init__(f"required binary '{binary}' is not installed on this host")
        self.binary = binary


@dataclass
class AdapterInput:
    tool: str
    target: str
    params: dict[str, Any]
    risk_tier: str
    engagement_id: str


@dataclass
class AdapterOutput:
    status: str
    tool: str
    raw_output_ref: str | None
    parsed_findings: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    timestamps: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "tool": self.tool,
            "raw_output_ref": self.raw_output_ref,
            "parsed_findings": self.parsed_findings,
            "evidence": self.evidence,
            "timestamps": self.timestamps,
            "error": self.error,
        }


class ToolAdapter(ABC):
    binary_name: str

    @abstractmethod
    def build_command(self, adapter_input: AdapterInput, output_path: Path) -> list[str]:
        ...

    @abstractmethod
    def parse_output(self, output_path: Path, raw_stdout: str) -> list[dict[str, Any]]:
        ...

    def _check_binary(self) -> None:
        if shutil.which(self.binary_name) is None:
            raise ToolNotInstalledError(self.binary_name)

    def _evidence_dir(self, engagement_id: str) -> Path:
        base = Path(get_settings().evidence_storage_path) / engagement_id
        base.mkdir(parents=True, exist_ok=True)
        return base

    def run(self, adapter_input: AdapterInput) -> AdapterOutput:
        started_at = datetime.now(timezone.utc).isoformat()

        try:
            self._check_binary()
        except ToolNotInstalledError as exc:
            return AdapterOutput(
                status="error",
                tool=adapter_input.tool,
                raw_output_ref=None,
                timestamps={"started_at": started_at, "finished_at": datetime.now(timezone.utc).isoformat()},
                error=str(exc),
            )

        run_id = uuid.uuid4().hex[:8]
        output_dir = self._evidence_dir(adapter_input.engagement_id)
        output_path = output_dir / f"{self.binary_name}-{run_id}.out"

        command = self.build_command(adapter_input, output_path)

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=adapter_input.params.get("timeout_seconds", 300),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return AdapterOutput(
                status="error",
                tool=adapter_input.tool,
                raw_output_ref=None,
                timestamps={"started_at": started_at, "finished_at": datetime.now(timezone.utc).isoformat()},
                error=f"execution timed out after {exc.timeout}s",
            )

        finished_at = datetime.now(timezone.utc).isoformat()

        if not output_path.exists():
            output_path.write_text(completed.stdout, encoding="utf-8")

        if completed.returncode != 0 and not output_path.exists():
            return AdapterOutput(
                status="error",
                tool=adapter_input.tool,
                raw_output_ref=None,
                timestamps={"started_at": started_at, "finished_at": finished_at},
                error=completed.stderr.strip() or f"exit code {completed.returncode}",
            )

        findings = self.parse_output(output_path, completed.stdout)

        return AdapterOutput(
            status="success",
            tool=adapter_input.tool,
            raw_output_ref=str(output_path),
            parsed_findings=findings,
            evidence=[str(output_path)],
            timestamps={"started_at": started_at, "finished_at": finished_at},
        )
