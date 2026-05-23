import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="HDB Resale Loan Calculator", layout="wide")

BSD_TIERS = [
    (180_000, 0.01),
    (180_000, 0.02),
    (640_000, 0.03),
    (500_000, 0.04),
    (1_500_000, 0.05),
    (float("inf"), 0.06),
]
STRESS_TEST_RATE = 0.04
HDB_LOAN_RATE = 0.026
MAX_MSR = 0.30
MAX_TDSR = 0.55
LTV_LIMIT = 0.75
VARIABLE_INCOME_HAIRCUT = 0.70
MAX_TENURE_HDB = 25
MAX_TENURE_BANK = 30
LEGAL_FEES_ESTIMATE = 3_000


def calculate_bsd(price):
    bsd = 0.0
    remaining = price
    for band, rate in BSD_TIERS:
        taxable = min(remaining, band)
        bsd += taxable * rate
        remaining -= taxable
        if remaining <= 0:
            break
    return bsd


def calculate_monthly_repayment(loan_amount, annual_rate, tenure_years):
    if loan_amount <= 0 or annual_rate <= 0 or tenure_years <= 0:
        return 0.0
    r = annual_rate / 12
    n = tenure_years * 12
    return loan_amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def calculate_max_loan_msr(gross_income, stress_rate, tenure_years):
    max_monthly = gross_income * MAX_MSR
    r = stress_rate / 12
    n = tenure_years * 12
    if r == 0:
        return max_monthly * n
    return max_monthly * ((1 + r) ** n - 1) / (r * (1 + r) ** n)


def calculate_max_loan_tdsr(gross_income, existing_debts, stress_rate, tenure_years):
    max_monthly = gross_income * MAX_TDSR - existing_debts
    if max_monthly <= 0:
        return 0.0
    r = stress_rate / 12
    n = tenure_years * 12
    if r == 0:
        return max_monthly * n
    return max_monthly * ((1 + r) ** n - 1) / (r * (1 + r) ** n)


def calculate_effective_income(fixed_income, variable_income):
    return fixed_income + variable_income * VARIABLE_INCOME_HAIRCUT


def calculate_downpayment(price, loan_type):
    total_dp = price * (1 - LTV_LIMIT)
    if loan_type == "Bank Loan":
        cash_min = price * 0.05
        cpf_portion = total_dp - cash_min
        return {"total": total_dp, "cash_min": cash_min, "cpf_max": cpf_portion}
    else:
        return {"total": total_dp, "cash_min": 0, "cpf_max": total_dp}


def generate_amortization_schedule(loan_amount, annual_rate, tenure_years):
    if loan_amount <= 0 or annual_rate <= 0 or tenure_years <= 0:
        return pd.DataFrame()
    r = annual_rate / 12
    n = tenure_years * 12
    monthly_payment = calculate_monthly_repayment(loan_amount, annual_rate, tenure_years)
    balance = loan_amount
    records = []
    for month in range(1, n + 1):
        interest = balance * r
        principal = monthly_payment - interest
        balance -= principal
        if balance < 0:
            balance = 0
        records.append({
            "Month": month,
            "Year": (month - 1) // 12 + 1,
            "Principal": principal,
            "Interest": interest,
            "Balance": balance,
            "Cumulative Interest": sum(rec["Interest"] for rec in records),
        })
    records[-1]["Cumulative Interest"] = sum(rec["Interest"] for rec in records)
    return pd.DataFrame(records)


st.title("HDB Resale Loan Calculator")
st.caption("Singapore | Simulate loan scenarios for HDB resale flat purchases")

