# ActiveDirectoryRoleService

A Django 5.1 web application for managing on-premises Active Directory. Provides directory browsing, user/group management with role-based delegation, DNS record management, GPO viewing, automated password expiry notifications, and self-service password resets.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 5.1, Bootstrap 5, htmx |
| Database | PostgreSQL 16 |
| AD Connection | ldap3 (LDAP/LDAPS) + optional GSSAPI Kerberos SSO |
| Email | Pluggable: SMTP (Postfix) or AWS SES |
| Background Tasks | Celery + Redis + django-celery-beat |
| Deployment | Docker Compose (Nginx, Gunicorn, Celery, PostgreSQL, Redis) |

## Quick Start

```bash
cp .env.example .env        # Edit with your AD/DB/Redis settings
make docker-build && make docker-up
# Visit https://localhost and log in with AD credentials
```

See `.env.example` for all configuration options.

---

## Application Layout

Every page uses a fixed dark navbar at the top and a dark sidebar on the left. The main content area is on the right.

```
+--[ AD Manager ]---[ EXAMPLE ]-------------------[ John Doe ]--[ Admin ]--[ Logout ]--+
|                                                                                       |
| +----------+  +------------------------------------------------------------------+    |
| | SIDEBAR  |  |  MAIN CONTENT AREA                                               |    |
| |          |  |                                                                   |    |
| | Dashboard|  |  (varies by page - see wireframes below)                          |    |
| | Users    |  |                                                                   |    |
| | Computers|  |                                                                   |    |
| | OUs      |  |                                                                   |    |
| | Groups   |  |                                                                   |    |
| | DNS *    |  |                                                                   |    |
| | GPOs *   |  |                                                                   |    |
| | Notifs   |  |                                                                   |    |
| | Audit *  |  |                                                                   |    |
| |          |  |                                                                   |    |
| +----------+  +------------------------------------------------------------------+    |
+-----------------------------------------------------------------------------------+---+

   * = Admin-only sidebar links
```

---

## Page Wireframes

### Login (`/accounts/login/`)

No sidebar. Centered card with AD domain label.

```
+-----------------------------------------------------------------------+
|                        AD Manager  [ EXAMPLE ]                        |
+-----------------------------------------------------------------------+
|                                                                       |
|                    +-----------------------------+                     |
|                    |       EXAMPLE Login          |                     |
|                    |                             |                     |
|                    |  Username  [_______________]|                     |
|                    |  Password  [_______________]|                     |
|                    |                             |                     |
|                    |       [ Sign In ]           |                     |
|                    +-----------------------------+                     |
|                                                                       |
+-----------------------------------------------------------------------+
```

### Dashboard (`/`)

Four colored stat cards, domain controller table, and quick-link buttons.

```
+-------------------------------------------------------------------+
|  Domain Dashboard                                                 |
|                                                                   |
|  +------------+  +------------+  +------------+  +------------+   |
|  | USERS      |  | COMPUTERS  |  | GROUPS     |  | DOMAIN     |   |
|  |   1,247    |  |     382    |  |     156    |  | CONTROLLERS|   |
|  | View all ->|  | View all ->|  | View all ->|  |      3     |   |
|  +-(blue)-----+  +-(green)----+  +-(cyan)-----+  +-(yellow)---+   |
|                                                                   |
|  +-- Domain Controllers ------------------------------------------+|
|  | Name          | DNS Name              | Operating System       ||
|  |---------------|----------------------|------------------------||
|  | DC01          | dc01.example.com     | Windows Server 2022    ||
|  | DC02          | dc02.example.com     | Windows Server 2022    ||
|  +---------------------------------------------------------------|+
|                                                                   |
|  +-- Quick Links ------------------------------------------------+|
|  | [ Browse Users ]  [ Browse Computers ]  [ Browse OU Tree ]    ||
|  +---------------------------------------------------------------+|
+-------------------------------------------------------------------+
```

### User List (`/directory/users/`)

Searchable table with pagination. "Create User" button visible only to Admins.

```
+-------------------------------------------------------------------+
|  Users  [1,247]                             [ + Create User ]     |
|                                                                   |
|  Search: [________________________] [Search]                      |
|                                                                   |
|  +---------------------------------------------------------------+|
|  | Name            | Username | Email              | Status |Last||
|  |-----------------|----------|--------------------| Logon  |    ||
|  | John Doe        | jdoe     | jdoe@example.com   |Enabled |2d ||
|  | Jane Smith      | jsmith   | jsmith@example.com |Enabled |5d ||
|  | Bob Disabled    | bdis     | bdis@example.com   |Disabled|30d||
|  | ...             | ...      | ...                | ...    |...||
|  +---------------------------------------------------------------+|
|                                                                   |
|  [< Prev]  Page 1 of 50  [Next >]                                |
+-------------------------------------------------------------------+
```

