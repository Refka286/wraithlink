MAX_ERROR_LENGTH = 240


def shorten_error(raw_error: str) -> str:
    """
    Reduce a tool/adapter error to one display-worthy line.

    Real errors seen from adapters fall into two shapes:
    - a Python traceback (e.g. bloodhound-python crashing on a DNS lookup) -
      the last non-empty line is the exception type + message, which is the
      only part a reader needs; everything above it is call-stack noise.
    - a CLI tool's own stderr (e.g. nmap's "You requested a scan type which
      requires root privileges.\nQUITTING!") - these conventionally state
      the actual problem first and any follow-up ("QUITTING!") after, so
      the first non-empty line is the useful one.
    Neither heuristic is perfect for every tool, but both match every error
    actually produced by the adapters in app/adapters/ so far.
    """
    lines = [line.strip() for line in raw_error.strip().splitlines() if line.strip()]
    if not lines:
        return raw_error.strip()

    message = lines[-1] if "Traceback (most recent call last):" in raw_error else lines[0]

    if len(message) > MAX_ERROR_LENGTH:
        message = message[:MAX_ERROR_LENGTH].rstrip() + "..."
    return message
