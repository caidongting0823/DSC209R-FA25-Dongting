# Final_gradient.py
# DSC 209R Project 1 — Points-only scatter with continuous FPro gradient + sqrt axes

import sys
from pathlib import Path
import pandas as pd

# ---------- Config ----------
INPUT_CSV = "../grocerydb.csv"      # adjust if needed
HTML_OUT  = "final_project1_altair_4.html"
COLOR_SCALE_SQRT = True             # set to False for linear color mapping

# ---------- Altair import ----------
try:
    import altair as alt
except ModuleNotFoundError:
    sys.exit(
        "Altair is required for this script.\n"
        "Install with: pip install altair\n"
        "Then re-run:  python Final_gradient.py"
    )

def load_and_prepare(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        sys.exit(f"ERROR: Could not find {csv_path.name} next to this script.")

    df = pd.read_csv(csv_path)

    required = [
        "name", "category", "FPro", "Protein", "Total Fat", "Carbohydrate",
        "Sugars, total", "Fiber, total dietary"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        sys.exit(f"ERROR: Missing required columns: {missing}")

    # Standardize column names used for plotting
    df = df.rename(columns={"Sugars, total": "Sugar", "Fiber, total dietary": "Fiber"})

    # Filter out zero-kcal beverages (e.g., water/unsweetened drinks)
    cat_lower = df["category"].astype(str).str.lower()
    zero_macros = (
        df["Protein"].fillna(0).eq(0)
        & df["Total Fat"].fillna(0).eq(0)
        & df["Carbohydrate"].fillna(0).eq(0)
    )
    df = df[~(cat_lower.str.startswith("drink-") & zero_macros)].copy()

    # Drop rows with missing key fields
    df = df.dropna(subset=["Sugar", "Fiber", "Protein", "Total Fat", "Carbohydrate", "FPro"])

    # Gentle plausibility screens
    df = df[(df["Sugar"] >= 0) & (df["Fiber"] >= 0) &
            (df["Protein"] >= 0) & (df["Total Fat"] >= 0) & (df["Carbohydrate"] >= 0)]
    df = df[df["Sugar"] <= df["Carbohydrate"]]
    df = df[df["Fiber"] <= df["Carbohydrate"]]
    df["macro_sum"] = df["Protein"] + df["Total Fat"] + df["Carbohydrate"]
    df = df[df["macro_sum"] <= 110]

    # Calories per 100 g (computed, not encoded)
    df["Calories_per_100g"] = 4*df["Protein"] + 4*df["Carbohydrate"] + 9*df["Total Fat"]

    # Clean strings
    df["name"] = df["name"].astype(str)
    df["category"] = df["category"].astype(str)
    return df

def make_chart(df: pd.DataFrame) -> alt.Chart:
    alt.data_transformers.disable_max_rows()

    # Continuous gradient: light green (low FPro) -> dark blue (high FPro)
    # Use sqrt color scale (optional) to pull apart low/mid values in a right-skewed FPro distribution.
    color_scale = alt.Scale(
        domain=[0, 1],
        scheme="viridis",
        type=("sqrt" if COLOR_SCALE_SQRT else "linear")
    )

    pts = (
        alt.Chart(df)
          .mark_circle(size=28, opacity=0.55)
          .encode(
              x=alt.X(
                  "Sugar:Q",
                  title="Sugar (g per 100 g)",
                  scale=alt.Scale(type="sqrt")     # expands the dense low end while keeping 0
              ),
              y=alt.Y(
                  "Fiber:Q",
                  title="Fiber (g per 100 g)",
                  scale=alt.Scale(type="sqrt")
              ),
              color=alt.Color(
                  "FPro:Q",
                  title="Processing level (FPro)",
                  scale=color_scale
              ),
              tooltip=[
                  "name:N", "category:N",
                  alt.Tooltip("FPro:Q", title="FPro"),
                  alt.Tooltip("Sugar:Q", title="Sugar (g/100 g)"),
                  alt.Tooltip("Fiber:Q", title="Fiber (g/100 g)"),
                  alt.Tooltip("Calories_per_100g:Q", title="Calories per 100 g"),
              ],
          )
          .properties(width=760, height=520)
    )

    title = "Processing ↑ is associated with higher sugar and lower fiber across grocery foods"
    chart = pts.properties(title=title)

    caption_text = (
        f"Square-root axes used to improve readability near zero; "
        f"{'sqrt color scale for FPro to enhance contrast in low–mid values; ' if COLOR_SCALE_SQRT else ''}"
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
    chart.save(HTML_OUT)
    print(f"Saved: {HTML_OUT}\nOpen this file in your browser to view the chart.")

    # Optional static exports
    try:
        from altair_saver import save as alt_save
        alt_save(chart, "final_project1_altair_gradient.png", scale_factor=2)
        alt_save(chart, "final_project1_altair_gradient.svg")
        print("Also saved PNG and SVG.")
    except Exception:
        pass

if __name__ == "__main__":
    main()
