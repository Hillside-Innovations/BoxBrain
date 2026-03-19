"""Best-effort LAN IPv4 for this machine (for phone QR links)."""

from __future__ import annotations

import ipaddress
import socket


def get_primary_lan_ipv4() -> str | None:
    """
    Return a likely LAN IPv4 address (private preferred), or None if unknown.

    Uses the default-route interface (UDP socket trick) plus hostname resolution
    as a fallback when there is no outbound connectivity.
    """
    candidates: list[str] = []

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip:
                candidates.append(ip)
        finally:
            s.close()
    except OSError:
        pass

    try:
        hn = socket.gethostname()
        for res in socket.getaddrinfo(hn, None, socket.AF_INET, socket.SOCK_STREAM):
            cand = res[4][0]
            if cand and cand not in candidates:
                candidates.append(cand)
    except OSError:
        pass

    def parse(raw: str) -> ipaddress.IPv4Address | None:
        try:
            a = ipaddress.ip_address(raw)
        except ValueError:
            return None
        return a if isinstance(a, ipaddress.IPv4Address) else None

    usable: list[ipaddress.IPv4Address] = []
    for raw in candidates:
        a = parse(raw)
        if a is None or a.is_loopback or a.is_link_local:
            continue
        usable.append(a)

    for a in usable:
        if a.is_private:
            return str(a)
    if usable:
        return str(usable[0])
    return None
