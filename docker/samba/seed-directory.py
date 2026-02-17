#!/usr/bin/env python3
"""
Idempotent seed script for the Samba AD DC development environment.

Creates test OUs, groups, users, and computers in the DEV.LOCAL domain.
Uses ldap3 to connect to the Samba DC via LDAP.

Usage:
    python3 seed-directory.py [--host LDAP_HOST] [--port LDAP_PORT]
"""
import argparse
import subprocess
import sys
import time

from ldap3 import (
    ALL,
    MODIFY_ADD,
    MODIFY_REPLACE,
    SUBTREE,
    Connection,
    Server,
)

# ── Configuration ────────────────────────────────────────────────────────────

BASE_DN = "DC=dev,DC=local"
ADMIN_DN = f"CN=Administrator,CN=Users,{BASE_DN}"
ADMIN_PASSWORD = "AdminP@ss123!"

# Test user password
USER_PASSWORD = "TestP@ssw0rd!2024"

# Service account
SVC_ACCOUNT = {
    "cn": "svc_admanager",
    "sAMAccountName": "svc_admanager",
    "password": "SvcP@ssw0rd!2024",
    "ou": f"OU=Service Accounts,{BASE_DN}",
    "description": "AD Role Service application service account",
}

# OUs to create
OUS = [
    f"OU=Users,{BASE_DN}",
    f"OU=Groups,{BASE_DN}",
    f"OU=Computers,{BASE_DN}",
    f"OU=Service Accounts,{BASE_DN}",
]

# Role groups
GROUPS = [
    {
        "cn": "ADRS-Admins",
        "sAMAccountName": "ADRS-Admins",
        "description": "AD Role Service - Admin role",
        "ou": f"OU=Groups,{BASE_DN}",
    },
    {
        "cn": "ADRS-HelpDesk",
        "sAMAccountName": "ADRS-HelpDesk",
        "description": "AD Role Service - HelpDesk role",
        "ou": f"OU=Groups,{BASE_DN}",
    },
    {
        "cn": "ADRS-GroupManagers",
        "sAMAccountName": "ADRS-GroupManagers",
        "description": "AD Role Service - GroupManager role",
        "ou": f"OU=Groups,{BASE_DN}",
    },
]

# Test users
USERS = [
    {
        "cn": "Admin User",
        "sAMAccountName": "admin.user",
        "givenName": "Admin",
        "sn": "User",
        "mail": "admin.user@dev.local",
        "description": "Test admin user",
        "ou": f"OU=Users,{BASE_DN}",
        "groups": ["ADRS-Admins"],
    },
    {
        "cn": "HelpDesk User",
        "sAMAccountName": "helpdesk.user",
        "givenName": "HelpDesk",
        "sn": "User",
        "mail": "helpdesk.user@dev.local",
        "description": "Test helpdesk user",
        "ou": f"OU=Users,{BASE_DN}",
        "groups": ["ADRS-HelpDesk"],
    },
    {
        "cn": "GroupManager User",
        "sAMAccountName": "groupmgr.user",
        "givenName": "GroupManager",
        "sn": "User",
        "mail": "groupmgr.user@dev.local",
        "description": "Test group manager user",
        "ou": f"OU=Users,{BASE_DN}",
        "groups": ["ADRS-GroupManagers"],
    },
    {
        "cn": "ReadOnly User",
        "sAMAccountName": "readonly.user",
        "givenName": "ReadOnly",
        "sn": "User",
        "mail": "readonly.user@dev.local",
        "description": "Test read-only user (no role group)",
        "ou": f"OU=Users,{BASE_DN}",
        "groups": [],
    },
    {
        "cn": "Normal User",
        "sAMAccountName": "normal.user",
        "givenName": "Normal",
        "sn": "User",
        "mail": "normal.user@dev.local",
        "description": "Test normal user (no role group)",
        "ou": f"OU=Users,{BASE_DN}",
        "groups": [],
    },
]

# Test computers
COMPUTERS = [
    {
        "cn": "WORKSTATION01",
        "sAMAccountName": "WORKSTATION01$",
        "description": "Test workstation 1",
        "ou": f"OU=Computers,{BASE_DN}",
    },
    {
        "cn": "WORKSTATION02",
        "sAMAccountName": "WORKSTATION02$",
        "description": "Test workstation 2",
        "ou": f"OU=Computers,{BASE_DN}",
    },
    {
        "cn": "SERVER01",
        "sAMAccountName": "SERVER01$",
        "description": "Test server 1",
        "ou": f"OU=Computers,{BASE_DN}",
    },
]


