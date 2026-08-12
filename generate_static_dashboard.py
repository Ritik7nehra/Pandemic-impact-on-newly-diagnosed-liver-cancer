#!/usr/bin/env python3
"""Generate a self-contained static HTML dashboard from the clean CSV."""
from __future__ import annotations

import calendar
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
from plotly.offline import get_plotlyjs

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "covid_liver_clean.csv"
OUTPUT_PATH = BASE_DIR / "static_dashboard.html"
COHORT_ORDER = ["Pre-pandemic", "Pandemic"]
MONTH_ORDER = list(calendar.month_abbr[1:])
COLOR_SEQUENCE = ["#24f0b6", "#7c5cff", "#ffb86b", "#ff5c93", "#2dd4ff", "#f8f871", "#a3e635"]
TEMPLATE = "plotly_dark"


def style_fig(fig, title):
    fig.update_layout(template=TEMPLATE, title=dict(text=title, x=0.02, xanchor="left", font=dict(size=21)),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#eef2ff"),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      margin=dict(l=25, r=25, t=75, b=45), hoverlabel=dict(bgcolor="#0b1220", font_size=13))
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.12)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.12)")
    return fig


def percent_stacked(df, category, title):
    tmp = df[["Cohort", category]].copy()
    tmp[category] = tmp[category].fillna("Not recorded").astype(str)
    tmp = tmp.groupby(["Cohort", category], dropna=False).size().reset_index(name="Cases")
    tmp["Percent"] = tmp["Cases"] / tmp.groupby("Cohort")["Cases"].transform("sum") * 100
    fig = px.bar(tmp, x="Cohort", y="Percent", color=category, text=tmp["Percent"].map(lambda x: f"{x:.0f}%"),
                 color_discrete_sequence=COLOR_SEQUENCE, category_orders={"Cohort": COHORT_ORDER},
                 hover_data={"Cases": True, "Percent": ":.1f"})
    fig.update_layout(xaxis_title="", yaxis_title="Percent of cases", yaxis_range=[0, 100])
    fig.update_traces(textposition="inside", insidetextanchor="middle")
    return style_fig(fig, title)


def fig_html(fig):
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, config={"displayModeBar": False, "responsive": True})


