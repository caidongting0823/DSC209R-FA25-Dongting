# Final.py
# Altair expository scatterplot for DSC 209R Project 1
# Idea: Processing ↑ is associated with higher sugar and lower fiber across grocery foods

import sys
from pathlib import Path
import pandas as pd

# --------- Config ---------
INPUT_CSV = "../grocerydb.csv"      # keep your path
HTML_OUT = "final_project1_altair_3.html"

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

    # Gentle plausibility filters
    df = df[(df["Sugar"] >= 0) & (df["Fiber"] >= 0) &
            (df["Protein"] >= 0) & (df["Total Fat"] >= 0) & (df["Carbohydrate"] >= 0)]
    df = df[df["Sugar"] <= df["Carbohydrate"]]
    df = df[df["Fiber"] <= df["Carbohydrate"]]
    df["macro_sum"] = df["Protein"] + df["Total Fat"] + df["Carbohydrate"]
    df = df[df["macro_sum"] <= 110]

    # Calories per 100 g (computed but not encoded)
    df["Calories_per_100g"] = 4 * df["Protein"] + 4 * df["Carbohydrate"] + 9 * df["Total Fat"]

    # ---- Discrete FPro bands with explicit order (fixes legend/mapping) ----
    labels = ["0–0.10", "0.10–0.40", "0.40–0.70", "0.70–1.00"]  # en-dash
    df["FPro_band"] = pd.cut(
        df["FPro"],
        bins=[-0.001, 0.10, 0.40, 0.70, 1.00],
        labels=labels,
        include_lowest=True
    )
    df["FPro_band"] = df["FPro_band"].astype(
        pd.CategoricalDtype(categories=labels, ordered=True)
    )

    # Clean category/name to strings
    df["category"] = df["category"].astype(str)
    df["name"] = df["name"].astype(str)
    return df

def make_chart(df: pd.DataFrame) -> alt.Chart:
    # Let Altair handle large datasets
    alt.data_transformers.disable_max_rows()

    # Points only; fixed size; discrete color bands; sqrt axes
    pts = alt.Chart(df).mark_circle(size=28, opacity=0.55).encode(
        x=alt.X(
            "Sugar:Q",
            title="Sugar (g per 100 g)",
            scale=alt.Scale(type="sqrt")          # expand crowded low end
        ),
        y=alt.Y(
            "Fiber:Q",
            title="Fiber (g per 100 g)",
            scale=alt.Scale(type="sqrt")          # keep 0, improve readability
        ),
        color=alt.Color(
            "FPro_band:N",
            title="Processing (FPro: low → high)",
            # lock mapping + legend order to our labels
            scale=alt.Scale(
                domain=["0–0.10", "0.10–0.40", "0.40–0.70", "0.70–1.00"],
                range=["#99A770", "#8bc1ad", "#8BD3B9", "#F6F185"]  # light green → dark blue
            ),
            sort=None
        ),
        tooltip=[
            "name:N", "category:N",
            alt.Tooltip("FPro:Q", title="FPro"),
            alt.Tooltip("Sugar:Q", title="Sugar (g/100 g)"),
            alt.Tooltip("Fiber:Q", title="Fiber (g/100 g)"),
            alt.Tooltip("Calories_per_100g:Q", title="Calories per 100 g")
        ],
    ).properties(width=760, height=520)

    title = "Processing ↑ is associated with higher sugar and lower fiber across grocery foods"
    chart = pts.properties(title=title)

    caption_text = (
        "Square-root axes used to improve readability near zero; "
        "filtered out zero-kcal beverages; dropped rows with missing key nutrients; "
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
    chart = make_chart(df)

    # Save HTML (works without extra deps)
    chart.save(HTML_OUT)
    print(f"\nSaved: {HTML_OUT}")
    print("Open this file in your browser to view the interactive chart.")

    # Optional: PNG/SVG if altair_saver is available
    try:
        from altair_saver import save as alt_save  # pip install altair_saver vega-lite vega
        alt_save(chart, "final_project1_altair.png", scale_factor=2)
        alt_save(chart, "final_project1_altair.svg")
        print("Also saved PNG and SVG.")
    except Exception:
        pass

if __name__ == "__main__":
    main()