with st.sidebar:
    st.header("Configuration")

    st.subheader("Property")
    resale_price = st.number_input("Resale HDB Price ($)", value=600_000, step=10_000, min_value=100_000, max_value=2_000_000)

    st.subheader("Loan Type")
    loan_type = st.radio("Financing", ["HDB Loan", "Bank Loan"], index=1)
    max_tenure = MAX_TENURE_HDB if loan_type == "HDB Loan" else MAX_TENURE_BANK

    st.subheader("Income")
    fixed_income = st.number_input("Fixed Monthly Income ($)", value=8_000, step=500, min_value=0)
    variable_income = st.number_input("Variable Monthly Income ($)", value=0, step=500, min_value=0)
    if variable_income > 0:
        st.caption(f"Effective variable (70% haircut): ${variable_income * VARIABLE_INCOME_HAIRCUT:,.0f}")
    existing_debts = st.number_input("Existing Monthly Debt Obligations ($)", value=0, step=100, min_value=0)

    st.subheader("Loan Parameters")
    if loan_type == "HDB Loan":
        interest_rate = st.slider("Interest Rate (% p.a.)", 2.0, 4.0, 2.6, step=0.1, disabled=True) / 100
        st.caption("HDB loan rate fixed at 2.6% (CPF OA + 0.1%)")
    else:
        interest_rate = st.slider("Interest Rate (% p.a.)", 1.0, 6.0, 4.0, step=0.1) / 100
    loan_tenure = st.slider("Loan Tenure (years)", 5, max_tenure, min(25, max_tenure))
    st.caption(f"MAS stress-test rate: {STRESS_TEST_RATE*100:.1f}% (used for MSR/TDSR cap)")

    st.subheader("Assets")
    cpf_oa_balance = st.number_input("CPF OA Balance ($)", value=100_000, step=10_000, min_value=0)
    cash_available = st.number_input("Cash Available ($)", value=100_000, step=10_000, min_value=0)

    st.subheader("Grants")
    cpf_housing_grant = st.number_input("CPF Housing Grant ($)", value=0, step=5_000, min_value=0, max_value=80_000)
    ehg = st.number_input("Enhanced Housing Grant ($)", value=0, step=5_000, min_value=0, max_value=80_000)
    phg = st.number_input("Proximity Housing Grant ($)", value=0, step=5_000, min_value=0, max_value=30_000)

effective_income = calculate_effective_income(fixed_income, variable_income)
total_grants = cpf_housing_grant + ehg + phg
effective_price = resale_price - total_grants

bsd = calculate_bsd(resale_price)
dp_info = calculate_downpayment(effective_price, loan_type)

max_loan_msr = calculate_max_loan_msr(effective_income, STRESS_TEST_RATE, loan_tenure)
max_loan_tdsr = calculate_max_loan_tdsr(effective_income, existing_debts, STRESS_TEST_RATE, loan_tenure)
max_loan_ltv = effective_price * LTV_LIMIT
max_loan = min(max_loan_msr, max_loan_tdsr, max_loan_ltv)
loan_amount = max(0, min(max_loan, effective_price - dp_info["total"]))

monthly_repayment = calculate_monthly_repayment(loan_amount, interest_rate, loan_tenure)
total_repayment = monthly_repayment * loan_tenure * 12
total_interest = total_repayment - loan_amount
msr_util = (monthly_repayment / (effective_income * MAX_MSR) * 100) if effective_income > 0 else 0
tdsr_util = ((monthly_repayment + existing_debts) / (effective_income * MAX_TDSR) * 100) if effective_income > 0 else 0

st.markdown("---")
st.subheader("Loan Overview")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Purchase Price", f"${resale_price:,.0f}")
c2.metric("Loan Amount", f"${loan_amount:,.0f}")
c3.metric("Monthly Repayment", f"${monthly_repayment:,.2f}")
c4.metric("Total Repayment", f"${total_repayment:,.0f}")
c5.metric("Total Interest", f"${total_interest:,.0f}")

st.markdown("---")
st.subheader("Loan Eligibility")

el1, el2, el3 = st.columns(3)
el1.metric("Max Loan (MSR)", f"${max_loan_msr:,.0f}", help="30% of gross income at 4% stress-test")
el2.metric("Max Loan (TDSR)", f"${max_loan_tdsr:,.0f}", help="55% of gross income less existing debts")
el3.metric("Max Loan (LTV)", f"${max_loan_ltv:,.0f}", help="75% of effective purchase price")

binding_constraint = "MSR" if max_loan == max_loan_msr else ("TDSR" if max_loan == max_loan_tdsr else "LTV")
st.info(f"Binding constraint: **{binding_constraint}** (max eligible loan: ${max_loan:,.0f})")

mu1, mu2 = st.columns(2)
mu1.metric("MSR Utilization", f"{msr_util:.1f}%", help="Should be <= 100%")
mu2.metric("TDSR Utilization", f"{tdsr_util:.1f}%", help="Should be <= 100%")

st.markdown("---")
st.subheader("Cost Breakdown at Completion")

cash_for_dp = dp_info["cash_min"]
cpf_for_dp = dp_info["cpf_max"]
total_cash_needed = cash_for_dp + bsd + LEGAL_FEES_ESTIMATE
cpf_needed = cpf_for_dp