### User Detail (`/directory/users/<dn>/`)

User attributes, action buttons (Admin/HelpDesk), group memberships.

```
+-------------------------------------------------------------------+
|  John Doe                                        [Enabled]        |
|  CN=John Doe,OU=Staff,DC=example,DC=com                          |
|                                                                   |
|  +-- Actions (Admin/HelpDesk) ---+  +-- User Attributes --------+|
|  | [Reset Password]              |  | Display Name  | John Doe   ||
|  | [Disable Account]             |  | Username      | jdoe       ||
|  | [Unlock Account]              |  | Email         | jdoe@...   ||
|  +--------------------------------+  | Title         | Engineer   ||
|                                      | Department    | IT         ||
|  +-- Group Memberships ----------+  | Phone         | x1234      ||
|  | o Domain Users                |  | Created       | 2024-01-15 ||
|  | o IT Staff                    |  | Last Logon    | 2026-02-14 ||
|  | o VPN Users                   |  | Pwd Last Set  | 2026-01-01 ||
|  +-------------------------------+  | UAC           | 0x200      ||
|                                      +-------------------------------+|
|  [< Back to Users]                                                |
+-------------------------------------------------------------------+
```

**Reset Password Modal (opens on click):**

```
+----------------------------------------------+
|  Reset Password for jdoe             [X]     |
|                                              |
|  New Password  [__________________] [Gen][eye]|
|                                              |
|  Password Rules:                             |
|    [x] At least 15 characters                |
|    [x] At least 1 uppercase letter           |
|    [x] At least 1 lowercase letter           |
|    [x] At least 1 number                     |
|    [x] At least 1 special character          |
|    [x] Passwords match                       |
|                                              |
|          [Reset Password]  [Cancel]          |
+----------------------------------------------+
```

### Create User (`/directory/users/create/`)

Full form with OU picker, personal details, password generator.

```
+-------------------------------------------------------------------+
|  Create New User                                                  |
|                                                                   |
|  -- Account Information --                                        |
|  Username (sAMAccountName)  [_______________]                     |
|  Target OU  [v OU=Staff,DC=example,DC=com     ]                  |
|                                                                   |
|  -- Personal Details --                                           |
|  First Name  [___________]   Last Name [____________]             |
|  Email       [___________]   Phone     [____________]             |
|  Job Title   [___________]   Department[____________]             |
|  Company     [___________]   Description[___________]             |
|                                                                   |
|  -- Password --                                                   |
|  Password          [_________________________] [Generate] [eye]   |
|  Confirm Password  [_________________________]                    |
|                                                                   |
|  Password Rules:        [x] 15+ chars   [x] 1 uppercase          |
|                         [x] 1 lowercase [x] 1 number             |
|                         [x] 1 special   [x] Passwords match      |
|                                                                   |
|  [x] Enable account after creation                                |
|  [ ] Send welcome email with credentials                          |
|                                                                   |
|  [ Create User ]   [ Cancel ]                                     |
+-------------------------------------------------------------------+
```

### Computer List (`/directory/computers/`)

```
+-------------------------------------------------------------------+
|  Computers  [382]                                                 |
|                                                                   |
|  Search: [________________________] [Search]                      |
|                                                                   |
|  | Name          | DNS Name              | OS               |Last|
|  |---------------|----------------------|------------------|Logn|
|  | WORKSTATION01 | ws01.example.com     | Windows 11 Pro   | 1d |
|  | SERVER-APP01  | app01.example.com    | Windows Srv 2022 | 0d |
|  | ...           | ...                  | ...              | .. |
|                                                                   |
|  [< Prev]  Page 1 of 16  [Next >]                                |
+-------------------------------------------------------------------+
```

### OU Tree (`/directory/ous/`)

Interactive tree with lazy-loaded child nodes via htmx.

