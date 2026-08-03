"""
Regression tests for bugs found and fixed during hands-on testing of the
platform (base.py error-detection ordering, ffuf baseline-noise filtering,
netexec hash-line parsing, target host whitespace, AI context size cap).

Risk engine hard-rule regressions (netexec:dcsync always forbidden despite
its score, netexec:kerberoast always requiring approval despite its score)
already have dedicated coverage in test_risk_engine.py
(test_dcsync_is_forbidden_due_to_irreversibility_not_score_alone and
test_kerberoast_is_never_automatic_even_though_score_is_low) - not
duplicated here.
"""
import json
from pathlib import Path

from app.adapters.base import AdapterInput, ToolAdapter
from app.adapters.ffuf import FfufAdapter
from app.adapters.netexec import NetExecAdapter


def dummy_input(tool: str, params: dict | None = None) -> AdapterInput:
    return AdapterInput(
        tool=tool,
        target="10.10.10.5",
        params=params or {},
        risk_tier="automatic",
        engagement_id="test-engagement",
    )


# ---------------------------------------------------------------------------
# 1. base.py: a nonzero exit with no output file must be status="error"
# ---------------------------------------------------------------------------

class _DummyAdapter(ToolAdapter):
    binary_name = "dummy-tool"

    def build_command(self, adapter_input, output_path):
        return ["dummy-tool"]

    def parse_output(self, adapter_input, output_path, raw_stdout):
        return []


class _FakePopen:
    """Stands in for subprocess.Popen: real Popen only sets .returncode
    after communicate() returns, and base.py's graceful-shutdown path calls
    terminate()/kill() on timeout - both are no-ops here since these tests
    don't exercise the timeout path."""

    def __init__(self, returncode: int, stdout: str, stderr: str):
        self._returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = None

    def communicate(self, timeout=None):
        self.returncode = self._returncode
        return self._stdout, self._stderr

    def terminate(self):
        pass

    def kill(self):
        pass


def test_nonzero_exit_with_no_output_written_is_reported_as_error(monkeypatch, tmp_path):
    # regression for: the fallback stdout-write ran BEFORE the error check,
    # so by the time "did the tool write a file?" was tested, base.py had
    # already created one from (possibly empty) stdout - meaning a crashed
    # tool was always reported as status="success" with zero findings
    monkeypatch.setattr("app.adapters.base.shutil.which", lambda name: "/usr/bin/dummy-tool")

    class FakeSettings:
        evidence_storage_path = str(tmp_path)

    monkeypatch.setattr("app.adapters.base.get_settings", lambda: FakeSettings())
    monkeypatch.setattr(
        "app.adapters.base.subprocess.Popen",
        lambda *a, **k: _FakePopen(returncode=1, stdout="", stderr="permission denied"),
    )

    output = _DummyAdapter().run(dummy_input("dummy"))

    assert output.status == "error"
    assert output.error == "permission denied"


def test_nonzero_exit_that_did_write_output_is_still_success(monkeypatch, tmp_path):
    # companion case: a tool that exits nonzero but DID produce partial
    # output (e.g. its own -o/-oX flag wrote the file directly) should keep
    # its existing behaviour and not be forced into "error"
    monkeypatch.setattr("app.adapters.base.shutil.which", lambda name: "/usr/bin/dummy-tool")

    class FakeSettings:
        evidence_storage_path = str(tmp_path)

    monkeypatch.setattr("app.adapters.base.get_settings", lambda: FakeSettings())

    def fake_popen(command, **kwargs):
        # emulate a tool that writes its own output file before exiting nonzero
        for token in command:
            if str(token).endswith(".out"):
                Path(token).write_text("partial output", encoding="utf-8")
        return _FakePopen(returncode=1, stdout="", stderr="warning: incomplete scan")

    class _AdapterWithOutputArg(_DummyAdapter):
        def build_command(self, adapter_input, output_path):
            return ["dummy-tool", str(output_path)]

    monkeypatch.setattr("app.adapters.base.subprocess.Popen", fake_popen)

    output = _AdapterWithOutputArg().run(dummy_input("dummy"))

    assert output.status == "success"


