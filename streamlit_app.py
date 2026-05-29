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


def calculate_max_loan_msr(gross_monthly_income, stress_rate, tenure_years):
    max_monthly = gross_monthly_income * MAX_MSR
    r = stress_rate / 12
    n = tenure_years * 12
    if r == 0:
        return max_monthly * n
    return max_monthly * ((1 + r) ** n - 1) / (r * (1 + r) ** n)


def calculate_max_loan_tdsr(gross_monthly_income, monthly_debts, stress_rate, tenure_years):
    max_monthly = gross_monthly_income * MAX_TDSR - monthly_debts
    if max_monthly <= 0:
        return 0.0
    r = stress_rate / 12
    n = tenure_years * 12
    if r == 0:
        return max_monthly * n
    return max_monthly * ((1 + r) ** n - 1) / (r * (1 + r) ** n)


def calculate_downpayment(price, loan_type):
    total_dp = price * (1 - LTV_LIMIT)
    if loan_type == "Bank Loan":
        cash_min = price * 0.05
        cpf_portion = total_dp - cash_min
        return {"total": total_dp, "cash_min": cash_min, "cpf_max": cpf_portion}
    else:
        return {"total": total_dp, "cash_min": 0, "cpf_max": total_dp}


st.title("HDB Resale Loan Calculator")
st.caption("Singapore | Simulate loan scenarios for HDB resale flat purchases")

tab_calculator, tab_guide = st.tabs(["Calculator", "Resale HDB Guide"])

with st.sidebar:
    st.header("Configuration")

    st.subheader("Property")
    resale_price = st.number_input("Resale HDB Price ($)", value=1_000_000, step=1_000, min_value=100_000, max_value=2_000_000, format="%d")
    cov = st.number_input("Cash Over Valuation ($)", value=0, step=1_000, min_value=0, max_value=500_000,
                          help="COV = Resale price minus HDB valuation. Must be paid in cash only (not CPF or loan).", format="%d")

    loan_type = "Bank Loan"
    max_tenure = MAX_TENURE_BANK

    st.subheader("Income & Debts")
    annual_income = st.number_input("Total Annual Income ($)", value=230_000, step=1_000, min_value=0, format="%d")
    annual_debts = st.number_input("Total Annual Debt Obligations ($)", value=0, step=1_000, min_value=0, format="%d")
    monthly_income = annual_income / 12
    monthly_debts = annual_debts / 12

    st.subheader("Loan Parameters")
    interest_rate = st.slider("Interest Rate (% p.a.)", 1.0, 6.0, 2.0, step=0.1) / 100
    loan_tenure = st.slider("Loan Tenure (years)", 5, max_tenure, max_tenure)

    st.subheader("Assets")
    cpf_oa_balance = st.number_input("CPF OA Balance ($)", value=200_000, step=1_000, min_value=0, format="%d")
    cash_available = st.number_input("Cash Available ($)", value=250_000, step=1_000, min_value=0, format="%d")

    st.subheader("Purchase Timeline")
    option_fee_input = st.number_input("Option Fee ($)", value=1_000, step=100, min_value=0, max_value=5_000,
                                       help="Paid in cash at Grant of OTP to secure the flat. Negotiable, capped within the $5,000 deposit.", format="%d")
    deposit_total_input = st.number_input("Total Option Deposit ($)", value=5_000, step=100, min_value=0, max_value=5_000,
                                          help="Combined option fee + exercise deposit. HDB caps this at $5,000, cash only.", format="%d")
    completion_weeks = st.slider("Weeks to Completion", 4, 16, 10,
                                 help="Time from securing the flat to key collection. Typically 8-12 weeks.")

num_buyers = 2
effective_price = resale_price
bsd = calculate_bsd(resale_price)
dp_info = calculate_downpayment(effective_price, loan_type)

max_loan_msr = calculate_max_loan_msr(monthly_income, STRESS_TEST_RATE, loan_tenure)
max_loan_tdsr = calculate_max_loan_tdsr(monthly_income, monthly_debts, STRESS_TEST_RATE, loan_tenure)
max_loan_ltv = effective_price * LTV_LIMIT
max_loan = min(max_loan_msr, max_loan_tdsr, max_loan_ltv)
loan_amount = max(0, min(max_loan, effective_price - dp_info["total"]))

