import json
from pathlib import Path
from typing import Any

from app.adapters.base import AdapterInput, ToolAdapter


class FfufAdapter(ToolAdapter):
    binary_name = "ffuf"

    def build_command(self, adapter_input: AdapterInput, output_path: Path) -> list[str]:
        wordlist = adapter_input.params.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        url = adapter_input.target.rstrip("/") + "/FUZZ"

        return [
            "ffuf",
            "-w", wordlist,
            "-u", url,
            "-of", "json",
            "-o", str(output_path),
            "-noninteractive",
        ]

    def parse_output(self, output_path: Path, raw_stdout: str) -> list[dict[str, Any]]:
        if not output_path.exists() or output_path.stat().st_size == 0:
            return []

        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        findings = []
        for result in data.get("results", []):
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
