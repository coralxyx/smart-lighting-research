from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

import hdbscan  # type: ignore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = (
    PROJECT_ROOT / "data" / "interim" / "valid-original-text-results-structured.xlsx"
)
TARGET_COLUMNS = [
    "usage_scenario",
    "aesthetic_indicator",
    "user_perceptions",
]
OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "valid-original-text-results-clustered.xlsx"
)
FALLBACK_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "valid-original-text-results-clustered-alt.xlsx"
)
HDBSCAN_PARAMS_BY_COLUMN = {
    "usage_scenario": {
        "min_cluster_size": 20,
        "min_samples": 10,
        "cluster_selection_epsilon": 0.16,
    },
    "aesthetic_indicator": {
        "min_cluster_size": 8,
        "min_samples": 2,
        "cluster_selection_epsilon": 0.03,
    },
    "user_perceptions": {
        "min_cluster_size": 40,
        "min_samples": 12,
        "cluster_selection_epsilon": 0.24,
    },
}


def clean_text(value):
    if pd.isna(value):
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    return " ".join(text.split())


def build_embeddings(texts):
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 4),
        min_df=1,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(texts)

    if matrix.shape[0] <= 2 or matrix.shape[1] <= 2:
        dense = matrix.toarray()
        return normalize(dense), vectorizer

    n_components = min(50, matrix.shape[0] - 1, matrix.shape[1] - 1)
    if n_components < 2:
        dense = matrix.toarray()
        return normalize(dense), vectorizer

    svd = TruncatedSVD(n_components=n_components, random_state=42)
    reduced = svd.fit_transform(matrix)
    return normalize(reduced), vectorizer


def run_hdbscan(embeddings, params):
    model = hdbscan.HDBSCAN(
        min_cluster_size=params["min_cluster_size"],
        min_samples=params["min_samples"],
        metric="euclidean",
        cluster_selection_method="eom",
        cluster_selection_epsilon=params["cluster_selection_epsilon"],
        prediction_data=False,
    )
    labels = model.fit_predict(embeddings)
    non_noise = labels[labels != -1]
    if len(set(non_noise)) < 2:
        return np.zeros(len(embeddings), dtype=int)
    return labels


def reorder_labels_by_size(labels):
    series = pd.Series(labels)
    ordered = (
        series.value_counts()
        .sort_values(ascending=False)
        .index.tolist()
    )
    mapping = {old_label: new_label for new_label, old_label in enumerate(ordered)}
    return np.array([mapping[label] for label in labels], dtype=int)


def cluster_unique_texts(texts, column_name):
    cleaned = [clean_text(text) for text in texts]
    non_empty_texts = [text for text in cleaned if text]

    if not non_empty_texts:
        return {
            "method": "empty_only",
            "text_to_cluster": {text: -1 for text in cleaned},
            "summary": pd.DataFrame(
                columns=["cluster_id", "size", "representative_text", "examples"]
            ),
        }

    unique_texts = list(dict.fromkeys(non_empty_texts))
    embeddings, _ = build_embeddings(unique_texts)
    labels = run_hdbscan(embeddings, HDBSCAN_PARAMS_BY_COLUMN[column_name])
    method = "hdbscan"

    labels = reorder_labels_by_size(labels)
    text_to_cluster = {text: int(label) for text, label in zip(unique_texts, labels)}
    text_to_cluster[""] = -1

    summary_rows = []
    summary_df = pd.DataFrame({"text": unique_texts, "cluster_id": labels})
    for cluster_id, group in summary_df.groupby("cluster_id", sort=True):
        examples = group["text"].tolist()[:8]
        representative = sorted(examples, key=lambda x: (len(x), x))[0]
        summary_rows.append(
            {
                "cluster_id": int(cluster_id),
                "size": int(len(group)),
                "representative_text": representative,
                "examples": "\n".join(examples),
            }
        )

    summary_rows.sort(key=lambda row: (-row["size"], row["cluster_id"]))
    return {
        "method": method,
        "text_to_cluster": text_to_cluster,
        "summary": pd.DataFrame(summary_rows),
    }


def main():
    df = pd.read_excel(INPUT_PATH)
    results_by_column = {}
    output_df = df.copy()

    for column in TARGET_COLUMNS:
        values = [clean_text(value) for value in df[column]]
        cluster_result = cluster_unique_texts(values, column)
        cluster_column = f"{column}_cluster"
        output_df[column] = values
        output_df[cluster_column] = [
            cluster_result["text_to_cluster"][value] for value in values
        ]

        unique_non_empty = len({value for value in values if value})
        assigned_clusters = (
            cluster_result["summary"]["cluster_id"].nunique()
            if not cluster_result["summary"].empty
            else 0
        )
        meta_df = pd.DataFrame(
            [
                {
                    "column_name": column,
                    "algorithm": cluster_result["method"],
                    "input_rows": len(values),
                    "unique_non_empty_texts": unique_non_empty,
                    "cluster_count": int(assigned_clusters),
                    "empty_label": -1,
                }
            ]
        )
        results_by_column[column] = {
            "summary": cluster_result["summary"],
            "meta": meta_df,
        }

    print(f"Input: {INPUT_PATH}")
    summary_frames = []
    meta_frames = []
    for column in TARGET_COLUMNS:
        summary_df = results_by_column[column]["summary"].copy()
        if not summary_df.empty:
            summary_df.insert(0, "column_name", column)
        else:
            summary_df = pd.DataFrame(
                columns=[
                    "column_name",
                    "cluster_id",
                    "size",
                    "representative_text",
                    "examples",
                ]
            )
        summary_frames.append(summary_df)
        meta_frames.append(results_by_column[column]["meta"])

    combined_summary_df = pd.concat(summary_frames, ignore_index=True)
    combined_meta_df = pd.concat(meta_frames, ignore_index=True)

    output_path_used = OUTPUT_PATH
    try:
        with pd.ExcelWriter(output_path_used, engine="openpyxl") as writer:
            output_df.to_excel(writer, sheet_name="clustered_rows", index=False)
            combined_summary_df.to_excel(
                writer, sheet_name="cluster_summary", index=False
            )
            combined_meta_df.to_excel(writer, sheet_name="meta", index=False)
    except PermissionError:
        output_path_used = FALLBACK_OUTPUT_PATH
        with pd.ExcelWriter(output_path_used, engine="openpyxl") as writer:
            output_df.to_excel(writer, sheet_name="clustered_rows", index=False)
            combined_summary_df.to_excel(
                writer, sheet_name="cluster_summary", index=False
            )
            combined_meta_df.to_excel(writer, sheet_name="meta", index=False)

    print(f"Output: {output_path_used}")
    print(f"Rows written: {len(output_df)}")
    for column in TARGET_COLUMNS:
        meta_row = results_by_column[column]["meta"].iloc[0].to_dict()
        print(
            f"{meta_row['column_name']}: method={meta_row['algorithm']}, "
            f"clusters={meta_row['cluster_count']}, "
            f"unique_non_empty={meta_row['unique_non_empty_texts']}"
        )


if __name__ == "__main__":
    main()