```
+-------------------------------------------------------------------+
|  Organizational Units                                             |
|                                                                   |
|  +-- OU Tree ------------------------------------------------+   |
|  |                                                            |   |
|  |  v example.com                                             |   |
|  |    v Staff                                                 |   |
|  |        > Engineering                                       |   |
|  |        > Marketing                                         |   |
|  |        > Finance                                           |   |
|  |    v Servers                                               |   |
|  |        > Production                                        |   |
|  |        > Staging                                           |   |
|  |    > Service Accounts                                      |   |
|  |    > Disabled Users                                        |   |
|  |                                                            |   |
|  +------------------------------------------------------------+   |
|                                                                   |
|  Click an OU to expand. Click the name to view details.           |
+-------------------------------------------------------------------+
```

### OU Detail (`/directory/ous/<dn>/`)

```
+-------------------------------------------------------------------+
|  OU: Engineering                                                  |
|  OU=Engineering,OU=Staff,DC=example,DC=com                        |
|                                                                   |
|  +-- OU Attributes ---+                                           |
|  | Name  | Engineering|                                           |
|  | Desc  | Eng team   |                                           |
|  +--------------------+                                           |
|                                                                   |
|  +-- Users ------+  +-- Computers --+  +-- Groups ---------+     |
|  | o John Doe    |  | o WS-ENG01   |  | o Eng Team        |     |
|  | o Jane Smith  |  | o WS-ENG02   |  | o Code Review     |     |
|  | o Bob Builder |  |              |  |                   |     |
|  +---------------+  +--------------+  +-------------------+     |
|                                                                   |
|  [< Back to OU Tree]                                              |
+-------------------------------------------------------------------+
```

### Group List (`/groups/`)

```
+-------------------------------------------------------------------+
|  AD Groups                                                        |
|                                                                   |
|  Search: [________________________] [Search]                      |
|                                                                   |
|  | Name             | Description         | Members | Type      |
|  |------------------|---------------------|---------|-----------|
|  | Domain Admins    | AD built-in admins  |    5    | Security  |
|  | IT Staff         | IT department group  |   23    | Security  |
|  | All-Company      | Distribution list   |  1200   | Distrib.  |
|  | ...              | ...                 |   ...   | ...       |
|                                                                   |
|  [< Prev]  Page 1 of 7  [Next >]                                 |
+-------------------------------------------------------------------+
```

### Group Detail (`/groups/<dn>/`)

Add/remove members available to Admin, HelpDesk, and delegated GroupManagers.

```
+-------------------------------------------------------------------+
|  Groups > IT Staff                                                |
|                                                                   |
|  +-- Group Info --------+  +-- Members (23) --------------------+|
|  | DN    | CN=IT Staff...|  |                                    ||
|  | Desc  | IT department  |  | Add member: [type to search___]  ||
|  | Mgr   | John Doe      |  |                                    ||
|  +------------------------+  | Name          | DN        |Action ||
|                              |---------------|-----------|-------||
|                              | John Doe      | CN=John.. |[Rmv] ||
|                              | Jane Smith    | CN=Jane.. |[Rmv] ||
|                              | Bob Builder   | CN=Bob..  |[Rmv] ||
|                              +-------------------------------+---+|
|                                                                   |
|  [< Back to Groups]                                               |
+-------------------------------------------------------------------+
```

### DNS Zone List (`/dns/`) -- Admin Only

```
+-------------------------------------------------------------------+
|  DNS Zones                                                        |
|                                                                   |
|  | Zone Name            | Distinguished Name       | Records    |
|  |----------------------|--------------------------|------------|
|  | example.com          | DC=example.com,CN=Mic... | [View]     |
|  | 10.in-addr.arpa      | DC=10.in-addr.arpa,...   | [View]     |
|  | _msdcs.example.com   | DC=_msdcs.example.com..  | [View]     |
+-------------------------------------------------------------------+
```

### DNS Record List (`/dns/<zone_dn>/`)

```
+-------------------------------------------------------------------+
|  DNS Zones > example.com Records                  [ + Create ]    |
|                                                                   |
|  | Name     | Type   | Data              | TTL  | Actions        |
|  |----------|--------|-------------------|------|----------------|
|  | @        | SOA    | dc01.example.com  | 3600 | [Edit][Delete] |
|  | @        | NS     | dc01.example.com  | 3600 | [Edit][Delete] |
|  | www      | A      | 10.0.1.50         | 3600 | [Edit][Delete] |
|  | mail     | MX     | 10 mail.example.. | 3600 | [Edit][Delete] |
|  | app      | CNAME  | www.example.com   | 3600 | [Edit][Delete] |
+-------------------------------------------------------------------+
```

