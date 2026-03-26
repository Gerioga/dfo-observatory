#!/usr/bin/env python3
"""
Development Finance Observatory — Interactive Dashboard
Serbia or Sahel. World Bank perspective. USD (year-specific ECB rates).
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Dev Finance Observatory", page_icon="🏦", layout="wide", initial_sidebar_state="expanded")

PASSWORD = os.environ.get("APP_PASSWORD", "donors26")
DATA_PATH = os.path.join(os.path.dirname(__file__), "data.csv")


def check_password():
    """Simple password gate."""
    if "authenticated" in st.session_state and st.session_state["authenticated"]:
        return True
    st.markdown("<div style='text-align:center;padding:80px 0 20px'><h1 style='color:#1F4E79'>Development Finance Observatory</h1></div>", unsafe_allow_html=True)
    _, c, _ = st.columns([1, 1, 1])
    with c:
        pwd = st.text_input("Password", type="password", key="pwd_input")
        if st.button("Enter", use_container_width=True, type="primary"):
            if pwd == PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password")
    return False

DFI_LIST = ["CEB", "EIB", "EBRD", "World Bank", "IFC", "MIGA", "KfW", "AFD", "Chinese donors"]
UN_LIST = ["UNDP", "UNICEF", "WFP", "FAO"]

INST_COLORS = {
    "EBRD": "#1F4E79", "World Bank": "#2D8659", "Chinese donors": "#C41E3A",
    "IFC": "#D97706", "MIGA": "#7C3AED", "KfW": "#0891B2", "AFD": "#BE185D",
    "EIB": "#E67E22", "CEB": "#8B4513",
    "UNDP": "#0072BC", "UNICEF": "#1CABE2", "WFP": "#E3242B", "FAO": "#006838",
}
COUNTRY_COLORS = {"Serbia": "#1F4E79", "Mali": "#E67E22", "Niger": "#27AE60", "Chad": "#8E44AD"}
COUNTRY_COORDS = {"Mali": [17.57, -4.0], "Niger": [17.61, 8.08], "Chad": [15.45, 18.73]}
CY = 2026


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH).fillna("")
    df["amount_usd"] = pd.to_numeric(df["amount_usd"], errors="coerce").fillna(0)
    df["amount_eur"] = pd.to_numeric(df["amount_eur"], errors="coerce").fillna(0)
    df["approval_year"] = pd.to_numeric(df["approval_year"], errors="coerce")
    # Capitalize sector names for display
    df["sector"] = df["sector"].str.title()
    return df


def fmt(v):
    if v >= 1e9: return f"${v/1e9:.1f}B"
    if v >= 1e6: return f"${v/1e6:.0f}M"
    return f"${v:,.0f}"

def gcfg(fig):
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
    return fig

def pfilter(data, period, yr_min):
    cut = {"All time": yr_min, "Last 10 years": CY-10, "Last 5 years": CY-5, "Last 2 years": CY-2}[period]
    return data[(data["approval_year"].isna()) | (data["approval_year"] >= cut)]


def compute_facts(data, region):
    """Key findings — last 5 years, WB-centric."""
    d5 = data[(data["approval_year"].isna()) | (data["approval_year"] >= CY - 5)]
    dfi5 = d5[d5["institution"].isin(DFI_LIST)]
    facts = []

    wb5 = dfi5[dfi5["institution"] == "World Bank"]
    if len(dfi5) > 0 and dfi5["amount_usd"].sum() > 0:
        wb_share = wb5["amount_usd"].sum() / dfi5["amount_usd"].sum() * 100
        facts.append(f"Over the last 5 years, **World Bank** accounts for **{wb_share:.0f}%** of DFI approvals ({fmt(wb5['amount_usd'].sum())}, {len(wb5)} projects).")

    non_wb = dfi5[dfi5["institution"] != "World Bank"].groupby("institution")["amount_usd"].sum()
    if len(non_wb) > 0:
        top = non_wb.idxmax()
        facts.append(f"**{top}** is the largest competing DFI in the last 5 years ({fmt(non_wb.max())}).")

    # Trend: WB growing or shrinking?
    wb_all = data[data["institution"] == "World Bank"]
    wb_yr = wb_all[wb_all["approval_year"].notna()].groupby("approval_year")["amount_usd"].sum()
    if len(wb_yr) > 3:
        slope = np.polyfit(wb_yr.index.values, wb_yr.values, 1)[0]
        direction = "growing" if slope > 0 else "declining"
        facts.append(f"World Bank annual approvals are **{direction}** over the long term (slope: {fmt(abs(slope))}/year).")

    top_sector = dfi5.groupby("sector")["amount_usd"].sum()
    if len(top_sector) > 0:
        ts = top_sector.idxmax()
        facts.append(f"**{ts.title()}** is the top sector in the last 5 years ({top_sector.max()/dfi5['amount_usd'].sum()*100:.0f}% of DFI volume).")

    china5 = d5[d5["institution"] == "Chinese donors"]
    if len(china5) > 0:
        facts.append(f"**Chinese donors**: {len(china5)} projects in last 5 years ({fmt(china5['amount_usd'].sum())}), "
                     f"{(china5['instrument_type']=='grant').sum()/max(len(china5),1)*100:.0f}% grants.")

    miga5 = d5[d5["institution"] == "MIGA"]
    if len(miga5) > 0:
        facts.append(f"**MIGA** guarantee exposure: {fmt(miga5['amount_usd'].sum())} (guarantee ceilings, not disbursed capital).")

    if region == "Sahel":
        un5 = d5[d5["institution"].isin(UN_LIST)]
        if len(un5) > 0:
            facts.append(f"**UN agencies** (UNDP, UNICEF, WFP, FAO): {len(un5)} activities, {fmt(un5['amount_usd'].sum())} in last 5 years.")

    return facts


# ═══════════════════════════════════════════════════════════════
# README
# ═══════════════════════════════════════════════════════════════
def readme_page():
    st.markdown("<div style='text-align:center;padding:30px 0'><h1 style='color:#1F4E79'>Development Finance Observatory</h1></div>", unsafe_allow_html=True)
    _, c, _ = st.columns([1, 3, 1])
    with c:
        st.markdown("""
