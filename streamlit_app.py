import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="HDB resale loan calculator",
    page_icon=":material/home_work:",
    layout="wide",
)

BSD_TIERS = [
    (180_000, 0.01),
    (180_000, 0.02),
    (640_000, 0.03),
    (500_000, 0.04),
    (1_500_000, 0.05),
    (float("inf"), 0.06),
]
STRESS_TEST_RATE = 0.04
MAX_MSR = 0.30
MAX_TDSR = 0.55
LTV_LIMIT = 0.75
MAX_TENURE_BANK = 30
LEGAL_FEES_ESTIMATE = 3_000
NUM_BUYERS = 2
CPF_OA_INTEREST_RATE = 0.025


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
    monthly_rate = annual_rate / 12
    months = tenure_years * 12
    return loan_amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)


def calculate_max_loan_msr(gross_monthly_income, stress_rate, tenure_years):
    max_monthly = gross_monthly_income * MAX_MSR
    monthly_rate = stress_rate / 12
    months = tenure_years * 12
    if monthly_rate == 0:
        return max_monthly * months
    return max_monthly * ((1 + monthly_rate) ** months - 1) / (monthly_rate * (1 + monthly_rate) ** months)


def calculate_max_loan_tdsr(gross_monthly_income, monthly_debts, stress_rate, tenure_years):
    max_monthly = gross_monthly_income * MAX_TDSR - monthly_debts
    if max_monthly <= 0:
        return 0.0
    monthly_rate = stress_rate / 12
    months = tenure_years * 12
    if monthly_rate == 0:
        return max_monthly * months
    return max_monthly * ((1 + monthly_rate) ** months - 1) / (monthly_rate * (1 + monthly_rate) ** months)


def calculate_bank_downpayment(price):
    total_downpayment = price * (1 - LTV_LIMIT)
    cash_minimum = price * 0.05
    cpf_portion = total_downpayment - cash_minimum
    return {"total": total_downpayment, "cash_min": cash_minimum, "cpf_max": cpf_portion}


def project_funds_buffer(
    cpf_start,
    cash_start,
    cpf_upfront,
    cash_upfront,
    monthly_cpf_contribution,
    monthly_cash_savings,
    monthly_mortgage,
    cpf_interest_rate,
    cash_interest_rate,
    projection_years,
):
    cpf_balance = cpf_start - cpf_upfront
    cash_balance = cash_start - cash_upfront
    monthly_cpf_interest = cpf_interest_rate / 12
    monthly_cash_interest = cash_interest_rate / 12
    records = [{
        "Month": 0,
        "CPF OA balance": cpf_balance,
        "Cash balance": cash_balance,
        "Total buffer": cpf_balance + cash_balance,
        "CPF used for mortgage": 0.0,
        "Cash used for mortgage": 0.0,
    }]

    for month in range(1, projection_years * 12 + 1):
        cpf_balance = cpf_balance * (1 + monthly_cpf_interest) + monthly_cpf_contribution
        cash_balance = cash_balance * (1 + monthly_cash_interest) + monthly_cash_savings

        cpf_mortgage = min(cpf_balance, monthly_mortgage)
        cash_mortgage = monthly_mortgage - cpf_mortgage
        cpf_balance -= cpf_mortgage
        cash_balance -= cash_mortgage

        records.append({
            "Month": month,
            "CPF OA balance": cpf_balance,
            "Cash balance": cash_balance,
            "Total buffer": cpf_balance + cash_balance,
            "CPF used for mortgage": cpf_mortgage,
            "Cash used for mortgage": cash_mortgage,
        })

    return pd.DataFrame(records)


def format_currency(amount):
    return f"${amount:,.0f}"


st.title("HDB resale loan calculator")
st.caption("Singapore bank-loan cashflow planner for two buyers")

tab_calculator, tab_guide = st.tabs([
    ":material/calculate: Calculator",
    ":material/menu_book: Resale HDB guide",
])