### GPO List (`/gpo/`) -- Admin Only, Read-Only

```
+-------------------------------------------------------------------+
|  Group Policy Objects                                             |
|                                                                   |
|  | Name                       | Status   | Created    | Modified |
|  |----------------------------|----------|------------|----------|
|  | Default Domain Policy      | Enabled  | 2020-03-01 | 2026-01 |
|  | Workstation Lockdown       | Enabled  | 2023-06-15 | 2025-11 |
|  | Server Hardening           | Disabled | 2024-01-10 | 2024-12 |
+-------------------------------------------------------------------+
```

### GPO Detail (`/gpo/<dn>/`)

```
+-------------------------------------------------------------------+
|  GPOs > Default Domain Policy                                     |
|                                                                   |
|  +-- GPO Info -----+  +-- Linked OUs ----------------------------+|
|  | Status |Enabled  |  | OU Name           | DN                  ||
|  | SYSVOL |\\...\.. |  |-------------------|--------------------||
|  | Version| 12      |  | example.com       | DC=example,DC=com  ||
|  | Created| 2020-.. |  | Staff             | OU=Staff,DC=...    ||
|  | Modifed| 2026-.. |  |                   |                    ||
|  +------------------+  +----------------------------------------+|
+-------------------------------------------------------------------+
```

### Notification Config (`/notifications/config/`) -- Admin Only

```
+-------------------------------------------------------------------+
|  Notification Configuration                                       |
|                                                                   |
|  [ General ] [ SMTP ] [ Amazon SES ]                              |
|  +------------------------------------------------------------+  |
|  | Backend Type    [v SMTP           ]                          |  |
|  | From Email      [noreply@example.com____]                    |  |
|  | Warning Days    [30,14,7,3,1____________]                    |  |
|  | [x] Notifications Enabled                                    |  |
|  +------------------------------------------------------------+  |
|                                                                   |
|  [ Save Configuration ]                                           |
+-------------------------------------------------------------------+
```

### Email Template List (`/notifications/templates/`)

```
+-------------------------------------------------------------------+
|  Email Templates                [ Send Email ] [ + Create ]       |
|                                                                   |
|  | Name                | Subject              |Active|Updated|Act|
|  |---------------------|----------------------|------|-------|---|
|  | password_expiry     | Password Expires in..|Active| 02-15 |EDT|
|  | password_reset      | Password Reset Req.. |Active| 02-15 |TST|
|  | welcome             | Welcome to {{domain}}|Active| 02-15 |USE|
|                                                                   |
|  Actions: [Edit] [Test] [Use]                                     |
+-------------------------------------------------------------------+
```

### Email Template Test & Preview (`/notifications/templates/<pk>/preview/`)

Two-column layout. Left: variable inputs and send-test. Right: rendered preview.

```
+-------------------------------------------------------------------+
|  Test Template: password_expiry    [Syntax Ref] [Edit] [Back]     |
|                                                                   |
|  +-- Variables ----------+  +-- Rendered Preview ---------------+|
|  |                       |  |                                    ||
|  | {{ display_name }}    |  | Subject: Password Expires in 7d   ||
|  | [John Doe________]   |  | +-------------------------------+ ||
|  |                       |  | |  Hello John Doe,              | ||
|  | {{ days_until_expiry}}|  | |                               | ||
|  | [7_________________]  |  | |  Your password will expire    | ||
|  |                       |  | |  in 7 days on March 15, 2026. | ||
|  | {{ expiry_date }}     |  | |                               | ||
|  | [March 15, 2026____]  |  | |  Please change it soon.      | ||
|  |                       |  | +-------------------------------+ ||
|  | [Preview]             |  |                                    ||
|  |                       |  +------------------------------------+|
|  |-----------------------|                                        |
|  | Send test email to:   |                                        |
|  | [you@example.com] [Send Test]                                  |
|  +------------------------+                                       |
+-------------------------------------------------------------------+
```

### Send Email (`/notifications/send/`)

Compose and send to specific addresses or an AD group.

