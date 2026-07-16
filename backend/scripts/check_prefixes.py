#!/usr/bin/env python3
"""Manual sanity check for the curated prefix map.

Verifies that ``core.prefixes.PREFIXES`` covers every ``@prefix`` declared across
the project's TTL files (``schema/*.ttl`` + ``data/*.ttl``, incl. the large
Glottolog dump — only headers are read). Reports prefixes that are declared but
missing from ``PREFIXES``, namespace mismatches, and entries in ``PREFIXES`` not
found in any file. Exits non-zero on missing/mismatched so it can gate a review.

Run:
    cd backend && uv run python scripts/check_prefixes.py
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from core.prefixes import PREFIXES, scan_ttl_prefixes  # noqa: E402


def main() -> int:
    ttl_files = sorted(
        str(p) for p in [*REPO_ROOT.glob("schema/*.ttl"), *REPO_ROOT.glob("data/*.ttl")]
    )
    declared = scan_ttl_prefixes(ttl_files)

    missing = {p: ns for p, ns in declared.items() if p not in PREFIXES}
    mismatched = {
        p: (ns, PREFIXES[p])
        for p, ns in declared.items()
        if p in PREFIXES and PREFIXES[p] != ns
    }
    extra = sorted(set(PREFIXES) - set(declared))

    print(f"Scanned {len(ttl_files)} TTL files; {len(declared)} declared prefixes.")
    if missing:
        print("\nMISSING from core.prefixes.PREFIXES (declared in TTL, not listed):")
        for prefix, ns in sorted(missing.items()):
            print(f'    "{prefix}": "{ns}",')
    if mismatched:
        print("\nMISMATCHED namespace (TTL declaration != PREFIXES):")
        for prefix, (declared_ns, current_ns) in sorted(mismatched.items()):
            print(f"    {prefix}: TTL={declared_ns}  PREFIXES={current_ns}")
    if extra:
        print("\nIn PREFIXES but not declared in any scanned TTL (ok if intentional):")
        print("    " + ", ".join(extra))

    if not missing and not mismatched:
        print("\nOK — every declared prefix is present with a matching namespace.")
        return 0
    print("\nFAIL — update core/prefixes.py to match.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
