import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.adapters.base import AdapterInput, AdapterOutput, ToolAdapter
from app.config import get_settings


class AcunetixNotConfiguredError(RuntimeError):
    def __init__(self):
        super().__init__(
            "Acunetix n'est pas configure sur cette plateforme (ACUNETIX_API_KEY / "
            "ACUNETIX_BASE_URL absents). Acunetix necessite une licence commerciale qui "
            "n'est pas disponible actuellement - voir la page Outils pour le detail."
        )


# Severity scale returned by the Acunetix REST API (integer 0-4, documented
# as Informational/Low/Medium/High/Critical) mapped onto this platform's own
# FindingSeverity enum (app/models/enums.py) so Acunetix findings line up
# with every other adapter's severities.
_SEVERITY_MAP = {0: "info", 1: "low", 2: "medium", 3: "high", 4: "critical"}

# well-known id of the built-in "Full Scan" profile shipped with every
# Acunetix instance, per the vendor's API documentation
FULL_SCAN_PROFILE_ID = "11111111-1111-1111-1111-111111111111"

# how often to poll GET /api/v1/scans/{scan_id} while a scan is running, and
# the hard ceiling before giving up and reporting whatever was collected
POLL_INTERVAL_SECONDS = 15
MAX_POLL_SECONDS = 3600

_TERMINAL_STATUSES = {"completed", "aborted", "failed"}


def _extract_scan_id(scan_resp: httpx.Response) -> str:
    """
    Acunetix returns the new scan's id in the response body on some API
    versions and only in the Location header (".../scans/<id>") on others -
    handle both since this has not been verified against a live instance.
    """
    try:
        body = scan_resp.json()
        if isinstance(body, dict) and body.get("scan_id"):
            return body["scan_id"]
    except json.JSONDecodeError:
        pass
    return scan_resp.headers.get("location", "").rstrip("/").rsplit("/", 1)[-1]


class AcunetixAdapter(ToolAdapter):
    """
    Acunetix is a hosted/API-driven scanner, not a CLI binary, so this
    adapter talks to its REST API directly instead of using the
    subprocess-based ToolAdapter.run() every other adapter relies on
    (see app/adapters/base.py).

    NOT LIVE-TESTED: no Acunetix license is available in this environment.
    The request/response shapes below are modeled on the structure
    documented in Acunetix's public REST API reference (target creation ->
    scan launch -> vulnerability retrieval) and will likely need small
    adjustments once run against a real instance.
    """

    # never actually looked up (run() is fully overridden below, so
    # _check_binary()/shutil.which() are never called) - kept only because
    # ToolAdapter declares this as a required class attribute
    binary_name = "acunetix"

    def build_command(self, adapter_input: AdapterInput, output_path: Path) -> list[str]:
        raise NotImplementedError(
            "AcunetixAdapter drives the REST API directly and never builds a CLI command"
        )

    def parse_output(
        self, adapter_input: AdapterInput, output_path: Path, raw_stdout: str
    ) -> list[dict[str, Any]]:
        if not output_path.exists() or output_path.stat().st_size == 0:
            return []

        try:
            vulnerabilities = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        findings = []
        for vuln in vulnerabilities:
            findings.append(
                {
                    "type": vuln.get("vt_name", "unknown"),
                    "name": vuln.get("vt_name"),
                    "severity": _SEVERITY_MAP.get(vuln.get("severity"), "info"),
                    "affects_url": vuln.get("affects_url"),
                    "confidence": vuln.get("confidence", "medium"),
                }
            )
        return findings

    def run(self, adapter_input: AdapterInput) -> AdapterOutput:
        started_at = datetime.now(timezone.utc).isoformat()
        settings = get_settings()

        if not settings.acunetix_api_key or not settings.acunetix_base_url:
            return AdapterOutput(
                status="error",
                tool=adapter_input.tool,
                raw_output_ref=None,
                timestamps={"started_at": started_at, "finished_at": datetime.now(timezone.utc).isoformat()},
                error=str(AcunetixNotConfiguredError()),
            )

        profile_id = adapter_input.params.get("scan_profile_id", FULL_SCAN_PROFILE_ID)
        headers = {"X-Auth": settings.acunetix_api_key, "Content-Type": "application/json"}

        try:
            with httpx.Client(
                base_url=settings.acunetix_base_url,
                headers=headers,
                verify=settings.acunetix_verify_tls,
                timeout=30,
            ) as client:
                target_resp = client.post(
                    "/api/v1/targets",
                    json={
                        "address": adapter_input.target,
                        "description": f"wraithlink:{adapter_input.engagement_id}",
                    },
                )
                target_resp.raise_for_status()
                target_id = target_resp.json()["target_id"]

                scan_resp = client.post(
                    "/api/v1/scans",
                    json={
                        "target_id": target_id,
                        "profile_id": profile_id,
                        "schedule": {"disable": False, "start_date": None, "time_sensitive": False},
                    },
                )
                scan_resp.raise_for_status()
                scan_id = _extract_scan_id(scan_resp)

                status_value = "processing"
                elapsed = 0
                while elapsed < MAX_POLL_SECONDS:
                    status_resp = client.get(f"/api/v1/scans/{scan_id}")
                    status_resp.raise_for_status()
                    session = status_resp.json().get("current_session", {})
                    status_value = session.get("status", "processing")
                    if status_value in _TERMINAL_STATUSES:
                        break
                    time.sleep(POLL_INTERVAL_SECONDS)
                    elapsed += POLL_INTERVAL_SECONDS

                vulns_resp = client.get(
                    "/api/v1/vulnerabilities",
                    params={"query": f"target_id:{target_id}"},
                )
                vulns_resp.raise_for_status()
                vulnerabilities = vulns_resp.json().get("vulnerabilities", [])
        except httpx.HTTPError as exc:
            return AdapterOutput(
                status="error",
                tool=adapter_input.tool,
                raw_output_ref=None,
                timestamps={"started_at": started_at, "finished_at": datetime.now(timezone.utc).isoformat()},
                error=f"Acunetix API error: {exc}",
            )

        run_id = uuid.uuid4().hex[:8]
        output_path = self._evidence_dir(adapter_input.engagement_id) / f"acunetix-{run_id}.out"
        output_path.write_text(json.dumps(vulnerabilities), encoding="utf-8")

        findings = self.parse_output(adapter_input, output_path, "")
        finished_at = datetime.now(timezone.utc).isoformat()

        return AdapterOutput(
            status="success",
            tool=adapter_input.tool,
            raw_output_ref=str(output_path),
            parsed_findings=findings,
            evidence=[str(output_path)],
            timestamps={"started_at": started_at, "finished_at": finished_at},
            note=(
                f"scan did not reach a terminal state within {MAX_POLL_SECONDS}s - results may be partial"
                if status_value not in _TERMINAL_STATUSES
                else None
            ),
        )