# ---------------------------------------------------------------------------
# 2. ffuf: baseline (dominant-size) noise filtering
# ---------------------------------------------------------------------------

def test_ffuf_filters_dominant_baseline_size_but_keeps_distinct_results(tmp_path):
    output_path = tmp_path / "ffuf.json"
    noise = [{"url": f"http://target/noise{i}", "status": 200, "length": 9903} for i in range(6)]
    real = [
        {"url": "http://target/api", "status": 500, "length": 2408},
        {"url": "http://target/robots.txt", "status": 200, "length": 28},
    ]
    output_path.write_text(json.dumps({"results": noise + real}), encoding="utf-8")

    findings = FfufAdapter().parse_output(dummy_input("ffuf"), output_path, "")

    urls = {finding["url"] for finding in findings}
    assert urls == {"http://target/api", "http://target/robots.txt"}


def test_ffuf_single_result_is_not_filtered_as_its_own_baseline(tmp_path):
    # regression for an edge case introduced by the fix above: with only one
    # result, it is trivially 100% of the sample and would otherwise be
    # treated as "dominant baseline noise" and dropped
    output_path = tmp_path / "ffuf.json"
    output_path.write_text(
        json.dumps({"results": [{"url": "http://target/admin", "status": 200, "length": 512}]}),
        encoding="utf-8",
    )

    findings = FfufAdapter().parse_output(dummy_input("ffuf"), output_path, "")

    assert len(findings) == 1
    assert findings[0]["url"] == "http://target/admin"


# ---------------------------------------------------------------------------
# 2b. ffuf: external targets get a longer timeout and a politer request pace
# ---------------------------------------------------------------------------

def test_ffuf_uses_longer_timeout_and_rate_limit_for_external_targets():
    external_input = AdapterInput(
        tool="ffuf", target="http://testphp.vulnweb.com", params={}, risk_tier="automatic", engagement_id="e1"
    )
    local_input = AdapterInput(
        tool="ffuf", target="http://host.docker.internal:3001", params={}, risk_tier="automatic", engagement_id="e1"
    )
    private_ip_input = AdapterInput(
        tool="ffuf", target="http://10.10.10.5", params={}, risk_tier="automatic", engagement_id="e1"
    )

    adapter = FfufAdapter()

    assert adapter.default_timeout(external_input) == 600
    assert adapter.default_timeout(local_input) == 300
    assert adapter.default_timeout(private_ip_input) == 300

    external_command = adapter.build_command(external_input, Path("/tmp/out.json"))
    local_command = adapter.build_command(local_input, Path("/tmp/out.json"))

    assert "-rate" in external_command and "-t" in external_command
    assert "-rate" not in local_command and "-t" not in local_command


def test_ffuf_explicit_timeout_seconds_param_overrides_the_locality_default():
    adapter_input = AdapterInput(
        tool="ffuf",
        target="http://testphp.vulnweb.com",
        params={"timeout_seconds": 45},
        risk_tier="automatic",
        engagement_id="e1",
    )
    # base.py reads params.get("timeout_seconds") before falling back to
    # default_timeout() - this documents that an explicit caller override
    # still wins even for a target that would otherwise get the external 600s
    assert adapter_input.params.get("timeout_seconds") or FfufAdapter().default_timeout(adapter_input) == 45


# ---------------------------------------------------------------------------
# 2c. base.py: on timeout, a graceful shutdown must not discard partial
# results - confirmed empirically that ffuf only flushes its -o file on
# clean exit, so a bare SIGKILL on timeout loses everything even if results
# were already found; base.py now sends SIGTERM and gives a grace period
# before falling back to SIGKILL
# ---------------------------------------------------------------------------