```
+-------------------------------------------------------------------+
|  Send Email                                    [Send History]     |
|                                                                   |
|  +-- Recipients --------------------------------------------------+
|  | (o) Specific email addresses   ( ) AD Group members            |
|  |                                                                |
|  | [user1@example.com                                ]            |
|  | [user2@example.com                                ]            |
|  +----------------------------------------------------------------+
|                                                                   |
|  +-- Email Content -----------------------------------------------+
|  | [ ] Start from template  [v Select template...]                |
|  |                                                                |
|  | Subject    [Important Announcement__________________]          |
|  | HTML Body  +---------------------------------------------+    |
|  |            | <h2>Hello,</h2>                             |    |
|  |            | <p>This is an announcement from IT.</p>     |    |
|  |            +---------------------------------------------+    |
|  | Text Body  [Plain text version (optional)___________]         |
|  +----------------------------------------------------------------+
|                                                                   |
|  [ Send Email ]   [ Cancel ]                                      |
+-------------------------------------------------------------------+
```

### Notification History (`/notifications/history/`)

```
+-------------------------------------------------------------------+
|  Notification History                                             |
|                                                                   |
|  From: [2026-01-01] To: [2026-02-16] Status: [v All] [Filter]    |
|                                                                   |
|  | Date       | Recipient         | Subject          | Status    |
|  |------------|-------------------|------------------|-----------|
|  | 2026-02-15 | jdoe@example.com  | Password Expires | Sent      |
|  | 2026-02-15 | jsmith@example.com| Welcome to EXAM..| Sent      |
|  | 2026-02-14 | bad@invalid       | Password Reset   | Failed    |
|                                                                   |
|  [< Prev]  Page 1 of 3  [Next >]                                 |
+-------------------------------------------------------------------+
```

### Self-Service Password Reset (`/notifications/password-reset/`)

Public page (no login required).

```
+-----------------------------------------------------------------------+
|                                                                       |
|                    +-----------------------------+                     |
|                    |     Password Reset          |                     |
|                    |                             |                     |
|                    | Enter your email address    |                     |
|                    | and we'll send a reset link.|                     |
|                    |                             |                     |
|                    | Email [__________________] |                     |
|                    |                             |                     |
|                    |   [ Send Reset Link ]       |                     |
|                    |                             |                     |
|                    |   Back to Login             |                     |
|                    +-----------------------------+                     |
+-----------------------------------------------------------------------+
```

### Set New Password (`/notifications/password-reset/<token>/`)

```
+-----------------------------------------------------------------------+
|                                                                       |
|                    +-------------------------------+                   |
|                    |     Set New Password          |                   |
|                    |                               |                   |
|                    | New Password     [__________] |                   |
|                    | Confirm Password [__________] |                   |
|                    |                               |                   |
|                    | [x] 15+ characters            |                   |
|                    | [x] 1 uppercase letter        |                   |
|                    | [x] 1 lowercase letter        |                   |
|                    | [x] 1 number                  |                   |
|                    | [x] 1 special character       |                   |
|                    | [x] Passwords match           |                   |
|                    |                               |                   |
|                    |    [ Reset Password ]         |                   |
|                    +-------------------------------+                   |
+-----------------------------------------------------------------------+
```

### Audit Log (`/audit/`) -- Admin Only

```
+-------------------------------------------------------------------+
|  Audit Log                               [CSV Export] [JSON Export]|
|                                                                   |
|  From:[________] To:[________] Category:[v All] User:[____]       |
|  Action:[________] Status:[v All]  [Filter]                       |
|                                                                   |
|  | Time       | User  | Action         | Category | Target  |Stat|
|  |------------|-------|----------------|----------|---------|-----|
|  | 02-16 09:12| admin | user.create    | User     | CN=Jo.. | OK |
|  | 02-16 09:11| admin | auth.login     | Auth     | CN=Ad.. | OK |
|  | 02-15 17:30| jdoe  | password.reset | User     | CN=jd.. | OK |
|  | 02-15 16:00| system| email.send     | Notif    | -       |Fail|
|                                                                   |
|  [< Prev]  Page 1 of 25  [Next >]                                |
+-------------------------------------------------------------------+
```

### Audit Detail (`/audit/<pk>/`)

```
+-------------------------------------------------------------------+
|  Audit Entry #1042                              [< Back to List]  |
|                                                                   |
|  +-- Details -------------------------------------------------+  |
|  | Timestamp | 2026-02-16 09:12:34                             |  |
|  | User      | admin                                          |  |
|  | Action    | user.create                                    |  |
|  | Category  | User                                           |  |
|  | Target DN | CN=John Doe,OU=Staff,DC=example,DC=com         |  |
|  | IP        | 10.0.1.25                                      |  |
|  | Status    | Success                                        |  |
|  | Detail    | {"sam": "jdoe", "ou": "OU=Staff,...",           |  |
|  |           |  "email_sent": true}                            |  |
|  +-------------------------------------------------------------+  |
+-------------------------------------------------------------------+
```

