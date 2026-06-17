from __future__ import annotations

from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = PROJECT_ROOT / "data" / "analysis_tables"
EXPORT_DIR = PROJECT_ROOT / "data" / "exports"
OUT_DIR = PROJECT_ROOT / "eb1a_research_exports"


def pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:.1%}"


def num(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:,.0f}"


def savefig(name: str) -> str:
    path = OUT_DIR / name
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()
    return name


def add_rate_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["decided"] = df["approved"] + df["denied"]
    df["approval_decided"] = np.where(df["decided"] > 0, df["approved"] / df["decided"], np.nan)
    df["denial_decided"] = np.where(df["decided"] > 0, df["denied"] / df["decided"], np.nan)
    df["approval_received"] = np.where(df["received"] > 0, df["approved"] / df["received"], np.nan)
    df["denial_received"] = np.where(df["received"] > 0, df["denied"] / df["received"], np.nan)
    return df


def load_data() -> dict[str, pd.DataFrame]:
    radp = pd.read_csv(ANALYSIS_DIR / "eb1eb2_total_radp.csv")
    yearly = pd.read_csv(ANALYSIS_DIR / "i140_yearly_total_eb1_eb2_snapshots.csv")

    facts = pd.read_csv(EXPORT_DIR / "i140_status_counts.csv")
    source_files = pd.read_csv(EXPORT_DIR / "source_files.csv")
    categories = pd.read_csv(EXPORT_DIR / "preference_categories.csv")
    statuses = pd.read_csv(EXPORT_DIR / "case_statuses.csv")
    countries = pd.read_csv(EXPORT_DIR / "countries.csv")

    for df in [radp, yearly]:
        df["period"] = pd.PeriodIndex(
            df["fiscal_year"].astype(str) + "Q" + df["fiscal_quarter"].astype(str)
            if "fiscal_quarter" in df.columns
            else df["fiscal_year"].astype(str),
            freq="Q-SEP" if "fiscal_quarter" in df.columns else "Y-SEP",
        )
        if "fiscal_quarter" in df.columns:
            df["period_label"] = df["fiscal_year"].astype(str) + " Q" + df["fiscal_quarter"].astype(str)

    radp = add_rate_columns(radp)
    yearly = add_rate_columns(yearly)

    return {
        "radp": radp,
        "yearly": yearly,
        "facts": facts,
        "source_files": source_files,
        "categories": categories,
        "statuses": statuses,
        "countries": countries,
    }


