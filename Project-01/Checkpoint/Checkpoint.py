# dsc209_project1_checkpoint.py
# Python 3.x — requires: pandas, numpy, matplotlib
# Usage: python dsc209_project1_checkpoint.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# -----------------------------
# CONFIG (you can tweak labels here)
# -----------------------------
INPUT_CSV = "grocerydb.csv"  # put your CSV in the same folder
OUT_PLOT1 = "plot1_sugar_vs_fiber_fpro.png"
OUT_PLOT2 = "plot2_price_premium_by_category.png"
OUT_PLOT3 = "plot3_store_by_fproclass_pricepercal.png"

# -----------------------------
# LOAD
# -----------------------------
if not Path(INPUT_CSV).exists():
    sys.exit(f"ERROR: Could not find {INPUT_CSV} next to this script.")

df = pd.read_csv(INPUT_CSV)

# -----------------------------
# ROBUST COLUMN NORMALIZATION
# -----------------------------
# 1) price_percal: accept multiple spellings
_price_cols = ["price percal", "price_percal", "price_per_cal", "price_per_kcal"]
_price_col = next((c for c in _price_cols if c in df.columns), None)
if _price_col is None:
    raise ValueError(f"Could not find a price-per-calorie column. Tried: {_price_cols}")
df["price_percal"] = pd.to_numeric(df[_price_col], errors="coerce")

# 2) FPro: must be continuous 0..1
if "FPro" not in df.columns:
    raise ValueError("Expected a continuous 'FPro' column (0–1).")
df["FPro"] = pd.to_numeric(df["FPro"], errors="coerce")

# 3) category / store as strings
for col in ["category", "store"]:
    if col in df.columns:
        df[col] = df[col].astype(str)
    else:
        raise ValueError(f"Missing required column '{col}' in CSV.")

# 4) Create integer FPro class 0..3 (prefer existing, else bin)
_possible_class_cols = ["FPro_class", "fpro_class", "processing_class"]
_class_col = next((c for c in _possible_class_cols if c in df.columns), None)

if _class_col is not None:
    df["FPro_class_int"] = pd.to_numeric(df[_class_col], errors="coerce").round().astype("Int64")
else:
    # Simple binning: adjust thresholds if your course specifies different ones
    # 0: <=0.10, 1: (0.10, 0.40], 2: (0.40, 0.70], 3: (0.70, 1.00]
    bins = [-0.001, 0.10, 0.40, 0.70, 1.00]
    df["FPro_class_int"] = pd.cut(df["FPro"], bins=bins, labels=[0, 1, 2, 3]).astype("Int64")

# -----------------------------
# PLOT 1 — Sugar vs Fiber colored by FPro
# Focus on snacks*, cereal, drink* categories
# -----------------------------
cat_lower = df["category"].str.lower()
mask_snacks = cat_lower.str.startswith("snacks-")
mask_cereal = cat_lower.eq("cereal") | cat_lower.eq("breakfast") | cat_lower.str.contains("cereal")
mask_drinks = cat_lower.str.startswith("drink-") | cat_lower.str.contains("soda")

mask_plot1 = mask_snacks | mask_cereal | mask_drinks

d1 = df.loc[
    mask_plot1,
    ["Sugars, total", "Fiber, total dietary", "FPro"]
].dropna()

plt.figure(figsize=(8.5, 6.8))
sc = plt.scatter(
    d1["Sugars, total"], d1["Fiber, total dietary"],
    c=d1["FPro"], s=16, alpha=0.7
)
cbar = plt.colorbar(sc)
cbar.set_label("FPro (processing level)")

plt.xlabel("Sugar (g per 100g)")
plt.ylabel("Fiber (g per 100g)")
plt.title("Processing ↑, fiber ↓, sugars ↑ — especially in snacks and cereals")
plt.figtext(
    0.5, -0.05,
    f"Filtered to snacks*, cereal, and drink* categories (n={len(d1)}). Each point is a product.",
    ha="center", fontsize=9
)
plt.tight_layout()
plt.savefig(OUT_PLOT1, dpi=200, bbox_inches="tight")
plt.close()

# -----------------------------
# PLOT 2 — Price vs Processing (category premiums)
# Compare median price_percal of Class 0 vs Class 3 by category
# EXCLUDE drink-* categories to avoid $/kcal blow-ups from ~0 kcal
# -----------------------------
d2 = df.loc[
    df["FPro_class_int"].isin([0, 3]) &
    (~df["category"].str.lower().str.startswith("drink-")),
    ["category", "FPro_class_int", "price_percal"]
].dropna()

if d2.empty:
    print("WARNING: No rows available for Plot 2 after filtering. Skipping this plot.")
