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

*(None at initial deployment — all `pip-audit` and `npm audit` findings resolved.)*

---

## Resolved

*(Move entries here once the upstream patch is released and applied.)*
