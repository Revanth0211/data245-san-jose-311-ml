"""Reproducible Member 1 pipeline for San Jose 311 illegal-dumping data.

Usage:
    python src/data_preparation.py --years 2017 2018 2019 2020 2021 2022 2023 2024 2025

The script downloads the annual files from the City of San Jose CKAN portal,
combines them, standardizes the schema, filters illegal-dumping requests,
removes exact/request-ID duplicates, and writes audit tables and a data
dictionary. Raw and generated data remain under data/, which is ignored by Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
SOURCE_API = "https://data.sanjoseca.gov/api/3/action/package_show?id=311-service-request-data"


def source_manifest() -> dict[int, dict[str, str]]:
    """Return year-to-download-URL mapping from the official CKAN API."""
    request = Request(SOURCE_API, headers={"User-Agent": "DATA245-member1-cleaner/1.0"})
    with urlopen(request, timeout=60) as response:
        payload = json.load(response)
    result = {}
    for resource in payload["result"]["resources"]:
        match = re.match(r"(\d{4}) Service Requests$", resource.get("name", ""))
        if match and resource.get("format", "").upper() == "CSV":
            result[int(match.group(1))] = {
                "name": resource["name"],
                "url": resource["url"],
                "resource_id": resource.get("id", ""),
            }
    return result

def download(url: str, destination: Path) -> tuple[int, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "curl",
        "-L",
        "--fail",
        "--retry", "3",
        "-A", "Mozilla/5.0",
        "-o", str(destination),
        url,
    ]

    subprocess.run(command, check=True)

    digest = hashlib.sha256()
    size = destination.stat().st_size

    with destination.open("rb") as input_file:
        while chunk := input_file.read(1024 * 1024):
            digest.update(chunk)

    return size, digest.hexdigest()

def clean_names(columns: list[str]) -> dict[str, str]:
    return {column: re.sub(r"[^a-z0-9]+", "_", column.lower()).strip("_") for column in columns}


def choose_column(frame: pd.DataFrame, candidates: list[str]) -> pd.Series:
    for candidate in candidates:
        if candidate in frame:
            return frame[candidate]
    return pd.Series(pd.NA, index=frame.index, dtype="object")


def standardize(frame: pd.DataFrame, year: int) -> pd.DataFrame:
    frame = frame.rename(columns=clean_names(list(frame.columns)))
    output = pd.DataFrame(index=frame.index)
    output["request_id"] = choose_column(frame, ["incident_id", "service_request_id", "request_id"]).astype("string").str.strip()
    output["status"] = choose_column(frame, ["status"]).astype("string").str.strip()
    output["source"] = choose_column(frame, ["source"]).astype("string").str.strip()
    output["category"] = choose_column(frame, ["category"]).astype("string").str.strip()
    output["service_type"] = choose_column(frame, ["service_type", "service_name", "type"]).astype("string").str.strip()
    output["latitude"] = pd.to_numeric(choose_column(frame, ["latitude", "lat"]), errors="coerce")
    output["longitude"] = pd.to_numeric(choose_column(frame, ["longitude", "lon", "lng"]), errors="coerce")
    output["date_created"] = pd.to_datetime(choose_column(frame, ["date_created", "created_date"]), errors="coerce")
    output["date_last_updated"] = pd.to_datetime(choose_column(frame, ["date_last_updated", "updated_date"]), errors="coerce")
    output["department"] = choose_column(frame, ["department"]).astype("string").str.strip()
    output["source_year"] = year
    return output


def illegal_dumping_mask(frame: pd.DataFrame) -> pd.Series:
    # Keep the rule auditable: match the service-type field first, then the
    # category field when older exports place the label there.
    pattern = r"illegal\s*dumping|illegal\s*dump"
    return frame["service_type"].fillna("").str.contains(pattern, case=False, regex=True) | frame["category"].fillna("").str.contains(pattern, case=False, regex=True)


def run(years: list[int]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    manifest = source_manifest()
    missing_years = sorted(set(years) - set(manifest))
    if missing_years:
        raise ValueError(f"No official CSV resource was found for: {missing_years}")

    audit_rows = []
    annual = []
    for year in years:
        meta = manifest[year]
        path = RAW_DIR / f"311-service-requests-{year}.csv"
        if not path.exists():
            size, checksum = download(meta["url"], path)
        else:
            size = path.stat().st_size
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        raw = pd.read_csv(path, low_memory=False)
        standardized = standardize(raw, year)
        match = illegal_dumping_mask(standardized)
        audit_rows.append({
            "year": year,
            "source_url": meta["url"],
            "resource_id": meta["resource_id"],
            "accessed_utc": datetime.now(timezone.utc).isoformat(),
            "local_filename": path.name,
            "sha256": checksum,
            "file_size_bytes": size,
            "source_rows": len(raw),
            "illegal_dumping_rows": int(match.sum()),
            "missing_request_id": int((standardized["request_id"].isna() | standardized["request_id"].eq("")).sum()),
            "missing_creation_date": int(standardized["date_created"].isna().sum()),
            "missing_coordinates": int(standardized[["latitude", "longitude"]].isna().any(axis=1).sum()),
        })
        annual.append(standardized.loc[match].copy())

    filtered = pd.concat(annual, ignore_index=True)
    before = len(filtered)
    missing_id = filtered["request_id"].isna() | filtered["request_id"].eq("")
    missing_date = filtered["date_created"].isna()
    invalid_coordinates = (
        (filtered["latitude"].notna() & ~filtered["latitude"].between(37.0, 37.6))
        | (filtered["longitude"].notna() & ~filtered["longitude"].between(-122.2, -121.5))
    )
    filtered["exclusion_reason"] = ""
    filtered.loc[missing_id, "exclusion_reason"] = "missing_request_id"
    filtered.loc[~missing_id & missing_date, "exclusion_reason"] = "invalid_creation_date"
    filtered.loc[~missing_id & ~missing_date & invalid_coordinates, "exclusion_reason"] = "invalid_coordinates"
    eligible = filtered.loc[filtered["exclusion_reason"].eq("")].copy()
    exact_duplicates = int(eligible.duplicated().sum())
    eligible = eligible.drop_duplicates()
    request_duplicates = int(eligible.duplicated(subset=["request_id"], keep="first").sum())
    eligible = eligible.drop_duplicates(subset=["request_id"], keep="first")
    eligible = eligible.sort_values(["date_created", "request_id"]).reset_index(drop=True)
    eligible["service_type"] = "Illegal Dumping"
    eligible = eligible.drop(columns=["exclusion_reason"])

    pd.DataFrame(audit_rows).to_csv(PROCESSED_DIR / "source_manifest.csv", index=False)
    filtered.to_csv(PROCESSED_DIR / "illegal_dumping_audit_rows.csv", index=False)
    eligible.to_csv(PROCESSED_DIR / "illegal_dumping_cleaned.csv", index=False)
    pd.DataFrame([
        {"stage": "illegal_dumping_rows_before_quality_rules", "records": before},
        {"stage": "excluded_missing_id_or_date_or_invalid_coordinates", "records": int((filtered["exclusion_reason"] != "").sum())},
        {"stage": "exact_duplicates_removed", "records": exact_duplicates},
        {"stage": "request_id_duplicates_removed", "records": request_duplicates},
        {"stage": "final_retained_records", "records": len(eligible)},
    ]).to_csv(PROCESSED_DIR / "cleaning_counts.csv", index=False)

    dictionary = pd.DataFrame([
        ["request_id", "string", "Unique 311 incident identifier; blank IDs excluded."],
        ["status", "string", "Source status, retained for downstream analysis."],
        ["source", "string", "How the request was submitted."],
        ["category", "string", "Original category label."],
        ["service_type", "string", "Canonical label set to Illegal Dumping after filtering."],
        ["latitude/longitude", "numeric", "Coordinates; outside San José plausibility bounds excluded when present."],
        ["date_created", "datetime", "Parsed source creation timestamp; invalid or missing values excluded."],
        ["date_last_updated", "datetime", "Parsed source update timestamp; not treated as completion time."],
        ["department", "string", "Source department."],
        ["source_year", "integer", "Annual file year used for coverage auditing."],
    ], columns=["field", "type", "definition_and_rule"])
    dictionary.to_csv(PROCESSED_DIR / "data_dictionary.csv", index=False)
    print(json.dumps({"years": years, "final_records": len(eligible), "output": str(PROCESSED_DIR)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, default=list(range(2017, 2026)))
    args = parser.parse_args()
    run(args.years)