else:
    med = d2.groupby(["category", "FPro_class_int"], as_index=False)["price_percal"].median()
    pv = med.pivot(index="category", columns="FPro_class_int", values="price_percal")
    pv = pv.rename(columns={0: "class0", 3: "class3"}).dropna(subset=["class0", "class3"])
    pv["delta"] = pv["class0"] - pv["class3"]
    pv = pv.sort_values("delta", ascending=True)

    fig, ax = plt.subplots(figsize=(9.5, max(4.2, 0.24 * len(pv))))
    ypos = np.arange(len(pv))

    ax.hlines(y=ypos, xmin=pv["class3"], xmax=pv["class0"], linewidth=1)
    ax.plot(pv["class3"], ypos, "o", label="Class 3 (ultra-processed)")
    ax.plot(pv["class0"], ypos, "o", label="Class 0 (minimally processed)")

    ax.set_yticks(ypos)
    ax.set_yticklabels(pv.index)
    ax.set_xlabel("Median price per calorie (USD per kcal)")
    ax.set_title("Price vs. Processing: Where do consumers pay premiums?")
    ax.legend(loc="lower right", fontsize=9)

    # Annotate top 5 categories where Class 0 is more expensive
    top5 = pv.nlargest(5, "delta")
    for cat, row in top5.iterrows():
        y = pv.index.get_loc(cat)
        ax.text(max(row["class0"], row["class3"]) * 1.02, y, f"Δ={row['delta']:.4f}",
                va="center", fontsize=8)

    fig.text(
        0.5, -0.03,
        "Δ = median(Class 0) – median(Class 3) price_percal; beverages excluded to avoid $/kcal inflation.",
        ha="center", fontsize=9
    )
    plt.tight_layout()
    plt.savefig(OUT_PLOT2, dpi=200, bbox_inches="tight")
    plt.close()

# -----------------------------
# PLOT 3 — Store × FPro_class medians (grouped bars, log y)
# -----------------------------
d3 = df[["store", "FPro_class_int", "price_percal"]].dropna()
grp = d3.groupby(["store", "FPro_class_int"], as_index=False)["price_percal"].median()

stores = list(grp["store"].unique())
classes = sorted([int(c) for c in grp["FPro_class_int"].dropna().unique()])

barw = 0.12 if len(classes) > 1 else 0.35
x = np.arange(len(stores))
fig, ax = plt.subplots(figsize=(10, 6))

for i, cls in enumerate(classes):
    # y-values per store for this class
    yvals = []
    for st in stores:
        sel = grp[(grp["store"] == st) & (grp["FPro_class_int"] == cls)]
        yvals.append(float(sel["price_percal"].iloc[0]) if not sel.empty else np.nan)
    # position bars centered around each x
    ax.bar(x + (i - len(classes)/2) * barw + barw/2, yvals, width=barw, label=f"FPro class {cls}")

ax.set_xticks(x)
ax.set_xticklabels(stores)
ax.set_yscale("log")  # wide range readability
ax.set_ylabel("Median price per calorie (USD per kcal, log scale)")
ax.set_title("Where should budget-conscious shoppers go for minimally processed food?")
ax.legend(title="Processing class", ncols=min(4, len(classes)), fontsize=8, title_fontsize=9)

fig.text(
    0.5, -0.03,
    "Median price per calorie by store and processing class. Log scale clarifies cross-store differences.",
    ha="center", fontsize=9
)
plt.tight_layout()
plt.savefig(OUT_PLOT3, dpi=200, bbox_inches="tight")
plt.close()

# -----------------------------
# PRINT A READY-TO-PASTE RATIONALE PARAGRAPH FOR PLOT 1
# -----------------------------
rationale = (
    "I prefer the sugar–fiber scatterplot colored by FPro because it communicates a clear, "
    "nutrition-relevant pattern using the strongest encodings: position for two quantitative variables "
    "and color for processing level. By focusing on snacks, cereals, and beverages, the plot highlights "
    "familiar products where processing often correlates with higher sugars and lower fiber—making the "
    "takeaway easy for a general audience. The visible clustering of high-FPro points in the low-fiber/"
    "high-sugar region supports the narrative that more processed items tend to have poorer fiber–sugar "
    "profiles. Axis labels with units, a concise takeaway title, and the colorbar anchor interpretation, "
    "balancing explanatory power and readability without overplotting."
)
print("\n--- Copy/Paste for your checkpoint (Plot 1 rationale) ---\n")
print(rationale)
print("\nSaved figures:")
print(f"  1) {OUT_PLOT1}")
print(f"  2) {OUT_PLOT2}")
print(f"  3) {OUT_PLOT3}")
