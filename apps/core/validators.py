"""
SSRF guard — blocks destination URLs that resolve to private or reserved
IP ranges, preventing the delivery worker from being used as a proxy to
reach internal infrastructure.

Blocked ranges (RFC 1918 + special-purpose):
  10.0.0.0/8        — private
  172.16.0.0/12     — private
  192.168.0.0/16    — private
  127.0.0.0/8       — loopback
  169.254.0.0/16    — link-local (AWS metadata: 169.254.169.254)
  ::1               — IPv6 loopback
  fc00::/7          — IPv6 unique local
"""

import ipaddress
import socket
from urllib.parse import urlparse

from django.core.exceptions import ValidationError

BLOCKED_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
]


def _is_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in BLOCKED_NETWORKS)
    except ValueError:
        return True


def validate_destination_url(url: str) -> None:
    """
    Raise ValidationError if the destination URL resolves to a private
    or reserved IP address.

    Called by the Destination model's clean() method (enforced on save)
    and by the delivery task before posting (defence in depth).
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise ValidationError("Destination URL has no hostname.")

        resolved_ip = socket.gethostbyname(hostname)

        if _is_private(resolved_ip):
            raise ValidationError(
                f"Destination URL resolves to a private or reserved IP address "
                f"({resolved_ip}). Internal destinations are not permitted."
            )
    except socket.gaierror:
        raise ValidationError(
            f"Destination hostname '{hostname}' could not be resolved. "
            "Verify the URL is correct and reachable."
        )