cost_data = {
    "Item": [
        f"Downpayment ({(1-LTV_LIMIT)*100:.0f}%)",
        f"  - Minimum Cash",
        f"  - CPF OA",
        "Buyer's Stamp Duty (BSD)",
        "Legal Fees (est.)",
        "Total Grants Offset",
        "",
        "TOTAL CASH NEEDED",
        "TOTAL CPF NEEDED",
    ],
    "Amount": [
        f"${dp_info['total']:,.0f}",
        f"${cash_for_dp:,.0f}",
        f"${cpf_for_dp:,.0f}",
        f"${bsd:,.0f}",
        f"${LEGAL_FEES_ESTIMATE:,.0f}",
        f"-${total_grants:,.0f}" if total_grants > 0 else "$0",
        "",
        f"${total_cash_needed:,.0f}",
        f"${cpf_needed:,.0f}",
    ],
    "Status": [
        "",
        "OK" if cash_available >= cash_for_dp else "SHORTFALL",
        "OK" if cpf_oa_balance >= cpf_for_dp else "SHORTFALL",
        "OK" if cash_available >= total_cash_needed else "WARNING",
        "",
        "",
        "",
        "OK" if cash_available >= total_cash_needed else "SHORTFALL",
        "OK" if cpf_oa_balance >= cpf_needed else "SHORTFALL",
    ],
}
cost_df = pd.DataFrame(cost_data)

def style_status(val):
    if val == "SHORTFALL":
        return "background-color: #ffcccc; color: #721c24"
    elif val == "WARNING":
        return "background-color: #fff3cd; color: #856404"
    elif val == "OK":
        return "background-color: #d4edda; color: #155724"
    return ""

st.dataframe(
    cost_df.style.map(style_status, subset=["Status"]),
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")
st.subheader("Repayment Schedule")

amort_df = generate_amortization_schedule(loan_amount, interest_rate, loan_tenure)

if not amort_df.empty:
    yearly = amort_df.groupby("Year").agg(
        Principal=("Principal", "sum"),
        Interest=("Interest", "sum"),
        EndBalance=("Balance", "last"),
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=yearly["Year"], y=yearly["Principal"],
        name="Principal", marker_color="#1f77b4",
    ))
    fig.add_trace(go.Bar(
        x=yearly["Year"], y=yearly["Interest"],
        name="Interest", marker_color="#ff7f0e",
    ))
    fig.update_layout(
        barmode="stack",
        xaxis_title="Year",
        yaxis_title="Annual Payment ($)",
        height=400,
        margin=dict(t=30, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=amort_df["Month"], y=amort_df["Balance"],
        name="Outstanding Balance",
        fill="tozeroy",
        line=dict(color="#2ca02c", width=2),
    ))
    fig2.update_layout(
        xaxis_title="Month",
        yaxis_title="Outstanding Balance ($)",
        height=350,
        margin=dict(t=30, b=40),
    )
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.subheader("Scenario Comparison")

st.caption("Compare different price points or interest rates")

scenarios = []
price_scenarios = [resale_price - 50_000, resale_price, resale_price + 50_000]
for sp in price_scenarios:
    eff_p = sp - total_grants
    ml_msr = calculate_max_loan_msr(effective_income, STRESS_TEST_RATE, loan_tenure)
    ml_tdsr = calculate_max_loan_tdsr(effective_income, existing_debts, STRESS_TEST_RATE, loan_tenure)
    ml_ltv = eff_p * LTV_LIMIT
    ml = min(ml_msr, ml_tdsr, ml_ltv)
    dp = eff_p * (1 - LTV_LIMIT)
    la = max(0, min(ml, eff_p - dp))
    mr = calculate_monthly_repayment(la, interest_rate, loan_tenure)
    ti = mr * loan_tenure * 12 - la
    scenarios.append({
        "Price": f"${sp:,.0f}",
        "Loan Amount": f"${la:,.0f}",
        "Monthly Repay": f"${mr:,.2f}",
        "Total Interest": f"${ti:,.0f}",
        "Downpayment": f"${dp:,.0f}",
        "BSD": f"${calculate_bsd(sp):,.0f}",
    })

scenario_df = pd.DataFrame(scenarios)
st.dataframe(scenario_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.subheader("Regulatory Reference")
with st.expander("Key Rules & Assumptions", expanded=False):
    st.markdown("""
| Rule | Value | Source |
|------|-------|--------|
| MSR Cap | 30% of gross monthly income | MAS |
| TDSR Cap | 55% of gross monthly income | MAS |
| Stress-Test Rate | 4% p.a. | MAS |
| LTV Limit | 75% | MAS/HDB |
| HDB Loan Rate | 2.6% p.a. (CPF OA + 0.1%) | HDB |
| Max Tenure (HDB) | 25 years | HDB |
| Max Tenure (Bank) | 30 years | MAS |
| BSD Tiers | 1%/2%/3%/4%/5%/6% on progressive bands | IRAS |
| Variable Income Haircut | 70% | MAS |
| CPF Housing Grant | Up to $80,000 (families) | HDB |
| Enhanced Housing Grant | Up to $80,000 | HDB |
| Proximity Housing Grant | Up to $30,000 | HDB |
""")
    st.caption("Rates and rules as of 2026. Always verify with official sources (HDB, MAS, IRAS, CPF Board).")
