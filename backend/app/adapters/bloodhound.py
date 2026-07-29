import json
import zipfile
from pathlib import Path
from typing import Any

from app.adapters.base import AdapterInput, ToolAdapter


class BloodHoundAdapter(ToolAdapter):
    binary_name = "bloodhound-python"

    def working_directory(self, output_path: Path) -> Path | None:
        return output_path.parent

    def build_command(self, adapter_input: AdapterInput, output_path: Path) -> list[str]:
        domain = adapter_input.params.get("domain", "")
        username = adapter_input.params.get("username", "")
        password = adapter_input.params.get("password", "")
        collection = adapter_input.params.get("collection_method", "All")

        # the collector writes its own timestamped zip into the working
        # directory rather than accepting an explicit output path - exact
        # flag names vary a little between bloodhound-python versions, check
        # against the version installed in your lab before relying on this
        return [
            "bloodhound-python",
            "-u", username,
            "-p", password,
            "-d", domain,
            "-ns", adapter_input.target,
            "-c", collection,
            "--zip",
        ]

    def parse_output(
        self, adapter_input: AdapterInput, output_path: Path, raw_stdout: str
    ) -> list[dict[str, Any]]:
        search_dir = output_path.parent
        zip_candidates = sorted(search_dir.glob("*bloodhound.zip"))
        if not zip_candidates:
            return []

        archive_path = zip_candidates[-1]
        findings = []

        with zipfile.ZipFile(archive_path) as archive:
            for name in archive.namelist():
                if not name.endswith(".json"):
                    continue
                with archive.open(name) as handle:
                    try:
                        data = json.load(handle)
                    except json.JSONDecodeError:
                        continue

                count = len(data.get("data", [])) if isinstance(data, dict) else 0
                if count == 0:
                    continue

                findings.append(
                    {
                        "type": f"bloodhound_{name.removesuffix('.json')}_collected",
                        "count": count,
                        "confidence": "high",
                    }
                )

        return findings
