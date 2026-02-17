"""Service for AD-integrated DNS management."""
import ipaddress
import logging
import socket
import struct

from django.conf import settings
from ldap3.core.exceptions import LDAPException

from directory.services.base_service import BaseLDAPService, LDAPServiceError

logger = logging.getLogger(__name__)

# DNS record type codes used in the AD dnsRecord binary format
DNS_TYPE_CODES = {
    'A': 1,
    'AAAA': 28,
    'CNAME': 5,
    'MX': 15,
    'PTR': 12,
    'SRV': 33,
    'TXT': 16,
}

DNS_TYPE_NAMES = {v: k for k, v in DNS_TYPE_CODES.items()}


def _encode_dns_name(name):
    """Encode a DNS name into the wire format used by AD (length-prefixed labels)."""
    parts = name.rstrip('.').split('.')
    result = b''
    for part in parts:
        encoded = part.encode('ascii')
        result += struct.pack('B', len(encoded)) + encoded
    result += b'\x00'
    return result


def _decode_dns_name(data, offset):
    """Decode a wire-format DNS name from data at offset."""
    labels = []
    while offset < len(data):
        length = data[offset]
        offset += 1
        if length == 0:
            break
        labels.append(data[offset:offset + length].decode('ascii', errors='replace'))
        offset += length
    return '.'.join(labels), offset


