import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "interim" / "valid-original-text-results.jsonl"
OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "interim" / "valid-original-text-results-structured.xlsx"
)


def normalize_user_perceptions(value):
    if isinstance(value, list):
        return "\n".join(str(item) for item in value if item is not None)
    if value is None:
        return ""
    return str(value)


def main():
    rows = []

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            data = json.loads(line)
            original_full_text = data.get("original_full_text", "")
            merged_triples = data.get("merged_triples") or []

            if not merged_triples:
                rows.append(
                    {
                        "original_full_text": original_full_text,
                        "usage_scenario": "",
                        "aesthetic_indicator": "",
                        "user_perceptions": "",
                    }
                )
                continue

            for triple in merged_triples:
                if not isinstance(triple, dict):
                    rows.append(
                        {
                            "original_full_text": original_full_text,
                            "usage_scenario": "",
                            "aesthetic_indicator": "",
                            "user_perceptions": str(triple),
                        }
                    )
                    continue

                rows.append(
                    {
                        "original_full_text": original_full_text,
                        "usage_scenario": triple.get("usage_scenario", ""),
                        "aesthetic_indicator": triple.get("aesthetic_indicator", ""),
                        "user_perceptions": normalize_user_perceptions(
                            triple.get("user_perceptions", "")
                        ),
                    }
                )

    df = pd.DataFrame(
        rows,
        columns=[
            "original_full_text",
            "usage_scenario",
            "aesthetic_indicator",
            "user_perceptions",
        ],
    )
    df.to_excel(OUTPUT_PATH, index=False)

    print(f"Input: {INPUT_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Rows written: {len(df)}")


if __name__ == "__main__":
    main()