def test_timeout_with_graceful_shutdown_keeps_partial_results(monkeypatch, tmp_path):
    monkeypatch.setattr("app.adapters.base.shutil.which", lambda name: "/usr/bin/dummy-tool")

    class FakeSettings:
        evidence_storage_path = str(tmp_path)

    monkeypatch.setattr("app.adapters.base.get_settings", lambda: FakeSettings())

    import subprocess as real_subprocess

    class _FakePopen:
        def __init__(self, command, **kwargs):
            self._output_path = Path(command[-1])
            self.returncode = None
            self._terminated = False

        def communicate(self, timeout=None):
            if not self._terminated:
                raise real_subprocess.TimeoutExpired(cmd="dummy-tool", timeout=timeout)
            self.returncode = 0
            return "", ""

        def terminate(self):
            self._terminated = True
            # emulate ffuf flushing whatever it had found before a clean SIGTERM exit
            self._output_path.write_text("partial output", encoding="utf-8")

        def kill(self):
            raise AssertionError("a graceful shutdown must not require a hard kill")

    monkeypatch.setattr("app.adapters.base.subprocess.Popen", _FakePopen)

    class _AdapterWithOutputArg(_DummyAdapter):
        def build_command(self, adapter_input, output_path):
            return ["dummy-tool", str(output_path)]

        def parse_output(self, adapter_input, output_path, raw_stdout):
            return [{"type": "partial_finding"}]

    output = _AdapterWithOutputArg().run(dummy_input("dummy"))

    assert output.status == "success"
    assert output.parsed_findings == [{"type": "partial_finding"}]
    assert output.note is not None
    assert "timed out" in output.note


def test_timeout_with_no_output_even_after_grace_period_is_reported_as_error(monkeypatch, tmp_path):
    monkeypatch.setattr("app.adapters.base.shutil.which", lambda name: "/usr/bin/dummy-tool")

    class FakeSettings:
        evidence_storage_path = str(tmp_path)

    monkeypatch.setattr("app.adapters.base.get_settings", lambda: FakeSettings())

    import subprocess as real_subprocess

    class _FakePopen:
        def __init__(self, command, **kwargs):
            self.returncode = None

        def communicate(self, timeout=None):
            if timeout is not None:
                raise real_subprocess.TimeoutExpired(cmd="dummy-tool", timeout=timeout)
            self.returncode = -9
            return "", ""

        def terminate(self):
            pass

        def kill(self):
            pass

    monkeypatch.setattr("app.adapters.base.subprocess.Popen", _FakePopen)

    output = _DummyAdapter().run(dummy_input("dummy"))

    assert output.status == "error"
    assert "timed out" in output.error


# ---------------------------------------------------------------------------
# 3. netexec: only real hash lines become findings, not tool log noise
# ---------------------------------------------------------------------------

def test_netexec_ignores_banner_and_status_lines_mixed_with_real_hashes(tmp_path):
    output_path = tmp_path / "nxc.out"
    output_path.write_text(
        "[*] First time use detected\n"
        "[*] Initializing LDAP protocol database\n"
        "LDAP  192.168.1.10  389  DC01  [*] Total of records returned 1\n"
        "LDAP  192.168.1.10  389  DC01  [-] Error in searchRequest -> operationsError\n"
        "$krb5tgs$23$*svc_sql$GOAD.LOCAL$MSSQLSvc/dc01.goad.local*$abcdef0123456789\n",
        encoding="utf-8",
    )

    findings = NetExecAdapter().parse_output(
        dummy_input("netexec", {"profile": "kerberoast"}), output_path, ""
    )

    assert len(findings) == 1
    assert findings[0]["type"] == "kerberoastable_account"
    assert findings[0]["account"] == "svc_sql"


def test_netexec_reports_zero_findings_when_only_log_noise_present(tmp_path):
    # this is the exact scenario that produced 28 fake findings in
    # production: nxc's own startup/status output, with zero real hashes
    output_path = tmp_path / "nxc.out"
    output_path.write_text(
        "[*] First time use detected\n"
        "[*] Creating home directory structure\n"
        "LDAP  192.168.1.10  389  DC01  [*] Total of records returned 0\n",
        encoding="utf-8",
    )

    findings = NetExecAdapter().parse_output(
        dummy_input("netexec", {"profile": "kerberoast"}), output_path, ""
    )

    assert findings == []
