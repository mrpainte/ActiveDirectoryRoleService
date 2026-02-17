#!/usr/bin/env bash
set -euo pipefail

PROVISIONED_MARKER="/var/lib/samba/.provisioned"

if [ ! -f "$PROVISIONED_MARKER" ]; then
    echo "=== Provisioning Samba AD DC ==="
    echo "  Domain:   ${SAMBA_DOMAIN}"
    echo "  Realm:    ${SAMBA_REALM}"

    # Remove default config files that interfere with provisioning
    rm -f /etc/samba/smb.conf
    rm -rf /var/lib/samba/*
    rm -rf /var/cache/samba/*
    rm -f /etc/krb5.conf

    # Provision the domain
    samba-tool domain provision \
        --server-role=dc \
        --use-rfc2307 \
        --dns-backend=SAMBA_INTERNAL \
        --realm="${SAMBA_REALM}" \
        --domain="${SAMBA_DOMAIN}" \
        --adminpass="${SAMBA_ADMIN_PASSWORD}" \
        --option="ldap server require strong auth = no" \
        --option="server services = -dns" \
        --host-ip="${SAMBA_HOST_IP}"

    # Copy Kerberos config
    cp /var/lib/samba/private/krb5.conf /etc/krb5.conf

    # Relax password policy for development
    echo "=== Relaxing password policy for development ==="
    samba-tool domain passwordsettings set \
        --complexity=off \
        --min-pwd-length=8 \
        --min-pwd-age=0 \
        --max-pwd-age=0 \
        --history-length=0

    # Patch smb.conf to allow insecure LDAP (needed for unicodePwd over plain LDAP)
    SMBCONF="/etc/samba/smb.conf"
    if ! grep -q "ldap server require strong auth" "$SMBCONF"; then
        sed -i '/\[global\]/a\\tldap server require strong auth = no' "$SMBCONF"
    fi

    # Disable DNS service to avoid port conflicts
    if ! grep -q "server services" "$SMBCONF"; then
        sed -i '/\[global\]/a\\tserver services = -dns' "$SMBCONF"
    fi

    touch "$PROVISIONED_MARKER"
    echo "=== Provisioning complete ==="
else
    echo "=== Samba AD DC already provisioned ==="
fi

echo "=== Starting Samba AD DC ==="
exec samba --foreground --no-process-group
