from pathlib import Path
from typing import Any

from app.adapters.base import AdapterInput, ToolAdapter

MODULE_FLAGS = {
    "kerberoast": "--kerberoasting",
    "asreproast": "--asreproast",
}

FINDING_TYPES = {
    "kerberoast": "kerberoastable_account",
    "asreproast": "asrep_roastable_account",
}


class NetExecAdapter(ToolAdapter):
    binary_name = "nxc"

    def build_command(self, adapter_input: AdapterInput, output_path: Path) -> list[str]:
        profile = adapter_input.params.get("profile", "kerberoast")
        module_flag = MODULE_FLAGS.get(profile, MODULE_FLAGS["kerberoast"])

        username = adapter_input.params.get("username", "")
        password = adapter_input.params.get("password", "")
        domain = adapter_input.params.get("domain")

        command = ["nxc", "ldap", adapter_input.target, "-u", username, "-p", password]
        if domain:
            command += ["-d", domain]
        command += [module_flag, str(output_path)]
        return command

    def parse_output(
        self, adapter_input: AdapterInput, output_path: Path, raw_stdout: str
    ) -> list[dict[str, Any]]:
        if not output_path.exists() or output_path.stat().st_size == 0:
            return []

        profile = adapter_input.params.get("profile", "kerberoast")
        finding_type = FINDING_TYPES.get(profile, FINDING_TYPES["kerberoast"])

        findings = []
        for line in output_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            fields = line.split("$")
            account = fields[3].lstrip("*") if len(fields) > 3 else None
            findings.append(
                {
                    "type": finding_type,
                    "account": account,
                    "hash_sample": line[:40] + "...",
                    "confidence": "high",
                }
            )
        return findings
