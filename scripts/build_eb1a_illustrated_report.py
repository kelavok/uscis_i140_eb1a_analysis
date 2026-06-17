from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = PROJECT_ROOT / "data" / "analysis_tables"
EXPORTS_DIR = PROJECT_ROOT / "eb1a_research_exports"
REPORT_MD = PROJECT_ROOT / "EB1A_ILLUSTRATED_REPORT.md"
REPORT_PDF = PROJECT_ROOT / "EB1A_ILLUSTRATED_REPORT.pdf"


@dataclass
class ChartSection:
    image: str
    title: str
    message: str
    notes: list[str]


def pct(value: float) -> str:
    return f"{value:.1%}"


def num(value: float) -> str:
    return f"{value:,.0f}"


def wrap(text: str, width: int = 92) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def load_summary_values() -> dict[str, object]:
    radp = pd.read_csv(ANALYSIS_DIR / "eb1eb2_total_radp.csv")
    e11 = radp[radp["type"] == "E11"].copy()
    e11["decided"] = e11["approved"] + e11["denied"]
    e11["approval_received"] = e11["approved"] / e11["received"]
    e11["denial_received"] = e11["denied"] / e11["received"]
    e11["denial_decided"] = e11["denied"] / e11["decided"]

    q1 = e11[e11["fiscal_quarter"] == 1].set_index("fiscal_year")
    annual = (
        e11.groupby("fiscal_year", as_index=False)
        .agg(
            received=("received", "sum"),
            approved=("approved", "sum"),
            denied=("denied", "sum"),
            pending=("pending", "last"),
            quarters=("fiscal_quarter", "count"),
        )
        .sort_values("fiscal_year")
    )
    annual["decided"] = annual["approved"] + annual["denied"]
    annual["denial_decided"] = annual["denied"] / annual["decided"]

    return {"q1": q1, "annual": annual}


