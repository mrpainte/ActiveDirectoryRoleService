"""Custom template filters for Active Directory data."""
import struct
from datetime import datetime, timezone

from django import template

from core.constants import UAC_FLAGS, AD_EPOCH_DIFF
from directory.services.base_service import dn_to_base64

register = template.Library()


@register.filter
def decode_uac(value):
    """Takes a UAC integer, returns list of flag names."""
    try:
        uac = int(value)
    except (TypeError, ValueError):
        return []
    flags = []
    for bit, name in sorted(UAC_FLAGS.items()):
        if uac & bit:
            flags.append(name)
    return flags


@register.filter
def ad_timestamp(value):
    """Convert AD timestamp (Windows FILETIME) to Python datetime.

    Windows FILETIME is 100-nanosecond intervals since January 1, 1601.
    """
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return None
    if ts == 0 or ts == 0x7FFFFFFFFFFFFFFF:
        return None
    unix_ts = (ts / 10_000_000) - AD_EPOCH_DIFF
    try:
        return datetime.fromtimestamp(unix_ts, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


@register.filter
def format_sid(binary_sid):
    """Convert a binary SID to its string representation (S-1-5-...)."""
    if not binary_sid or not isinstance(binary_sid, (bytes, bytearray)):
        return str(binary_sid) if binary_sid else ''
    try:
        revision = binary_sid[0]
        sub_authority_count = binary_sid[1]
        authority = int.from_bytes(binary_sid[2:8], byteorder='big')
        sub_authorities = []
        for i in range(sub_authority_count):
            offset = 8 + i * 4
            sa = struct.unpack('<I', binary_sid[offset:offset + 4])[0]
            sub_authorities.append(str(sa))
        return 'S-%d-%d-%s' % (revision, authority, '-'.join(sub_authorities))
    except (IndexError, struct.error):
        return ''


@register.filter
def dn_encode(dn):
    """URL-safe base64 encode a DN."""
    if not dn:
        return ''
    return dn_to_base64(dn)


@register.filter
def dn_short(dn):
    """Extract the CN (or first RDN) from a DN for display."""
    if not dn:
        return ''
    first_rdn = dn.split(',')[0]
    if '=' in first_rdn:
        return first_rdn.split('=', 1)[1]
    return first_rdn
