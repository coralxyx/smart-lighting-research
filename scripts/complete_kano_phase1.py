from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_PATH = PROJECT_ROOT / "analysis" / "generated" / "kano-phase1-workbook-data.json"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "kano_phase1" / "kano-phase1-reproduced.xlsx"


def main() -> None:
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "finalize_kano_phase1.py")],
        cwd=PROJECT_ROOT,
        check=True,
    )

    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    completed_mapping = dict(payload["touchpoint_by_aesthetic"])
    for row in payload["summary_rows"]:
        if row.get("touchpoint"):
            completed_mapping.setdefault(str(row["aesthetic"]), str(row["touchpoint"]))
    for row in payload["pair_rows"]:
        if not row.get("touchpoint"):
            row["touchpoint"] = completed_mapping.get(str(row["aesthetic"]), "")
    payload["touchpoint_by_aesthetic"] = completed_mapping
    payload["method"]["mapping_completion_note"] = (
        "旧方法表未列出风格设计和色彩的触点类型；"
        "依六个场景表中的一致值回填为视觉触点。"
    )
    PAYLOAD_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    subprocess.run(
        [
            "node",
            str(PROJECT_ROOT / "scripts" / "build_kano_workbook.mjs"),
            str(PAYLOAD_PATH),
            str(OUTPUT_PATH),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )
    print(f"Completed workbook: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