def wait_for_ldap(server_uri, max_retries=30, delay=2):
    """Wait for LDAP server to become available."""
    for attempt in range(1, max_retries + 1):
        try:
            server = Server(server_uri, get_info=ALL)
            conn = Connection(server, user=ADMIN_DN, password=ADMIN_PASSWORD, auto_bind=True)
            conn.unbind()
            print(f"LDAP server is ready (attempt {attempt})")
            return True
        except Exception as e:
            print(f"Waiting for LDAP server (attempt {attempt}/{max_retries}): {e}")
            time.sleep(delay)
    print("ERROR: LDAP server did not become available")
    return False


def get_connection(server_uri):
    """Create and return an LDAP connection."""
    server = Server(server_uri, get_info=ALL)
    conn = Connection(server, user=ADMIN_DN, password=ADMIN_PASSWORD, auto_bind=True)
    return conn


def dn_exists(conn, dn):
    """Check if a DN already exists."""
    conn.search(dn, "(objectClass=*)", search_scope="BASE")
    return len(conn.entries) > 0


def create_ou(conn, ou_dn):
    """Create an OU if it doesn't exist."""
    if dn_exists(conn, ou_dn):
        print(f"  OU already exists: {ou_dn}")
        return
    ou_name = ou_dn.split(",")[0].split("=")[1]
    attrs = {
        "objectClass": ["top", "organizationalUnit"],
        "ou": ou_name,
    }
    conn.add(ou_dn, attributes=attrs)
    if conn.result["result"] == 0:
        print(f"  Created OU: {ou_dn}")
    else:
        print(f"  ERROR creating OU {ou_dn}: {conn.result}")


def create_group(conn, group_info):
    """Create a security group if it doesn't exist."""
    group_dn = f"CN={group_info['cn']},{group_info['ou']}"
    if dn_exists(conn, group_dn):
        print(f"  Group already exists: {group_dn}")
        return
    attrs = {
        "objectClass": ["top", "group"],
        "cn": group_info["cn"],
        "sAMAccountName": group_info["sAMAccountName"],
        "description": group_info["description"],
        "groupType": -2147483646,  # Global security group
    }
    conn.add(group_dn, attributes=attrs)
    if conn.result["result"] == 0:
        print(f"  Created group: {group_dn}")
    else:
        print(f"  ERROR creating group {group_dn}: {conn.result}")


