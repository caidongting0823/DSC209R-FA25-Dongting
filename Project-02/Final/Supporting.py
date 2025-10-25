# -*- coding: utf-8 -*-
# Dumbbell chart (Altair) — Clinics % change vs Abortion rate % change
# Requires: pandas, altair, openpyxl (for reading .xlsx)
# pip install pandas altair openpyxl

import pandas as pd
import numpy as np
import altair as alt
from pathlib import Path

# ------------------------------------------------------------
# 1) Load data
# ------------------------------------------------------------
xlsx_path = Path("../Dataset/GuttmacherInstituteAbortionDataByState.xlsx")
df = pd.read_excel(xlsx_path, sheet_name="Guttmacher")

# 为了兼容列名中可能存在的不同短横/长横，做个“模糊取名”
def pick_col(startswith_text):
    for c in df.columns:
        if str(c).strip().lower().startswith(startswith_text):
            return c
    raise KeyError(f"Cannot find column starting with: {startswith_text}")

clinics_col = pick_col("% change in the no. of abortion clinics".lower())
rate_col    = pick_col("% change in abortion rate".lower())
state_col   = "U.S. State"

use = df[[state_col, clinics_col, rate_col]].copy()
use.columns = ["state", "delta_clinics_pct", "delta_rate_pct"]

# Data cleaning: transform to numeric, drop NaNs
for c in ["delta_clinics_pct", "delta_rate_pct"]:
    use[c] = pd.to_numeric(use[c], errors="coerce")
use = use.dropna(subset=["delta_clinics_pct", "delta_rate_pct"]).copy()

# ------------------------------------------------------------
# 2) Sorting (top: more negative clinics % change)
# ------------------------------------------------------------
use = use.sort_values(
    by=["delta_clinics_pct", "delta_rate_pct"],
    ascending=[True, True]
).reset_index(drop=True)

# To provide a fixed order for y axis
state_order = use["state"].tolist()

# 额外字段：诊所增减方向（用于配色）
def dir_label(x):
    if x < 0:
        return "Clinics ↓"
    elif x > 0:
        return "Clinics ↑"
    else:
        return "Clinics ="
use["clinics_dir"] = use["delta_clinics_pct"].apply(dir_label)

# 供阴影线使用的“行索引”与轻度平滑路径（移动平均）
use["row_index"] = np.arange(len(use))
win = 7  # 平滑窗口（奇数）
use["clinics_smooth"] = (
    use["delta_clinics_pct"]
    .rolling(window=win, center=True, min_periods=1)
    .mean()
)

# ------------------------------------------------------------
# 3) Common encodings, scales, and colors
# ------------------------------------------------------------
# x 轴正→负（inverted domain）
xmin = float(min(use["delta_clinics_pct"].min(), use["delta_rate_pct"].min())) - 2
xmax = float(max(use["delta_clinics_pct"].max(), use["delta_rate_pct"].max())) + 2
x_scale = alt.Scale(domain=[xmax, xmin])  # 注意：先大后小 => 反向

color_scale = alt.Scale(
    domain=["Clinics ↓", "Clinics =", "Clinics ↑"],
    range=["#568203", "#BABABA", "#F08080"]
)

height = 18 * len(use)  # 行高（可按需要调小/调大）
base = alt.Chart(use).properties(width=900, height=height)

# ------------------------------------------------------------
# 4) Layers
# ------------------------------------------------------------
# (a) 阴影灰线（更淡更宽）
shadow = (
    base.mark_line(stroke="#CFD8DC", strokeWidth=30, opacity=0.20, strokeCap="round")
    .encode(
        x=alt.X("clinics_smooth:Q", scale=x_scale, title="Percent Change (2017–2020)"),
        y=alt.Y("state:N", sort=state_order, title="State"),
        order="row_index:Q"
    )
)

# (b) 连接两端点的“哑铃线”
rule = (
    base.mark_rule()
    .encode(
        x=alt.X("delta_clinics_pct:Q", scale=x_scale),
        x2="delta_rate_pct:Q",
        y=alt.Y("state:N", sort=state_order),
        color=alt.Color("clinics_dir:N", scale=color_scale, title="Color encodes clinics % change")
    )
)

# (c) 左端点（诊所%变化）— 方块，且带“端点形状”图例
left_pts = (
    base.mark_point(shape="square", filled=True, size=150, stroke="black", strokeWidth=0.2)
    .encode(
        x=alt.X("delta_clinics_pct:Q", scale=x_scale),
        y=alt.Y("state:N", sort=state_order),
        color=alt.Color("clinics_dir:N", scale=color_scale, legend=None),
        shape=alt.Shape("endpoint:N",
                        scale=alt.Scale(domain=["Clinics Δ", "Rate Δ"],
                                        range=["square", "circle"]),
                        legend=alt.Legend(title="Endpoints")),
    )
    .transform_calculate(endpoint="'Clinics Δ'")
)

# (d) 右端点（堕胎率%变化）— 三角
right_pts = (
    base.mark_point(shape="circle", filled=True, size=150, stroke="black", strokeWidth=0.2)
    .encode(
        x=alt.X("delta_rate_pct:Q", scale=x_scale),
        y=alt.Y("state:N", sort=state_order),
        color=alt.Color("clinics_dir:N", scale=color_scale, legend=None),
        shape=alt.Shape("endpoint:N",
                        scale=alt.Scale(domain=["Clinics Δ", "Rate Δ"],
                                        range=["square", "circle"]),
                        legend=alt.Legend(title="Endpoints")),
    )
    .transform_calculate(endpoint="'Rate Δ'")
)

# (e) x=0 的参考虚线 — thicker, medium gray, bottom layer
vline0 = alt.Chart(pd.DataFrame({"x": [10]})).mark_rule(
    strokeDash=[4, 4], color="black", strokeWidth=2, opacity=0.3, strokeCap="round"
).encode(x=alt.X("x:Q", scale=x_scale))

chart = alt.layer(vline0, shadow, rule, left_pts, right_pts).resolve_scale(color="shared")

# 标题
chart = chart.properties(
    title=alt.TitleParams(
        text=["Clinic Closures vs. Abortion Rate Changes by State (Dumbbell)",
              "Sorted by clinics % change (ASC), then rate % change (ASC); shadow path through clinics % change"],
        anchor="start", fontSize=14
    )
)

# ------------------------------------------------------------
# 5) Save / display
# ------------------------------------------------------------
out_html = Path("supporting.html")
chart.save(out_html)  # 生成 HTML，浏览器打开即可
chart
