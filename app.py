#!/usr/bin/env python3
"""
Development Donor Engagement Tracker — Interactive Dashboard
Serbia or Sahel. World Bank perspective. USD (year-specific ECB rates).
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Donor Engagement Tracker", page_icon="🏦", layout="wide", initial_sidebar_state="collapsed")

PASSWORD = os.environ.get("APP_PASSWORD", "donors26")
DATA_PATH = os.path.join(os.path.dirname(__file__), "data.csv")


def check_password():
    if "authenticated" in st.session_state and st.session_state["authenticated"]:
        return True
    st.markdown("<div style='text-align:center;padding:80px 0 20px'><h1 style='color:#1F4E79'>Development Donor Engagement Tracker</h1></div>", unsafe_allow_html=True)
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
WBG_LIST = ["World Bank", "IFC", "MIGA"]
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

DONOR_GROUPS = {
    "World Bank Group": ["World Bank", "IFC", "MIGA"],
    "UN Agencies": ["UNDP", "UNICEF", "WFP", "FAO"],
    "EBRD": ["EBRD"],
    "Chinese donors": ["Chinese donors"],
    "KfW": ["KfW"],
    "AFD": ["AFD"],
    "EIB": ["EIB"],
    "CEB": ["CEB"],
}
DONOR_GROUP_COLORS = {
    "World Bank Group": "#2D8659", "UN Agencies": "#0072BC", "EBRD": "#1F4E79",
    "Chinese donors": "#C41E3A", "KfW": "#0891B2", "AFD": "#BE185D",
    "EIB": "#E67E22", "CEB": "#8B4513",
}


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH).fillna("")
    df["amount_usd"] = pd.to_numeric(df["amount_usd"], errors="coerce").fillna(0)
    df["amount_eur"] = pd.to_numeric(df["amount_eur"], errors="coerce").fillna(0)
    df["approval_year"] = pd.to_numeric(df["approval_year"], errors="coerce")
    # Fill missing approval_year from approval_date (IFC/MIGA have dates but no year)
    mask = df["approval_year"].isna() & (df["approval_date"] != "")
    if mask.any():
        parsed = pd.to_datetime(df.loc[mask, "approval_date"], errors="coerce", dayfirst=False)
        df.loc[mask, "approval_year"] = parsed.dt.year
    df["sector"] = df["sector"].str.title()
    return df


def fmt(v):
    """Format amounts in billions."""
    if abs(v) >= 1e9: return f"${v/1e9:.1f}B"
    if abs(v) >= 1e8: return f"${v/1e9:.2f}B"
    if abs(v) >= 1e6: return f"${v/1e9:.3f}B"
    return f"${v:,.0f}"

def gcfg(fig):
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
    return fig

def pfilter(data, period, yr_min):
    cut = {"All time": yr_min, "Last 10 years": CY-10, "Last 5 years": CY-5, "Last 2 years": CY-2}[period]
    return data[(data["approval_year"].isna()) | (data["approval_year"] >= cut)]

def assign_donor_group(inst):
    for group, members in DONOR_GROUPS.items():
        if inst in members:
            return group
    return inst


def compute_facts(data, region):
    d5 = data[(data["approval_year"].isna()) | (data["approval_year"] >= CY - 5)]
    dfi5 = d5[d5["institution"].isin(DFI_LIST)]
    facts = []

    # WB Group share (WB + IFC + MIGA)
    wbg5 = dfi5[dfi5["institution"].isin(WBG_LIST)]
    if len(dfi5) > 0 and dfi5["amount_usd"].sum() > 0:
        wbg_share = wbg5["amount_usd"].sum() / dfi5["amount_usd"].sum() * 100
        facts.append(f"Over the last 5 years, **World Bank Group** (WB + IFC + MIGA) accounts for **{wbg_share:.0f}%** of DFI approvals ({fmt(wbg5['amount_usd'].sum())}, {len(wbg5)} projects).")

    # Largest non-WBG DFI
    non_wbg = dfi5[~dfi5["institution"].isin(WBG_LIST)].groupby("institution")["amount_usd"].sum()
    if len(non_wbg) > 0:
        top = non_wbg.idxmax()
        facts.append(f"**{top}** is the largest non-WBG development partner in the last 5 years ({fmt(non_wbg.max())}).")

    # Trend
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
    st.markdown("<div style='text-align:center;padding:30px 0'><h1 style='color:#1F4E79'>Development Donor Engagement Tracker</h1></div>", unsafe_allow_html=True)
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

**Note on Sahel DFI coverage:** Only **AFD** represents European bilateral DFIs in the Sahel dataset.
EBRD, EIB, KfW, and CEB do not have project-level data available for Mali, Niger, or Chad.

## Currency

All amounts in **USD** (billions). EUR converted using year-specific ECB annual average rates.
Chinese donors in constant 2021 USD.

## Public vs Private

**Public**: sovereign/govt borrower. **Private**: company/fund/FI borrower (mostly IFC/MIGA).

## Sources

CEB (Excel) · EIB (Excel) · EBRD (IATI) · WB (API) · IFC (Finances One) ·
MIGA (Finances One) · KfW (IATI/BMZ) · AFD (OpenDataSoft) ·
Chinese donors (AidData v3.0) · UNDP/UNICEF/WFP/FAO (IATI)
        """)

        # Source coverage table — computed from data
        st.markdown("## Source Coverage")
        st.caption("Earliest and latest approval year per institution, by region.")
        df_cov = load_data()
        df_cov = df_cov[df_cov["approval_year"].notna()]
        sahel_c = ["Mali", "Niger", "Chad"]
        rows = []
        for inst in sorted(df_cov["institution"].unique()):
            idf = df_cov[df_cov["institution"] == inst]
            # Serbia
            s = idf[idf["country"] == "Serbia"]
            s_range = f"{int(s['approval_year'].min())}–{int(s['approval_year'].max())}" if len(s) > 0 else "—"
            s_n = len(s) if len(s) > 0 else 0
            # Sahel
            h = idf[idf["country"].isin(sahel_c)]
            h_range = f"{int(h['approval_year'].min())}–{int(h['approval_year'].max())}" if len(h) > 0 else "—"
            h_n = len(h) if len(h) > 0 else 0
            rows.append({"Institution": inst, "Serbia (years)": s_range, "Serbia (#)": s_n,
                          "Sahel (years)": h_range, "Sahel (#)": h_n})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🇷🇸 SERBIA", use_container_width=True, type="primary"):
                st.session_state["page"] = "Serbia"; st.rerun()
        with c2:
            if st.button("🌍 SAHEL", use_container_width=True, type="primary"):
                st.session_state["page"] = "Sahel"; st.rerun()