def build_sections(summary: dict[str, object]) -> list[ChartSection]:
    q1 = summary["q1"]
    annual = summary["annual"]

    fy2022_q1 = q1.loc[2022]
    fy2023_q1 = q1.loc[2023]
    fy2024_q1 = q1.loc[2024]
    fy2025_q1 = q1.loc[2025]
    fy2026_q1 = q1.loc[2026]
    fy2025_annual = annual[annual["fiscal_year"] == 2025].iloc[0]
    fy2026_annual = annual[annual["fiscal_year"] == 2026].iloc[0]

    return [
        ChartSection(
            image="01_e11_quarterly_flows.png",
            title="1. Direct EB1A flow signal",
            message=(
                "The direct E11 quarterly series shows that the recent issue is not just volume. "
                "Denials become visibly heavier while approvals no longer keep the same relation to receipts."
            ),
            notes=[
                "Data source: quarterly RADP-style E11 rows, FY2022 through FY2026 Q1.",
                "This is the cleanest direct EB1A flow chart currently available in the project.",
            ],
        ),
        ChartSection(
            image="02_e11_pending_inventory.png",
            title="2. Pending inventory becomes part of the story",
            message=(
                f"E11 pending inventory reaches {num(fy2025_annual['pending'])} at FY2025 Q4 "
                f"and {num(fy2026_annual['pending'])} at FY2026 Q1. Fresh periods cannot be read "
                "only through approvals and denials because many cases have not resolved yet."
            ),
            notes=[
                "Pending is a stock/current-status measure, not a clean same-quarter cohort flow.",
                "High pending can hide future denials or approvals that will only appear in later USCIS releases.",
            ],
        ),
        ChartSection(
            image="03_e11_denial_rates.png",
            title="3. Denial rates rise, especially on decided basis",
            message=(
                "Denied / decided is the clearest severity metric because it compares denials only against "
                "resolved outcomes. It avoids treating pending cases as if they were already approvals or denials."
            ),
            notes=[
                "Received-basis rates are useful for workload context but are distorted by fresh pending inventory.",
                "Decided-basis rates are more useful for adjudication severity, though still incomplete for fresh periods.",
            ],
        ),
        ChartSection(
            image="04_e11_q1_rate_comparison.png",
            title="4. Like-for-like Q1 comparison",
            message=(
                f"FY2022-FY2025 Q1 denied/decided is relatively stable: "
                f"{pct(fy2022_q1['denial_decided'])}, {pct(fy2023_q1['denial_decided'])}, "
                f"{pct(fy2024_q1['denial_decided'])}, and {pct(fy2025_q1['denial_decided'])}. "
                f"FY2026 Q1 jumps to {pct(fy2026_q1['denial_decided'])}, while approval/received falls to "
                f"{pct(fy2026_q1['approval_received'])}."
            ),
            notes=[
                "This is the most intuitive seasonal test: Q1 compared with Q1.",
                "The expanded baseline makes FY2026 Q1 look abnormal against every available Q1 year, not only FY2024/FY2025.",
            ],
        ),
        ChartSection(
            image="05_e11_annual_denial_share.png",
            title="5. Annual E11 denial share",
            message=(
                "Annual aggregation shows a clear worsening into FY2025, while FY2026 Q1 is much more negative. "
                "FY2026 should be read as an early signal, not as a full-year result."
            ),
            notes=[
                "FY2026 is Q1 only and must stay visually marked as partial.",
                "The annual view is helpful for direction, but quarterly detail is still needed.",
            ],
        ),
        ChartSection(
            image="06_eb1_pending_resolution_proxy.png",
            title="6. EB1 proxy for pending resolution",
            message=(
                "Direct E11 cohort-level pending conversion is not observable in the current files. "
                "As a proxy, EB1 FY2025 newly resolved outcomes between the FY2025 Q4 and FY2026 Q1 snapshots "
                "show a much higher denial share than FY2024."
            ),
            notes=[
                "EB1 is broader than E11 and includes E12 and E13.",
                "This proxy does not prove E11 conversion, but it is directionally consistent with a more negative pending outcome mix.",
            ],
        ),
        ChartSection(
            image="07_eb1_proxy_forecast_scenarios.png",
            title="7. Scenario forecast, not a precise prediction",
            message=(
                "The scenario chart stress-tests how final denial share changes if remaining pending cases resolve "
                "under optimistic, observed-base, or pessimistic assumptions. It is a decision-support view, not a direct forecast."
            ),
            notes=[
                "The base case uses observed EB1 FY2025 proxy behavior.",
                "The chart should be updated after each new USCIS quarter.",
            ],
        ),
    ]


