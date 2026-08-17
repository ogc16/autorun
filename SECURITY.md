# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 1.0.x | Yes |

## Reporting a Vulnerability

If you discover a security vulnerability, **do not** open a public GitHub issue.

Instead, report it privately by emailing the maintainer or opening a **private** issue (if your GitHub repo settings allow it).

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge your report within 48 hours and provide an estimated timeline for a fix.

## Security Considerations

AutoRun executes arbitrary scripts with the privileges of the app process. In production:

- Deploy behind TLS (reverse proxy or platform-managed certs).
- Run the container as the non-root `autorun` user (the Dockerfile does this by default).
- Isolate the host — scripts run with the app's privileges.
- Change the default seeded passwords immediately.
- Set a strong `AUTORUN_JWT_SECRET` (32+ random bytes, base64 encoded).
- Keep MySQL on a private network.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full security hardening checklist.
