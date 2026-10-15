"""Offline validation of the reconciled C2 seed and its evidence fingerprints."""

import argparse
from pathlib import Path

from opportunity_api.ingestion.seed import AUDIT, SEED, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seed", nargs="?", type=Path, default=SEED)
    parser.add_argument("--audit", type=Path, default=AUDIT)
    args = parser.parse_args()
    payloads, rejected = prepare(args.seed, args.audit)
    if rejected or len(payloads) != 50:
        print({"accepted": len(payloads), "rejected": rejected})
        return 1
    print(
        "PASS: 50 audited records; run db:seed:check for source/publication gates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
