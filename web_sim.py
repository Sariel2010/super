#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit Web App — Superannuation Learning Simulator (Australia)
Educational, plain‑language version with:
• Why super matters
• Rights & responsibilities (AU)
• Costs vs benefits
• Calculator with charts (matplotlib)
• Quizzes
• AU quick reference & sources
 
Disclaimer: Educational only, not financial advice. Rules change over time.
"""
 
import datetime as dt
from textwrap import dedent
 
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
 
# -----------------------------
# App settings
# -----------------------------
st.set_page_config(
    page_title="Superannuation Learning Simulator (AU)",
    page_icon="💼",
    layout="wide"
)
 
# -----------------------------
# AU rules snapshot (educational)
# -----------------------------
AU_RULES = {
    # SG schedule: 11.5% through 30 Jun 2025; 12% from 1 Jul 2025 onwards.
    "sg_schedule": [
        (dt.date(2024, 7, 1), dt.date(2025, 6, 30), 0.115),
        (dt.date(2025, 7, 1), dt.date(2100, 6, 30), 0.120),
    ],
    "under18_rule": "Under 18? SG is generally payable only in weeks you work > 30 hours.",
    "quarter_due_dates": "Quarterly due dates (until Payday Super starts): 28 Oct, 28 Jan, 28 Apr, 28 Jul.",
    # Contribution caps from 1 Jul 2024 (general caps snapshot)
    "caps": {
        "concessional": 30_000,        # before-tax cap (includes SG + salary sacrifice + personal deductible)
        "non_concessional": 120_000,   # after-tax cap
        "bring_forward_max": 360_000,  # if eligible
    },
    "division293_threshold": 250_000,  # income + concessional contributions (simplified)
    "contributions_tax": 0.15,         # base contributions tax on concessional contributions (inside fund)
    "payday_super_note": "From 1 Jul 2026 (planned), SG moves to payday frequency (not quarterly).",
    "preservation_age_note": "Preservation age is 60 for DOB on/after 1 Jul 1964; access also at 65 or on retirement after preservation age."
}
 
# -----------------------------
# Session defaults
# -----------------------------
if "name" not in st.session_state:
    st.session_state.name = "Friend"
if "quiz_state" not in st.session_state:
    st.session_state.quiz_state = {"why": {}, "rights": {}, "costs": {}}
 
# -----------------------------
# Helpers
# -----------------------------
def money(x: float) -> str:
    return f"${x:,.2f}"
 
def current_sg_rate(on_date: dt.date) -> float:
    for start, end, rate in AU_RULES["sg_schedule"]:
        if start <= on_date <= end:
            return rate
    return AU_RULES["sg_schedule"][-1][2]
 
def calc_concessional_components(salary: float,
                                 extra_rate: float,
                                 sg_rate: float,
                                 div293_threshold: float,
                                 base_ctax: float):
    """
    Returns: employer, extra, concessional_total, base_contrib_tax, div293_extra (estimate)
    Division 293 (simplified): if (salary + concessional) > threshold,
    add extra 15% to min(concessional, amount over threshold).
    """
    employer = salary * sg_rate
    extra = salary * extra_rate
    concessional = employer + extra
    base = concessional * base_ctax
    over = max(0.0, (salary + concessional) - div293_threshold)
    div293 = min(concessional, over) * 0.15
    return employer, extra, concessional, base, div293
 
def simulate_growth(balance_start: float,
                    salary: float,
                    extra_rate: float,
                    years: int,
                    return_rate: float,
                    fees_flat: float,
                    fees_pct: float,
                    inflation: float,
                    start_date: dt.date):
    """
    Yearly records with: start, net_contrib, growth, fees, end, end_real, contrib_tax, div293, etc.
    """
    records = []
    balance = balance_start
    for yr in range(1, years + 1):
        year_date = start_date + dt.timedelta(days=365 * (yr - 1))
        sg_rate = current_sg_rate(year_date)
 
        emp, extra, concessional, base_tax, div293 = calc_concessional_components(
            salary=salary,
            extra_rate=extra_rate,
            sg_rate=sg_rate,
            div293_threshold=AU_RULES["division293_threshold"],
            base_ctax=AU_RULES["contributions_tax"]
        )
 
        net_contrib = concessional - (base_tax + div293)
        effective_base = balance + net_contrib * 0.5   # approx mid‑year growth
        growth = effective_base * return_rate
 
        tentative = balance + net_contrib + growth
        fees = fees_flat + tentative * fees_pct
        end = tentative - fees
        end_real = end / ((1 + inflation) ** yr)
 
        records.append({
            "Year": yr,
            "SG rate": round(sg_rate * 100, 2),
            "Start balance": round(balance, 2),
            "Employer (SG)": round(emp, 2),
            "Your extra": round(extra, 2),
            "Concessional total": round(concessional, 2),
            "Contributions tax (incl Div293)": round(base_tax + div293, 2),
            "Div293 (est)": round(div293, 2),
            "Net contributions": round(net_contrib, 2),
            "Growth (before fees)": round(growth, 2),
            "Fees": round(fees, 2),
            "End balance": round(end, 2),
            "End (today’s $)": round(end_real, 2),
        })
        balance = end
    return records
 
def df_from_records(records):
    return pd.DataFrame(records)
 
def plot_projection(records):
    years = [r["Year"] for r in records]
    end = [r["End balance"] for r in records]
    end_real = [r["End (today’s $)"] for r in records]
    contribs = [r["Net contributions"] for r in records]
    growth = [r["Growth (before fees)"] for r in records]
    fees = [r["Fees"] for r in records]
 
    figs = {}
 
    # 1) Line chart: nominal vs real
    fig1, ax1 = plt.subplots(figsize=(8.5, 4.8))
    ax1.plot(years, end, label="Balance (nominal)", linewidth=2.2)
    ax1.plot(years, end_real, label="Balance (today’s $)", linewidth=2.2, linestyle="--")
    ax1.set_title("Projected Super Balance Over Time")
    ax1.set_xlabel("Years from start"); ax1.set_ylabel("Balance ($)")
    ax1.grid(alpha=0.25); ax1.legend()
    figs["line"] = fig1
 
    # 2) Stacked bars by decade
    def chunk_sum(lst, chunk=10):
        return [round(sum(lst[i:i+chunk]), 2) for i in range(0, len(lst), chunk)]
    decade_labels = [f"Y{1+i*10}–{min((i+1)*10, len(years))}" for i in range((len(years)+9)//10)]
    contrib_dec = chunk_sum(contribs)
    growth_dec = chunk_sum(growth)
    fees_dec = chunk_sum(fees)
 
    fig2, ax2 = plt.subplots(figsize=(8.5, 4.8))
    x = range(len(decade_labels)); width = 0.55
    ax2.bar(x, contrib_dec, width=width, label="Net contributions")
    ax2.bar(x, growth_dec, width=width, bottom=contrib_dec, label="Investment growth")
    bottom2 = [c + g for c, g in zip(contrib_dec, growth_dec)]
    ax2.bar(x, [-f for f in fees_dec], width=width, bottom=bottom2, label="Fees (negative)", color="#d62728")
    ax2.set_xticks(list(x), decade_labels)
    ax2.set_title("Contributions, Growth, and Fees by Decade")
    ax2.set_ylabel("Dollars ($)"); ax2.grid(axis="y", alpha=0.25); ax2.legend()
    figs["stacked"] = fig2
 
    # 3) Pie breakdown
    total_contrib = round(sum(contribs), 2)
    total_growth = round(sum(growth), 2)
    total_fees = round(sum(fees), 2)
 
    fig3, ax3 = plt.subplots(figsize=(5.5, 5.5))
    vals = [max(total_contrib, 0), max(total_growth, 0), max(total_fees, 0)]
    labels = ["Net contributions", "Investment growth", "Fees"]
    colors = ["#1f77b4", "#2ca02c", "#d62728"]
    ax3.pie(
        vals,
        labels=[f"{labels[i]}: {money(vals[i])}" for i in range(3)],
        autopct="%1.1f%%", startangle=140, colors=colors,
        wedgeprops={"linewidth": 1, "edgecolor": "white"}
    )
    ax3.set_title("End Result Breakdown")
    figs["pie"] = fig3
 
    return figs
 
# -----------------------------
# UI sections
# -----------------------------
def page_welcome():
    st.title("💼 Superannuation Learning Simulator (Australia)")
    st.caption("Educational only — not financial advice. Rules change, always check official sources.")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(dedent(f"""
        **Hi {st.session_state.name}!** 
        This web app helps you learn:
        - Why superannuation matters for young people 
        - Your basic rights & responsibilities in Australia 
        - Costs vs benefits 
        - A hands‑on calculator with charts 
        - Quick quizzes 
        - An Australia quick‑reference & sources
        """))
        st.text_input("First name (optional)", key="name")
    with col2:
        st.info("Tip: Use the navigation in the left sidebar to jump between sections.")
 
def page_why_super_matters():
    st.header("Why Superannuation Matters (Especially When You Start Young)")
    st.markdown(dedent("""
    - **It’s your money for future you** — invested over many years. 
    - **Time is your superpower**: compounding needs years to snowball. 
    - **Employer contributions** add extra money on top of your pay. 
    - **Small, steady amounts** now can become a much bigger balance later. 
    """))
 
def page_rights_responsibilities():
    st.header("Rights & Responsibilities in Australia (Plain Language)")
    sg_now = current_sg_rate(dt.date.today()) * 100
    st.markdown(dedent(f"""
    **Your rights**
    - Receive employer super at the **SG rate** (currently **{sg_now:.1f}%** — see sources). 
    - Choose your own fund; if you don’t, your employer must use your **stapled fund**. 
    - See clear info from your fund: balance, fees, options, performance. 
    - Combine extra accounts to reduce duplicate fees.
 
    **Your responsibilities**
    - Provide your fund details (or TFN) to your employer. 
    - Check contributions arrive on time; keep your contact details updated. 
    - Compare fees and long‑term performance; pick an investment option that suits your risk level. 
    - Know the **contribution caps** if you put in extra.
 
    **Employers (simple)**
    - Must pay SG for eligible workers **on time** (quarterly until Payday Super starts). 
    - Must request **stapled fund** details if you don’t make a choice. 
    """))
 
def page_costs_vs_benefits():
    st.header("Costs vs Benefits of Super")
    st.subheader("Benefits")
    st.markdown("- Long‑term **investment growth**")
    st.markdown("- Possible **tax advantages** (subject to rules)")
    st.markdown("- **Employer SG** boosts your savings")
    st.markdown("- Optional **insurance** through your fund")
    st.subheader("Costs")
    st.markdown("- **Account/investment fees**")
    st.markdown("- **Insurance premiums** (if applicable)")
    st.markdown("- **Switching/transaction costs** in some options")
    st.info("Takeaway: lower fees + suitable, long‑term performance make a big difference.")
 
def page_calculator():
    st.header("Super Growth Calculator — with Charts")
    st.caption("Adjust inputs on the left. Numbers are approximate and simplified for learning.")
    with st.sidebar:
        st.subheader("Inputs")
        salary = st.number_input("Annual salary (approx OTE)", min_value=0.0, value=55_000.0, step=1000.0)
        extra_rate = st.slider("Your extra (salary‑sacrifice) %", 0.0, 20.0, 2.0, 0.5) / 100.0
        start_balance = st.number_input("Current super balance", min_value=0.0, value=3_000.0, step=500.0)
        return_rate = st.slider("Expected annual return %", -10.0, 15.0, 6.0, 0.5) / 100.0
        fees_flat = st.number_input("Annual flat fees ($)", min_value=0.0, value=120.0, step=10.0)
        fees_pct = st.slider("Annual % fees", 0.0, 3.0, 0.6, 0.1) / 100.0
        inflation = st.slider("Inflation %", 0.0, 10.0, 2.5, 0.5) / 100.0
        years = st.slider("Projection years", 1, 60, 40)
 
    records = simulate_growth(
        balance_start=start_balance,
        salary=salary,
        extra_rate=extra_rate,
        years=years,
        return_rate=return_rate,
        fees_flat=fees_flat,
        fees_pct=fees_pct,
        inflation=inflation,
        start_date=dt.date.today()
    )
 
    df = df_from_records(records)
    end_nom = df["End balance"].iloc[-1]
    end_real = df["End (today’s $)"].iloc[-1]
    total_contrib = df["Net contributions"].sum()
    total_growth = df["Growth (before fees)"].sum()
    total_fees = df["Fees"].sum()
    total_ctax = df["Contributions tax (incl Div293)"].sum()
    total_div293 = df["Div293 (est)"].sum()
    sg_now = current_sg_rate(dt.date.today()) * 100
 
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Projected balance (nominal)", money(end_nom))
    c2.metric("Projected balance (today’s $)", money(end_real))
    c3.metric("Total net contributions", money(total_contrib))
    c4.metric("Total fees", money(total_fees))
 
    st.write(f"**Current SG applied:** {sg_now:.1f}% • **Contributions tax paid (incl est Div293):** {money(total_ctax)} (Div293 est: {money(total_div293)})")
 
    figs = plot_projection(records)
    st.pyplot(figs["line"], use_container_width=True)
    st.pyplot(figs["stacked"], use_container_width=True)
    st.pyplot(figs["pie"], use_container_width=True)
 
    st.subheader("Yearly table")
    st.dataframe(df.head(15), use_container_width=True)
 
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download full table (CSV)", csv, file_name="super_projection.csv", mime="text/csv")
 
def page_quizzes():
    st.header("Quick Quizzes")
    st.caption("Immediate feedback; scores are not saved beyond this session.")
 
    quizzes = {
        "why": [
            {"q": "What powers big balances when you start young?", "opts": ["High fees", "Compounding over time", "Guessing the market"], "a": "Compounding over time"},
            {"q": "Superannuation is mainly for:", "opts": ["Daily spending", "Retirement savings", "Holiday cash"], "a": "Retirement savings"},
        ],
        "rights": [
            {"q": "If you don’t choose a fund, employers must use your:", "opts": ["Default fund", "Stapled fund", "Bank account"], "a": "Stapled fund"},
            {"q": "Under 18s receive SG when they:", "opts": ["Earn > $450/month", "Work > 30 hours in a week", "Have two jobs"], "a": "Work > 30 hours in a week"},
        ],
        "costs": [
            {"q": "A common super cost is:", "opts": ["Fees", "Parking", "Movie tickets"], "a": "Fees"},
            {"q": "A key benefit is:", "opts": ["Tax advantages (rules apply)", "Guaranteed returns"], "a": "Tax advantages (rules apply)"},
        ],
    }
 
    for block_key, questions in quizzes.items():
        with st.expander(f"Quiz: {block_key.title()}", expanded=True):
            score = 0
            for i, q in enumerate(questions, 1):
                key = f"{block_key}_{i}"
                st.radio(f"Q{i}. {q['q']}", options=q["opts"], key=key, index=None)
                selected = st.session_state.get(key, None)
                if selected is not None:
                    if selected == q["a"]:
                        st.success("Correct ✅")
                        score += 1
                    else:
                        st.error(f"Not quite ❌ — Correct answer: **{q['a']}**")
            st.info(f"Score: **{score} / {len(questions)}**")
 
def page_au_quick_reference():
    st.header("Australia Quick Reference (Educational Summary)")
    sg_now = current_sg_rate(dt.date.today()) * 100
 
    st.markdown(dedent(f"""
    **Super Guarantee (SG)**
    - Current applied rate: **{sg_now:.1f}%** (see sources). 
    - Due at least quarterly until Payday Super commences.
 
    **Due dates (quarterly)** 
    - {AU_RULES['quarter_due_dates']}
 
    **Eligibility** 
    - {AU_RULES['under18_rule']}
 
    **Contribution caps (from 1 Jul 2024)** 
    - Concessional (before‑tax): **${AU_RULES['caps']['concessional']:,}** p.a. 
    - Non‑concessional (after‑tax): **${AU_RULES['caps']['non_concessional']:,}** p.a. 
    - Possible bring‑forward to **${AU_RULES['caps']['bring_forward_max']:,}** if eligible. 
 
    **High incomes** 
    - Division 293 may add **15%** where income + concessional contributions exceed **${AU_RULES['division293_threshold']:,}** (simplified estimate in calculator).
 
    **Access** 
    - {AU_RULES['preservation_age_note']}
    """))
    st.warning("These are simplified snapshots. Always confirm the latest details with official sources on the Sources page.")
 
def page_sources():
    st.header("Sources")
    st.markdown(dedent("""
    - **ATO — Super Guarantee (rates, due dates)** 
      https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/super-guarantee
    - **ATO — Super payment due dates** 
      https://www.ato.gov.au/businesses-and-organisations/super-for-employers/paying-super-contributions/super-payment-due-dates
    - **ATO — Payday Super (what’s changing)** 
      https://www.ato.gov.au/businesses-and-organisations/super-for-employers/payday-super/about-payday-super
    - **ATO — Under 18 eligibility (30 hours rule)** 
      https://www.ato.gov.au/businesses-and-organisations/super-for-employers/work-out-if-you-have-to-pay-super
    - **ATO — Contribution caps** 
      https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/contributions-caps 
      https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/super/growing-and-keeping-track-of-your-super/caps-limits-and-tax-on-super-contributions/non-concessional-contributions-cap
    - **ATO — Division 293** 
      https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/super/growing-and-keeping-track-of-your-super/caps-limits-and-tax-on-super-contributions/division-293-tax-on-concessional-contributions-by-high-income-earners
    - **ATO — Accessing your super to retire / Preservation age** 
      https://www.ato.gov.au/individuals-and-families/jobs-and-employment-types/working-as-an-employee/leaving-the-workforce/accessing-your-super-to-retire
    """))
    st.caption("Links are provided for learning; this app is not affiliated with these organisations.")
 
# -----------------------------
# Navigation
# -----------------------------
with st.sidebar:
    st.title("Navigate")
    page = st.radio(
        "Choose a section",
        ["Welcome", "Why Super Matters", "Rights & Responsibilities", "Costs vs Benefits",
         "Calculator", "Quizzes", "AU Quick Reference", "Sources"],
        index=0
    )
 
# -----------------------------
# Router
# -----------------------------
if page == "Welcome":
    page_welcome()
elif page == "Why Super Matters":
    page_why_super_matters()
elif page == "Rights & Responsibilities":
    page_rights_responsibilities()
elif page == "Costs vs Benefits":
    page_costs_vs_benefits()
elif page == "Calculator":
    page_calculator()
elif page == "Quizzes":
    page_quizzes()
elif page == "AU Quick Reference":
    page_au_quick_reference()
elif page == "Sources":
    page_sources()
 