def home():
    st.markdown("<div style='text-align:center;padding:60px 0 30px'><h1 style='color:#1F4E79;font-size:2.5em'>Development Donor Engagement Tracker</h1><p style='color:#666'>Cross-Regional Development Finance Analysis</p></div>", unsafe_allow_html=True)
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
    sahel_countries = ["Mali", "Niger", "Chad"]
    if region == "Serbia":
        data = df[df["country"] == "Serbia"].copy()
        label, color = "Serbia", "#1F4E79"
    else:
        data = df[df["country"].isin(sahel_countries)].copy()
        label, color = "Sahel (Mali · Niger · Chad)", "#E67E22"

    with st.sidebar:
        st.markdown(f"### {label}")
        st.markdown(f"**{len(data):,}** projects · **{fmt(data['amount_usd'].sum())}**")
        st.divider()
        if st.button("← Home"): del st.session_state["page"]; st.rerun()
        if st.button("📖 README"): st.session_state["page"] = "readme"; st.rerun()
        other = "Sahel" if region == "Serbia" else "Serbia"
        if st.button(f"→ {other}"): st.session_state["page"] = other; st.rerun()

    yr_min = int(data["approval_year"].dropna().min()) if len(data["approval_year"].dropna()) > 0 else 2000

    # Header
    st.markdown(f"<div style='background:{color};padding:15px 25px;border-radius:8px;margin-bottom:20px'><h2 style='color:white;margin:0'>Development Donor Engagement Tracker — {label}</h2><p style='color:rgba(255,255,255,.7);margin:5px 0 0'>{len(data):,} projects · {data['institution'].nunique()} institutions · {fmt(data['amount_usd'].sum())}</p></div>", unsafe_allow_html=True)

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
    if facts:
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
                val = cd["amount_usd"].sum(); display = fmt(val); size = max(val / 1e8, 5)
            elif map_indicator == "Number of projects":
                val = len(cd); display = str(val); size = max(val / 5, 5)
            elif map_indicator == "WB commitments (USD)":
                val = cd[cd["institution"] == "World Bank"]["amount_usd"].sum(); display = fmt(val); size = max(val / 1e8, 5)
            elif map_indicator == "DFI count":
                val = cd[cd["institution"].isin(DFI_LIST)]["institution"].nunique(); display = str(val); size = val * 15
            elif map_indicator == "Public share (%)":
                val = (cd["public_private"] == "public").sum() / max(len(cd), 1) * 100; display = f"{val:.0f}%"; size = val / 2
            else:
                if len(cd) > 0: ts = cd.groupby("sector")["amount_usd"].sum().idxmax(); display = ts.title()
                else: display = "N/A"
                size = 20; val = 0
            map_data.append({"country": country, "lat": coords[0], "lon": coords[1], "value": display, "size": max(size, 3)})

        map_df = pd.DataFrame(map_data)
        fig_map = px.scatter_mapbox(map_df, lat="lat", lon="lon", size="size",
            hover_name="country", hover_data={"value": True, "size": False, "lat": False, "lon": False},
            color_discrete_sequence=[color], title=f"{map_indicator} by Country",
            zoom=3, center={"lat": 16, "lon": 8})
        fig_map.update_layout(mapbox_style="carto-positron", height=400, margin=dict(l=0, r=0, t=40, b=0))
        fig_map.add_trace(go.Scattermapbox(
            lat=[d["lat"] for d in map_data], lon=[d["lon"] for d in map_data], mode="text",
            text=[f"{d['country']}: {d['value']}" for d in map_data],
            textfont=dict(size=14, color="black"), showlegend=False))
        st.plotly_chart(fig_map, use_container_width=True)

    st.divider()

    # ─── COMMITMENTS BY INSTITUTION ───
    st.markdown("#### Commitments by Institution")
    ci_c1, ci_c2 = st.columns([1, 1])
    with ci_c1:
        ci_period = st.radio("Period", ["All time", "Last 10 years", "Last 5 years", "Last 2 years"], horizontal=True, key="ci_p")
    with ci_c2:
        if region == "Sahel":
            ci_country = st.selectbox("Country", ["All countries"] + sorted(data["country"].unique()), key="ci_country")
        else:
            ci_country = "All countries"

    d_ci = pfilter(data, ci_period, yr_min)
    if ci_country != "All countries":
        d_ci = d_ci[d_ci["country"] == ci_country]

    col_ci1, col_ci2 = st.columns([1, 2])
    with col_ci1:
        d_ci_g = d_ci.copy()
        d_ci_g["donor_group"] = d_ci_g["institution"].apply(assign_donor_group)
        idata = d_ci_g.groupby("donor_group")["amount_usd"].sum().sort_values(ascending=True).reset_index()
        idata["bn"] = idata["amount_usd"] / 1e9
        fig = px.bar(idata, y="donor_group", x="bn", orientation="h", color="donor_group",
                     color_discrete_map=DONOR_GROUP_COLORS,
                     title=f"By Donor Group ({ci_period})")
        fig.update_layout(showlegend=False, yaxis_title="", xaxis_title="USD (billions)", height=350,
                         margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(gcfg(fig), use_container_width=True)

    with col_ci2:
        if region == "Sahel":
            cross = d_ci.copy()
            cross["donor_group"] = cross["institution"].apply(assign_donor_group)
            cross = cross.groupby(["country", "donor_group"])["amount_usd"].sum().reset_index()
            group_totals = cross.groupby("donor_group")["amount_usd"].sum().sort_values(ascending=False)
            total = group_totals.sum()
            top_groups = group_totals[group_totals / max(total, 1) >= 0.01].index.tolist()
            cross = cross[cross["donor_group"].isin(top_groups)]
            cross["bn"] = cross["amount_usd"] / 1e9
            fig2 = px.bar(cross, x="country", y="bn", color="donor_group",
                          color_discrete_map=DONOR_GROUP_COLORS,
                          title=f"Main Contributors by Country ({ci_period})",
                          barmode="stack")
            fig2.update_layout(xaxis_title="", yaxis_title="USD (billions)", height=350,
                              margin=dict(l=10,r=10,t=40,b=10),
                              legend=dict(orientation="h", yanchor="bottom", y=-0.25, font=dict(size=10)))
        else:
            sdata = d_ci.groupby("sector")["amount_usd"].sum().sort_values(ascending=True).tail(10).reset_index()
            sdata["bn"] = sdata["amount_usd"] / 1e9
            fig2 = px.bar(sdata, y="sector", x="bn", orientation="h",
                          title=f"Top 10 Sectors ({ci_period})", color_discrete_sequence=[color])
            fig2.update_layout(showlegend=False, yaxis_title="", xaxis_title="USD (billions)", height=350,
                              margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(gcfg(fig2), use_container_width=True)

    # ─── TOP 10 SECTORS ───
    if region == "Sahel":
        st.divider()
        st.markdown("#### Top 10 Sectors")
        sc1, sc2, sc3 = st.columns([1, 1, 1])
        with sc1:
            sec_period = st.radio("Period", ["Last 5 years", "All time", "Last 10 years", "Last 2 years"],
                                  horizontal=True, key="sec_p")
        with sc2:
            sec_stack = st.radio("Stack by", ["None", "Country", "Donor group"], horizontal=True, key="sec_stack")
        with sc3:
            sec_country = st.selectbox("Country", ["All countries"] + sorted(data["country"].unique()), key="sec_country")

        d_sec = pfilter(data, sec_period, yr_min)
        if sec_country != "All countries":
            d_sec = d_sec[d_sec["country"] == sec_country]

        # Always compute sector totals for ordering
        sector_totals = d_sec.groupby("sector")["amount_usd"].sum().nlargest(10)
        top_sectors = sector_totals.index.tolist()
        # Order: largest at top (ascending for horizontal bar = largest at bottom visually → reverse)
        sector_order = sector_totals.sort_values(ascending=True).index.tolist()
        sdata_base = d_sec[d_sec["sector"].isin(top_sectors)]

        if sec_stack == "Country":
            sec_agg = sdata_base.groupby(["sector", "country"])["amount_usd"].sum().reset_index()
            sec_agg["bn"] = sec_agg["amount_usd"] / 1e9
            fig_s = px.bar(sec_agg, y="sector", x="bn", color="country", orientation="h",
                           color_discrete_map=COUNTRY_COLORS,
                           category_orders={"sector": sector_order},
                           title=f"Top 10 Sectors by Country ({sec_period})", barmode="stack")
            fig_s.update_layout(yaxis_title="", xaxis_title="USD (billions)", height=420,
                               margin=dict(l=10,r=10,t=40,b=10),
                               legend=dict(orientation="h", yanchor="bottom", y=-0.15))
        elif sec_stack == "Donor group":
            sdata_base = sdata_base.copy()
            sdata_base["donor_group"] = sdata_base["institution"].apply(assign_donor_group)
            sec_agg = sdata_base.groupby(["sector", "donor_group"])["amount_usd"].sum().reset_index()
            sec_agg["bn"] = sec_agg["amount_usd"] / 1e9
            fig_s = px.bar(sec_agg, y="sector", x="bn", color="donor_group", orientation="h",
                           color_discrete_map=DONOR_GROUP_COLORS,
                           category_orders={"sector": sector_order},
                           title=f"Top 10 Sectors by Donor Group ({sec_period})", barmode="stack")
            fig_s.update_layout(yaxis_title="", xaxis_title="USD (billions)", height=420,
                               margin=dict(l=10,r=10,t=40,b=10),
                               legend=dict(orientation="h", yanchor="bottom", y=-0.15))
        else:
            sec_agg = sdata_base.groupby("sector")["amount_usd"].sum().reset_index()
            sec_agg["bn"] = sec_agg["amount_usd"] / 1e9
            fig_s = px.bar(sec_agg, y="sector", x="bn", orientation="h",
                           category_orders={"sector": sector_order},
                           title=f"Top 10 Sectors ({sec_period})", color_discrete_sequence=[color])
            fig_s.update_layout(showlegend=False, yaxis_title="", xaxis_title="USD (billions)", height=420,
                               margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(gcfg(fig_s), use_container_width=True)

    st.divider()

    # ─── SANKEY: INSTITUTION → SECTOR ───
    st.markdown("#### Fund Flows: Institution → Sector")
    sk_c1, sk_c2 = st.columns([1, 1])
    with sk_c1:
        sk_period = st.radio("Period", ["All time", "Last 10 years", "Last 5 years", "Last 2 years"],
                             horizontal=True, key="sk_p")
    with sk_c2:
        if region == "Sahel":
            sk_countries = sorted(data["country"].unique())
        else:
            sk_countries = ["Serbia"]
        sk_country = st.selectbox("Country", sk_countries, key="sk_country")

    d_sk = pfilter(data, sk_period, yr_min)
    d_sk = d_sk[d_sk["country"] == sk_country]
    d_sk = d_sk[d_sk["amount_usd"] > 0]

    if len(d_sk) > 0:
        # Aggregate flows
        flows = d_sk.groupby(["institution", "sector"])["amount_usd"].sum().reset_index()
        flows = flows[flows["amount_usd"] > 0].sort_values("amount_usd", ascending=False)
        # Keep top 10 sectors to avoid clutter
        top_secs = flows.groupby("sector")["amount_usd"].sum().nlargest(10).index.tolist()
        flows = flows[flows["sector"].isin(top_secs)]

        institutions = sorted(flows["institution"].unique())
        sectors = sorted(flows["sector"].unique())
        all_labels = institutions + sectors
        inst_idx = {name: i for i, name in enumerate(institutions)}
        sec_idx = {name: i + len(institutions) for i, name in enumerate(sectors)}

        sources = [inst_idx[r["institution"]] for _, r in flows.iterrows()]
        targets = [sec_idx[r["sector"]] for _, r in flows.iterrows()]
        values = [r["amount_usd"] / 1e6 for _, r in flows.iterrows()]

        # Colors: institutions get their branded color, sectors get gray
        def hex_to_rgba(h, a=0.4):
            h = h.lstrip("#")
            if len(h) == 3: h = "".join(c*2 for c in h)
            return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"

        node_colors = [INST_COLORS.get(i, "#999") for i in institutions] + ["#B0BEC5"] * len(sectors)
        link_colors = [hex_to_rgba(INST_COLORS.get(institutions[s], "#cccccc")) for s in sources]

        fig_sk = go.Figure(go.Sankey(
            node=dict(pad=15, thickness=20, label=all_labels, color=node_colors),
            link=dict(source=sources, target=targets, value=values, color=link_colors)))
        fig_sk.update_layout(
            title=f"Fund Flows — {sk_country} ({sk_period})",
            height=500, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_sk, use_container_width=True)
        st.caption("Amounts in USD millions. Top 10 sectors shown.")
    else:
        st.info("No data for this selection.")

    st.divider()

    # ─── PUBLIC vs PRIVATE ───
    st.markdown("#### Public vs Private")
    pp_c1, pp_c2, pp_c3 = st.columns([1, 1, 1])
    with pp_c1:
        pp_period = st.radio("Period", ["All time", "Last 10 years", "Last 5 years", "Last 2 years"],
                             horizontal=True, key="pp_p")
    with pp_c2:
        if region == "Sahel":
            pp_country = st.selectbox("Country", ["All countries"] + sorted(data["country"].unique()), key="pp_country")
        else:
            pp_country = "All countries"
    with pp_c3:
        all_groups = sorted(data.copy().assign(dg=data["institution"].apply(assign_donor_group))["dg"].unique())
        pp_donor = st.selectbox("Donor group", ["All donors"] + all_groups, key="pp_donor")

    d_pp = pfilter(data, pp_period, yr_min)
    if pp_country != "All countries":
        d_pp = d_pp[d_pp["country"] == pp_country]
    if pp_donor != "All donors":
        members = DONOR_GROUPS.get(pp_donor, [pp_donor])
        d_pp = d_pp[d_pp["institution"].isin(members)]

    if region == "Sahel" and pp_country == "All countries":
        countries_in_data = sorted(d_pp["country"].unique())
        if countries_in_data:
            cols_pp = st.columns(len(countries_in_data))
            for idx, country in enumerate(countries_in_data):
                with cols_pp[idx]:
                    cd = d_pp[d_pp["country"] == country]
                    ppd = cd.groupby("public_private")["amount_usd"].sum().reset_index()
                    ppd["bn"] = ppd["amount_usd"] / 1e9
                    fig_pp = px.pie(ppd, names="public_private", values="bn",
                                    title=f"{country} ({pp_period})",
                                    hole=0.4, color_discrete_sequence=["#1F4E79", "#D97706"])
                    fig_pp.update_layout(height=300, margin=dict(l=10,r=10,t=40,b=10))
                    fig_pp.update_traces(textposition="outside", textinfo="label+percent")
                    st.plotly_chart(fig_pp, use_container_width=True)
    else:
        pp1_col, pp2_col = st.columns(2)
        title_suffix = f" — {pp_country}" if pp_country != "All countries" else ""
        with pp1_col:
            ppd = d_pp.groupby("public_private")["amount_usd"].sum().reset_index()
            ppd["bn"] = ppd["amount_usd"] / 1e9
            fig_pp = px.pie(ppd, names="public_private", values="bn",
                            title=f"By Amount ({pp_period}){title_suffix}",
                            hole=0.4, color_discrete_sequence=["#1F4E79", "#D97706"])
            fig_pp.update_layout(height=300, margin=dict(l=10,r=10,t=40,b=10))
            fig_pp.update_traces(textposition="outside", textinfo="label+percent")
            st.plotly_chart(fig_pp, use_container_width=True)
        with pp2_col:
            ppc = d_pp["public_private"].value_counts().reset_index()
            ppc.columns = ["type", "count"]
            fig_ppc = px.pie(ppc, names="type", values="count",
                             title=f"By Count ({pp_period}){title_suffix}",
                             hole=0.4, color_discrete_sequence=["#1F4E79", "#D97706"])
            fig_ppc.update_layout(height=300, margin=dict(l=10,r=10,t=40,b=10))
            fig_ppc.update_traces(textposition="outside", textinfo="label+percent")
            st.plotly_chart(fig_ppc, use_container_width=True)


    st.divider()

    # ─── APPROVALS OVER TIME (last 25 years) ───
    st.markdown("#### Approvals Over Time (last 25 years)")
    aot_c1, aot_c2, aot_c3 = st.columns(3)
    with aot_c1:
        if region == "Sahel":
            aot_country = st.selectbox("Country", ["All countries"] + sorted(data["country"].unique()), key="aot_country")
        else:
            aot_country = "All countries"
    with aot_c2:
        all_groups_aot = sorted(data.copy().assign(dg=data["institution"].apply(assign_donor_group))["dg"].unique())
        aot_group = st.selectbox("Donor group", ["All donor groups"] + all_groups_aot, key="aot_group")
    with aot_c3:
        if aot_group != "All donor groups":
            members_aot = DONOR_GROUPS.get(aot_group, [aot_group])
            possible_inst = sorted(data[data["institution"].isin(members_aot)]["institution"].unique())
        else:
            possible_inst = sorted(data["institution"].unique())
        aot_inst = st.selectbox("Institution", ["All institutions"] + possible_inst, key="aot_inst")

    timeline = data[data["approval_year"].notna()].copy()
    timeline = timeline[timeline["approval_year"] >= CY - 25]
    if aot_country != "All countries":
        timeline = timeline[timeline["country"] == aot_country]
    if aot_group != "All donor groups":
        members_aot = DONOR_GROUPS.get(aot_group, [aot_group])
        timeline = timeline[timeline["institution"].isin(members_aot)]
    if aot_inst != "All institutions":
        timeline = timeline[timeline["institution"] == aot_inst]

    timeline["year"] = timeline["approval_year"].astype(int)
    tl = timeline.groupby(["year", "institution"])["amount_usd"].sum().reset_index()
    tl["bn"] = tl["amount_usd"] / 1e9

    filter_desc = []
    if aot_country != "All countries": filter_desc.append(aot_country)
    if aot_group != "All donor groups": filter_desc.append(aot_group)
    if aot_inst != "All institutions": filter_desc.append(aot_inst)
    title_suffix = f" — {', '.join(filter_desc)}" if filter_desc else ""

    fig_tl = px.bar(tl, x="year", y="bn", color="institution", color_discrete_map=INST_COLORS,
                    title=f"Approved Commitments (USD bn, stacked){title_suffix}", barmode="stack")
    for inst in sorted(timeline["institution"].unique()):
        inst_yr = timeline[timeline["institution"] == inst].groupby("year")["amount_usd"].sum().reset_index()
        if len(inst_yr) > 2:
            x, y = inst_yr["year"].values, inst_yr["amount_usd"].values / 1e9
            z = np.polyfit(x, y, 1)
            fig_tl.add_trace(go.Scatter(
                x=x, y=np.poly1d(z)(x), mode="lines", name=f"{inst} trend",
                line=dict(color=INST_COLORS.get(inst, "#999"), width=1.5, dash="dot"),
                opacity=0.35, showlegend=False))
    fig_tl.update_layout(xaxis_title="Year", yaxis_title="USD (billions)", height=450,
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
        st.caption(f"Approvals peaked in **{peak}**. Last 5 years leader: **{top_recent}**. "
                   f"WB trend: **{wb_trend}**. Avg annual: {fmt(total_yr.mean())}.")

    # ─── YEAR-OVER-YEAR GROWTH ───
    if len(total_yr) > 2:
        yoy = total_yr.sort_index()
        yoy_pct = yoy.pct_change() * 100
        yoy_df = pd.DataFrame({"year": yoy_pct.index.astype(int), "yoy_pct": yoy_pct.values,
                                "amount": yoy.values / 1e9}).dropna()
        yoy_df["color"] = yoy_df["yoy_pct"].apply(lambda x: "#2D8659" if x >= 0 else "#C41E3A")
        yoy_df["label"] = yoy_df["yoy_pct"].apply(lambda x: f"+{x:.0f}%" if x >= 0 else f"{x:.0f}%")

        fig_yoy = go.Figure()
        fig_yoy.add_trace(go.Bar(
            x=yoy_df["year"], y=yoy_df["yoy_pct"],
            marker_color=yoy_df["color"].tolist(),
            text=yoy_df["label"], textposition="outside", textfont=dict(size=10),
            hovertemplate="Year: %{x}<br>YoY: %{y:.1f}%<br>Volume: $%{customdata:.2f}B<extra></extra>",
            customdata=yoy_df["amount"]))
        fig_yoy.add_hline(y=0, line_width=1, line_color="gray")
        # 3-year rolling average
        if len(yoy_df) >= 3:
            roll = yoy_df.set_index("year")["yoy_pct"].rolling(3, center=True).mean().dropna()
            fig_yoy.add_trace(go.Scatter(
                x=roll.index, y=roll.values, mode="lines",
                line=dict(color="#1F4E79", width=2, dash="dash"),
                name="3-yr rolling avg", hovertemplate="%{y:.1f}%<extra>3yr avg</extra>"))
        fig_yoy.update_layout(
            title=f"Year-over-Year Growth in Approvals (%){title_suffix}",
            xaxis_title="Year", yaxis_title="YoY Change (%)", height=350,
            margin=dict(l=10, r=10, t=40, b=10), showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.25))
        st.plotly_chart(gcfg(fig_yoy), use_container_width=True)

    # ─── TOP 25 PROJECTS (last 7 years) ───
    st.divider()
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
    top25["amount_usd"] = top25["amount_usd"].apply(lambda x: f"${x/1e6:.1f}M" if x > 0 else "—")
    top25["approval_year"] = top25["approval_year"].apply(lambda x: str(int(x)) if pd.notna(x) else "—")
    top25.columns = ["Institution", "Country", "Title", "Sector", "Amount (USD)", "Year", "Instrument"]
    st.dataframe(top25, use_container_width=True, height=400, hide_index=True)

    # ─── UN AGENCIES (Sahel) ───
    if region == "Sahel":
        st.divider()
        un_data = data[data["institution"].isin(UN_LIST)]
        if len(un_data) > 0:
            st.markdown("#### UN Agencies")
            st.caption("Programme budgets — not comparable with DFI loans/guarantees.")

            un_country = st.selectbox("Country", ["All countries"] + sorted(un_data["country"].unique()), key="un_country")
            un_filtered = un_data if un_country == "All countries" else un_data[un_data["country"] == un_country]
            un_suffix = f" — {un_country}" if un_country != "All countries" else ""

            # UN Commitments bar
            un_i = un_filtered.groupby("institution")["amount_usd"].sum().sort_values(ascending=True).reset_index()
            un_i["bn"] = un_i["amount_usd"] / 1e9
            fig_un = px.bar(un_i, y="institution", x="bn", orientation="h", color="institution",
                            color_discrete_map=INST_COLORS,
                            title=f"UN Commitments (USD bn){un_suffix}")
            fig_un.update_layout(showlegend=False, yaxis_title="", xaxis_title="USD (billions)", height=280,
                                margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(gcfg(fig_un), use_container_width=True)

            # Line chart: UN top sectors over last 10 years — FULL WIDTH below
            un_10 = un_filtered[un_filtered["approval_year"].notna()].copy()
            un_10 = un_10[un_10["approval_year"] >= CY - 10]
            un_10["year"] = un_10["approval_year"].astype(int)
            top_un_sectors = un_10.groupby("sector")["amount_usd"].sum().nlargest(6).index.tolist()
            un_10_top = un_10[un_10["sector"].isin(top_un_sectors)]
            un_sec_yr = un_10_top.groupby(["year", "sector"])["amount_usd"].sum().reset_index()
            un_sec_yr["bn"] = un_sec_yr["amount_usd"] / 1e9
            fig_us = px.line(un_sec_yr, x="year", y="bn", color="sector",
                             title=f"UN — Top Sectors over Time (last 10 years){un_suffix}",
                             markers=True)
            fig_us.update_layout(yaxis_title="USD (billions)", xaxis_title="Year", height=450,
                                margin=dict(l=10,r=10,t=40,b=60),
                                legend=dict(orientation="h", yanchor="top", y=-0.15, font=dict(size=11)),
                                xaxis=dict(dtick=1, tickangle=0))
            st.plotly_chart(gcfg(fig_us), use_container_width=True)

            # ─── UN HEATMAP (active projects only) ───
            st.markdown("##### Active Projects Heatmap")
            un_active = un_filtered[un_filtered["status"].isin(["Active", "Exécution"])]
            if len(un_active) > 0:
                heat = un_active.groupby(["institution", "sector"]).size().reset_index(name="count")
                heat_pivot = heat.pivot_table(index="sector", columns="institution", values="count", fill_value=0)
                heat_pivot["_total"] = heat_pivot.sum(axis=1)
                heat_pivot = heat_pivot.nlargest(12, "_total").drop(columns=["_total"])
                fig_heat = px.imshow(heat_pivot,
                                     labels=dict(x="Agency", y="Sector", color="Projects"),
                                     title=f"Active UN Projects — Agency × Sector{un_suffix}",
                                     color_continuous_scale="Blues", text_auto=True, aspect="auto")
                fig_heat.update_layout(height=450, margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.info("No active UN projects in current selection.")

    st.divider()

    # ─── PROJECT LIST ───
    st.markdown("#### Project List")
    search_q = st.text_input("Search projects (title, description, institution, sector)", key="proj_search", placeholder="e.g. energy, EBRD, railway...")
    cols = ["project_id", "institution", "country", "title", "sector", "amount_usd",
            "approval_year", "status", "instrument_type", "public_private", "source_url"]
    tbl = data[cols].copy()
    if search_q:
        q = search_q.lower()
        mask = (data["title"].str.lower().str.contains(q, na=False) |
                data["description"].str.lower().str.contains(q, na=False) |
                data["institution"].str.lower().str.contains(q, na=False) |
                data["sector"].str.lower().str.contains(q, na=False))
        tbl = tbl[mask.values]
        st.caption(f"{len(tbl)} projects matching \"{search_q}\"")
    tbl["amount_usd"] = tbl["amount_usd"].apply(lambda x: f"${x/1e6:.1f}M" if x > 0 else "—")
    tbl["approval_year"] = tbl["approval_year"].apply(lambda x: str(int(x)) if pd.notna(x) else "—")
    tbl["link"] = tbl.apply(lambda r: r["source_url"] if r["source_url"] and r["source_url"] != "" else "", axis=1)
    tbl["id"] = tbl["project_id"]
    tbl = tbl.drop(columns=["source_url", "project_id"])
    tbl.columns = ["Institution", "Country", "Title", "Sector", "Amount", "Year", "Status", "Instrument", "Pub/Priv", "Link", "ID"]
    tbl = tbl[["ID", "Institution", "Country", "Title", "Sector", "Amount", "Year", "Status", "Instrument", "Pub/Priv", "Link"]]
    st.dataframe(tbl, use_container_width=True, height=500, hide_index=True,
                 column_config={"Link": st.column_config.LinkColumn("Link", display_text="🔗", width=50)})

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button("Download CSV", data.to_csv(index=False), f"dfo_{region.lower()}.csv", "text/csv")
    with dl2:
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
