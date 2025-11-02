# 0) Setup
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("plots", exist_ok=True)

DATA_PATH = "us_earthquakes_m4.5_complete.csv"  # your uploaded file
df = pd.read_csv(DATA_PATH)

# Basic cleanups
df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
df["year"] = df["time"].dt.year
# A few depths can be negative; cap at 0 for plotting sanity (optional)
df["depth_clean"] = df["depth"].clip(lower=0)

# Region order for consistent plots
region_order = ["Alaska", "Conterminous US", "Hawaii", "Puerto Rico"]
df["region"] = pd.Categorical(df["region"], categories=region_order, ordered=True)


#### Plot 1: Annual counts (all regions combined)

annual = df.groupby("year").size().rename("count").reset_index()

plt.figure(figsize=(10, 4))
plt.plot(annual["year"], annual["count"], linewidth=1.5)
plt.title("Annual Earthquake Counts (M≥4.5), United States & Territories, 1925–2025")
plt.xlabel("Year")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig("docs/plots/01_annual_counts.png", dpi=200)
# plt.show()


#### Plot 2: Annual counts by region (stacked area or multiple lines)

annual_region = (
    df.groupby(["year", "region"]).size().unstack(fill_value=0)[region_order]
)

# Stacked area:
plt.figure(figsize=(10, 5))
plt.stackplot(
    annual_region.index,
    [annual_region[r] for r in region_order],
    labels=region_order,
    alpha=0.9,
)
plt.title("Annual Earthquake Counts by Region (M≥4.5), 1925–2025")
plt.xlabel("Year")
plt.ylabel("Count")
plt.legend(loc="upper left", ncols=2, frameon=False)
plt.tight_layout()
plt.savefig("docs/plots/02_annual_by_region_stacked.png", dpi=200)
# plt.show()

# (Alternative: multiple lines)
plt.figure(figsize=(10, 5))
for r in region_order:
    plt.plot(annual_region.index, annual_region[r], label=r, linewidth=1.5)
plt.title("Annual Earthquake Counts by Region (M≥4.5), 1925–2025")
plt.xlabel("Year"); plt.ylabel("Count")
plt.legend(ncols=2, frameon=False)
plt.tight_layout()
plt.savefig("docs/plots/02b_annual_by_region_lines.png", dpi=200)
# plt.show()

#### Plot 3: Magnitude distribution (histogram + optional log-y)

plt.figure(figsize=(7, 4))
bins = np.arange(df["mag"].min(), df["mag"].max() + 0.1, 0.1)
plt.hist(df["mag"], bins=bins, edgecolor="none")
plt.title("Magnitude Distribution (M≥4.5)")
plt.xlabel("Magnitude"); plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig("docs/plots/03_magnitude_hist.png", dpi=200)
# plt.show()

# Optional: log-y to emphasize tail
plt.figure(figsize=(7, 4))
plt.hist(df["mag"], bins=bins, edgecolor="none")
plt.yscale("log")
plt.title("Magnitude Distribution (M≥4.5) — Log Scale")
plt.xlabel("Magnitude"); plt.ylabel("Frequency (log)")
plt.tight_layout()
plt.savefig("docs/plots/03b_magnitude_hist_logy.png", dpi=200)
# plt.show()


#### Plot 4: Depth by region (boxplot)

# Drop NaN depths for boxplot
depth_df = df.dropna(subset=["depth_clean"])

plt.figure(figsize=(7.5, 4.5))
data = [depth_df.loc[depth_df["region"]==r, "depth_clean"] for r in region_order]
plt.boxplot(data, labels=region_order, showfliers=False)
plt.title("Focal Depth by Region (km) — M≥4.5")
plt.xlabel("Region"); plt.ylabel("Depth (km)")
plt.tight_layout()
plt.savefig("docs/plots/04_depth_by_region_box.png", dpi=200)
# plt.show()


#### Plot 5: Depth vs. Magnitude scatter plot

# Basic hexbin map-like view (no basemap needed)
valid = df.dropna(subset=["longitude", "latitude"])
plt.figure(figsize=(8.5, 4.5))
hb = plt.hexbin(
    valid["longitude"], valid["latitude"],
    gridsize=140, mincnt=1, bins="log"
)
plt.colorbar(hb, label="Count (log10 scale)")
plt.title("Spatial Density of Epicenters (M≥4.5), 1925–2025")
plt.xlabel("Longitude"); plt.ylabel("Latitude")
plt.tight_layout()
plt.savefig("docs/plots/05_spatial_hexbin.png", dpi=200)
# plt.show()


#### Plot 6: Quick epicenter map (interactive HTML)

# If Plotly is available, this gives you a lightweight interactive map for the checkpoint
try:
    import plotly.express as px

    fig = px.scatter_geo(
        df.dropna(subset=["latitude","longitude","mag"]),
        lat="latitude", lon="longitude",
        color="region",
        size="mag",
        hover_data={"mag": True, "depth": True, "place": True, "time": True, "region": True},
        scope="usa",  # Alaska/Hawaii insets included
        opacity=0.6,
        title="U.S. Earthquakes (M≥4.5), 1925–2025"
    )
    # Tweak marker sizing to keep max sizes reasonable
    fig.update_traces(marker=dict(sizemin=2, sizeref=0.08))
    fig.write_html("docs/plots/06_epicenter_map_interactive.html", include_plotlyjs="cdn")
    print("Saved interactive map:", "docs/plots/06_epicenter_map_interactive.html")

except ImportError:
    # Fallback: static scatter without a basemap (still useful to turn in)
    plt.figure(figsize=(8.5, 4.5))
    s = plt.scatter(df["longitude"], df["latitude"], s=(df["mag"]-4.4)*6, alpha=0.25)
    plt.title("Epicenters (M≥4.5), 1925–2025 — static fallback")
    plt.xlabel("Longitude"); plt.ylabel("Latitude")
    plt.tight_layout()
    plt.savefig("docs/plots/06_epicenter_scatter_fallback.png", dpi=200)
    print("Plotly not installed; saved static fallback PNG.")

