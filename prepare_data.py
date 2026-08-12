#!/usr/bin/env python3
"""Prepare the COVID-19 liver cancer dataset for the dashboard."""
from __future__ import annotations

import argparse
import calendar
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RAW_ENCODING_CANDIDATES: tuple[str, ...] = ("utf-8", "cp1252", "latin1")


def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in RAW_ENCODING_CANDIDATES:
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise RuntimeError(f"Could not read {path}: {last_error}") from last_error


def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    text_cols = out.select_dtypes(include=["object"]).columns
    for col in text_cols:
        out[col] = (out[col].astype("string").str.strip().str.replace("\u2014", "-", regex=False).str.replace("\u2013", "-", regex=False))
        out[col] = out[col].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NA": pd.NA})
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
    if pd.isna(value): return "Not recorded"
    value = str(value).strip()
    if value in {"OLTx", "Resection", "Ablation"}: return "Curative intent"
    if value in {"TACE", "SIRT"}: return "Locoregional therapy"
    if value == "Medical": return "Systemic medical therapy"
    if value == "Supportive care": return "Supportive care"
    return "Other / review"


def stage_group(row: pd.Series) -> str:
    cancer_type = row.get("Cancer_Type")
    if cancer_type == "HCC":
        bclc = row.get("HCC_BCLC_Stage")
        return "HCC stage not recorded" if pd.isna(bclc) else f"HCC BCLC {bclc}"
    if cancer_type == "ICC":
        icc = row.get("ICC_TNM_Stage")
        return "ICC stage not recorded" if pd.isna(icc) else f"ICC TNM {icc}"
    return "Review"


def age_group(age: object) -> str:
    if pd.isna(age): return "Unknown"
    age = float(age)
    if age < 50: return "<50"
    if age < 60: return "50-59"
    if age < 70: return "60-69"
    if age < 80: return "70-79"
    return "80+"


def size_group(size: object) -> str:
    if pd.isna(size): return "Unknown"
    size = float(size)
    if size < 20: return "<20 mm"
    if size < 50: return "20-49 mm"
    if size < 100: return "50-99 mm"
    return "100+ mm"


def flag_unusual_treatment_interval(value: object) -> str:
    if pd.isna(value): return "Missing"
    value = float(value)
    if value < 0: return "Negative interval - review"
    if value > 12: return ">12 months - review"
    return "Plausible"


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    required = {"Year", "Month", "Treatment_grps", "Age", "Cirrhosis", "Alive_Dead"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Input dataset is missing required columns: {', '.join(missing)}")
    out = clean_text_columns(df)
    year_map = {"Prepandemic": "Pre-pandemic", "Pre-pandemic": "Pre-pandemic", "Pandemic": "Pandemic", "Postpandemic": "Pandemic", "Post-pandemic": "Pandemic"}
    out["Cohort"] = out["Year"].map(year_map).fillna(out["Year"])
    out["Cohort_Order"] = out["Cohort"].map({"Pre-pandemic": 1, "Pandemic": 2}).fillna(99).astype(int)
    out["Month"] = pd.to_numeric(out["Month"], errors="coerce")
    out["Month_Name"] = out["Month"].apply(lambda x: calendar.month_abbr[int(x)] if pd.notna(x) and 1 <= int(x) <= 12 else "Unknown")
    out["Month_Order"] = out["Month"]
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
    numeric_cols = ["Age", "Size", "Survival_fromMDM", "Time_diagnosis_1st_Tx", "Time_MDM_1st_treatment", "Time_decisiontotreat_1st_treatment", "Months_from_last_surveillance", "PS"]
    for col in numeric_cols:
        if col in out.columns: out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def build_data_dictionary(columns: Iterable[str]) -> pd.DataFrame:
    descriptions = {
        "Cancer": "Raw cancer flag in the source file; Cancer_Type is the derived analysis field.", "Year": "Original cohort label.", "Month": "Month number in the 12-month cohort window.", "Bleed": "Spontaneous tumour haemorrhage flag.", "Mode_Presentation": "Surveillance, incidental, or symptomatic presentation.", "Age": "Patient age in years.", "Gender": "Patient gender.", "Etiology": "Underlying disease etiology where recorded.", "Cirrhosis": "Underlying cirrhosis flag.", "Size": "Tumour diameter in millimetres.", "HCC_TNM_Stage": "HCC TNM stage.", "HCC_BCLC_Stage": "HCC BCLC stage.", "ICC_TNM_Stage": "ICC TNM stage.", "Treatment_grps": "First-line treatment group.", "Survival_fromMDM": "Survival from multidisciplinary meeting in months.", "Alive_Dead": "Alive or dead at follow-up.", "Surveillance_programme": "Formal surveillance programme status.", "Surveillance_effectiveness": "Surveillance adherence during the previous year.", "Mode_of_surveillance_detection": "Mode of surveillance detection.", "Time_diagnosis_1st_Tx": "Time from diagnosis to first treatment.", "PS": "Performance status.", "Time_MDM_1st_treatment": "Time from MDM to first treatment.", "Time_decisiontotreat_1st_treatment": "Time from decision to treat to first treatment.", "Prev_known_cirrhosis": "Whether cirrhosis was previously known.", "Months_from_last_surveillance": "Months from last surveillance.", "Cohort": "Clean cohort label.", "Cancer_Type": "Derived cancer type from HCC/ICC staging fields.", "Cancer_Type_Simple": "HCC, ICC, or Review.", "Treatment_Category": "Grouped treatment category.", "Stage_Group": "Readable stage group.", "Age_Group": "Age band.", "Tumour_Size_Group": "Tumour size band.", "Alive_Flag": "1 when Alive_Dead is Alive.", "Death_Flag": "1 when Alive_Dead is Dead.",
    }
    return pd.DataFrame([{"column": col, "description": descriptions.get(col, "Source or derived dashboard field.")} for col in columns])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare COVID liver cancer dataset")
    parser.add_argument("--input", type=Path, default=BASE_DIR / "covid-liver.csv")
    parser.add_argument("--output", type=Path, default=BASE_DIR / "covid_liver_clean.csv")
    parser.add_argument("--dictionary", type=Path, default=BASE_DIR / "data_dictionary.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw = read_csv_with_fallback(args.input)
    clean = prepare_dataframe(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(args.output, index=False)
    build_data_dictionary(clean.columns).to_csv(args.dictionary, index=False)
    print(f"Prepared {len(clean):,} rows and {len(clean.columns):,} columns")
    print(f"Clean data: {args.output}")
    print(f"Data dictionary: {args.dictionary}")


if __name__ == "__main__":
    main()