def write_markdown(summary: dict[str, object], sections: list[ChartSection]) -> None:
    annual = summary["annual"]
    annual_lines = []
    for _, row in annual.iterrows():
        label = f"FY{int(row['fiscal_year'])}"
        if row["quarters"] < 4:
            label += " Q1 only"
        annual_lines.append(
            f"- **{label}:** received {num(row['received'])}, approved {num(row['approved'])}, "
            f"denied {num(row['denied'])}, pending {num(row['pending'])}, "
            f"denied/decided {pct(row['denial_decided'])}."
        )

    md = f"""# EB1A / E11 Trend Analysis: Illustrated Report

## Executive Summary

This report summarizes the local USCIS I-140 analysis focused on EB1A / E11. The main question is whether the EB1A adjudication environment worsened in FY2025 and FY2026 Q1, and whether recent pending inventory is likely to resolve into denials at a higher rate than earlier periods.

The evidence is directionally consistent with that hypothesis:

- Direct E11 quarterly data shows weaker approval performance and stronger denial pressure in recent periods.
- The like-for-like Q1 comparison is especially concerning: FY2022-FY2025 Q1 denial/decided is stable near 25-27%, while FY2026 Q1 jumps to 52.5%.
- E11 pending inventory expanded materially through FY2025 and FY2026 Q1.
- Direct E11 pending conversion is not observable, so EB1 is used as a proxy for how pending inventory is resolving.
- The EB1 FY2025 proxy transition from the FY2025 Q4 snapshot to the FY2026 Q1 snapshot is much more negative than the comparable FY2024 transition.

## Research Hypothesis

The working hypothesis is:

1. EB1A / E11 denial pressure increased in FY2025 and became especially visible in FY2026 Q1.
2. Some denials appearing in FY2026 Q1 may correspond to older pending or RFE-affected cases rather than only petitions received in FY2026 Q1.
3. A fall in fast approvals combined with elevated pending inventory may be an early warning signal.
4. FY2025 pending inventory may eventually resolve into denials at a higher rate than earlier historical periods.

The USCIS aggregate files do not contain RFE events, so the RFE mechanism is an interpretation to test indirectly, not an observed fact.

## Data Used

- `data/analysis_tables/eb1eb2_total_radp.csv`
  - Quarterly RADP-style rows for `TOTAL`, `EB1`, `E11`, `EB2`, and `NIW`.
  - Coverage: FY2022 through FY2026 Q1.
  - Main use: direct E11 / EB1A quarterly flow and rate analysis.
- `data/analysis_tables/i140_yearly_total_eb1_eb2_snapshots.csv`
  - Yearly current-status snapshots for `TOTAL`, `EB1`, and `EB2`.
  - Main use: high-level context and EB1 proxy scenario analysis.
- `data/exports/i140_status_counts.csv` plus dimension tables
  - Normalized fact and dimension exports from PostgreSQL.
  - Main use: reconstructing EB1 snapshot-to-snapshot changes.

## Method in Plain Language

The analysis separates three concepts:

- **Received basis:** approvals or denials divided by received petitions. This is useful for workload context but can look artificially weak when many cases are still pending.
- **Decided basis:** approvals or denials divided by `approved + denied`. This better captures adjudication severity among cases that have actually resolved.
- **Pending proxy:** because exact E11 cohort-level pending conversion is not available, EB1 snapshot changes are used cautiously as a proxy.

## Chart-Based Findings

"""

    for section in sections:
        md += f"### {section.title}\n\n"
        md += f"![{section.title}](eb1a_research_exports/{section.image})\n\n"
        md += f"**Main message:** {section.message}\n\n"
        md += "**Notes:**\n\n"
        for note in section.notes:
            md += f"- {note}\n"
        md += "\n"

    md += f"""## Numeric Anchors

### Annual E11 Summary

{chr(10).join(annual_lines)}

## Final Interpretation

The strongest direct evidence comes from E11 itself: recent quarters, and especially FY2026 Q1, show a much less favorable mix of approvals and denials. The expanded Q1 comparison is particularly useful because it reduces seasonality concerns and uses every available Q1 baseline year from FY2022 through FY2026.

The pending story is more complex. The available files do not let us directly follow E11 pending petitions from one snapshot into final outcomes. For that reason, the report uses EB1 as a proxy. This proxy is imperfect because EB1 includes E11, E12, and E13, but it still gives a useful warning signal: the FY2025 EB1 snapshot transition into FY2026 Q1 shows a much higher denial share among newly resolved outcomes than the FY2024 comparison.

Overall, the evidence supports a cautious but materially negative interpretation: the EB1A / E11 environment appears to have worsened in FY2025 and FY2026 Q1, and recent pending inventory should not be assumed to resolve at older, more favorable rates.

## Caveats

- FY2026 currently means FY2026 Q1 only.
- RFE is not directly observed in the source data.
- EB1 is a proxy for pending conversion, not exact E11 tracking.
- USCIS can revise historical counts between reports.
- Pending is an inventory/current-status measure, not a clean same-quarter flow.

## Reproducibility

The chart export pack can be rebuilt with:

```powershell
python scripts\\export_eb1a_research_package.py
```

This illustrated report can be rebuilt with:

```powershell
python scripts\\build_eb1a_illustrated_report.py
```
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def draw_text_page(pdf: PdfPages, title: str, paragraphs: list[str], bullets: list[str] | None = None) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    fig.text(0.08, 0.93, title, fontsize=22, fontweight="bold", va="top")
    y = 0.86
    for para in paragraphs:
        fig.text(0.08, y, wrap(para, 82), fontsize=11.5, va="top", linespacing=1.35)
        y -= 0.035 * (wrap(para, 82).count("\n") + 1) + 0.025
    if bullets:
        for bullet in bullets:
            fig.text(0.105, y, u"\u2022 " + wrap(bullet, 78).replace("\n", "\n  "), fontsize=11.2, va="top", linespacing=1.35)
            y -= 0.035 * (wrap(bullet, 78).count("\n") + 1) + 0.012
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def draw_chart_page(pdf: PdfPages, section: ChartSection) -> None:
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor("white")
    fig.text(0.055, 0.94, section.title, fontsize=19, fontweight="bold", va="top")
    fig.text(0.055, 0.88, wrap(section.message, 118), fontsize=10.8, va="top", linespacing=1.25)

    image_path = EXPORTS_DIR / section.image
    img = Image.open(image_path)
    ax = fig.add_axes([0.055, 0.17, 0.89, 0.62])
    ax.imshow(img)
    ax.axis("off")

    note_text = " | ".join(section.notes)
    fig.text(0.055, 0.085, "Notes: " + wrap(note_text, 126), fontsize=9.2, va="top", color="#333333")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def write_pdf(summary: dict[str, object], sections: list[ChartSection]) -> None:
    q1 = summary["q1"]
    with PdfPages(REPORT_PDF) as pdf:
        draw_text_page(
            pdf,
            "EB1A / E11 Trend Analysis",
            [
                "Illustrated report based on the local USCIS I-140 dataset.",
                "The report asks whether EB1A / E11 denial pressure increased in FY2025 and FY2026 Q1, and whether recent pending inventory should be expected to resolve less favorably than in earlier periods.",
            ],
            [
                f"FY2022-FY2025 Q1 E11 denied/decided stays around 25-27%; FY2026 Q1 reaches {pct(q1.loc[2026, 'denial_decided'])}.",
                f"FY2026 Q1 E11 approval/received falls to {pct(q1.loc[2026, 'approval_received'])}.",
                "Direct E11 pending conversion is not observable, so EB1 snapshot behavior is used only as a proxy.",
            ],
        )
        draw_text_page(
            pdf,
            "Data and Method",
            [
                "The report uses local analysis tables exported from PostgreSQL. The key table is the quarterly RADP-style dataset with TOTAL, EB1, E11, EB2, and NIW rows from FY2022 through FY2026 Q1.",
                "The analysis distinguishes received-basis rates from decided-basis rates. Received-basis rates are useful for workload, but decided-basis rates are better for adjudication severity because pending cases are excluded from the denominator.",
                "For pending conversion, exact E11 cohort tracking is not available in the current source files. EB1 snapshot changes are therefore used as a cautious proxy.",
            ],
        )
        for section in sections:
            draw_chart_page(pdf, section)
        draw_text_page(
            pdf,
            "Final Interpretation and Caveats",
            [
                "The evidence supports a cautious but materially negative interpretation: the EB1A / E11 environment appears to have worsened in FY2025 and FY2026 Q1.",
                "The strongest direct evidence is the expanded Q1 like-for-like comparison and the E11 decided-basis denial share. The EB1 proxy adds a second warning signal for pending inventory, but it should not be treated as exact E11 conversion.",
            ],
            [
                "FY2026 is currently Q1 only and should not be annualized mechanically.",
                "RFE is not directly observed in the USCIS aggregate data.",
                "EB1 includes E11, E12, and E13, so EB1 proxy results can differ from exact EB1A behavior.",
                "USCIS can revise historical counts between releases.",
            ],
        )


def main() -> None:
    summary = load_summary_values()
    sections = build_sections(summary)
    write_markdown(summary, sections)
    write_pdf(summary, sections)
    print("Wrote EB1A_ILLUSTRATED_REPORT.md and EB1A_ILLUSTRATED_REPORT.pdf")


if __name__ == "__main__":
    main()
