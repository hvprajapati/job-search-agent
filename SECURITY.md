# Security Policy

## Reporting a Vulnerability
Email `security@pathfinder.dev`. Do not open public issues. Response within 48 hours.

## Security Measures
- JWT RS256 with refresh token rotation and anti-theft detection
- Argon2id password hashing
- Prompt injection detection in agent guardrail
- Rate limiting via Redis sliding window
- PII redaction in logs and error tracking
- CORS with explicit origins
- Security headers (HSTS, CSP, X-Frame-Options)
- File upload validation (type, size, ClamAV scanning)

## Supported Versions
| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Active |

## Dependencies
Automated scanning via Dependabot. Critical patches applied within 72 hours.