def build_snapshot_transitions(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    facts = data["facts"]
    merged = (
        facts.merge(data["categories"], left_on="category_id", right_on="id", suffixes=("", "_category"))
        .merge(data["statuses"], left_on="status_id", right_on="id", suffixes=("", "_status"))
        .merge(data["countries"], left_on="country_id", right_on="id", suffixes=("", "_country"))
        .merge(data["source_files"], left_on="source_file_id", right_on="id", suffixes=("", "_source"))
    )

    all_country = merged["country_code"].eq("ALL") | merged["country_name"].eq("All Countries")
    subset = merged[
        all_country
        & merged["category_code"].isin(["TOTAL", "EB1", "EB2"])
        & merged["report_family"].eq("preference_country")
        & merged["status_code"].isin(["approved", "denied", "pending", "pending_other"])
    ].copy()
    subset["status_bucket"] = subset["status_code"].replace({"pending_other": "pending"})

    grouped = (
        subset.groupby(
            [
                "category_code",
                "cohort_fiscal_year",
                "report_fiscal_year",
                "report_quarter",
                "snapshot_date",
                "file_name",
                "status_bucket",
            ],
            dropna=False,
        )["count_value"]
        .sum()
        .reset_index()
    )
    wide = (
        grouped.pivot_table(
            index=[
                "category_code",
                "cohort_fiscal_year",
                "report_fiscal_year",
                "report_quarter",
                "snapshot_date",
                "file_name",
            ],
            columns="status_bucket",
            values="count_value",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    for col in ["approved", "denied", "pending"]:
        if col not in wide.columns:
            wide[col] = 0

    previous = wide[(wide["report_fiscal_year"] == 2025) & (wide["report_quarter"] == 4)]
    current = wide[(wide["report_fiscal_year"] == 2026) & (wide["report_quarter"] == 1)]

    transitions = previous.merge(
        current,
        on=["category_code", "cohort_fiscal_year"],
        suffixes=("_prev", "_curr"),
    )
    transitions["pending_drop"] = transitions["pending_prev"] - transitions["pending_curr"]
    transitions["approved_inc"] = transitions["approved_curr"] - transitions["approved_prev"]
    transitions["denied_inc"] = transitions["denied_curr"] - transitions["denied_prev"]
    transitions["resolved_inc"] = transitions["approved_inc"] + transitions["denied_inc"]
    transitions["denied_share_resolved"] = np.where(
        transitions["resolved_inc"] > 0,
        transitions["denied_inc"] / transitions["resolved_inc"],
        np.nan,
    )
    transitions["approval_share_resolved"] = np.where(
        transitions["resolved_inc"] > 0,
        transitions["approved_inc"] / transitions["resolved_inc"],
        np.nan,
    )
    return transitions


def make_charts(data: dict[str, pd.DataFrame], transitions: pd.DataFrame) -> dict[str, str]:
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams["font.family"] = "DejaVu Sans"

    radp = data["radp"]
    e11 = radp[radp["type"] == "E11"].copy().sort_values("period")

    charts: dict[str, str] = {}

    fig, ax = plt.subplots(figsize=(13, 6))
    for col, label, color in [
        ("received", "Received", "#1f77b4"),
        ("approved", "Approved", "#2ca02c"),
        ("denied", "Denied", "#d62728"),
    ]:
        ax.plot(e11["period_label"], e11[col], marker="o", linewidth=2.5, label=label, color=color)
    ax.set_title("E11 / EB1A Quarterly Flow Counts")
    ax.set_ylabel("Petitions")
    ax.set_xlabel("")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    charts["01_e11_quarterly_flows.png"] = savefig("01_e11_quarterly_flows.png")

    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.plot(e11["period_label"], e11["pending"], marker="o", linewidth=2.5, color="#9467bd")
    ax.fill_between(range(len(e11)), e11["pending"], color="#9467bd", alpha=0.15)
    ax.set_title("E11 / EB1A Pending Inventory")
    ax.set_ylabel("Pending inventory")
    ax.set_xlabel("")
    ax.tick_params(axis="x", rotation=45)
    charts["02_e11_pending_inventory.png"] = savefig("02_e11_pending_inventory.png")

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(e11["period_label"], e11["denial_decided"], marker="o", linewidth=2.5, label="Denied / (Approved + Denied)")
    ax.plot(e11["period_label"], e11["denial_received"], marker="o", linewidth=2.5, label="Denied / Received")
    ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
    ax.set_title("E11 / EB1A Denial Rates by Quarter")
    ax.set_ylabel("Denial rate")
    ax.set_xlabel("")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    charts["03_e11_denial_rates.png"] = savefig("03_e11_denial_rates.png")

    q1 = e11[e11["fiscal_quarter"] == 1].copy()
    q1_long = q1.melt(
        id_vars=["fiscal_year"],
        value_vars=["approval_received", "denial_received", "denial_decided"],
        var_name="metric",
        value_name="rate",
    )
    labels = {
        "approval_received": "Approved / Received",
        "denial_received": "Denied / Received",
        "denial_decided": "Denied / Decided",
    }
    q1_long["metric"] = q1_long["metric"].map(labels)
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.barplot(data=q1_long, x="fiscal_year", y="rate", hue="metric", ax=ax)
    ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
    ax.set_title("E11 / EB1A Q1 Comparison Across Available RADP Years")
    ax.set_xlabel("Fiscal year Q1")
    ax.set_ylabel("Rate")
    ax.legend(title="")
    charts["04_e11_q1_rate_comparison.png"] = savefig("04_e11_q1_rate_comparison.png")

    annual = (
        e11.groupby("fiscal_year", as_index=False)
        .agg(
            received=("received", "sum"),
            approved=("approved", "sum"),
            denied=("denied", "sum"),
            pending_end=("pending", "last"),
            quarters=("fiscal_quarter", "count"),
        )
        .sort_values("fiscal_year")
    )
    annual = add_rate_columns(annual.rename(columns={"pending_end": "pending"}))
    annual["year_label"] = np.where(annual["quarters"] < 4, annual["fiscal_year"].astype(str) + " Q1 only", annual["fiscal_year"].astype(str))
    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.bar(annual["year_label"], annual["denial_decided"], color="#d62728", alpha=0.82)
    ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
    ax.set_title("E11 / EB1A Annual Decided-Basis Denial Share")
    ax.set_xlabel("")
    ax.set_ylabel("Denied / (Approved + Denied)")
    ax.bar_label(bars, labels=[pct(v) for v in annual["denial_decided"]], padding=3, fontsize=10)
    charts["05_e11_annual_denial_share.png"] = savefig("05_e11_annual_denial_share.png")

    proxy = transitions[
        (transitions["category_code"] == "EB1")
        & transitions["cohort_fiscal_year"].isin([2024, 2025])
    ].copy()
    proxy["cohort_label"] = "FY" + proxy["cohort_fiscal_year"].astype(int).astype(str)
    proxy_long = proxy.melt(
        id_vars=["cohort_label"],
        value_vars=["approved_inc", "denied_inc"],
        var_name="resolved_type",
        value_name="count",
    )
    proxy_long["resolved_type"] = proxy_long["resolved_type"].map({"approved_inc": "Approval increase", "denied_inc": "Denial increase"})
    fig, ax = plt.subplots(figsize=(12, 7))
    sns.barplot(data=proxy_long, x="cohort_label", y="count", hue="resolved_type", ax=ax)
    ax.set_title("EB1 Proxy Transition\nFY2025 Q4 Snapshot to FY2026 Q1 Snapshot", fontsize=22, pad=18)
    ax.set_xlabel("Cohort fiscal year")
    ax.set_ylabel("Increase in outcomes")
    ax.legend(title="")
    ax.set_ylim(0, proxy_long["count"].max() * 1.35)
    for _, row in proxy.iterrows():
        ax.text(
            row["cohort_label"],
            max(row["approved_inc"], row["denied_inc"]) * 1.12,
            f"denied share resolved: {pct(row['denied_share_resolved'])}",
            ha="center",
            fontsize=10,
        )
    charts["06_eb1_pending_resolution_proxy.png"] = savefig("06_eb1_pending_resolution_proxy.png")

    yearly = data["yearly"]
    eb1_2025 = yearly[(yearly["type"] == "EB1") & (yearly["fiscal_year"] == 2025) & (yearly["snapshot_type"] == "historic")].iloc[0]
    eb1_2026 = yearly[(yearly["type"] == "EB1") & (yearly["fiscal_year"] == 2026) & (yearly["snapshot_type"] == "actual")].iloc[0]
    base = proxy[proxy["cohort_fiscal_year"] == 2025]["denied_share_resolved"].iloc[0]
    scenarios = pd.DataFrame(
        {
            "scenario": ["optimistic", "base EB1 FY2025", "pessimistic"],
            "pending_to_denial": [0.35, base, 0.55],
        }
    )
    scenarios["pending_to_approval"] = 1 - scenarios["pending_to_denial"]
    rows = []
    for _, scenario in scenarios.iterrows():
        for target, obs in [("EB1 FY2025", eb1_2025), ("EB1 FY2026 Q1", eb1_2026)]:
            expected_denied = obs["denied"] + obs["pending"] * scenario["pending_to_denial"]
            expected_approved = obs["approved"] + obs["pending"] * scenario["pending_to_approval"]
            denom = expected_denied + expected_approved
            rows.append(
                {
                    "target": target,
                    "scenario": scenario["scenario"],
                    "expected_denial_share": expected_denied / denom,
                    "pending_to_denial": scenario["pending_to_denial"],
                }
            )
    forecast = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.barplot(data=forecast, x="scenario", y="expected_denial_share", hue="target", ax=ax)
    ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
    ax.set_title("EB1 Proxy Scenario: Expected Final Denial Share Among Decided")
    ax.set_xlabel("")
    ax.set_ylabel("Expected denial share")
    ax.tick_params(axis="x", rotation=15)
    ax.legend(title="")
    charts["07_eb1_proxy_forecast_scenarios.png"] = savefig("07_eb1_proxy_forecast_scenarios.png")

    data["annual_e11"] = annual
    data["q1_e11"] = q1
    data["proxy_transitions"] = proxy
    data["forecast"] = forecast
    return charts


def write_readme(data: dict[str, pd.DataFrame], charts: dict[str, str]) -> None:
    e11 = data["radp"][data["radp"]["type"] == "E11"].copy()
    annual = data["annual_e11"]
    q1 = data["q1_e11"]
    proxy = data["proxy_transitions"]

    fy2022_q1 = q1[q1["fiscal_year"] == 2022].iloc[0]
    fy2023_q1 = q1[q1["fiscal_year"] == 2023].iloc[0]
    fy2024_q1 = q1[q1["fiscal_year"] == 2024].iloc[0]
    fy2025_q1 = q1[q1["fiscal_year"] == 2025].iloc[0]
    fy2026_q1 = q1[q1["fiscal_year"] == 2026].iloc[0]
    proxy_2025 = proxy[proxy["cohort_fiscal_year"] == 2025].iloc[0]
    proxy_2024 = proxy[proxy["cohort_fiscal_year"] == 2024].iloc[0]

    chart_notes = [
        (
            "01_e11_quarterly_flows.png",
            "E11 quarterly received, approved, and denied counts.",
            "Shows the direct EB1A flow signal from FY2022 through FY2026 Q1. The key visual question is whether denials rise while approvals weaken.",
        ),
        (
            "02_e11_pending_inventory.png",
            "E11 pending inventory.",
            "Shows that pending inventory rose sharply into FY2025/FY2026. This supports the idea that fresh quarters cannot be read only through approvals and denials.",
        ),
        (
            "03_e11_denial_rates.png",
            "E11 quarterly denial rates.",
            "Compares denial rate on received basis and decided basis. The decided-basis line is cleaner for adjudication severity because it excludes pending from the denominator.",
        ),
        (
            "04_e11_q1_rate_comparison.png",
            "E11 Q1 comparison across FY2022-FY2026.",
            f"FY2022-FY2025 Q1 denied/decided stays near 25-27%, while FY2026 Q1 jumps to {pct(fy2026_q1['denial_decided'])}. Approval/received also falls to {pct(fy2026_q1['approval_received'])} in FY2026 Q1. This is the strongest like-for-like seasonal check.",
        ),
        (
            "05_e11_annual_denial_share.png",
            "Annual E11 decided-basis denial share.",
            "Aggregates quarterly E11 outcomes by fiscal year. FY2026 is marked as Q1 only and should not be treated as a full-year result.",
        ),
        (
            "06_eb1_pending_resolution_proxy.png",
            "EB1 proxy pending-resolution transition.",
            f"Between FY2025 Q4 and FY2026 Q1 snapshots, the EB1 FY2025 cohort had {num(proxy_2025['approved_inc'])} additional approvals and {num(proxy_2025['denied_inc'])} additional denials; the denial share of newly resolved outcomes was {pct(proxy_2025['denied_share_resolved'])}. For EB1 FY2024 the comparable share was {pct(proxy_2024['denied_share_resolved'])}.",
        ),
        (
            "07_eb1_proxy_forecast_scenarios.png",
            "EB1 proxy scenario forecast.",
            "Stress-tests final denial share under optimistic, observed-base, and pessimistic pending-to-denial assumptions. This is a proxy model, not a direct E11 cohort forecast.",
        ),
    ]

    annual_lines = []
    for _, row in annual.iterrows():
        label = f"FY{int(row['fiscal_year'])}"
        if row["quarters"] < 4:
            label += " Q1 only"
        annual_lines.append(f"- {label}: decided-basis denial share {pct(row['denial_decided'])}; pending at last observed quarter {num(row['pending'])}.")

    readme = f"""# EB1A / E11 Research Export Pack

This folder contains exported charts from the local EB1A / E11 trend analysis. The charts are based on local CSV exports from the USCIS PostgreSQL project, not on live USCIS web access.

## Data Sources

- `data/analysis_tables/eb1eb2_total_radp.csv`
  - Quarterly RADP-style data for `TOTAL`, `EB1`, `E11`, `EB2`, and `NIW`.
  - Coverage: FY2022 through FY2026 Q1.
  - Main use here: direct E11 / EB1A quarterly flow and rate analysis.
- `data/analysis_tables/i140_yearly_total_eb1_eb2_snapshots.csv`
  - Yearly current-status snapshots for `TOTAL`, `EB1`, and `EB2`.
  - Main use here: EB1 proxy context and scenario forecasting.
- `data/exports/i140_status_counts.csv` plus dimension tables
  - Normalized fact and dimension exports.
  - Main use here: reconstructing EB1 snapshot-to-snapshot changes from FY2025 Q4 to FY2026 Q1.

## Research Question

The working question is whether the EB1A / E11 adjudication environment became materially less favorable in FY2025 and FY2026 Q1, and whether recent pending inventory is likely to resolve into denials at a higher rate than earlier periods.

## Key Notes Before Reading the Charts

- `E11` is EB1A / Aliens with Extraordinary Ability.
- `EB1` is broader than E11 and also includes E12 and E13.
- Direct E11 quarterly data exists from FY2022 through FY2026 Q1 in the RADP-style table.
- Direct E11 cohort-level pending conversion is not observable in the current dataset.
- EB1 is used only as a proxy for pending-resolution behavior.
- `pending` in RADP should be read as inventory/current status, not as a clean same-quarter cohort flow.
- FY2026 currently means FY2026 Q1 only.

## Chart Guide

"""
    for file_name, title, interpretation in chart_notes:
        readme += f"### [{file_name}]({file_name})\n\n"
        readme += f"**What it shows:** {title}\n\n"
        readme += f"**Why it matters:** {interpretation}\n\n"

    readme += f"""## Numeric Anchors

### E11 Q1 Like-for-Like Comparison

- FY2022 Q1: approved/received {pct(fy2022_q1['approval_received'])}; denied/received {pct(fy2022_q1['denial_received'])}; denied/decided {pct(fy2022_q1['denial_decided'])}.
- FY2023 Q1: approved/received {pct(fy2023_q1['approval_received'])}; denied/received {pct(fy2023_q1['denial_received'])}; denied/decided {pct(fy2023_q1['denial_decided'])}.
- FY2024 Q1: approved/received {pct(fy2024_q1['approval_received'])}; denied/received {pct(fy2024_q1['denial_received'])}; denied/decided {pct(fy2024_q1['denial_decided'])}.
- FY2025 Q1: approved/received {pct(fy2025_q1['approval_received'])}; denied/received {pct(fy2025_q1['denial_received'])}; denied/decided {pct(fy2025_q1['denial_decided'])}.
- FY2026 Q1: approved/received {pct(fy2026_q1['approval_received'])}; denied/received {pct(fy2026_q1['denial_received'])}; denied/decided {pct(fy2026_q1['denial_decided'])}.

### Annual E11 Summary

{chr(10).join(annual_lines)}

### EB1 Pending-Resolution Proxy

- EB1 FY2024 cohort, FY2025 Q4 to FY2026 Q1 snapshot transition: approval increase {num(proxy_2024['approved_inc'])}; denial increase {num(proxy_2024['denied_inc'])}; denial share of newly resolved outcomes {pct(proxy_2024['denied_share_resolved'])}.
- EB1 FY2025 cohort, FY2025 Q4 to FY2026 Q1 snapshot transition: approval increase {num(proxy_2025['approved_inc'])}; denial increase {num(proxy_2025['denied_inc'])}; denial share of newly resolved outcomes {pct(proxy_2025['denied_share_resolved'])}.

## Main Interpretation

The direct E11 data supports the hypothesis that the EB1A environment worsened in FY2025 and especially FY2026 Q1. The strongest direct evidence is the Q1 like-for-like comparison: approval/received drops sharply from FY2024 Q1 to FY2026 Q1, while FY2026 Q1 denial pressure is much higher.

The EB1 proxy adds a second signal: between the FY2025 Q4 and FY2026 Q1 snapshots, newly resolved EB1 FY2025 outcomes were split much more negatively than the comparable FY2024 transition. This is not exact E11 pending conversion, but it is directionally consistent with the hypothesis that FY2025 pending inventory may resolve with elevated denial share.

## Caveats

- The package does not prove that FY2026 Q1 denials came from FY2025 RFE cases; RFE status is not present in the aggregate USCIS files.
- EB1 proxy results can be distorted by E12 and E13 behavior.
- Snapshot transitions can include USCIS reporting revisions, not only true adjudication changes.
- FY2026 Q1 should not be annualized mechanically.
- Pending inventory should not be treated as if it were a clean received cohort.

## Rebuild

Run this from the project root to regenerate the package:

```powershell
python scripts\\export_eb1a_research_package.py
```
"""
    (OUT_DIR / "README.md").write_text(textwrap.dedent(readme).strip() + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    data = load_data()
    transitions = build_snapshot_transitions(data)
    charts = make_charts(data, transitions)
    write_readme(data, charts)

    manifest = pd.DataFrame(
        [{"file": "README.md", "description": "Chart guide and research interpretation"}]
        + [{"file": file_name, "description": "PNG chart"} for file_name in charts]
    )
    manifest.to_csv(OUT_DIR / "manifest.csv", index=False)
    print(f"Wrote {len(charts)} charts plus README to eb1a_research_exports")


if __name__ == "__main__":
    main()
