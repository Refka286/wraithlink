import ipaddress
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.adapters.base import AdapterInput, ToolAdapter

# above this share of results sharing one response size, that size is
# treated as a false-positive baseline (e.g. an SPA/catch-all route
# returning the same body for every unmatched path) rather than real hits
BASELINE_DOMINANCE_THRESHOLD = 0.5

# below this many total results, "dominance" isn't statistically meaningful -
# without this a single genuine finding is trivially 100% of a 1-result set
# and would be filtered out as its own "baseline noise"
BASELINE_MIN_SAMPLE = 5

LOCAL_HOSTNAMES = {"localhost", "host.docker.internal"}

# local lab targets are fast and on our own network; external targets are
# slower, may rate-limit/block aggressive scanning, and deserve more time
# and a politer request pace as a matter of pentest hygiene
LOCAL_TIMEOUT_SECONDS = 300
EXTERNAL_TIMEOUT_SECONDS = 600
EXTERNAL_RATE_LIMIT = 40  # requests/sec cap
EXTERNAL_THREADS = 10  # concurrent workers, below ffuf's default of 40


class FfufAdapter(ToolAdapter):
    binary_name = "ffuf"

    @staticmethod
    def _is_local_target(target: str) -> bool:
        host = urlparse(target).hostname or target
        if host in LOCAL_HOSTNAMES:
            return True
        try:
            return ipaddress.ip_address(host).is_private
        except ValueError:
            return False

    def default_timeout(self, adapter_input: AdapterInput) -> int:
        return LOCAL_TIMEOUT_SECONDS if self._is_local_target(adapter_input.target) else EXTERNAL_TIMEOUT_SECONDS

    def build_command(self, adapter_input: AdapterInput, output_path: Path) -> list[str]:
        wordlist = adapter_input.params.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        url = adapter_input.target.rstrip("/") + "/FUZZ"

        command = [
            "ffuf",
            "-w", wordlist,
            "-u", url,
            "-of", "json",
            "-o", str(output_path),
            "-noninteractive",
        ]

        if not self._is_local_target(adapter_input.target):
            command += ["-rate", str(EXTERNAL_RATE_LIMIT), "-t", str(EXTERNAL_THREADS)]

        return command

    def parse_output(
        self, adapter_input: AdapterInput, output_path: Path, raw_stdout: str
    ) -> list[dict[str, Any]]:
        if not output_path.exists() or output_path.stat().st_size == 0:
            return []

        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        results = data.get("results", [])
        if not results:
            return []

        size_counts = Counter(result.get("length") for result in results)
        dominant_size, dominant_count = size_counts.most_common(1)[0]
        baseline_size = (
            dominant_size
            if len(results) >= BASELINE_MIN_SAMPLE
            and dominant_count / len(results) > BASELINE_DOMINANCE_THRESHOLD
            else None
        )

        findings = []
        for result in results:
            if baseline_size is not None and result.get("length") == baseline_size:
                continue
            findings.append(
                {
                    "type": "discovered_path",
                    "url": result.get("url"),
                    "status": result.get("status"),
                    "length": result.get("length"),
                    "confidence": "medium",
                }
            )
        return findings