### Group Delegation (`/groups/delegation/`) -- Admin Only

```
+-------------------------------------------------------------------+
|  Delegated Groups                       [ + Create Delegated Group]|
|                                                                   |
|  | Display Name  | Group DN             | Managers    | Status   |
|  |---------------|----------------------|-------------|----------|
|  | IT Staff      | CN=IT Staff,OU=Gr... | admin, jmgr | Enabled  |
|  | Marketing     | CN=Marketing,OU=G... | mktg_lead   | Enabled  |
|                                                                   |
|  Actions: [Assign Manager]                                        |
+-------------------------------------------------------------------+
```

---

## Process Flows

### 1. Authentication Flow

```
                 +------------------+
                 |   Login Page     |
                 |  /accounts/login |
                 +--------+---------+
                          |
                    POST username
                    + password
                          |
                          v
               +---------------------+
               | ADLDAPBackend       |
               | .authenticate()    |
               +--------+------------+
                        |
                        v
          +----------------------------+
          | Search AD by sAMAccountName|
          | (service account bind)     |
          +-------------+--------------+
                        |
                    User found?
                   /          \
                 No            Yes
                 |              |
                 v              v
           +---------+  +------------------+
           | Login   |  | Bind as user     |
           | failed  |  | (verify password)|
           +---------+  +--------+---------+
                                 |
                            Bind OK?
                           /        \
                         No          Yes
                         |            |
                         v            v
                   +---------+  +------------------------+
                   | Login   |  | Create/Update          |
                   | failed  |  | Django User +          |
                   +---------+  | UserProfile            |
                                +----------+-------------+
                                           |
                                           v
                                +---------------------+
                                | Sync AD group       |
                                | memberships to      |
                                | Django Roles        |
                                | (Admin/HelpDesk/    |
                                |  GroupMgr/ReadOnly)  |
                                +----------+----------+
                                           |
                                           v
                                +---------------------+
                                | Log audit entry     |
                                | (auth.login)        |
                                +----------+----------+
                                           |
                                           v
                                +---------------------+
                                | Redirect to         |
                                | Dashboard (/)       |
                                +---------------------+
```

### 2. User Creation Flow (Admin)

```
  +------------------+        +---------------------+
  | User List Page   | -----> | Create User Form    |
  | /directory/users |  click | /directory/users/    |
  +------------------+  btn   |         create/      |
                              +----------+----------+
                                         |
                                   POST form data
                                   (name, OU, password)
                                         |
                                         v
                              +---------------------+
                              | Validate password   |
                              | (15 chars, 1 upper, |
                              |  1 lower, 1 digit,  |
                              |  1 special)          |
                              +----------+----------+
                                         |
                                     Valid?
                                    /      \
                                  No        Yes
                                  |          |
                                  v          v
                            +--------+ +------------------------+
                            | Show   | | Step 1: Create user    |
                            | errors | | in AD (DISABLED)       |
                            +--------+ | UAC = 0x0202           |
                                       +----------+-------------+
                                                  |
                                                  v
                                       +------------------------+
                                       | Step 2: Set password   |
                                       | via unicodePwd         |
                                       | (UTF-16-LE encoded)    |
                                       +----------+-------------+
                                                  |
                                             Success?
                                            /        \
                                          No          Yes
                                          |            |
                                          v            v
                                  +-----------+ +--------------------+
                                  | Cleanup:  | | Step 3: Enable     |
                                  | Delete    | | account            |
                                  | AD object | | (clear disable     |
                                  +-----------+ |  flag in UAC)      |
                                                +----------+---------+
                                                           |
                                                  Send welcome email?
                                                  /               \
                                                No                 Yes
                                                |                   |
                                                |                   v
                                                |         +-------------------+
                                                |         | Queue Celery task:|
                                                |         | Send welcome email|
                                                |         | with credentials  |
                                                |         +-------------------+
                                                |                   |
                                                v                   v
                                       +-----------------------------+
                                       | Log audit entry             |
                                       | (user.create)               |
                                       +-------------+---------------+
                                                     |
                                                     v
                                       +-----------------------------+
                                       | Redirect to User List      |
                                       | with success message       |
                                       +-----------------------------+
```

### 3. Self-Service Password Reset Flow