with st.sidebar:
    st.header("Configuration")
    st.caption("Bank loan only | 2 buyers | No grants")

    st.subheader("Property")
    resale_price = st.number_input("Resale HDB price ($)", value=1_000_000, step=1_000, min_value=100_000, max_value=2_000_000, format="%d")
    cov = st.number_input("Cash over valuation ($)", value=0, step=1_000, min_value=0, max_value=500_000,
                          help="COV = Resale price minus HDB valuation. Must be paid in cash only (not CPF or loan).", format="%d")

    st.subheader("Income & debts")
    monthly_salary = st.number_input("Combined monthly gross salary ($)", value=19_167, step=500, min_value=0, format="%d")
    monthly_debts = st.number_input("Monthly debt obligations ($)", value=0, step=100, min_value=0, format="%d")
    monthly_income = monthly_salary

    st.subheader("Monthly accumulation")
    cpf_oa_contribution_rate = st.slider("CPF OA contribution to housing (%)", 0.0, 30.0, 23.0, step=0.5) / 100
    cash_savings_rate = st.slider("Cash savings rate (%)", 0.0, 80.0, 25.0, step=1.0) / 100
    st.caption("Rates are applied to combined monthly salary for projection purposes.")

    st.subheader("Loan parameters")
    interest_rate = st.slider("Interest rate (% p.a.)", 1.0, 6.0, 2.0, step=0.1) / 100
    loan_tenure = st.slider("Loan tenure (years)", 5, MAX_TENURE_BANK, MAX_TENURE_BANK)

    st.subheader("Assets")
    cpf_oa_balance = st.number_input("CPF OA balance ($)", value=200_000, step=1_000, min_value=0, format="%d")
    cash_available = st.number_input("Cash available ($)", value=250_000, step=1_000, min_value=0, format="%d")

    with st.expander("Projection assumptions", icon=":material/trending_up:"):
        projection_years = st.slider("Projection period (years)", 1, min(10, MAX_TENURE_BANK), 5)
        cpf_interest_rate = st.slider("CPF OA interest (% p.a.)", 0.0, 5.0, CPF_OA_INTEREST_RATE * 100, step=0.1) / 100
        cash_interest_rate = st.slider("Cash interest (% p.a.)", 0.0, 5.0, 0.5, step=0.1) / 100

bsd = calculate_bsd(resale_price)
downpayment = calculate_bank_downpayment(resale_price)

max_loan_msr = calculate_max_loan_msr(monthly_income, STRESS_TEST_RATE, loan_tenure)
max_loan_tdsr = calculate_max_loan_tdsr(monthly_income, monthly_debts, STRESS_TEST_RATE, loan_tenure)
max_loan_ltv = resale_price * LTV_LIMIT
max_loan = min(max_loan_msr, max_loan_tdsr, max_loan_ltv)
loan_amount = max(0, min(max_loan, resale_price - downpayment["total"]))

monthly_repayment = calculate_monthly_repayment(loan_amount, interest_rate, loan_tenure)
total_repayment = monthly_repayment * loan_tenure * 12
total_interest = total_repayment - loan_amount

monthly_cpf_contribution = monthly_salary * cpf_oa_contribution_rate
monthly_cash_savings = monthly_salary * cash_savings_rate

