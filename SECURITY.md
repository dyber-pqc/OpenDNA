# Security Policy

## Supported Versions

We support the latest minor release line.

| Version | Supported |
|---------|-----------|
| 0.4.x   | ✅        |
| 0.3.x   | ⚠ Security fixes only |
| < 0.3   | ❌        |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, email **security@dyber.org** with:

1. A description of the vulnerability
2. Steps to reproduce
3. Impact assessment (what an attacker could do)
4. Any suggested fix (optional)

We aim to:
- Acknowledge receipt within **48 hours**
- Provide an initial response within **5 business days**
- Release a fix within **30 days** for high-severity issues

## Disclosure Process

1. Report received and acknowledged
2. We investigate and confirm the issue
3. We develop a fix on a private branch
4. We coordinate disclosure with the reporter
5. Fix is released and CVE assigned (if applicable)
6. Public disclosure with credit to the reporter (unless anonymous requested)

## Known Security Considerations

OpenDNA is **local-first** and runs on your machine. Important caveats:

- **No authentication by default.** The API listens on `localhost:8765` with no auth. Do not expose it to a network you don't trust.
- **Network mode is not yet hardened.** If you bind to `0.0.0.0`, anyone who can reach the host can use your compute and read your sequences.
- **Models download from HuggingFace.** Verify the integrity of cached models if you operate in a regulated environment.
- **No encryption at rest.** Project files in `~/.opendna/` are plain JSON.
- **AI agent can execute tools.** The agent calls real functions; do not feed it untrusted instructions in environments where this matters.

## Out of Scope

The following are not considered vulnerabilities:

- Use of memory/disk by user-submitted jobs (it's a compute platform)
- Slow performance on minimal hardware
- Broken third-party services (UniProt, PDB, AlphaFold DB)
- Issues in commands explicitly designed to be unsafe (e.g., direct file paths)

## Bounty Program

We do not currently have a paid bounty program but we will publicly credit reporters in release notes (unless anonymous requested).