```
  +--------------------+
  | Password Reset     |
  | Request Page       |
  | (public, no login) |
  +----------+---------+
             |
        POST email
             |
             v
  +---------------------+
  | Search AD for user  |
  | by email address    |
  +----------+----------+
             |
         Found?
        /       \
      No         Yes
      |           |
      |           v
      |   +----------------------+
      |   | Generate signed      |
      |   | token (1hr expiry)   |
      |   +----------+-----------+
      |              |
      |              v
      |   +----------------------+
      |   | Queue Celery task:   |
      |   | Send password_reset  |
      |   | email with link      |
      |   +----------------------+
      |              |
      v              v
  +----------------------------------+
  | Show "Check Your Email" page     |
  | (same message whether found      |
  |  or not - prevents enumeration)  |
  +----------------------------------+

         --- User clicks email link ---

  +------------------------------------+
  | Set New Password Page              |
  | /notifications/password-reset/     |
  |                        <token>/    |
  +------------------+-----------------+
                     |
               Validate token
              (signature + expiry)
                /          \
           Invalid          Valid
              |               |
              v               v
  +----------------+  +-----------------------+
  | Show error:    |  | Show password form    |
  | "Link expired  |  | with live rule        |
  |  or invalid"   |  | checklist             |
  +----------------+  +-----------+-----------+
                                  |
                             POST new password
                                  |
                                  v
                      +---------------------+
                      | Validate password   |
                      | (same 15-char rules)|
                      +----------+----------+
                                 |
                             Valid?
                            /      \
                          No        Yes
                          |          |
                          v          v
                    +--------+ +---------------------+
                    | Show   | | Set password in AD  |
                    | errors | | (unicodePwd)        |
                    +--------+ +----------+----------+
                                          |
                                          v
                               +---------------------+
                               | Log audit entry     |
                               | (password.reset)    |
                               +----------+----------+
                                          |
                                          v
                               +---------------------+
                               | Redirect to Login   |
                               | with success msg    |
                               +---------------------+
```

### 4. Password Expiry Notification Flow (Automated)

```
  +---------------------------+
  | Celery Beat Scheduler     |
  | (daily at configured time)|
  +-------------+-------------+
                |
                v
  +---------------------------+
  | check_password_expirations|
  | (Celery task)             |
  +-------------+-------------+
                |
                v
  +---------------------------+
  | Load NotificationConfig   |
  | (warn_days: 30,14,7,3,1)  |
  +-------------+-------------+
                |
                v
  +---------------------------+
  | Query ALL AD users via    |
  | LDAP: get pwdLastSet,     |
  | maxPwdAge, email          |
  +-------------+-------------+
                |
                v
  +---------------------------+
  | For each user, calculate  |
  | days until password expiry|
  +-------------+-------------+
                |
       For each user where
       days_until_expiry
       matches a warn_day:
                |
                v
  +------------------------------+
  | Render password_expiry       |
  | email template with context: |
  | {display_name, email,        |
  |  days_until_expiry,          |
  |  expiry_date}                |
  +-------------+----------------+
                |
                v
  +------------------------------+
  | Send via configured backend  |
  | (SMTP or SES)               |
  +-------------+----------------+
                |
                v
  +------------------------------+
  | Create SentNotification      |
  | record (status, errors)      |
  +------------------------------+
```

### 5. Email Template Editing & Testing Flow

```
  +---------------------+
  | Template List       |
  | /notifications/     |
  |         templates/  |
  +----------+----------+
             |
     +-------+--------+--------+
     |                 |        |
     v                 v        v
  [Edit]           [Test]    [Create]
     |                 |        |
     v                 v        v
  +----------+  +-----------+  +-----------+
  | Edit     |  | Preview   |  | Create    |
  | Template |  | & Test    |  | Template  |
  | page     |  | page      |  | page      |
  +----+-----+  +-----+-----+  +-----------+
       |              |
       |              |  Auto-extracts {{ variables }}
       |              |  from template content
       |              v
       |        +------------------+
       |        | Fill in variable |
       |        | values in form   |
       |        +--------+---------+
       |                 |
       |        +--------+---------+
       |        |                  |
       |        v                  v
       |   [Preview]         [Send Test]
       |        |                  |
       |        v                  v
       |   +-----------+   +------------------+
       |   | Render    |   | Send real email  |
       |   | template  |   | to test address  |
       |   | with vars |   | with filled vars |
       |   | and show  |   +------------------+
       |   | in page   |
       |   +-----------+
       |
       +----> [Syntax Reference Modal]
              Shows: variables, filters,
              conditionals, loops, examples
```

