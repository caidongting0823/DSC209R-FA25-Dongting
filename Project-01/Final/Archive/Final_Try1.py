# Final_v3_points_only.py
# DSC 209R Project 1 — Clean points-only scatter (color=FPro) + LOESS + annotations
# Output: final_project1_altair_v3_points.html

import sys
from pathlib import Path
import pandas as pd

INPUT_CSV = "grocerydb.csv"
HTML_OUT  = "final_project1_altair_v3_points.html"

try:
    import altair as alt
except ModuleNotFoundError:
    sys.exit(
        "Altair is required for this script.\n"
        "Install: pip install altair\n"
        "Re-run: python Final_v3_points_only.py"
    )

def load_and_clean(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        sys.exit(f"ERROR: Missing {csv_path.name} next to this script.")

    df = pd.read_csv(csv_path)

    needed = [
        "name", "category", "FPro", "Protein", "Total Fat", "Carbohydrate",
        "Sugars, total", "Fiber, total dietary"
    ]
    miss = [c for c in needed if c not in df.columns]
    if miss:
        sys.exit(f"ERROR: Missing required columns: {miss}")

    df = df.rename(columns={"Sugars, total": "Sugar", "Fiber, total dietary": "Fiber"})

    # Filter out zero-kcal beverages to avoid meaningless 0/0 piles
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

    df["name"] = df["name"].astype(str)
    df["category"] = df["category"].astype(str)
    return df

def build_annotations(df: pd.DataFrame) -> pd.DataFrame:
    def med(sub):
        if sub.empty: return None
        return {"x": float(sub["Sugar"].median()), "y": float(sub["Fiber"].median())}

    ann = []

    mp = df[(df["FPro"] <= 0.15) & (df["Sugar"] <= 5) & (df["Fiber"] <= 5)]
    pt = med(mp)
    if pt:
        pt["text"] = "Minimally processed cluster\n(low sugar, little/no fiber)"
        ann.append(pt)

    ups = df[(df["FPro"] >= 0.85) & (df["Sugar"] >= 25) & (df["Fiber"] <= 2)]
    pt = med(ups)
    if pt:
        pt["text"] = "Ultra-processed sweets\n(high sugar, little fiber)"
        ann.append(pt)

    hf = df[(df["FPro"] <= 0.35) & (df["Fiber"] >= 6) & (df["Sugar"] <= 15)]
    pt = med(hf)
    if pt:
        pt["text"] = "High-fiber whole foods\n(higher fiber, lower sugar)"
        ann.append(pt)

    return pd.DataFrame(ann) if ann else pd.DataFrame(columns=["x","y","text"])

def make_chart(df: pd.DataFrame, annotations: pd.DataFrame):
    alt.data_transformers.disable_max_rows()

    # Tiny jitter near 0 to separate stacks; leaves values visually unchanged
    # Vega expressions allow random()
    jittered = (
        alt.Chart(df)
          .transform_calculate(
              Sugar_jit="datum.Sugar + (datum.Sugar < 2 ? (random()-0.5)*0.6 : 0)",
              Fiber_jit="datum.Fiber + (datum.Fiber < 2 ? (random()-0.5)*0.6 : 0)"
          )
    )

    pts = (
        jittered
          .mark_circle(size=18, opacity=0.38, stroke="white", strokeWidth=0.25)
          .encode(
              x=alt.X("Sugar_jit:Q", title="Sugar (g per 100 g)"),
              y=alt.Y("Fiber_jit:Q", title="Fiber (g per 100 g)"),
              color=alt.Color("FPro:Q", title="Processing level (FPro)",
                              scale=alt.Scale(domain=[0,1], scheme="viridis")),
              tooltip=["name","category",
                       alt.Tooltip("FPro:Q", title="FPro"),
                       alt.Tooltip("Sugar:Q", title="Sugar (g/100 g)"),
                       alt.Tooltip("Fiber:Q", title="Fiber (g/100 g)")]
          )
          .properties(width=760, height=520)
    )

    # LOESS uses the true values (no jitter) for a faithful trend
    trend = (
        alt.Chart(df)
          .transform_loess("Sugar","Fiber", bandwidth=0.25)
          .mark_line()
          .encode(x="Sugar:Q", y="Fiber:Q")
    )

    text = (
        alt.Chart(annotations).mark_text(align="left", dx=6, dy=-6)
          .encode(x="x:Q", y="y:Q", text="text:N")
        if not annotations.empty
        else alt.Chart(pd.DataFrame({"x": [], "y": [], "text": []})).mark_text()
    )

    title = "Processing ↑ is associated with higher sugar and lower fiber across grocery foods"
    caption = (
        "Filtered out zero-kcal beverages; dropped rows with missing key nutrients; "
        "removed implausible values (sugar/fiber ≤ carbs; macros ≤ 110 g/100 g)."
    )

    main = (pts + trend + text).properties(title=title)
    caption_mark = (
        alt.Chart(pd.DataFrame({"label":[caption]}))
          .mark_text(align="center", baseline="top", fontSize=11, dy=6)
          .encode(text="label:N")
          .properties(width=760)
    )

    return alt.vconcat(main, caption_mark, spacing=6)

def main():
    df = load_and_clean(Path(INPUT_CSV))
    annotations = build_annotations(df)
    chart = make_chart(df, annotations)
    chart.save(HTML_OUT)
    print(f"Saved: {HTML_OUT}\nOpen in a browser to view the chart.")

    # Optional static exports if deps are present
    try:
        from altair_saver import save as alt_save
        alt_save(chart, "final_project1_altair_v3_points.png", scale_factor=2)
        alt_save(chart, "final_project1_altair_v3_points.svg")
        print("Also saved PNG and SVG.")
    except Exception:
        pass

if __name__ == "__main__":
    main()
