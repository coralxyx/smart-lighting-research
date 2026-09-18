from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "kano_v2" / "kano-inspired-v2.xlsx"


def main() -> None:
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "run_kano_v2.py")],
        cwd=PROJECT_ROOT,
        check=True,
    )
    subprocess.run(
        [
            "node",
            str(PROJECT_ROOT / "scripts" / "finalize_kano_v2_workbook.mjs"),
            str(OUTPUT_PATH),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )
    print(f"Final workbook: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