### 6. Group Delegation & Self-Service Flow

```
  Admin sets up delegation:

  +---------------------+       +---------------------+
  | Delegation List     | ----> | Create Delegated    |
  | /groups/delegation/ |       | Group               |
  +---------------------+       | (set AD group DN,   |
                                |  display name)      |
                                +----------+----------+
                                           |
                                           v
                                +---------------------+
                                | Assign Manager      |
                                | (pick Django user)  |
                                +---------------------+

  GroupManager uses self-service:

  +---------------------+       +---------------------+
  | My Groups           | ----> | Group Detail        |
  | /groups/my-groups/  |       | /groups/<dn>/       |
  +---------------------+       +----------+----------+
                                           |
                                  +--------+--------+
                                  |                 |
                                  v                 v
                          +-------------+   +---------------+
                          | Add Member  |   | Remove Member |
                          | (typeahead  |   | (click Remove |
                          |  search)    |   |  button)      |
                          +------+------+   +-------+-------+
                                 |                  |
                                 v                  v
                          +-----------------------------+
                          | Modify AD group membership  |
                          | via LDAP (member attribute)  |
                          +-----------------------------+
                                        |
                                        v
                          +-----------------------------+
                          | Log audit entry             |
                          | (group.add_member /         |
                          |  group.remove_member)       |
                          +-----------------------------+
```

### 7. DNS Record Management Flow (Admin)

```
  +----------------+       +------------------+       +------------------+
  | Zone List      | ----> | Record List      | ----> | Create Record    |
  | /dns/          |       | /dns/<zone_dn>/  |       | Form             |
  +----------------+       +--------+---------+       | (name, type,     |
                                    |                 |  data, TTL)      |
                                    |                 +--------+---------+
                                    |                          |
                              +-----+-----+              POST to LDAP
                              |           |              (binary dnsRecord
                              v           v               encoding)
                         [Edit]      [Delete]                 |
                           |            |                     v
                           v            v            +------------------+
                    +----------+  +----------+       | Record created   |
                    | Edit form|  | Confirm  |       | in AD-integrated |
                    | (pre-    |  | deletion |       | DNS zone         |
                    |  filled) |  | page     |       +------------------+
                    +----------+  +----------+
```

---

## Roles & Permissions Matrix

| Feature | ReadOnly | GroupManager | HelpDesk | Admin |
|---------|----------|-------------|----------|-------|
| Dashboard | View | View | View | View |
| Browse Users/Computers/OUs | View | View | View | View |
| User Detail | View | View | View | View |
| Reset Password | - | - | Yes | Yes |
| Enable/Disable/Unlock User | - | - | Yes | Yes |
| Create User | - | - | - | Yes |
| Browse Groups | View | View | View | View |
| Manage Group Members | - | Delegated only | All | All |
| My Delegated Groups | - | Yes | - | - |
| Setup Delegation | - | - | - | Yes |
| DNS Management | - | - | - | Yes |
| GPO Viewing | - | - | - | Yes |
| Notification Config | - | - | - | Yes |
| Email Templates | - | - | - | Yes |
| Send Email | - | - | - | Yes |
| Audit Log | - | - | - | Yes |
| Self-Service Password Reset | Public (no login required) | | | |

---

## Configuration

All settings are via environment variables. Copy `.env.example` and edit:

```bash
cp .env.example .env
```

Key variable groups:

| Prefix | Purpose |
|--------|---------|
| `AD_*` | LDAP server, base DN, service account, SSL |
| `DB_*` | PostgreSQL host, port, name, credentials |
| `CELERY_*` | Redis broker URL |
| `EMAIL_*` | SMTP host, port, from address |
| `AWS_SES_*` | SES region, access keys |
| `RATE_LIMIT_*` | Login throttling (requests/window) |

## Docker Deployment

```bash
make docker-build    # Build images
make docker-up       # Start all 6 services
make docker-logs     # Tail logs
make docker-down     # Stop
```

Services: **nginx** (reverse proxy) / **web** (Gunicorn) / **celery-worker** / **celery-beat** / **postgres** / **redis**

## Development

```bash
make dev             # Django dev server
make migrate         # Run migrations
make seed-roles      # Create default roles + email templates
make celery-worker   # Local Celery worker
make celery-beat     # Local Celery beat
```