def metric_card(label, value, note=""):
    return f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>'


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Clean data not found: {DATA_PATH}. Run prepare_data.py first.")
    df = pd.read_csv(DATA_PATH)
    total = len(df)
    hcc = int((df["Cancer_Type_Simple"] == "HCC").sum())
    icc = int((df["Cancer_Type_Simple"] == "ICC").sum())
    pre = df[df["Cohort"] == "Pre-pandemic"]
    pan = df[df["Cohort"] == "Pandemic"]
    pre_n, pan_n = len(pre), len(pan)
    case_delta = (pan_n - pre_n) / pre_n * 100 if pre_n else float("nan")
    median_survival = df["Survival_fromMDM"].median()
    median_age = df["Age"].median()
    deaths = int((df["Alive_Dead"] == "Dead").sum())

    by_cohort_type = df.groupby(["Cohort", "Cancer_Type_Simple"], dropna=False).size().reset_index(name="Cases")
    fig_case_mix = px.bar(by_cohort_type, x="Cohort", y="Cases", color="Cancer_Type_Simple", barmode="group", text_auto=True,
                          color_discrete_sequence=COLOR_SEQUENCE, category_orders={"Cohort": COHORT_ORDER, "Cancer_Type_Simple": ["HCC", "ICC", "Review"]})
    fig_case_mix.update_traces(textposition="outside", cliponaxis=False)
    fig_case_mix = style_fig(fig_case_mix, "Case volume and cancer type mix")

    monthly = df.groupby(["Cohort", "Month_Order", "Month_Name"], dropna=False).size().reset_index(name="Cases").sort_values(["Cohort", "Month_Order"])
    fig_monthly = px.line(monthly, x="Month_Name", y="Cases", color="Cohort", markers=True,
                          category_orders={"Month_Name": MONTH_ORDER, "Cohort": COHORT_ORDER}, color_discrete_sequence=COLOR_SEQUENCE)
    fig_monthly.update_traces(line=dict(width=4), marker=dict(size=10))
    fig_monthly.update_layout(xaxis_title="Month in cohort window", yaxis_title="Cases")
    fig_monthly = style_fig(fig_monthly, "Monthly case volume")

    fig_presentation = percent_stacked(df, "Mode_Presentation", "Presentation route share")
    fig_treatment = percent_stacked(df, "Treatment_Category", "Treatment category share")
    fig_alive = percent_stacked(df, "Alive_Dead", "Alive/dead outcome share")
    fig_survival = px.box(df.dropna(subset=["Survival_fromMDM"]), x="Cohort", y="Survival_fromMDM", color="Cohort", points="outliers",
                          color_discrete_sequence=COLOR_SEQUENCE, category_orders={"Cohort": COHORT_ORDER})
    fig_survival.update_layout(xaxis_title="", yaxis_title="Months")
    fig_survival = style_fig(fig_survival, "Survival from MDM")
    fig_size = px.histogram(df.dropna(subset=["Size"]), x="Size", color="Cohort", nbins=24, marginal="box", barmode="overlay", opacity=0.72,
                            color_discrete_sequence=COLOR_SEQUENCE, category_orders={"Cohort": COHORT_ORDER}, labels={"Size": "Tumour size (mm)"})
    fig_size = style_fig(fig_size, "Tumour size distribution")
    hcc_df, icc_df = df[df["Cancer_Type_Simple"] == "HCC"], df[df["Cancer_Type_Simple"] == "ICC"]
    fig_hcc_stage = percent_stacked(hcc_df, "HCC_BCLC_Stage", "HCC BCLC stage share") if not hcc_df.empty else None
    fig_icc_stage = percent_stacked(icc_df, "ICC_TNM_Stage", "ICC TNM stage share") if not icc_df.empty else None
    fig_surveillance = percent_stacked(df, "Surveillance_effectiveness", "Surveillance effectiveness")
    missing = (df.isna().mean() * 100).sort_values(ascending=False).head(14).reset_index()
    missing.columns = ["Column", "Missing_Percent"]
    fig_missing = px.bar(missing, x="Missing_Percent", y="Column", orientation="h", color="Missing_Percent", color_continuous_scale="Viridis", text=missing["Missing_Percent"].map(lambda x: f"{x:.1f}%"))
    fig_missing.update_yaxes(autorange="reversed")
    fig_missing.update_layout(xaxis_title="Missing values (%)", yaxis_title="", showlegend=False, xaxis_range=[0, 100])
    fig_missing = style_fig(fig_missing, "Data quality: top missing fields")

    sym_pre = pre["Mode_Presentation"].eq("Symptomatic").mean() * 100 if pre_n else 0
    sym_pan = pan["Mode_Presentation"].eq("Symptomatic").mean() * 100 if pan_n else 0
    surv_pre = pre["Mode_Presentation"].eq("Surveillance").mean() * 100 if pre_n else 0
    surv_pan = pan["Mode_Presentation"].eq("Surveillance").mean() * 100 if pan_n else 0
    med_surv_pre, med_surv_pan = pre["Survival_fromMDM"].median(), pan["Survival_fromMDM"].median()
    cards = "".join([
        metric_card("Total PLC cases", f"{total:,}", "All records in source file"),
        metric_card("Pre-pandemic cases", f"{pre_n:,}", "March 2019-February 2020"),
        metric_card("Pandemic cases", f"{pan_n:,}", f"{case_delta:.1f}% versus pre-pandemic"),
        metric_card("HCC / ICC", f"{hcc:,} / {icc:,}", "Derived from staging fields"),
        metric_card("Median age", f"{median_age:.0f} yrs", "All cases"),
        metric_card("Median survival", f"{median_survival:.1f} mo", "From MDM"),
        metric_card("Deaths recorded", f"{deaths:,}", f"{deaths / total * 100:.1f}% of cases"),
    ])
    insight_html = f'<section class="insights"><h2>Key signals in this dataset</h2><p><b>Case volume fell</b> from {pre_n:,} to {pan_n:,} records ({case_delta:.1f}%).</p><p><b>Symptomatic presentation increased</b> from {sym_pre:.1f}% to {sym_pan:.1f}%, while surveillance presentation moved from {surv_pre:.1f}% to {surv_pan:.1f}%.</p><p><b>Median survival from MDM</b> shifted from {med_surv_pre:.1f} to {med_surv_pan:.1f} months. Treat this as descriptive, not causal, because follow-up time and case mix may differ.</p></section>'
    figures = [fig_case_mix, fig_monthly, fig_presentation, fig_treatment, fig_alive, fig_survival, fig_size, fig_hcc_stage, fig_icc_stage, fig_surveillance, fig_missing]
    chart_html = "\n".join(f"<div class='chart'>{fig_html(fig)}</div>" for fig in figures if fig is not None)
    plotly_js = get_plotlyjs()
    html = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>COVID-19 Liver Cancer Dashboard</title><script>{plotly_js}</script><style>