with tab_calculator:
    st.subheader("Key numbers")

    cash_for_downpayment = downpayment["cash_min"]
    cpf_for_downpayment = downpayment["cpf_max"]
    total_upfront_excluding_cov = downpayment["total"] + bsd + LEGAL_FEES_ESTIMATE
    total_upfront = total_upfront_excluding_cov + cov

    cpf_used = min(cpf_oa_balance, cpf_for_downpayment + bsd + LEGAL_FEES_ESTIMATE)
    cash_used = cash_for_downpayment + max(0, (cpf_for_downpayment + bsd + LEGAL_FEES_ESTIMATE) - cpf_oa_balance) + cov

    cpf_balance_after_upfront = cpf_oa_balance - cpf_used
    cash_balance_after_upfront = cash_available - cash_used
    total_buffer_after_upfront = cpf_balance_after_upfront + cash_balance_after_upfront

    key_columns = st.columns(4, vertical_alignment="center")
    key_columns[0].metric("Loan amount", format_currency(loan_amount), border=True)
    key_columns[1].metric("Monthly repayment", format_currency(monthly_repayment), border=True)
    key_columns[2].metric("Total upfront", format_currency(total_upfront), border=True)
    key_columns[3].metric("Post-upfront buffer", format_currency(total_buffer_after_upfront), border=True)

    st.subheader("Upfront costs")

    if cov > 0:
        cost_columns = st.columns(4, vertical_alignment="center")
        cost_columns[0].metric("Downpayment (25%)", format_currency(downpayment["total"]), border=True)
        cost_columns[1].metric("Buyer's stamp duty", format_currency(bsd), border=True)
        cost_columns[2].metric("Legal fees (est.)", format_currency(LEGAL_FEES_ESTIMATE), border=True)
        cost_columns[3].metric("COV (cash only)", format_currency(cov), border=True)
    else:
        cost_columns = st.columns(3, vertical_alignment="center")
        cost_columns[0].metric("Downpayment (25%)", format_currency(downpayment["total"]), border=True)
        cost_columns[1].metric("Buyer's stamp duty", format_currency(bsd), border=True)
        cost_columns[2].metric("Legal fees (est.)", format_currency(LEGAL_FEES_ESTIMATE), border=True)

    st.markdown("**Payment source** (CPF OA drawn first, then cash)")
    if cov > 0:
        st.caption(f"COV of {format_currency(cov)} must be paid in cash - cannot use CPF or loan.")
    st.caption("Bank loan requires minimum 5% of purchase price in cash for downpayment.")

    payment_columns = st.columns(2, vertical_alignment="center")
    payment_columns[0].metric(
        "From CPF OA",
        format_currency(cpf_used),
        delta=f"Balance: {format_currency(cpf_balance_after_upfront)}" if cpf_balance_after_upfront >= 0 else "Insufficient",
        delta_color="normal" if cpf_oa_balance >= cpf_used else "inverse",
        border=True,
    )
    payment_columns[1].metric(
        "From cash",
        format_currency(cash_used),
        delta=f"Balance: {format_currency(cash_balance_after_upfront)}" if cash_balance_after_upfront >= 0 else "Insufficient",
        delta_color="normal" if cash_available >= cash_used else "inverse",
        border=True,
    )

    st.subheader("Funds buffer projection")

    buffer_projection = project_funds_buffer(
        cpf_start=cpf_oa_balance,
        cash_start=cash_available,
        cpf_upfront=cpf_used,
        cash_upfront=cash_used,
        monthly_cpf_contribution=monthly_cpf_contribution,
        monthly_cash_savings=monthly_cash_savings,
        monthly_mortgage=monthly_repayment,
        cpf_interest_rate=cpf_interest_rate,
        cash_interest_rate=cash_interest_rate,
        projection_years=projection_years,
    )

    chart_df = buffer_projection.melt(
        id_vars="Month",
        value_vars=["CPF OA balance", "Cash balance", "Total buffer"],
        var_name="Account",
        value_name="Balance",
    )

    fig = go.Figure()
    for account, account_df in chart_df.groupby("Account"):
        fig.add_trace(go.Scatter(
            x=account_df["Month"],
            y=account_df["Balance"],
            mode="lines",
            name=account,
        ))
    fig.add_hline(y=0, line_dash="dash", line_color="#9ca3af")
    fig.update_layout(
        xaxis_title="Months after purchase",
        yaxis_title="Projected balance ($)",
        height=420,
        margin=dict(t=20, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, width="stretch")

    ending_buffer = buffer_projection.iloc[-1]["Total buffer"]
    min_buffer = buffer_projection["Total buffer"].min()
    cash_support_months = int((buffer_projection["Cash used for mortgage"] > 0).sum())

    buffer_columns = st.columns(3, vertical_alignment="center")
    buffer_columns[0].metric(f"Buffer after {projection_years} years", format_currency(ending_buffer), border=True)
    buffer_columns[1].metric("Lowest projected buffer", format_currency(min_buffer), border=True)
    buffer_columns[2].metric("Months cash tops up loan", f"{cash_support_months}", border=True)

    with st.expander("Loan constraints", expanded=False, icon=":material/tune:"):
        st.markdown(f"""
| Constraint | Max loan | What it means |
|------------|----------|---------------|
| **MSR** | {format_currency(max_loan_msr)} | Mortgage Servicing Ratio: monthly mortgage cannot exceed 30% of gross income (stress-tested at 4%) |
| **TDSR** | {format_currency(max_loan_tdsr)} | Total Debt Servicing Ratio: all monthly debts cannot exceed 55% of gross income |
| **LTV** | {format_currency(max_loan_ltv)} | Loan-to-Value: loan cannot exceed 75% of purchase price or valuation |
""")
        binding = "MSR" if max_loan == max_loan_msr else ("TDSR" if max_loan == max_loan_tdsr else "LTV")
        st.info(f"Binding constraint: **{binding}** - max eligible loan: **{format_currency(max_loan)}**", icon=":material/info:")

    st.subheader("Loan summary")

    loan_summary_columns = st.columns(3, vertical_alignment="center")
    loan_summary_columns[0].metric("Per person / month", format_currency(monthly_repayment / NUM_BUYERS), help="Split across 2 buyers", border=True)
    loan_summary_columns[1].metric("Interest rate", f"{interest_rate*100:.1f}% p.a.", border=True)
    loan_summary_columns[2].metric("Total interest", format_currency(total_interest), border=True)

    st.subheader("Summary table")

    summary = pd.DataFrame({
        "Item": [
            "Purchase price",
            "",
            "Downpayment (25%)",
            "  - From CPF OA",
            "  - From cash",
            "Buyer's stamp duty (BSD)",
            "Legal fees (est.)",
            "Cash over valuation (COV)",
            "",
            "Total upfront (from CPF OA)",
            "Total upfront (from cash)",
            "",
            "Loan amount (75%)",
            "Monthly repayment",
            "Monthly per person (2 buyers)",
            "Monthly CPF OA contribution",
            "Monthly cash savings",
            f"Projected buffer after {projection_years} years",
            "Total repayment (over tenure)",
            "Total interest paid",
        ],
        "Amount": [
            format_currency(resale_price),
            "",
            format_currency(downpayment["total"]),
            format_currency(cpf_used),
            format_currency(cash_used),
            format_currency(bsd),
            format_currency(LEGAL_FEES_ESTIMATE),
            format_currency(cov),
            "",
            format_currency(cpf_used),
            format_currency(cash_used),
            "",
            format_currency(loan_amount),
            f"{format_currency(monthly_repayment)}/mo",
            f"{format_currency(monthly_repayment / NUM_BUYERS)}/mo",
            f"{format_currency(monthly_cpf_contribution)}/mo",
            f"{format_currency(monthly_cash_savings)}/mo",
            format_currency(ending_buffer),
            format_currency(total_repayment),
            format_currency(total_interest),
        ],
    })
    st.dataframe(summary, hide_index=True, width="stretch")

with tab_guide:
    st.header("Guide to buying a resale HDB flat in Singapore")
    st.caption("This guide covers resale HDB flats only (not BTO, EC, or private property).")

    st.subheader("1. Eligibility")
    st.markdown("""
**Who can buy a resale HDB flat?**

| Scheme | Who qualifies |
|--------|--------------|
| Public Scheme | Families with at least 1 Singapore Citizen or PR |
| Fiance/Fiancee Scheme | Engaged couples planning to marry within 3 months of completion |
| Single SC Scheme | Singles aged 35+ (Singapore Citizens only) |
| Joint Singles Scheme | Up to 4 single SCs jointly purchasing |
| Non-Citizen Spouse Scheme | SC with non-resident spouse (valid Visit/Work Pass) |

**Key conditions:**
- At least 1 buyer must be a Singapore Citizen (for SC + PR couples, the SC must be listed)
- PRs can buy resale after 3 years of PR status (under Public Scheme with another PR or SC)
- **No income ceiling** for purchasing a resale flat with bank financing
- Must not own other property locally or overseas (or dispose within 6 months of purchase)
- Private property owners under 55 must wait **15 months** after selling private property before buying resale HDB
""")

    st.subheader("2. Bank financing assumptions")
    st.markdown("""
| Feature | Bank loan treatment in this calculator |
|---------|--------------------------------------|
| **Interest rate** | User-adjustable market rate |
| **LTV limit** | 75% |
| **Downpayment** | 25% total, with minimum 5% in cash |
| **Max tenure** | 30 years, subject to bank and age limits |
| **Eligibility** | Subject to bank credit assessment, MSR, and TDSR |
| **Refinancing** | Generally possible after lock-in period |

This app is intentionally scoped to bank financing because the buyer pair is not eligible for an HDB loan based on HFE.
""")

    st.subheader("3. Loan limits (MSR & TDSR)")
    st.markdown("""
**Mortgage Servicing Ratio (MSR) - 30%**
- Monthly mortgage repayment cannot exceed **30%** of gross monthly income
- Applies to HDB and EC purchases only
- Calculated at **4% stress-test rate** (not your actual loan rate)

**Total Debt Servicing Ratio (TDSR) - 55%**
- Total monthly debt obligations cannot exceed **55%** of gross monthly income
- Applies to all property purchases
- Also uses 4% stress-test rate for the mortgage component

For HDB resale with a bank loan, you must pass **both** MSR and TDSR.
""")

    st.subheader("4. Buyer's stamp duty (BSD)")
    st.markdown("""
| Purchase price band | Rate |
|-------------------|------|
| First $180,000 | 1% |
| Next $180,000 ($180K - $360K) | 2% |
| Next $640,000 ($360K - $1M) | 3% |
| Next $500,000 ($1M - $1.5M) | 4% |
| Next $1,500,000 ($1.5M - $3M) | 5% |
| Amount exceeding $3M | 6% |

**Example:** $600,000 flat = $1,800 + $3,600 + $7,200 = **$12,600 BSD**

ABSD is **0%** for first-time SC buyers of resale HDB.
""")

    st.subheader("5. CPF usage for resale HDB")
    st.markdown("""
CPF OA can be used for: downpayment, monthly mortgage, stamp duty, and legal fees.

**Limits:**
- Up to the **Valuation Limit** (lower of purchase price or valuation)
- Flat's remaining lease must cover youngest buyer to **age 95** for full CPF usage
- If remaining lease < 20 years, CPF cannot be used at all
- Cash over valuation must be paid in cash only
""")

    st.subheader("6. Buying process")
    st.markdown("""
| Step | Action | Notes |
|------|--------|-------|
| 1 | Apply for HFE Letter | Mandatory before getting OTP |
| 2 | Search for flat & negotiate price | Use HDB Resale Flat Listing |
| 3 | Obtain OTP from seller | Option fee up to $1,000 |
| 4 | Exercise OTP | Within 21 calendar days |
| 5 | Submit Request for Value | Next working day after OTP |
| 6 | Confirm financing with bank | Letter of Offer required |
| 7 | Submit resale application | Via HDB Flat Portal |
| 8 | Endorse documents & pay fees | ~3 weeks after acceptance |
| 9 | HDB approval | Within 28 working days |
| 10 | Completion - collect keys | ~8 weeks from acceptance |

Total timeline: approximately **8-12 weeks** from OTP to keys.
""")

    st.subheader("7. Costs summary")
    st.markdown("""
| Cost item | Amount | Payment |
|-----------|--------|---------|
| Option Fee + Exercise | Up to $5,000 | Cash |
| Downpayment (25%) | Varies | Cash + CPF |
| Buyer's Stamp Duty | Tiered | Cash or CPF |
| Resale Application Fee | $80 | Cash |
| Request for Value | $120 | Cash |
| Legal Fees | $2,000 - $3,000 | Cash or CPF |
| Stamp Duty on Mortgage | 0.4% of loan (max $500) | Cash |
| Cash over valuation (COV) | Negotiated | Cash only |
""")

    st.subheader("8. After purchase")
    st.markdown("""
- **MOP:** 5 years (must live in flat, cannot rent out entire unit)
- **Room rental:** Allowed from Day 1 with HDB approval
- **Entire flat subletting:** Only after MOP
""")

    st.subheader("Official sources")
    st.markdown("""
- [HDB - Resale Buying Process](https://www.hdb.gov.sg/buying-a-flat/resale-flats/process-for-buying-a-resale-flat)
- [IRAS - Buyer's Stamp Duty](https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/buyer's-stamp-duty-(bsd))
- [MAS - Property Loan Rules](https://www.mas.gov.sg/regulation/explainers/new-housing-loans)
- [CPF Board - Housing](https://www.cpf.gov.sg/member/growing-your-savings/saving-for-housing)
""")
    st.caption("Accurate as of 2026. Always verify with official sources before making financial decisions.")
