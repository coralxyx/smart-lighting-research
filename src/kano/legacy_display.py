from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook


def load_legacy_perception_display(
    reference_path: str | Path,
) -> dict[tuple[str, str], dict[str, str]]:
    """Load only legacy tie-order presentation for perception summaries."""
    workbook = load_workbook(Path(reference_path), read_only=False, data_only=True)
    worksheet = workbook["Kano汇总"]
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row in range(4, worksheet.max_row + 1):
        scene = worksheet.cell(row, 1).value
        aesthetic = worksheet.cell(row, 3).value
        if not scene or not aesthetic:
            continue
        result[(str(scene), str(aesthetic))] = {
            "main_perception": str(worksheet.cell(row, 12).value or ""),
            "perception_distribution": str(worksheet.cell(row, 13).value or ""),
        }
    workbook.close()
    return result


def apply_legacy_tie_order(
    payload: dict[str, object], display_rows: dict[tuple[str, str], dict[str, str]]
) -> None:
    """Preserve old display order when equal counts make ordering non-unique."""
    for row in payload["summary_rows"]:
        display = display_rows.get((str(row["scene"]), str(row["aesthetic"])))
        if display:
            row.update(display)