class DNSService(BaseLDAPService):
    """LDAP operations for AD-integrated DNS zones and records."""

    def _get_dns_bases(self):
        """Return the search bases for AD-integrated DNS."""
        base_dn = settings.AD_BASE_DN
        return [
            f'CN=MicrosoftDNS,DC=DomainDnsZones,{base_dn}',
            f'CN=MicrosoftDNS,DC=ForestDnsZones,{base_dn}',
        ]

    def list_zones(self):
        """List all DNS zones from AD-integrated DNS."""
        zones = []
        for dns_base in self._get_dns_bases():
            try:
                entries = self.search(
                    dns_base,
                    '(objectClass=dnsZone)',
                    ['dc', 'name', 'distinguishedName', 'whenCreated'],
                )
                for entry in entries:
                    entry['dns_base'] = dns_base
                zones.extend(entries)
            except LDAPServiceError:
                logger.debug("DNS base not available: %s", dns_base)
        return zones

    def list_records(self, zone_dn):
        """List DNS records (dnsNode objects) within a zone."""
        try:
            return self.search(
                zone_dn,
                '(objectClass=dnsNode)',
                ['dc', 'name', 'dnsRecord', 'distinguishedName', 'whenCreated'],
            )
        except LDAPServiceError:
            logger.exception("Failed to list records in zone %s", zone_dn)
            raise

    def get_record(self, dn):
        """Get a single DNS record node."""
        return self.get(dn, ['dc', 'name', 'dnsRecord', 'distinguishedName', 'whenCreated'])

    def create_record(self, zone_dn, name, record_type, data, ttl=3600):
        """Create a DNS record node in the specified zone."""
        record_bytes = self._encode_dns_record(record_type, data, ttl)
        record_dn = f'DC={name},{zone_dn}'
        conn = self.pool.get_connection()
        try:
            status = conn.add(
                record_dn,
                ['top', 'dnsNode'],
                {'dnsRecord': record_bytes},
            )
            if not status:
                raise LDAPServiceError(
                    f"Failed to create DNS record: {conn.result}"
                )
            return True
        except LDAPException as exc:
            logger.exception("Failed to create DNS record %s in %s", name, zone_dn)
            raise LDAPServiceError(f"Create DNS record failed: {exc}") from exc
        finally:
            conn.unbind()

    def update_record(self, dn, record_type, data, ttl=3600):
        """Update an existing DNS record."""
        from ldap3 import MODIFY_REPLACE
        record_bytes = self._encode_dns_record(record_type, data, ttl)
        changes = {'dnsRecord': [(MODIFY_REPLACE, [record_bytes])]}
        try:
            return self.modify(dn, changes)
        except LDAPServiceError:
            logger.exception("Failed to update DNS record %s", dn)
            raise

    def delete_record(self, dn):
        """Delete a DNS record node."""
        try:
            return self.delete(dn)
        except LDAPServiceError:
            logger.exception("Failed to delete DNS record %s", dn)
            raise

    @staticmethod
    def _encode_dns_record(record_type, data, ttl):
        """Encode a DNS record into the binary format expected by AD.

        The AD dnsRecord attribute uses a binary structure:
        - Bytes 0-1: Data length (uint16 LE)
        - Bytes 2-3: Record type (uint16 LE)
        - Bytes 4-4: Version (uint8) = 5
        - Bytes 5-5: Rank (uint8) = 240 (zone level)
        - Bytes 6-7: Flags (uint16 LE) = 0
        - Bytes 8-11: Serial (uint32 LE) = 1
        - Bytes 12-15: TTL in seconds (uint32 BE, per MS spec)
        - Bytes 16-19: Reserved (uint32 LE) = 0
        - Bytes 20-23: Timestamp (uint32 LE) = 0 (static)
        - Bytes 24+: Record data (type-specific)
        """
        rtype = DNS_TYPE_CODES.get(record_type.upper())
        if rtype is None:
            raise LDAPServiceError(f"Unsupported record type: {record_type}")

        rdata = DNSService._encode_rdata(record_type.upper(), data)

        header = struct.pack(
            '<HH BB HI',
            len(rdata),       # data length
            rtype,            # record type
            5,                # version
            240,              # rank (zone level)
            0,                # flags
            1,                # serial
        )
        header += struct.pack('>I', ttl)  # TTL is big-endian
        header += struct.pack('<II', 0, 0)  # reserved + timestamp

        return header + rdata

    @staticmethod
    def _encode_rdata(record_type, data):
        """Encode the record-type-specific data portion."""
        if record_type == 'A':
            return socket.inet_aton(data)
        elif record_type == 'AAAA':
            return ipaddress.IPv6Address(data).packed
        elif record_type == 'CNAME' or record_type == 'PTR':
            return _encode_dns_name(data)
        elif record_type == 'MX':
            parts = data.split()
            if len(parts) == 2:
                priority, host = int(parts[0]), parts[1]
            else:
                priority, host = 10, data
            return struct.pack('<H', priority) + _encode_dns_name(host)
        elif record_type == 'SRV':
            parts = data.split()
            if len(parts) >= 4:
                priority, weight, port, target = (
                    int(parts[0]), int(parts[1]), int(parts[2]), parts[3]
                )
            else:
                raise LDAPServiceError(
                    "SRV data must be: priority weight port target"
                )
            return (
                struct.pack('<HHH', priority, weight, port) +
                _encode_dns_name(target)
            )
        elif record_type == 'TXT':
            encoded = data.encode('utf-8')
            return struct.pack('B', len(encoded)) + encoded
        else:
            raise LDAPServiceError(f"Unsupported record type: {record_type}")

    @staticmethod
    def _decode_dns_record(raw_bytes):
        """Decode a binary dnsRecord attribute to a dict."""
        if len(raw_bytes) < 24:
            return None
        data_len, rtype, version, rank, flags, serial = struct.unpack(
            '<HH BB HI', raw_bytes[:10]
        )
        ttl = struct.unpack('>I', raw_bytes[10:14])[0]
        rdata = raw_bytes[24:]

        record_type_name = DNS_TYPE_NAMES.get(rtype, f'TYPE{rtype}')
        decoded_data = DNSService._decode_rdata(record_type_name, rdata)

        return {
            'type': record_type_name,
            'data': decoded_data,
            'ttl': ttl,
        }

    @staticmethod
    def _decode_rdata(record_type, rdata):
        """Decode the record-type-specific data portion."""
        try:
            if record_type == 'A' and len(rdata) >= 4:
                return socket.inet_ntoa(rdata[:4])
            elif record_type == 'AAAA' and len(rdata) >= 16:
                return str(ipaddress.IPv6Address(rdata[:16]))
            elif record_type in ('CNAME', 'PTR'):
                name, _ = _decode_dns_name(rdata, 0)
                return name
            elif record_type == 'MX' and len(rdata) >= 2:
                priority = struct.unpack('<H', rdata[:2])[0]
                name, _ = _decode_dns_name(rdata, 2)
                return f"{priority} {name}"
            elif record_type == 'SRV' and len(rdata) >= 6:
                priority, weight, port = struct.unpack('<HHH', rdata[:6])
                name, _ = _decode_dns_name(rdata, 6)
                return f"{priority} {weight} {port} {name}"
            elif record_type == 'TXT' and len(rdata) >= 1:
                length = rdata[0]
                return rdata[1:1 + length].decode('utf-8', errors='replace')
            else:
                return rdata.hex()
        except Exception:
            return rdata.hex() if rdata else ''
