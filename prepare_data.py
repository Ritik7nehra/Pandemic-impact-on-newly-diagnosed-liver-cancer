#!/usr/bin/env python3
"""Prepare the COVID-19 liver cancer dataset for dashboarding.

This script keeps the original columns and adds derived fields used by the
Streamlit and static dashboards. It is intentionally conservative: it does not
impute clinical values or remove records.
"""
from __future__ import annotations

import argparse
import calendar
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

RAW_ENCODING_CANDIDATES: tuple[str, ...] = ("utf-8", "cp1252", "latin1")


def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in RAW_ENCODING_CANDIDATES:
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise UnicodeDecodeError("utf-8", b"", 0, 1, f"Could not read {path}: {last_error}")


def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    text_cols = out.select_dtypes(include=["object"]).columns
    for col in text_cols:
        out[col] = (
            out[col]
            .astype("string")
            .str.strip()
            .str.replace("\u2014", "-", regex=False)
            .str.replace("\u2013", "-", regex=False)
        )
        out[col] = out[col].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    return out


def derive_cancer_type(row: pd.Series) -> str:
    has_hcc = pd.notna(row.get("HCC_TNM_Stage")) or pd.notna(row.get("HCC_BCLC_Stage"))
    has_icc = pd.notna(row.get("ICC_TNM_Stage"))
    if has_hcc and has_icc:
        return "Review: HCC and ICC staging present"
    if has_hcc:
        return "HCC"
    if has_icc:
        return "ICC"
    return "Review: cancer type not staged"


def treatment_category(value: object) -> str:
    if pd.isna(value):
        return "Not recorded"
    value = str(value)
    if value in {"OLTx", "Resection", "Ablation"}:
        return "Curative intent"
    if value in {"TACE", "SIRT"}:
        return "Locoregional therapy"
    if value == "Medical":
        return "Systemic medical therapy"
    if value == "Supportive care":
        return "Supportive care"
    return "Other / review"


def stage_group(row: pd.Series) -> str:
    cancer_type = row.get("Cancer_Type")
    if cancer_type == "HCC":
        bclc = row.get("HCC_BCLC_Stage")
        if pd.isna(bclc):
            return "HCC stage not recorded"
        return f"HCC BCLC {bclc}"
    if cancer_type == "ICC":
        icc = row.get("ICC_TNM_Stage")
        if pd.isna(icc):
            return "ICC stage not recorded"
        return f"ICC TNM {icc}"
    return "Review"


def age_group(age: object) -> str:
    if pd.isna(age):
        return "Unknown"
    age_float = float(age)
    if age_float < 50:
        return "<50"
    if age_float < 60:
        return "50-59"
    if age_float < 70:
        return "60-69"
    if age_float < 80:
        return "70-79"
    return "80+"


def size_group(size: object) -> str:
    if pd.isna(size):
        return "Unknown"
    size_float = float(size)
    if size_float < 20:
        return "<20 mm"
    if size_float < 50:
        return "20-49 mm"
    if size_float < 100:
        return "50-99 mm"
    return "100+ mm"