monthly_repayment = calculate_monthly_repayment(loan_amount, interest_rate, loan_tenure)
total_repayment = monthly_repayment * loan_tenure * 12
total_interest = total_repayment - loan_amount

with tab_calculator:
    st.subheader("Purchase Price")
    st.metric("Resale HDB Price", f"${resale_price:,.0f}")


    st.markdown("---")
    st.subheader("Upfront Costs")

    cash_for_dp = dp_info["cash_min"]
    cpf_for_dp = dp_info["cpf_max"]
    total_upfront_excl_cov = dp_info["total"] + bsd + LEGAL_FEES_ESTIMATE
    total_upfront = total_upfront_excl_cov + cov

    if loan_type == "Bank Loan":
        cpf_used = min(cpf_oa_balance, cpf_for_dp + bsd + LEGAL_FEES_ESTIMATE)
        cash_used = cash_for_dp + max(0, (cpf_for_dp + bsd + LEGAL_FEES_ESTIMATE) - cpf_oa_balance) + cov

    if cov > 0:
        uc1, uc2, uc3, uc4 = st.columns(4)
        uc1.metric("Downpayment (25%)", f"${dp_info['total']:,.0f}")
        uc2.metric("Buyer's Stamp Duty", f"${bsd:,.0f}")
        uc3.metric("Legal Fees (est.)", f"${LEGAL_FEES_ESTIMATE:,.0f}")
        uc4.metric("COV (Cash Only)", f"${cov:,.0f}")
    else:
        uc1, uc2, uc3 = st.columns(3)
        uc1.metric("Downpayment (25%)", f"${dp_info['total']:,.0f}")
        uc2.metric("Buyer's Stamp Duty", f"${bsd:,.0f}")
        uc3.metric("Legal Fees (est.)", f"${LEGAL_FEES_ESTIMATE:,.0f}")

    st.markdown("**Payment Source** (CPF OA drawn first, then cash)")
    if cov > 0:
        st.caption(f"COV of ${cov:,.0f} must be paid in cash — cannot use CPF or loan.")
    st.caption("Bank loan requires minimum 5% of purchase price in cash for downpayment.")

    ps1, ps2, ps3 = st.columns(3)
    ps1.metric("From CPF OA", f"${cpf_used:,.0f}",
               delta=f"Balance: ${cpf_oa_balance - cpf_used:,.0f}" if cpf_oa_balance >= cpf_used else "Insufficient",
               delta_color="normal" if cpf_oa_balance >= cpf_used else "inverse")
    ps2.metric("From Cash", f"${cash_used:,.0f}",
               delta=f"Balance: ${cash_available - cash_used:,.0f}" if cash_available >= cash_used else "Insufficient",
               delta_color="normal" if cash_available >= cash_used else "inverse")
    ps3.metric("Total Upfront", f"${total_upfront:,.0f}")

    st.markdown("---")
    st.subheader("Loan")

    with st.expander("MSR / TDSR / LTV Breakdown", expanded=False):
        st.markdown(f"""
| Constraint | Max Loan | What it means |
|------------|----------|---------------|
| **MSR** | ${max_loan_msr:,.0f} | Mortgage Servicing Ratio: monthly mortgage cannot exceed 30% of gross income (stress-tested at 4%) |
| **TDSR** | ${max_loan_tdsr:,.0f} | Total Debt Servicing Ratio: all monthly debts cannot exceed 55% of gross income |
| **LTV** | ${max_loan_ltv:,.0f} | Loan-to-Value: loan cannot exceed 75% of purchase price or valuation |
""")
        binding = "MSR" if max_loan == max_loan_msr else ("TDSR" if max_loan == max_loan_tdsr else "LTV")
        st.info(f"Binding constraint: **{binding}** — max eligible loan: **${max_loan:,.0f}**")

    l1, l2, l3 = st.columns(3)
    l1.metric("Loan Amount", f"${loan_amount:,.0f}")
    l2.metric("Interest Rate", f"{interest_rate*100:.1f}% p.a.")
    l3.metric("Duration", f"{loan_tenure} years")

    l4, l5, l6 = st.columns(3)
    l4.metric("Monthly Repayment", f"${monthly_repayment:,.0f}")
    l5.metric("Per Person / Month", f"${monthly_repayment / num_buyers:,.0f}",
              help="Split across 2 buyers")
    l6.metric("Total Interest Paid", f"${total_interest:,.0f}")

    st.markdown("---")
    st.subheader("Downpayment Pay-Off Timeline")
    st.caption(
        "A resale HDB is already built, so there is no Progressive Payment Scheme like an EC. "
        "You pay at transaction milestones over roughly 8-12 weeks; the bank loan only disburses "
        "at completion, after which monthly repayment begins."
    )

    # The cash deposit is paid in two stages and counts towards the 25% downpayment.
    # CPF and the remaining cash are only paid at completion. The deposit is cash only
    # (not CPF or loan) and HDB caps the combined option + deposit at $5,000.
    # The exercise window is fixed by HDB at 21 days (3 weeks); option fee, deposit and
    # completion timing are variable and come from the sidebar, so the chart stays reactive.
    EXERCISE_WEEKS = 3
    exercise_weeks = EXERCISE_WEEKS
    deposit_total = min(deposit_total_input, cash_used)
    option_fee = min(option_fee_input, deposit_total)
    exercise_fee = deposit_total - option_fee
    completion_cash = max(0.0, cash_used - deposit_total)
    completion_cpf = cpf_used
    completion_total = completion_cash + completion_cpf

    milestones = [
        ("Grant of OTP", 0, option_fee, "Cash",
         "Option Fee paid to the seller to secure the flat (counts towards the downpayment)."),
        ("Exercise OTP", exercise_weeks, exercise_fee, "Cash",
         f"Deposit balance paid within 21 days. Option + deposit is capped at ${deposit_total_input:,.0f}."),
        ("Completion / Keys", completion_weeks, completion_total, "CPF OA + Cash",
         "Balance of 25% downpayment, BSD, legal fees and COV. Bank loan (75%) disburses to the seller."),
    ]

    weeks = [m[1] for m in milestones]
    tick_labels = [m[0] for m in milestones]
    cumulative = []
    running = 0.0
    for _, _, amount, _, _ in milestones:
        running += amount
        cumulative.append(running)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weeks, y=cumulative,
        mode="lines+markers+text",
        line=dict(shape="hv", color="#1f77b4", width=3),
        marker=dict(size=14, color="#1f77b4"),
        text=[f"${c:,.0f}" for c in cumulative],
        textposition="top center",
        hovertext=[f"{label}: +${amount:,.0f} ({src})<br>{desc}"
                   for label, _, amount, src, desc in milestones],
        hoverinfo="text",
        name="Cumulative upfront paid",
    ))
    # The bank loan only disburses at completion; mark where monthly repayment begins.
    fig.add_vline(x=completion_weeks, line_dash="dash", line_color="#2ca02c")
    fig.add_annotation(
        x=completion_weeks, y=max(cumulative) if cumulative else 0, yshift=38,
        text="Bank loan disburses -> monthly repayment begins",
        showarrow=False, font=dict(color="#2ca02c", size=12),
    )
    fig.update_layout(
        xaxis=dict(
            title="Weeks from securing the flat",
            tickmode="array", tickvals=weeks, ticktext=tick_labels,
            range=[-1, completion_weeks + 3],
        ),
        yaxis_title="Cumulative upfront paid ($)",
        height=400,
        margin=dict(t=60, b=40),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Milestone breakdown**")
    milestone_table = pd.DataFrame({
        "Milestone": ["Grant of OTP", "Exercise OTP", "Completion / Keys", "First Installment"],
        "When": [
            "Week 0",
            f"Week {exercise_weeks} (within 21 days)",
            f"Week {completion_weeks}",
            f"~1 month after completion (~Week {completion_weeks + 4})",
        ],
        "Payment": [
            f"${option_fee:,.0f}",
            f"${exercise_fee:,.0f}",
            f"${completion_total:,.0f}",
            f"${monthly_repayment:,.0f}/mo",
        ],
        "Source": ["Cash", "Cash", "CPF OA + Cash", "CPF OA / Cash"],
        "Notes": [
            "Option Fee to secure the flat (part of downpayment)",
            f"Deposit balance; option + deposit capped at ${deposit_total_input:,.0f}",
            "Balance of 25% downpayment + BSD + legal fees + COV; bank loan (75%) disburses",
            "Mortgage repayment begins after loan disbursement",
        ],
    })
    st.table(milestone_table)

    st.markdown("---")
    st.subheader("Summary Table")

    breakdown_data = {
        "Item": [
            "Purchase Price",
            "",
            "Downpayment (25%)",
            "  - From CPF OA",
            "  - From Cash",
            "Buyer's Stamp Duty (BSD)",
            "Legal Fees (est.)",
            "Cash Over Valuation (COV)",
            "",
            "Total Upfront (from CPF OA)",
            "Total Upfront (from Cash)",
            "",
            "Loan Amount (75%)",
            "Monthly Repayment",
            "Monthly Per Person (2 buyers)",
            "Total Repayment (over tenure)",
            "Total Interest Paid",
        ],
        "Amount": [
            f"${resale_price:,.0f}",
            "",
            f"${dp_info['total']:,.0f}",
            f"${cpf_used:,.0f}",
            f"${cash_used:,.0f}",
            f"${bsd:,.0f}",
            f"${LEGAL_FEES_ESTIMATE:,.0f}",
            f"${cov:,.0f}",
            "",
            f"${cpf_used:,.0f}",
            f"${cash_used:,.0f}",
            "",
            f"${loan_amount:,.0f}",
            f"${monthly_repayment:,.0f}/mo",
            f"${monthly_repayment / num_buyers:,.0f}/mo",
            f"${total_repayment:,.0f}",
            f"${total_interest:,.0f}",
        ],
    }
    st.table(pd.DataFrame(breakdown_data))

with tab_guide:
    st.header("Guide to Buying a Resale HDB Flat in Singapore")
    st.caption("This guide covers resale HDB flats only (not BTO, EC, or private property).")

    st.subheader("1. Eligibility")
    st.markdown("""
**Who can buy a resale HDB flat?**

| Scheme | Who Qualifies |
|--------|--------------|
| Public Scheme | Families with at least 1 Singapore Citizen or PR |
| Fiance/Fiancee Scheme | Engaged couples planning to marry within 3 months of completion |
| Single SC Scheme | Singles aged 35+ (Singapore Citizens only) |
| Joint Singles Scheme | Up to 4 single SCs jointly purchasing |
| Non-Citizen Spouse Scheme | SC with non-resident spouse (valid Visit/Work Pass) |

**Key conditions:**
- At least 1 buyer must be a Singapore Citizen (for SC + PR couples, the SC must be listed)
- PRs can buy resale after 3 years of PR status (under Public Scheme with another PR or SC)
- **No income ceiling** for purchasing a resale flat (income ceiling only applies to grants and HDB loans)
- Must not own other property locally or overseas (or dispose within 6 months of purchase)
- Private property owners under 55 must wait **15 months** after selling private property before buying resale HDB
""")

    st.subheader("2. Financing Options")
    st.markdown("""
| Feature | HDB Loan | Bank Loan |
|---------|----------|-----------|
| **Interest Rate** | 2.6% p.a. (fixed, pegged at CPF OA rate + 0.1%) | Market rates (typically 1.4% - 4%) |
| **LTV Limit** | 75% | 75% |
| **Downpayment** | 25% (can be fully paid from CPF OA and/or cash) | 25% (minimum 5% must be in cash) |
| **Max Tenure** | 25 years (or until age 65) | 30 years (or until age 65) |
| **Eligibility** | SC only; income ceiling $14,000 (families) / $7,000 (singles) | No income ceiling; subject to credit assessment |
| **Early Repayment** | No penalty | Typically 1.5% penalty during lock-in |
| **Refinancing** | Not allowed | Allowed after lock-in period |

**Note:** LTV was reduced from 80% to **75%** for HDB loans effective 20 August 2024.
""")

    st.subheader("3. Loan Limits (MSR & TDSR)")
    st.markdown("""
**Mortgage Servicing Ratio (MSR) - 30%**
- Monthly mortgage repayment cannot exceed **30%** of gross monthly income
- Applies to HDB and EC purchases only
- Calculated at **4% stress-test rate** (not your actual loan rate)

**Total Debt Servicing Ratio (TDSR) - 55%**
- Total monthly debt obligations cannot exceed **55%** of gross monthly income
- Applies to all property purchases
- Also uses 4% stress-test rate for the mortgage component

**Variable income:** Only 70% of bonuses, commissions, and overtime is counted.

For HDB resale with a bank loan, you must pass **both** MSR and TDSR.
""")

    st.subheader("4. Buyer's Stamp Duty (BSD)")
    st.markdown("""
| Purchase Price Band | Rate |
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

    st.subheader("5. CPF Usage for Resale HDB")
    st.markdown("""
CPF OA can be used for: downpayment, monthly mortgage, stamp duty, and legal fees.

**Limits:**
- Up to the **Valuation Limit** (lower of purchase price or valuation)
- Flat's remaining lease must cover youngest buyer to **age 95** for full CPF usage
- If remaining lease < 20 years, CPF cannot be used at all
- For HDB loans, you may retain up to **$20,000** in CPF OA
""")

    st.subheader("6. CPF Housing Grants (Resale)")
    st.markdown("""
| Grant | Families | Singles | Income Ceiling |
|-------|----------|---------|----------------|
| **CPF Housing Grant** | Up to $80,000 | Up to $40,000 | $14,000 / $7,000 |
| **Enhanced Housing Grant (EHG)** | Up to $80,000 | Up to $40,000 | $9,000 / $4,500 |
| **Proximity Housing Grant (PHG)** | Up to $30,000 | Up to $15,000 | No ceiling |

Maximum combined: up to **$190,000** for eligible families.
""")

    st.subheader("7. Buying Process")
    st.markdown("""
| Step | Action | Notes |
|------|--------|-------|
| 1 | Apply for HFE Letter | Mandatory before getting OTP |
| 2 | Search for flat & negotiate price | Use HDB Resale Flat Listing |
| 3 | Obtain OTP from seller | Option fee up to $1,000 |
| 4 | Exercise OTP | Within 21 calendar days |
| 5 | Submit Request for Value | Next working day after OTP |
| 6 | Confirm financing (HDB/bank) | Letter of Offer required |
| 7 | Submit resale application | Via HDB Flat Portal |
| 8 | Endorse documents & pay fees | ~3 weeks after acceptance |
| 9 | HDB approval | Within 28 working days |
| 10 | Completion - collect keys | ~8 weeks from acceptance |

Total timeline: approximately **8-12 weeks** from OTP to keys.
""")

    st.subheader("8. Costs Summary")
    st.markdown("""
| Cost Item | Amount | Payment |
|-----------|--------|---------|
| Option Fee + Exercise | Up to $5,000 | Cash |
| Downpayment (25%) | Varies | Cash + CPF |
| Buyer's Stamp Duty | Tiered | Cash or CPF |
| Resale Application Fee | $80 | Cash |
| Request for Value | $120 | Cash |
| Legal Fees | $2,000 - $3,000 | Cash or CPF |
| Stamp Duty on Mortgage | 0.4% of loan (max $500) | Cash |
| Cash-Over-Valuation (COV) | Negotiated | Cash only |
""")

    st.subheader("9. After Purchase")
    st.markdown("""
- **MOP:** 5 years (must live in flat, cannot rent out entire unit)
- **Room rental:** Allowed from Day 1 with HDB approval
- **Entire flat subletting:** Only after MOP
""")

    st.markdown("---")
    st.subheader("Official Sources")
    st.markdown("""
- [HDB - Resale Buying Process](https://www.hdb.gov.sg/buying-a-flat/resale-flats/process-for-buying-a-resale-flat)
- [HDB - Grants & Loan Eligibility](https://www.hdb.gov.sg/buying-a-flat/flat-grant-and-loan-eligibility)
- [IRAS - Buyer's Stamp Duty](https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/buyer's-stamp-duty-(bsd))
- [MAS - Property Loan Rules](https://www.mas.gov.sg/regulation/explainers/new-housing-loans)
- [CPF Board - Housing](https://www.cpf.gov.sg/member/growing-your-savings/saving-for-housing)
""")
    st.caption("Accurate as of 2026. Always verify with official sources before making financial decisions.")
