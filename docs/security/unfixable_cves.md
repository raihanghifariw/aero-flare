# Aero-Flare: Unfixable CVEs & Security Exemptions

This file documents any HIGH/CRITICAL CVEs found by `pip-audit` or `npm audit`
that cannot be resolved by updating a dependency (e.g. no patched version exists).

Each entry must include:
1. CVE/GHSA ID
2. Affected package + version
3. Description of the vulnerability
4. Why it cannot be fixed (no upstream patch, pinned transitive dep, etc.)
5. Mitigation in place
6. Review date + reviewer

---

## Format

```
### CVE-XXXX-XXXXX — package@version
- **Severity:** HIGH / CRITICAL
- **Description:** ...
- **Why unfixable:** ...
- **Mitigation:** ...
- **Review date:** YYYY-MM-DD
- **Reviewer:** @github-username
```

---

## Active Exemptions

### GHSA-postcss-next14 — next@14.2.35 / postcss internal bundle
- **Severity:** HIGH
- **Affected:** `postcss <=8.5.22` bundled internally by `next@14.x`
- **CVEs:** GHSA-qx2v-qp2m-jg93, GHSA-6g55-p6wh-862q, GHSA-fxqj-rqcc-2cmp, GHSA-r28c-9q8g-f849
- **Description:** PostCSS XSS, arbitrary file read, and path traversal via sourceMappingURL in CSS source maps. All affect build-time CSS processing only.
- **Why unfixable:** Transitive dependency bundled inside `next` package. Fix requires upgrading to Next.js 15 which is a breaking change (App Router API changes, React 19 requirement).
- **Mitigation:** (1) Vulnerabilities are build-time only — not exploitable at runtime in production. (2) No user-controlled CSS input is processed via PostCSS in this project. (3) CI audit-level set to `critical` until Next.js 15 migration is planned.
- **Review date:** 2026-08-27
- **Reviewer:** @raihanghifariw

---

## Resolved

*(Move entries here once the upstream patch is released and applied.)*
