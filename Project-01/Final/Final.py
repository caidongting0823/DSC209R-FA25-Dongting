# Final.py
# Altair expository scatterplot for DSC 209R Project 1
# Idea: Processing ↑ is associated with higher sugar and lower fiber across grocery foods

import sys
from pathlib import Path
import pandas as pd

# --------- Config ---------
INPUT_CSV = "../grocerydb.csv"
HTML_OUT = "final_project1_altair_2.html"
NATURE_SANS = "Helvetica Neue, Helvetica, Arial, sans-serif"

# --------- Altair import with helpful error if missing ---------
try:
    import altair as alt
except ModuleNotFoundError:
    sys.exit(
        "Altair is required for this script.\n"
        "Install with: pip install altair\n"
        "Then re-run:  python Final.py"
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

    # Convenience rename
    df = df.rename(columns={"Sugars, total": "Sugar", "Fiber, total dietary": "Fiber"})

    # Filter out obvious non-food zero-kcal beverages
    cat_lower = df["category"].astype(str).str.lower()
    zero_macros = (
        df["Protein"].fillna(0).eq(0)
        & df["Total Fat"].fillna(0).eq(0)
        & df["Carbohydrate"].fillna(0).eq(0)
    )
    df = df[~(cat_lower.str.startswith("drink-") & zero_macros)].copy()

    # Drop rows missing key fields
    df = df.dropna(subset=["Sugar", "Fiber", "Protein", "Total Fat", "Carbohydrate", "FPro"])

    # Basic plausibility filters (keep this gentle to avoid over-pruning)
    df = df[(df["Sugar"] >= 0) & (df["Fiber"] >= 0) &
            (df["Protein"] >= 0) & (df["Total Fat"] >= 0) & (df["Carbohydrate"] >= 0)]
    df = df[df["Sugar"] <= df["Carbohydrate"]]
    df = df[df["Fiber"] <= df["Carbohydrate"]]
    df["macro_sum"] = df["Protein"] + df["Total Fat"] + df["Carbohydrate"]
    df = df[df["macro_sum"] <= 110]
    df = df[(df["Sugar"] <= 90) & (df["Fiber"] <= 49.9)]

    print(f"N (after filters & trims): {len(df):,}")

    # Calories per 100 g for size encoding (4/4/9 rule)
    df["Calories_per_100g"] = 4 * df["Protein"] + 4 * df["Carbohydrate"] + 9 * df["Total Fat"]

    # Clean category/name to strings
    df["category"] = df["category"].astype(str)
    df["name"] = df["name"].astype(str)

    return df

def build_annotations(df: pd.DataFrame) -> pd.DataFrame:
    def median_point(sub):
        if sub.empty:
            return None
        return {"x": float(sub["Sugar"].median()), "y": float(sub["Fiber"].median())}

    annos = []

    # Minimally processed cluster: low FPro, low sugar/fiber (e.g., meats/eggs)
    mp = df[(df["FPro"] <= 0.15) & (df["Sugar"] <= 5) & (df["Fiber"] <= 5)]
    pt = median_point(mp)
    if pt:
        pt["text"] = "Minimally processed cluster\n(low sugar, little/no fiber)"
        annos.append(pt)

    # Ultra-processed sweets: high FPro, high sugar, low fiber
    ups = df[(df["FPro"] >= 0.85) & (df["Sugar"] >= 25) & (df["Fiber"] <= 2)]
    pt = median_point(ups)
    if pt:
        pt["text"] = "Ultra-processed sweets\n(high sugar, little fiber)"
        annos.append(pt)

    # High-fiber whole foods: low-ish FPro, higher fiber, lower sugar
    hf = df[(df["FPro"] <= 0.35) & (df["Fiber"] >= 6) & (df["Sugar"] <= 15)]
    pt = median_point(hf)
    if pt:
        pt["text"] = "High-fiber whole foods\n(higher fiber, lower sugar)"
        annos.append(pt)

    return pd.DataFrame(annos) if annos else pd.DataFrame(columns=["x", "y", "text"])

def make_chart(df: pd.DataFrame, annotations: pd.DataFrame) -> alt.Chart:
    # Let Altair handle large datasets
    alt.data_transformers.disable_max_rows()

    # NOTE: fixed-size points (no size encoding)
    base = alt.Chart(df).mark_circle(size=40, opacity=0.35).encode(
        x=alt.X("Sugar:Q",
                title="Sugar (g per 100 g)",
                axis=alt.Axis(
                    titleFontWeight="bold", titlePadding=8, titleFontSize=12,
                    labelFontSize=11, tickSize=3, tickCount=12
                )),
        y=alt.Y("Fiber:Q",
                title="Fiber (g per 100 g)",
                axis=alt.Axis(
                    titleFontWeight="bold", titlePadding=8, titleFontSize=12,
                    labelFontSize=11, tickSize=3, tickCount=10
                )),
        color=alt.Color(
            "FPro:Q",
            title="Processing Level",
            scale=alt.Scale(domain=[0, 0.8, 1], range=["#89F336", "#50C878", "#0000CD"]),
            legend=alt.Legend(
                orient="right",
                offset=-200,  # <— pull legend toward the plot (try -6 to -14)
                titlePadding=4,
                labelPadding=6,
                gradientLength=200,  # shorter gradient = tighter legend
                gradientThickness=12
            ),
        ),
        # keep Calories_per_100g in tooltips if you still want to show it on hover
        tooltip=[
            "name:N", "category:N",
            alt.Tooltip("FPro:Q", title="FPro"),
            alt.Tooltip("Sugar:Q", title="Sugar (g/100 g)", ),
            alt.Tooltip("Fiber:Q", title="Fiber (g/100 g)"),
            alt.Tooltip("Calories_per_100g:Q", title="Calories per 100 g")
        ],
    ).properties(width=700, height=500)

    title = {
        "text": "The Nutrition Trade-Off: Why Processing Level Predicts Nutritional Quality",
        "subtitle": [
            "From fresh vegetables to packaged snacks, each level of processing adds sugar while stripping away dietary fiber"
        ],
        "fontSize": 18,
        "fontWeight": "bold",
        "subtitleFontSize": 13,
        "subtitleColor": "gray",
        "anchor": "middle",  # Left-aligned
        "subtitlePadding": 8,
        "offset": 10  # Add spacing above title
    }


    chart = (base).properties(title=title)

    # --- footer: concise methods (left) + source (right) ---
    chart_width = 700  # keep footer aligned with chart width

    footer_left = (
        alt.Chart(pd.DataFrame({
            "label": ["* n = 25,670 • Removed Implausible, Missing & Extreme Data • Exclude 0-kcal beverages"]
        }))
        .mark_text(font=NATURE_SANS, align="left", baseline="top", fontSize=10, color="#555", dy=4)
        .encode(text="label:N")
        .properties(width=chart_width / 2)
    )

    footer_right = (
        alt.Chart(pd.DataFrame({
            "label": ["Source: GroceryDB, 2025"]
        }))
        .mark_text(font=NATURE_SANS, align="right", baseline="top", fontSize=10, fontWeight="bold", color="#555", dy=4)
        .encode(text="label:N")
        .properties(width=chart_width / 2)
    )

    footer = alt.hconcat(footer_left, footer_right, spacing=10).resolve_legend(color="independent")

    return alt.vconcat(chart, footer, spacing=6)


def main():
    df = load_and_prepare(Path(INPUT_CSV))
    annotations = build_annotations(df)
    chart = make_chart(df, annotations)

    # Always save HTML (works without extra dependencies)
    chart.save(HTML_OUT)
    print(f"\nSaved: {HTML_OUT}")
    print("Open this file in your browser to view the interactive chart.")

    # Optional: try PNG/SVG if altair_saver is available (won't error if missing)
    try:
        from altair_saver import save as alt_save  # pip install altair_saver vega-lite vega
        alt_save(chart, "final_project1_altair.png", scale_factor=2)
        alt_save(chart, "final_project1_altair.svg")
        print("Also saved PNG and SVG.")
    except Exception:
        # PNG/SVG exporting often requires additional deps; HTML is sufficient for submission/viewing
        pass

if __name__ == "__main__":
    main()