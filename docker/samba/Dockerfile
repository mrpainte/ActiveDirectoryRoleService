FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    SAMBA_DOMAIN=DEV \
    SAMBA_REALM=DEV.LOCAL \
    SAMBA_HOST_IP=0.0.0.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    samba \
    samba-ad-dc \
    samba-ad-provision \
    samba-dsdb-modules \
    samba-vfs-modules \
    winbind \
    krb5-user \
    krb5-kdc \
    ldb-tools \
    python3 \
    python3-pip \
    python3-ldap3 \
    && rm -rf /var/lib/apt/lists/*

COPY samba-entrypoint.sh /usr/local/bin/samba-entrypoint.sh
RUN chmod +x /usr/local/bin/samba-entrypoint.sh

COPY seed-directory.py /usr/local/bin/seed-directory.py
RUN chmod +x /usr/local/bin/seed-directory.py

EXPOSE 389 636 88 464 53 135 139 445 3268 3269

HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=12 \
    CMD samba-tool processes 2>/dev/null | grep -q "ldap_server" || exit 1

ENTRYPOINT ["samba-entrypoint.sh"]