:root{{--bg:#08111f;--panel:rgba(16,28,47,.82);--text:#f8fafc;--muted:rgba(248,250,252,.70);--line:rgba(255,255,255,.10);--green:#24f0b6}}*{{box-sizing:border-box}}body{{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--text);background:radial-gradient(circle at 10% 4%,rgba(36,240,182,.15),transparent 26%),radial-gradient(circle at 90% 16%,rgba(124,92,255,.18),transparent 30%),linear-gradient(135deg,#08111f 0%,#0e1726 52%,#070b14 100%);min-height:100vh}}.wrap{{width:min(1440px,94vw);margin:0 auto;padding:34px 0 52px}}.hero{{padding:30px 34px;border:1px solid var(--line);border-radius:30px;background:linear-gradient(135deg,rgba(36,240,182,.16),rgba(124,92,255,.13));box-shadow:0 28px 70px rgba(0,0,0,.32)}}.eyebrow{{color:var(--green);font-weight:800;letter-spacing:.12em;text-transform:uppercase;font-size:12px}}h1{{font-size:clamp(38px,5vw,70px);line-height:.95;margin:12px 0 14px;letter-spacing:-.06em}}.subtitle{{color:var(--muted);max-width:960px;font-size:18px;line-height:1.55}}.metrics{{display:grid;grid-template-columns:repeat(7,minmax(150px,1fr));gap:14px;margin:18px 0}}.metric-card{{padding:18px;border-radius:22px;background:var(--panel);border:1px solid var(--line);box-shadow:0 20px 48px rgba(0,0,0,.28)}}.metric-label{{color:var(--muted);font-size:13px}}.metric-value{{font-size:29px;font-weight:850;letter-spacing:-.04em;margin-top:5px}}.metric-note{{color:var(--green);font-size:12px;margin-top:4px}}.insights{{padding:20px 24px;margin:18px 0;background:rgba(36,240,182,.08);border-left:5px solid var(--green);border-radius:18px;color:rgba(248,250,252,.84)}}.insights h2{{margin:0 0 8px}}.insights p{{margin:7px 0;line-height:1.5}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:18px}}.chart{{min-height:440px;background:rgba(16,28,47,.72);border:1px solid var(--line);border-radius:24px;padding:10px;box-shadow:0 24px 60px rgba(0,0,0,.25);overflow:hidden}}.note{{color:var(--muted);margin-top:22px;font-size:13px;line-height:1.5}}@media(max-width:1180px){{.metrics{{grid-template-columns:repeat(3,1fr)}}.grid{{grid-template-columns:1fr}}}}@media(max-width:720px){{.metrics{{grid-template-columns:1fr}}.hero{{padding:24px}}}}</style></head><body><main class="wrap"><section class="hero"><div class="eyebrow">Primary liver cancer services dashboard</div><h1>COVID-19 impact on newly diagnosed liver cancer</h1><div class="subtitle">A descriptive dashboard comparing the 12 months before the pandemic with the first 12 months of the pandemic for referrals to the NUTH HPB multidisciplinary team.</div></section><section class="metrics">{cards}</section>{insight_html}<section class="grid">{chart_html}</section><p class="note">Source: uploaded COVID liver cancer CSV. Dashboard fields are descriptive and should not be interpreted as causal clinical evidence. Missing data are retained and visible in the data-quality chart.</p></main></body></html>'''
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Static dashboard written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