def samba_tool_setpassword(username, password):
    """Set a user's password using samba-tool (avoids LDAP encryption requirement)."""
    result = subprocess.run(
        ["samba-tool", "user", "setpassword", username, f"--newpassword={password}"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"  Set password for: {username}")
        return True
    else:
        print(f"  ERROR setting password for {username}: {result.stderr.strip()}")
        return False


def create_user(conn, user_info, password):
    """Create a user account if it doesn't exist, set password, and enable."""
    user_dn = f"CN={user_info['cn']},{user_info['ou']}"
    if dn_exists(conn, user_dn):
        print(f"  User already exists: {user_dn}")
        # Still try to add to groups in case that was missed
        add_user_to_groups(conn, user_dn, user_info.get("groups", []))
        return

    # Step 1: Create user (disabled)
    # UAC: NORMAL_ACCOUNT (0x200) | ACCOUNTDISABLE (0x2) = 0x202 = 514
    attrs = {
        "objectClass": ["top", "person", "organizationalPerson", "user"],
        "cn": user_info["cn"],
        "sAMAccountName": user_info["sAMAccountName"],
        "userPrincipalName": f"{user_info['sAMAccountName']}@dev.local",
        "givenName": user_info["givenName"],
        "sn": user_info["sn"],
        "displayName": user_info["cn"],
        "description": user_info["description"],
        "userAccountControl": 514,
    }
    if "mail" in user_info:
        attrs["mail"] = user_info["mail"]

    conn.add(user_dn, attributes=attrs)
    if conn.result["result"] != 0:
        print(f"  ERROR creating user {user_dn}: {conn.result}")
        return
    print(f"  Created user: {user_dn}")

    # Step 2: Set password via samba-tool (runs locally, no LDAP encryption needed)
    if not samba_tool_setpassword(user_info["sAMAccountName"], password):
        # Clean up the disabled user
        conn.delete(user_dn)
        return

    # Step 3: Enable account (NORMAL_ACCOUNT = 512, DONT_EXPIRE_PASSWORD = 65536)
    conn.modify(user_dn, {"userAccountControl": [(MODIFY_REPLACE, [66048])]})
    if conn.result["result"] != 0:
        print(f"  ERROR enabling user {user_dn}: {conn.result}")
        return
    print(f"  Enabled user: {user_info['sAMAccountName']}")

    # Step 4: Add to groups
    add_user_to_groups(conn, user_dn, user_info.get("groups", []))


def add_user_to_groups(conn, user_dn, group_names):
    """Add a user to the specified groups."""
    for group_name in group_names:
        group_dn = f"CN={group_name},OU=Groups,{BASE_DN}"
        # Check if already a member
        conn.search(group_dn, "(objectClass=group)", attributes=["member"])
        if conn.entries:
            members = conn.entries[0].member.values if hasattr(conn.entries[0], "member") else []
            if user_dn.lower() in [m.lower() for m in members]:
                print(f"  User already in group: {group_name}")
                continue

        conn.modify(group_dn, {"member": [(MODIFY_ADD, [user_dn])]})
        if conn.result["result"] == 0:
            print(f"  Added to group: {group_name}")
        elif conn.result["result"] == 68:  # Already exists
            print(f"  User already in group: {group_name}")
        else:
            print(f"  ERROR adding to group {group_name}: {conn.result}")


def create_computer(conn, computer_info):
    """Create a computer account if it doesn't exist."""
    computer_dn = f"CN={computer_info['cn']},{computer_info['ou']}"
    if dn_exists(conn, computer_dn):
        print(f"  Computer already exists: {computer_dn}")
        return
    # UAC: WORKSTATION_TRUST_ACCOUNT = 4096
    attrs = {
        "objectClass": ["top", "person", "organizationalPerson", "user", "computer"],
        "cn": computer_info["cn"],
        "sAMAccountName": computer_info["sAMAccountName"],
        "description": computer_info["description"],
        "userAccountControl": 4096,
    }
    conn.add(computer_dn, attributes=attrs)
    if conn.result["result"] == 0:
        print(f"  Created computer: {computer_dn}")
    else:
        print(f"  ERROR creating computer {computer_dn}: {conn.result}")


def main():
    parser = argparse.ArgumentParser(description="Seed Samba AD DC with test data")
    parser.add_argument("--host", default="ldap://samba-dc", help="LDAP server URI")
    parser.add_argument("--port", type=int, default=389, help="LDAP port")
    args = parser.parse_args()

    server_uri = args.host
    if "://" not in server_uri:
        server_uri = f"ldap://{server_uri}"

    print(f"=== Seeding directory: {server_uri} ===")
    print(f"  Base DN: {BASE_DN}")

    if not wait_for_ldap(server_uri):
        sys.exit(1)

    conn = get_connection(server_uri)

    try:
        # Create OUs
        print("\n--- Creating OUs ---")
        for ou_dn in OUS:
            create_ou(conn, ou_dn)

        # Create groups
        print("\n--- Creating Groups ---")
        for group_info in GROUPS:
            create_group(conn, group_info)

        # Create service account
        print("\n--- Creating Service Account ---")
        svc_user_info = {
            "cn": SVC_ACCOUNT["cn"],
            "sAMAccountName": SVC_ACCOUNT["sAMAccountName"],
            "givenName": "Service",
            "sn": "Account",
            "description": SVC_ACCOUNT["description"],
            "ou": SVC_ACCOUNT["ou"],
            "groups": [],
        }
        create_user(conn, svc_user_info, SVC_ACCOUNT["password"])

        # Grant service account read access (add to Domain Admins for dev simplicity)
        svc_dn = f"CN={SVC_ACCOUNT['cn']},{SVC_ACCOUNT['ou']}"
        domain_admins_dn = f"CN=Domain Admins,CN=Users,{BASE_DN}"
        conn.modify(domain_admins_dn, {"member": [(MODIFY_ADD, [svc_dn])]})
        if conn.result["result"] == 0:
            print(f"  Added svc_admanager to Domain Admins (dev only)")
        elif conn.result["result"] == 68:
            print(f"  svc_admanager already in Domain Admins")
        else:
            print(f"  Note: Could not add to Domain Admins: {conn.result}")

        # Create test users
        print("\n--- Creating Users ---")
        for user_info in USERS:
            create_user(conn, user_info, USER_PASSWORD)

        # Create computers
        print("\n--- Creating Computers ---")
        for computer_info in COMPUTERS:
            create_computer(conn, computer_info)

        print("\n=== Seeding complete ===")
        print(f"\nService account DN: CN={SVC_ACCOUNT['cn']},{SVC_ACCOUNT['ou']}")
        print(f"Service account password: {SVC_ACCOUNT['password']}")
        print(f"\nTest user password: {USER_PASSWORD}")
        print("  admin.user    -> ADRS-Admins (Admin)")
        print("  helpdesk.user -> ADRS-HelpDesk (HelpDesk)")
        print("  groupmgr.user -> ADRS-GroupManagers (GroupManager)")
        print("  readonly.user -> (no role group)")
        print("  normal.user   -> (no role group)")

    finally:
        conn.unbind()


if __name__ == "__main__":
    main()
