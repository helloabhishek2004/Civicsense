# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes     |

CivicSense is an early-stage research prototype. Only the latest release on the `master` branch receives security attention.

---

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Report vulnerabilities privately using one of these channels:

1. **GitHub Private Vulnerability Reporting** (preferred):  
   Go to [Security → Report a Vulnerability](https://github.com/helloabhishek2004/Civicsense/security/advisories/new) on the repository page.

2. **Email**:  
   Send details to **civicsense-security@proton.me** with the subject line:  
   `[CivicSense Security] <Brief description>`

### What to include

- A clear description of the vulnerability
- The affected component (Android app / Backend API / Dashboard / ML pipeline / Database schema)
- Steps to reproduce, including any relevant code snippets, payloads, or screenshots
- Your assessment of the potential impact and severity
- Your preferred credit/attribution (optional — anonymous reporting is fine)

### Response timeline

| Stage | Target |
|-------|--------|
| Acknowledge receipt | Within 48 hours |
| Confirm validity and scope | Within 5 business days |
| Patch ready for critical/high severity | Within 14 days |
| Patch ready for medium/low severity | Within 30 days |
| Public disclosure (coordinated) | After patch is released |

We will keep you informed of progress throughout and coordinate disclosure timing with you.

---

## Known Security Caveats (v0.1.0)

These are known limitations of the current prototype that you should be aware of before deploying in any real environment:

### Authentication
- The Android app uses a device-scoped `citizen_id` (UUIDv4 prefixed `czn_`) stored in Android DataStore. This is **not real authentication** — it is a prototype ownership token. Reports can be submitted by anyone who discovers the API.
- The web dashboard has no authentication in the current version. Deploy behind a VPN or private network for any real use.
- The backend has no JWT / session auth implementation yet. All `/api/v1/` endpoints are currently open.

### Google Maps API Key
- The Android app and dashboard require a Google Maps API key. Always restrict your key by:
  - **Android**: Package name (`com.civicsense`) and SHA-1 certificate fingerprint
  - **Dashboard**: HTTP referrer restriction (your domain)
  - Never commit a real key to source control; use `.env` / `local.properties` (both are gitignored)

### Evidence Storage
- Uploaded images are stored on the local filesystem under `uploads/`. In production, move storage to a private cloud bucket with access controls. Do not serve `uploads/` directly via a public URL without access control.

### Database
- Default credentials in `docker-compose.yml` are for **local development only**. Change all credentials before any deployment.

### Data Privacy
- The system stores citizen names, phone numbers, postal codes, and GPS coordinates. Ensure your deployment complies with applicable data protection regulations (e.g., DPDP Act in India, GDPR in Europe) before collecting real citizen data.

---

## What NOT to Report

The following are **out of scope** for security reports:

- Rate-limiting or DoS on a local development instance
- Theoretical vulnerabilities without a working proof of concept
- Social engineering attacks
- Issues in third-party libraries that have already been publicly disclosed (please check if a fix is available and open a regular dependency update PR)
- Missing HTTP security headers on the local development server

---

Thank you for helping keep CivicSense and its future users safe.