## What this is

Maps project-level data from development finance institutions into a common format.
Commitments from World Bank, EBRD, EIB, IFC, Chinese donors, UN agencies — filtered
and compared side by side.

---

## What is shown

**Approved commitments only.** Disbursements are not tracked. **MIGA** figures are
**guarantee ceilings** (max exposure), not cash investments.

**Cancelled/dropped/suspended projects excluded** (51 removed).

**Co-financing is not netted out.** Same project may appear under multiple institutions.
Cross-institution totals are indicative, not precise.

---

## Coverage

| Region | Countries | DFIs | UN |
|--------|-----------|------|----|
| **ECA** | Serbia | CEB, EIB, EBRD, WB, IFC, MIGA, KfW, AFD, Chinese donors | — |
| **Sahel** | Mali, Niger, Chad | WB, IFC, MIGA, AFD, Chinese donors | UNDP, UNICEF, WFP, FAO |

## Currency

**USD** — EUR converted using year-specific ECB annual average rates. Chinese donors in constant 2021 USD.

## Public vs Private

**Public**: sovereign/govt borrower. **Private**: company/fund/FI borrower.

## Sources

CEB (Excel) · EIB (Excel) · EBRD (IATI) · WB (API) · IFC (Finances One) ·
MIGA (Finances One) · KfW (IATI/BMZ) · AFD (OpenDataSoft) ·
Chinese donors (AidData v3.0) · UNDP/UNICEF/WFP/FAO (IATI)
        """)
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🇷🇸 SERBIA", use_container_width=True, type="primary"):
                st.session_state["page"] = "Serbia"; st.rerun()
        with c2:
            if st.button("🌍 SAHEL", use_container_width=True, type="primary"):
                st.session_state["page"] = "Sahel"; st.rerun()


def home():
    st.markdown("<div style='text-align:center;padding:60px 0 30px'><h1 style='color:#1F4E79;font-size:2.5em'>Development Finance Observatory</h1><p style='color:#666'>Cross-Regional Development Finance Analysis</p></div>", unsafe_allow_html=True)
    _, c, _ = st.columns([1, 3, 1])
    with c:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🇷🇸 SERBIA\n\nECA", use_container_width=True, type="primary"):
                st.session_state["page"] = "Serbia"; st.rerun()
        with c2:
            if st.button("🌍 SAHEL\n\nMali · Niger · Chad", use_container_width=True, type="primary"):
                st.session_state["page"] = "Sahel"; st.rerun()
        with c3:
            if st.button("📖 README\n\nMethodology", use_container_width=True):
                st.session_state["page"] = "readme"; st.rerun()


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════
def dashboard(df, region):
    if region == "Serbia":
        data = df[df["country"] == "Serbia"].copy()
        label, color = "Serbia", "#1F4E79"
    else:
        data = df[df["country"].isin(["Mali", "Niger", "Chad"])].copy()
        label, color = "Sahel (Mali · Niger · Chad)", "#E67E22"

    with st.sidebar:
        st.markdown(f"### {label}")
        st.markdown(f"**{len(data):,}** projects · **{fmt(data['amount_usd'].sum())}**")
        st.divider()
        if st.button("← Home"): del st.session_state["page"]; st.rerun()
        if st.button("📖 README"): st.session_state["page"] = "readme"; st.rerun()
        st.markdown("#### Filters")
        institutions = sorted(data["institution"].unique())
        sel_inst = st.multiselect("Institution", institutions, default=institutions)
        sectors = sorted(data["sector"].unique())
        sel_sectors = st.multiselect("Sector", sectors, default=sectors)
        pp = st.radio("Public / Private", ["All", "Public", "Private"], horizontal=True)
        if region == "Sahel":
            sel_c = st.multiselect("Country", sorted(data["country"].unique()), default=sorted(data["country"].unique()))
            data = data[data["country"].isin(sel_c)]

    data = data[data["institution"].isin(sel_inst) & data["sector"].isin(sel_sectors)]
    if pp == "Public": data = data[data["public_private"] == "public"]
    elif pp == "Private": data = data[data["public_private"] == "private"]

    yr_min = int(data["approval_year"].dropna().min()) if len(data["approval_year"].dropna()) > 0 else 2000

    # Header
    st.markdown(f"<div style='background:{color};padding:15px 25px;border-radius:8px;margin-bottom:20px'><h2 style='color:white;margin:0'>Development Finance Observatory — {label}</h2><p style='color:rgba(255,255,255,.7);margin:5px 0 0'>{len(data):,} projects · {data['institution'].nunique()} institutions · {fmt(data['amount_usd'].sum())}</p></div>", unsafe_allow_html=True)

    # KPIs
    k1, k2, k3, k4, k5 = st.columns(5)
    wb = data[data["institution"] == "World Bank"]
    k1.metric("Total Projects", f"{len(data):,}")
    k2.metric("WB Projects", f"{len(wb):,}")
    k3.metric("Total USD", fmt(data["amount_usd"].sum()))
    k4.metric("WB Share", f"{wb['amount_usd'].sum()/max(data['amount_usd'].sum(),1)*100:.0f}%")
    k5.metric("Institutions", data["institution"].nunique())

    # ─── KEY FINDINGS (last 5 years) ───
    st.divider()
    st.markdown("#### Key Findings (last 5 years)")
    facts = compute_facts(data, region)
    cols_f = st.columns(min(len(facts), 3))
    for i, fact in enumerate(facts):
        cols_f[i % 3].info(fact)

    # ─── MAP (Sahel only) ───
    if region == "Sahel":
        st.divider()
        st.markdown("#### Sahel Map")
        mc1, mc2 = st.columns([2, 1])
        with mc2:
            map_period = st.selectbox("Period", ["All time", "Last 10 years", "Last 5 years", "Last 2 years"], key="map_p")
        map_cut = {"All time": 1900, "Last 10 years": CY-10, "Last 5 years": CY-5, "Last 2 years": CY-2}[map_period]
        map_base = data[(data["approval_year"].isna()) | (data["approval_year"] >= map_cut)]
        with mc1:
            map_indicator = st.selectbox("Indicator", [
            "Total commitments (USD)", "Number of projects", "WB commitments (USD)",
            "DFI count", "Public share (%)", "Top sector by volume"
        ], key="map_ind")

        map_data = []
        for country, coords in COUNTRY_COORDS.items():
            cd = map_base[map_base["country"] == country]
            if map_indicator == "Total commitments (USD)":
                val = cd["amount_usd"].sum()
                display = fmt(val)
                size = max(val / 1e8, 5)
            elif map_indicator == "Number of projects":
                val = len(cd)
                display = str(val)
                size = max(val / 5, 5)
            elif map_indicator == "WB commitments (USD)":
                val = cd[cd["institution"] == "World Bank"]["amount_usd"].sum()
                display = fmt(val)
                size = max(val / 1e8, 5)
            elif map_indicator == "DFI count":
                val = cd[cd["institution"].isin(DFI_LIST)]["institution"].nunique()
                display = str(val)
                size = val * 15
            elif map_indicator == "Public share (%)":
                val = (cd["public_private"] == "public").sum() / max(len(cd), 1) * 100
                display = f"{val:.0f}%"
                size = val / 2
            else:  # Top sector
                if len(cd) > 0:
                    ts = cd.groupby("sector")["amount_usd"].sum().idxmax()
                    display = ts.title()
                else:
                    display = "N/A"
                size = 20
                val = 0

            map_data.append({"country": country, "lat": coords[0], "lon": coords[1],
                            "value": display, "size": max(size, 3)})

        map_df = pd.DataFrame(map_data)

        fig_map = px.scatter_mapbox(
            map_df, lat="lat", lon="lon", size="size",
            hover_name="country", hover_data={"value": True, "size": False, "lat": False, "lon": False},
            color_discrete_sequence=[color],
            title=f"{map_indicator} by Country",
            zoom=3, center={"lat": 16, "lon": 8},
        )
        fig_map.update_layout(mapbox_style="carto-positron", height=400,
                             margin=dict(l=0, r=0, t=40, b=0))
        # Add country labels
        fig_map.add_trace(go.Scattermapbox(
            lat=[d["lat"] for d in map_data],
            lon=[d["lon"] for d in map_data],
            mode="text",
            text=[f"{d['country']}: {d['value']}" for d in map_data],
            textfont=dict(size=14, color="black"),
            showlegend=False,
        ))
        st.plotly_chart(fig_map, use_container_width=True)

    st.divider()

    # ─── ALL COMMITMENTS ───
    st.markdown("#### Commitments by Institution")
    p1 = st.radio("Period", ["All time", "Last 10 years", "Last 5 years", "Last 2 years"], horizontal=True, key="p1")
    d1 = pfilter(data, p1, yr_min)

    c1, c2 = st.columns(2)
    with c1:
        # Group UN agencies into single "UN Agencies" bar
        d1_grouped = d1.copy()
        d1_grouped.loc[d1_grouped["institution"].isin(UN_LIST), "institution"] = "UN Agencies"
        idata = d1_grouped.groupby("institution")["amount_usd"].sum().sort_values(ascending=True).reset_index()
        idata["mn"] = idata["amount_usd"] / 1e6
        colors_grouped = {**INST_COLORS, "UN Agencies": "#0072BC"}
        fig = px.bar(idata, y="institution", x="mn", orientation="h", color="institution",
                     color_discrete_map=colors_grouped, title=f"By Institution ({p1}, USD mn)")
        fig.update_layout(showlegend=False, yaxis_title="", xaxis_title="USD (mn)", height=350, margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(gcfg(fig), use_container_width=True)

    with c2:
        if region == "Sahel":
            # Stacked bar: country × institution
            cross = d1.groupby(["country", "institution"])["amount_usd"].sum().reset_index()
            cross["mn"] = cross["amount_usd"] / 1e6
            fig2 = px.bar(cross, x="country", y="mn", color="institution",
                          color_discrete_map=INST_COLORS,
                          title=f"By Country × Institution ({p1}, USD mn)",
                          barmode="stack")
            fig2.update_layout(xaxis_title="", yaxis_title="USD (mn)", height=350,
                              margin=dict(l=10,r=10,t=40,b=10),
                              legend=dict(orientation="h", yanchor="bottom", y=-0.35))
        else:
            sdata = d1.groupby("sector")["amount_usd"].sum().sort_values(ascending=True).tail(10).reset_index()
            sdata["mn"] = sdata["amount_usd"] / 1e6
            fig2 = px.bar(sdata, y="sector", x="mn", orientation="h",
                          title=f"Top 10 Sectors ({p1}, USD mn)", color_discrete_sequence=[color])
            fig2.update_layout(showlegend=False, yaxis_title="", xaxis_title="USD (mn)", height=350, margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(gcfg(fig2), use_container_width=True)

    if region == "Sahel":
        sdata = d1.groupby("sector")["amount_usd"].sum().sort_values(ascending=True).tail(10).reset_index()
        sdata["mn"] = sdata["amount_usd"] / 1e6
        fig_s = px.bar(sdata, y="sector", x="mn", orientation="h",
                       title=f"Top 10 Sectors ({p1}, USD mn)", color_discrete_sequence=[color])
        fig_s.update_layout(showlegend=False, yaxis_title="", xaxis_title="USD (mn)", height=300, margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(gcfg(fig_s), use_container_width=True)

    st.divider()

    # ─── PUBLIC vs PRIVATE ───
    st.markdown("#### Public vs Private")
    p2 = st.radio("Period", ["All time", "Last 10 years", "Last 5 years", "Last 2 years"], horizontal=True, key="p2")
    d2 = pfilter(data, p2, yr_min)
    pp1, pp2 = st.columns(2)
    with pp1:
        ppd = d2.groupby("public_private")["amount_usd"].sum().reset_index()
        ppd["mn"] = ppd["amount_usd"] / 1e6
        fig_pp = px.pie(ppd, names="public_private", values="mn", title=f"By Amount ({p2}, USD mn)",
                        hole=0.4, color_discrete_sequence=["#1F4E79", "#D97706"])
        fig_pp.update_layout(height=300, margin=dict(l=10,r=10,t=40,b=10))
        fig_pp.update_traces(textposition="outside", textinfo="label+percent")
        st.plotly_chart(fig_pp, use_container_width=True)
    with pp2:
        ppc = d2["public_private"].value_counts().reset_index()
        ppc.columns = ["type", "count"]
        fig_ppc = px.pie(ppc, names="type", values="count", title=f"By Count ({p2})",
                         hole=0.4, color_discrete_sequence=["#1F4E79", "#D97706"])
        fig_ppc.update_layout(height=300, margin=dict(l=10,r=10,t=40,b=10))
        fig_ppc.update_traces(textposition="outside", textinfo="label+percent")
        st.plotly_chart(fig_ppc, use_container_width=True)

    st.divider()

    # ─── APPROVALS OVER TIME (last 25 years) ───
    st.markdown("#### Approvals Over Time (last 25 years)")
    timeline = data[data["approval_year"].notna()].copy()
    timeline = timeline[timeline["approval_year"] >= CY - 25]
    timeline["year"] = timeline["approval_year"].astype(int)
    tl = timeline.groupby(["year", "institution"])["amount_usd"].sum().reset_index()
    tl["mn"] = tl["amount_usd"] / 1e6

    fig_tl = px.bar(tl, x="year", y="mn", color="institution", color_discrete_map=INST_COLORS,
                    title="DFI Approved Commitments (USD mn, stacked)", barmode="stack")
    for inst in sorted(timeline["institution"].unique()):
        inst_yr = timeline[timeline["institution"] == inst].groupby("year")["amount_usd"].sum().reset_index()
        if len(inst_yr) > 2:
            x, y = inst_yr["year"].values, inst_yr["amount_usd"].values / 1e6
            z = np.polyfit(x, y, 1)
            fig_tl.add_trace(go.Scatter(
                x=x, y=np.poly1d(z)(x), mode="lines", name=f"{inst} trend",
                line=dict(color=INST_COLORS.get(inst, "#999"), width=1.5, dash="dot"),
                opacity=0.35, showlegend=False))
    fig_tl.update_layout(xaxis_title="Year", yaxis_title="USD (mn)", height=450,
                         margin=dict(l=10,r=10,t=40,b=10),
                         legend=dict(orientation="h", yanchor="bottom", y=-0.25))
    st.plotly_chart(gcfg(fig_tl), use_container_width=True)

    # Auto commentary
    total_yr = timeline.groupby("year")["amount_usd"].sum()
    wb_yr = timeline[timeline["institution"] == "World Bank"].groupby("year")["amount_usd"].sum()
    if len(total_yr) > 2:
        peak = total_yr.idxmax()
        wb_trend = "growing" if len(wb_yr) > 2 and np.polyfit(wb_yr.index.values, wb_yr.values, 1)[0] > 0 else "declining"
        recent_top = timeline[timeline["year"] >= CY - 5].groupby("institution")["amount_usd"].sum()
        top_recent = recent_top.idxmax() if len(recent_top) > 0 else "N/A"
        st.caption(f"DFI approvals peaked in **{peak}**. Over the last 5 years, **{top_recent}** leads. "
                   f"World Bank trend is **{wb_trend}**. Average annual: {fmt(total_yr.mean())}.")

    # ─── TOP 25 PROJECTS (last 7 years) ───
    st.markdown("#### Largest 25 Projects (last 7 years)")
    top_base = data[(data["approval_year"].notna()) & (data["approval_year"] >= CY - 7)].copy()

    tf1, tf2 = st.columns([1, 1])
    with tf1:
        top_inst_options = ["All"] + sorted(top_base["institution"].unique())
        top_inst = st.selectbox("Filter by institution", top_inst_options, key="top_inst")
    with tf2:
        top_sec_options = ["All"] + sorted(top_base["sector"].unique())
        top_sec = st.selectbox("Filter by sector", top_sec_options, key="top_sec")

    if top_inst != "All":
        top_base = top_base[top_base["institution"] == top_inst]
    if top_sec != "All":
        top_base = top_base[top_base["sector"] == top_sec]

    top25 = top_base.nlargest(25, "amount_usd")[
        ["institution", "country", "title", "sector", "amount_usd", "approval_year", "instrument_type"]
    ].copy()
    top25["amount_usd"] = top25["amount_usd"].apply(lambda x: f"${x:,.0f}" if x > 0 else "—")
    top25["approval_year"] = top25["approval_year"].apply(lambda x: str(int(x)) if pd.notna(x) else "—")
    top25.columns = ["Institution", "Country", "Title", "Sector", "Amount (USD)", "Year", "Instrument"]
    st.dataframe(top25, use_container_width=True, height=400, hide_index=True)

    st.divider()

    # ─── INSTRUMENT TYPE ───
    st.markdown("#### Instrument Type Breakdown")
    st.caption("Instruments differ by institution — not directly comparable across institutions.")
    ic1, ic2 = st.columns([1, 1])
    with ic1:
        inst_sel = st.selectbox("Institution", ["All DFIs"] + sorted(data["institution"].unique()), key="instr_i")
    with ic2:
        p4 = st.radio("Period", ["All time", "Last 10 years", "Last 5 years", "Last 2 years"], horizontal=True, key="p4")

    d_instr = pfilter(data if inst_sel == "All DFIs" else data[data["institution"] == inst_sel], p4, yr_min)

    ic3, ic4 = st.columns(2)
    with ic3:
        idr = d_instr["instrument_type"].value_counts().reset_index()
        idr.columns = ["instrument", "count"]
        fig_i = px.pie(idr, names="instrument", values="count",
                       title=f"Instrument — {inst_sel} ({p4})", hole=0.4)
        fig_i.update_layout(height=300, margin=dict(l=10,r=10,t=40,b=10))
        fig_i.update_traces(textposition="outside", textinfo="label+percent")
        st.plotly_chart(fig_i, use_container_width=True)
    with ic4:
        ida = d_instr.groupby("instrument_type").agg(
            total_usd=("amount_usd", "sum"),
            count=("amount_usd", "size")
        ).sort_values("total_usd", ascending=True).reset_index()
        ida["mn"] = ida["total_usd"] / 1e6
        ida["label"] = ida.apply(lambda r: f"{r['instrument_type']} ({int(r['count'])})", axis=1)

        fig_ia = px.bar(ida, y="label", x="mn", orientation="h",
                        title=f"By Amount — {inst_sel} ({p4}, USD mn — count in parentheses)",
                        color_discrete_sequence=[color])
        fig_ia.update_layout(showlegend=False, yaxis_title="", xaxis_title="USD (mn)", height=300, margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(gcfg(fig_ia), use_container_width=True)

    # ─── UN AGENCIES (Sahel) ───
    if region == "Sahel":
        st.divider()
        un_data = data[data["institution"].isin(UN_LIST)]
        if len(un_data) > 0:
            st.markdown("#### UN Agencies & Operational Actors")
            st.caption("Programme budgets — not comparable with DFI loans/guarantees.")
            u1, u2 = st.columns(2)
            with u1:
                un_i = un_data.groupby("institution")["amount_usd"].sum().sort_values(ascending=True).reset_index()
                un_i["mn"] = un_i["amount_usd"] / 1e6
                fig_un = px.bar(un_i, y="institution", x="mn", orientation="h", color="institution",
                                color_discrete_map=INST_COLORS, title="UN Commitments (USD mn)")
                fig_un.update_layout(showlegend=False, yaxis_title="", xaxis_title="USD (mn)", height=280, margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(gcfg(fig_un), use_container_width=True)
            with u2:
                un_s = un_data.groupby("sector")["amount_usd"].sum().sort_values(ascending=True).tail(8).reset_index()
                un_s["mn"] = un_s["amount_usd"] / 1e6
                fig_us = px.bar(un_s, y="sector", x="mn", orientation="h",
                                title="UN — Top Sectors (USD mn)", color_discrete_sequence=["#0072BC"])
                fig_us.update_layout(showlegend=False, yaxis_title="", xaxis_title="USD (mn)", height=280, margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(gcfg(fig_us), use_container_width=True)

    st.divider()

    # ─── PROJECT LIST ───
    st.markdown("#### Project List")
    cols = ["project_id", "institution", "country", "title", "sector", "amount_usd",
            "approval_year", "status", "instrument_type", "public_private", "source_url"]
    tbl = data[cols].copy()
    tbl["amount_usd"] = tbl["amount_usd"].apply(lambda x: f"${x:,.0f}" if x > 0 else "—")
    tbl["approval_year"] = tbl["approval_year"].apply(lambda x: str(int(x)) if pd.notna(x) else "—")
    tbl["link"] = tbl.apply(lambda r: r["source_url"] if r["source_url"] and r["source_url"] != "" else "", axis=1)
    tbl["id"] = tbl["project_id"]
    tbl = tbl.drop(columns=["source_url", "project_id"])
    tbl.columns = ["Institution", "Country", "Title", "Sector", "Amount", "Year", "Status", "Instrument", "Pub/Priv", "Link", "ID"]
    tbl = tbl[["ID", "Institution", "Country", "Title", "Sector", "Amount", "Year", "Status", "Instrument", "Pub/Priv", "Link"]]
    st.dataframe(tbl, use_container_width=True, height=500, hide_index=True,
                 column_config={"Link": st.column_config.LinkColumn("Link", display_text="🔗", width=50)})

    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Download CSV", data.to_csv(index=False), f"dfo_{region.lower()}.csv", "text/csv")
    with c2:
        st.info("Charts: hover → 📷 → PNG")


def main():
    if not check_password():
        return
    df = load_data()
    page = st.session_state.get("page")
    if page == "readme": readme_page()
    elif page == "Serbia": dashboard(df, "Serbia")
    elif page == "Sahel": dashboard(df, "Sahel")
    else: home()

if __name__ == "__main__":
    main()
