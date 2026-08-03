import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.adapters.base import AdapterInput, ToolAdapter


class NmapAdapter(ToolAdapter):
    binary_name = "nmap"

    def build_command(self, adapter_input: AdapterInput, output_path: Path) -> list[str]:
        profile = adapter_input.params.get("profile", "syn-stealth")
        ports = adapter_input.params.get("ports", "1-1024")

        profile_flags = {
            "syn-stealth": ["-sS"],
            "connect": ["-sT"],
            "version": ["-sV"],
        }

        # targets are stored as full URLs for the HTTP-based tools (ffuf,
        # nuclei, sqlmap) - nmap only accepts a bare hostname/IP as its
        # target argument, so a scheme prefix must be stripped here
        parsed = urlparse(adapter_input.target)
        host = parsed.hostname or adapter_input.target

        command = ["nmap", *profile_flags.get(profile, ["-sS"]), "-p", ports, "-oX", str(output_path)]
        command.append(host)
        return command

    def parse_output(
        self, adapter_input: AdapterInput, output_path: Path, raw_stdout: str
    ) -> list[dict[str, Any]]:
        if not output_path.exists() or output_path.stat().st_size == 0:
            return []

        try:
            root = ET.parse(output_path).getroot()
        except ET.ParseError:
            return []

        findings: list[dict[str, Any]] = []
        for host in root.findall("host"):
            for port in host.findall("./ports/port"):
                state = port.find("state")
                if state is None or state.get("state") != "open":
                    continue
                service = port.find("service")
                findings.append(
                    {
                        "type": "open_port",
                        "port": int(port.get("portid", 0)),
                        "service": service.get("name") if service is not None else "unknown",
                        "confidence": "high",
                    }
                )
        return findings
