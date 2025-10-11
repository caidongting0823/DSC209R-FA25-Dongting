# Final.py
# DSC 209R Project 1 — Points-only scatter; linear axes + optional edge trimming

import sys
from pathlib import Path
import pandas as pd

# --------- Config ---------
INPUT_CSV = "../grocerydb.csv"
HTML_OUT  = "final_project1_altair_trimmed.html"

# Trimming controls
PERCENTILE = 0.99          # 0.99 = 99th percentile for axis zoom / filter
FILTER_EXTREMES = False    # False = zoom axes only; True = drop points above cutoffs

# --------- Altair import ---------
try:
    import altair as alt
except ModuleNotFoundError:
    sys.exit(
        "Altair is required. Install with: pip install altair\n"
        "Then rerun: python Final.py"
    )

def load_and_prepare(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        sys.exit(f"ERROR: Could not find {csv_path.name} next to this script.")

    df = pd.read_csv(csv_path)

    # Ensure expected columns exist
    required = [
        "name", "category", "FPro", "Protein", "Total Fat", "Carbohydrate",
        "Sugars, total", "Fiber, total dietary"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        sys.exit(f"ERROR: Missing required columns: {missing}")

    # Rename for plotting
    df = df.rename(columns={"Sugars, total": "Sugar", "Fiber, total dietary": "Fiber"})

    # Filter out zero-kcal beverages
    cat_lower = df["category"].astype(str).str.lower()
    zero_macros = (
        df["Protein"].fillna(0).eq(0)
        & df["Total Fat"].fillna(0).eq(0)
        & df["Carbohydrate"].fillna(0).eq(0)
    )
    df = df[~(cat_lower.str.startswith("drink-") & zero_macros)].copy()

    # Drop rows missing key fields
    df = df.dropna(subset=["Sugar", "Fiber", "Protein", "Total Fat", "Carbohydrate", "FPro"])

    # Plausibility checks
    df = df[(df["Sugar"] >= 0) & (df["Fiber"] >= 0) &
            (df["Protein"] >= 0) & (df["Total Fat"] >= 0) & (df["Carbohydrate"] >= 0)]
    df = df[df["Sugar"] <= df["Carbohydrate"]]
    df = df[df["Fiber"] <= df["Carbohydrate"]]
    df["macro_sum"] = df["Protein"] + df["Total Fat"] + df["Carbohydrate"]
    df = df[df["macro_sum"] <= 110]

    # Optional derived field (not encoded now, but kept for tooltip if needed)
    df["Calories_per_100g"] = 4*df["Protein"] + 4*df["Carbohydrate"] + 9*df["Total Fat"]

    # Strings
    df["category"] = df["category"].astype(str)
    df["name"] = df["name"].astype(str)
    return df

def apply_edge_trim(df: pd.DataFrame):
    # Compute cutoffs
    x_cut = float(df["Sugar"].quantile(PERCENTILE))
    y_cut = float(df["Fiber"].quantile(PERCENTILE))

    if FILTER_EXTREMES:
        # Remove points beyond cutoffs
        trimmed = df[(df["Sugar"] <= x_cut) & (df["Fiber"] <= y_cut)].copy()
        return trimmed, x_cut, y_cut, True
    else:
        # Keep all data; we’ll just zoom axes to these cutoffs
        return df.copy(), x_cut, y_cut, False

def make_chart(df: pd.DataFrame, x_cut: float, y_cut: float, filtered: bool) -> alt.Chart:
    alt.data_transformers.disable_max_rows()

    base = alt.Chart(df).mark_circle(size=50, opacity=0.55).encode(
        # LINEAR axes; zoomed domain to reduce empty far-right/top space
        x=alt.X("Sugar:Q", title="Sugar (g per 100 g)",
                scale=alt.Scale(domain=[0, x_cut])),
        y=alt.Y("Fiber:Q", title="Fiber (g per 100 g)",
                scale=alt.Scale(domain=[0, y_cut])),
        # keep your current gradient mapping (light green -> purple)
        color=alt.Color(
            "FPro:Q",
            title="Processing level (FPro)",
            scale=alt.Scale(domain=[0, 0.5, 1], range=["#89F336", "#50C878", "#7F00FF"]),
        ),
        tooltip=[
            "name:N", "category:N",
            alt.Tooltip("FPro:Q", title="FPro"),
            alt.Tooltip("Sugar:Q", title="Sugar (g/100 g)"),
            alt.Tooltip("Fiber:Q", title="Fiber (g/100 g)"),
            alt.Tooltip("Calories_per_100g:Q", title="Calories per 100 g"),
        ],
    ).properties(width=760, height=520)

    title = "Processing ↑ is associated with higher sugar and lower fiber across grocery foods"
    chart = base.properties(title=title)

    # Caption explains what we did
    trim_note = (
        f"axes zoomed to 99th pct (Sugar ≤ {x_cut:.1f}, Fiber ≤ {y_cut:.1f})"
        if not filtered else
        f"excluded values above 99th pct (Sugar > {x_cut:.1f} or Fiber > {y_cut:.1f})"
    )
    caption_text = (
        f"{trim_note}; filtered out zero-kcal beverages; dropped rows with missing key nutrients; "
        "removed implausible values (sugar/fiber ≤ carbs; macros ≤ 110 g/100 g)."
    )

    caption = (
        alt.Chart(pd.DataFrame({"label": [caption_text]}))
          .mark_text(align="center", baseline="top", fontSize=11, dy=6)
          .encode(text="label:N")
          .properties(width=760)
    )

    return alt.vconcat(chart, caption, spacing=6)

def main():
    df = load_and_prepare(Path(INPUT_CSV))
    df2, x_cut, y_cut, filtered = apply_edge_trim(df)
    chart = make_chart(df2, x_cut, y_cut, filtered)
    chart.save(HTML_OUT)
    print(f"Saved: {HTML_OUT}\nOpen this file in your browser to view the chart.")

    # Optional: static exports
    try:
        from altair_saver import save as alt_save
        alt_save(chart, "final_project1_altair_trimmed.png", scale_factor=2)
        alt_save(chart, "final_project1_altair_trimmed.svg")
        print("Also saved PNG and SVG.")
    except Exception:
        pass

if __name__ == "__main__":
    main()