def flag_unusual_treatment_interval(value: object) -> str:
    if pd.isna(value):
        return "Missing"
    value_float = float(value)
    if value_float < 0:
        return "Negative interval - review"
    if value_float > 12:
        return ">12 months - review"
    return "Plausible"


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = clean_text_columns(df)

    # Standardize cohort labels while preserving the original Year field.
    year_map = {
        "Prepandemic": "Pre-pandemic",
        "Pre-pandemic": "Pre-pandemic",
        "Pandemic": "Pandemic",
        "Postpandemic": "Pandemic",
        "Post-pandemic": "Pandemic",
    }
    out["Cohort"] = out["Year"].map(year_map).fillna(out["Year"])
    out["Cohort_Order"] = out["Cohort"].map({"Pre-pandemic": 1, "Pandemic": 2}).fillna(99).astype(int)

    # Month labels for readable plots.
    out["Month_Name"] = out["Month"].apply(lambda x: calendar.month_abbr[int(x)] if pd.notna(x) and 1 <= int(x) <= 12 else "Unknown")
    out["Month_Order"] = pd.to_numeric(out["Month"], errors="coerce")

    # Derived clinical fields.
    out["Cancer_Type"] = out.apply(derive_cancer_type, axis=1)
    out["Cancer_Type_Simple"] = out["Cancer_Type"].where(out["Cancer_Type"].isin(["HCC", "ICC"]), "Review")
    out["Treatment_Category"] = out["Treatment_grps"].apply(treatment_category)
    out["Stage_Group"] = out.apply(stage_group, axis=1)
    out["Age_Group"] = out["Age"].apply(age_group)
    out["Tumour_Size_Group"] = out["Size"].apply(size_group)
    out["Alive_Flag"] = (out["Alive_Dead"] == "Alive").astype(int)
    out["Death_Flag"] = (out["Alive_Dead"] == "Dead").astype(int)

    out["Presentation_Context"] = out["Mode_Presentation"].fillna("Unknown")
    out["Has_Cirrhosis"] = out["Cirrhosis"].map({"Y": "Cirrhosis", "N": "No cirrhosis"}).fillna("Not recorded")
    out["Has_Bleed"] = out["Bleed"].map({"Y": "Bleed", "N": "No bleed"}).fillna("Not recorded")
    out["Known_Cirrhosis_Before"] = out["Prev_known_cirrhosis"].map({"Y": "Known", "N": "Not known"}).fillna("Not recorded")
    out["Diagnosis_to_Treatment_Flag"] = out["Time_diagnosis_1st_Tx"].apply(flag_unusual_treatment_interval)

    numeric_cols = [
        "Age",
        "Size",
        "Survival_fromMDM",
        "Time_diagnosis_1st_Tx",
        "Time_MDM_1st_treatment",
        "Time_decisiontotreat_1st_treatment",
        "Months_from_last_surveillance",
        "PS",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def build_data_dictionary(columns: Iterable[str]) -> pd.DataFrame:
    descriptions = {
        "Cancer": "Raw cancer flag in the source file. In this dataset it aligns mainly with HCC versus ICC records; use Cancer_Type for dashboard analysis.",
        "Year": "Original cohort label in the source file.",
        "Month": "Month number in the 12-month cohort window.",
        "Bleed": "Spontaneous tumour haemorrhage flag.",
        "Mode_Presentation": "Surveillance, incidental, or symptomatic presentation.",
        "Age": "Patient age in years.",
        "Gender": "Patient gender in the source file.",
        "Etiology": "Underlying disease etiology where recorded.",
        "Cirrhosis": "Underlying cirrhosis flag.",
        "Size": "Tumour diameter in millimetres.",
        "HCC_TNM_Stage": "Hepatocellular carcinoma TNM stage.",
        "HCC_BCLC_Stage": "Hepatocellular carcinoma BCLC stage.",
        "ICC_TNM_Stage": "Intrahepatic cholangiocarcinoma TNM stage.",
        "Treatment_grps": "First-line treatment group.",
        "Survival_fromMDM": "Survival from multidisciplinary meeting in months.",
        "Alive_Dead": "Alive or dead at follow-up.",
        "Type_of_incidental_finding": "Type of incidental finding.",
        "Surveillance_programme": "Whether patient was in a formal surveillance programme.",
        "Surveillance_effectiveness": "Surveillance adherence during the previous year.",
        "Mode_of_surveillance_detection": "Mode of incident surveillance test.",
        "Time_diagnosis_1st_Tx": "Time from diagnosis to first treatment.",
        "Date_incident_surveillance_scan": "Incident surveillance scan flag in source file.",
        "PS": "Performance status.",
        "Time_MDM_1st_treatment": "Time from MDM to first treatment.",
        "Time_decisiontotreat_1st_treatment": "Time from decision to treat to first treatment.",
        "Prev_known_cirrhosis": "Whether cirrhosis was previously known.",
        "Months_from_last_surveillance": "Months from last surveillance.",
        "Cohort": "Clean cohort label: Pre-pandemic or Pandemic.",
        "Cancer_Type": "Derived cancer type using available HCC and ICC staging fields.",
        "Cancer_Type_Simple": "Simplified cancer type: HCC, ICC, or Review.",
        "Treatment_Category": "Treatment grouped into curative intent, locoregional, systemic, supportive, not recorded, or review.",
        "Stage_Group": "Readable stage group derived from HCC BCLC or ICC TNM stage.",
        "Age_Group": "Age band.",
        "Tumour_Size_Group": "Tumour size band.",
        "Alive_Flag": "1 if Alive_Dead is Alive, else 0.",
        "Death_Flag": "1 if Alive_Dead is Dead, else 0.",
    }
    rows = [{"column": col, "description": descriptions.get(col, "Derived or source column used by dashboard.")} for col in columns]
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare COVID liver cancer dataset")
    parser.add_argument("--input", type=Path, default=Path("data/covid-liver.csv"), help="Raw CSV path")
    parser.add_argument("--output", type=Path, default=Path("data/covid_liver_clean.csv"), help="Clean CSV path")
    parser.add_argument("--dictionary", type=Path, default=Path("data/data_dictionary.csv"), help="Data dictionary path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw = read_csv_with_fallback(args.input)
    clean = prepare_dataframe(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(args.output, index=False)
    data_dictionary = build_data_dictionary(clean.columns)
    data_dictionary.to_csv(args.dictionary, index=False)
    print(f"Prepared {len(clean):,} rows and {len(clean.columns):,} columns")
    print(f"Clean data: {args.output}")
    print(f"Data dictionary: {args.dictionary}")


if __name__ == "__main__":
    main()
