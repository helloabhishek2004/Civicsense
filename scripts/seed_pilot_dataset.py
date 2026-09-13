"""Script to export or seed the CivicSense synthetic pilot dataset.

Usage:
  python scripts/seed_pilot_dataset.py --export-only
  python scripts/seed_pilot_dataset.py --seed-db
  python scripts/seed_pilot_dataset.py --seed-db --reset
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
_SCRIPTS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPTS_DIR.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.evaluation.pilot_seed_dataset import (  # noqa: E402
    generate_pilot_dataset_dict,
    seed_database,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or export CivicSense synthetic pilot dataset.")
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Export dataset to JSON file without touching the database.",
    )
    parser.add_argument(
        "--seed-db",
        action="store_true",
        help="Seed the active database with the pilot dataset.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Purge existing reports/issues/matches before seeding.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(_PROJECT_ROOT / "datasets" / "pilot_seed_dataset.json"),
        help="Output path for exported JSON dataset.",
    )

    args = parser.parse_args()

    # Default action if neither is specified: export to JSON
    dataset_dict = generate_pilot_dataset_dict()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dataset_dict, f, indent=2)
    print(f"Exported {len(dataset_dict['reports'])} reports and {len(dataset_dict['issues'])} issues to: {out_path}")

    if args.seed_db:
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            summary = seed_database(db, reset=args.reset)
            print("Database successfully seeded:")
            for k, v in summary.items():
                print(f"  {k}: {v}")
        except Exception as exc:
            print(f"Failed to seed database: {exc}", file=sys.stderr)
            sys.exit(1)
        finally:
            db.close()


if __name__ == "__main__":
    main()
