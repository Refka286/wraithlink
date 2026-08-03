from app.knowledge.error_format import shorten_error

# real error text captured earlier this session from an actual nmap run
# (backend/app/adapters/nmap.py) against an unprivileged worker container
NMAP_PRIVILEGE_ERROR = "You requested a scan type which requires root privileges.\nQUITTING!"

# real error text captured earlier this session from an actual
# bloodhound-python crash (backend/app/adapters/bloodhound.py)
BLOODHOUND_TRACEBACK = """INFO: BloodHound.py for BloodHound LEGACY (BloodHound 4.2 and 4.3)
Traceback (most recent call last):
  File "/usr/local/bin/bloodhound-python", line 8, in <module>
    sys.exit(main())
  File "/usr/local/lib/python3.11/site-packages/bloodhound/__init__.py", line 347, in main
    bloodhound.run(collect=collect,
  File "/usr/local/lib/python3.11/site-packages/ldap3/core/connection.py", line 1373, in do_ntlm_bind
    response = self.post_send_single_response(self.send('bindRequest', request, controls))
ldap3.core.exceptions.LDAPSessionTerminatedByServerError: session terminated by server"""


def test_shortens_nmap_privilege_error_to_the_meaningful_first_line():
    assert shorten_error(NMAP_PRIVILEGE_ERROR) == "You requested a scan type which requires root privileges."


def test_shortens_python_traceback_to_the_exception_line():
    assert shorten_error(BLOODHOUND_TRACEBACK) == "ldap3.core.exceptions.LDAPSessionTerminatedByServerError: session terminated by server"


def test_single_line_error_is_returned_unchanged():
    assert shorten_error("required binary 'nxc' is not installed on this host") == (
        "required binary 'nxc' is not installed on this host"
    )


def test_very_long_single_line_is_truncated_with_ellipsis():
    long_message = "x" * 500
    result = shorten_error(long_message)
    assert result.endswith("...")
    assert len(result) <= 243  # 240 chars + "..."


def test_empty_or_whitespace_error_returns_stripped_string():
    assert shorten_error("   ") == ""
