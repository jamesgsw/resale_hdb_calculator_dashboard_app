# HDB Resale Loan Calculator - Context

> AI assistant context file for the HDB Resale Loan Calculator Streamlit app.

## Project Overview

| Item | Value |
|------|-------|
| **App** | `resale_hdb_calculator.py` - Single-file Streamlit app |
| **Deployment** | Streamlit Community Cloud (via GitHub) |
| **Stack** | Python 3.10+, Streamlit, Plotly, Pandas |

```bash
pip install streamlit plotly pandas
streamlit run resale_hdb_calculator.py
```

---

## Purpose

A cashflow and loan simulation tool for buyers evaluating HDB resale flat purchases in Singapore. Allows users to input a resale price and understand:
- Maximum eligible loan (constrained by MSR, TDSR, LTV)
- Monthly repayment and total interest
- Upfront costs (downpayment, BSD, legal fees)
- Amortization schedule over the loan tenure
- Side-by-side scenario comparison

---

## Loan Type Options

| Loan Type | Interest Rate | Max Tenure | LTV | Downpayment |
|-----------|--------------|------------|-----|-------------|
| **HDB Loan** | 2.6% p.a. (fixed, CPF OA + 0.1%) | 25 years | 75% | 25% (all CPF/cash) |
| **Bank Loan** | Market rate (user-adjustable) | 30 years | 75% | 25% (min 5% cash + 20% CPF) |

---

## Regulatory Framework (Singapore)

### BSD Rates (IRAS, effective 15 Feb 2023)

| Band | Rate |
|------|------|
| First $180K | 1% |
| Next $180K ($180K-$360K) | 2% |
| Next $640K ($360K-$1M) | 3% |
| Next $500K ($1M-$1.5M) | 4% |
| Next $1.5M ($1.5M-$3M) | 5% |
| Above $3M | 6% |

### MAS Loan Rules

| Rule | Value | Applicability |
|------|-------|---------------|
| **MSR Cap** | 30% of gross monthly income | HDB & EC (bank loans) |
| **TDSR Cap** | 55% of gross monthly income | All property loans |
| **Stress-test Rate** | 4% p.a. (or prevailing, whichever higher) | Both MSR & TDSR calculations |
| **LTV Limit** | 75% | Both HDB and bank loans (since Aug 2024) |

### Variable Income

- Only 70% of variable income (bonuses, commissions, freelance) counted for MSR/TDSR
- Formula: `effective_income = fixed_income + variable_income * 0.70`

### CPF Housing Grants (Resale)

| Grant | Max (Families) | Max (Singles) | Income Ceiling |
|-------|---------------|---------------|----------------|
| CPF Housing Grant | $80,000 | $40,000 | $14,000 |
| Enhanced Housing Grant (EHG) | $80,000 | $40,000 | $9,000 |
| Proximity Housing Grant (PHG) | $30,000 | $15,000 | None |

---

## Calculation Logic

### Maximum Loan Determination

The actual loan is the minimum of three caps:

```
max_loan = min(MSR_max, TDSR_max, LTV_max)

MSR_max:  (income * 0.30) * [(1+r)^n - 1] / [r * (1+r)^n]
TDSR_max: (income * 0.55 - existing_debts) * [(1+r)^n - 1] / [r * (1+r)^n]
LTV_max:  effective_price * 0.75

Where: r = stress_test_rate / 12, n = tenure_years * 12
```

### Monthly Repayment (Standard Amortization)

```
monthly = P * [r(1+r)^n] / [(1+r)^n - 1]
Where: P = loan_amount, r = annual_rate / 12, n = tenure * 12
```

### Effective Purchase Price

```
effective_price = resale_price - total_grants
```

### Downpayment

```
downpayment = effective_price * 25%
Bank Loan: min 5% cash + up to 20% CPF
HDB Loan: entire 25% from CPF and/or cash
```

### Total Upfront Cash Required

```
cash_needed = cash_downpayment + BSD + legal_fees (~$3,000)
```

---

## Dashboard Sections

1. **Loan Overview** - 5 KPI metrics (price, loan, monthly repay, total repay, total interest)
2. **Loan Eligibility** - MSR/TDSR/LTV max loan amounts, binding constraint indicator, utilization %
3. **Cost Breakdown** - Table of upfront costs with cash/CPF split and sufficiency status
4. **Repayment Schedule** - Stacked bar chart (principal vs interest by year) + declining balance curve
5. **Scenario Comparison** - 3 price scenarios (+/-$50K) with key metrics
6. **Regulatory Reference** - Expandable table of all rules and sources

---

## Sidebar Inputs

| Section | Input | Default | Range |
|---------|-------|---------|-------|
| Property | Resale HDB Price | $600,000 | $100K - $2M |
| Loan Type | HDB Loan / Bank Loan | Bank Loan | Radio |
| Income | Fixed Monthly Income | $8,000 | $0+ |
| Income | Variable Monthly Income | $0 | $0+ |
| Income | Existing Monthly Debts | $0 | $0+ |
| Loan | Interest Rate | 4.0% (bank) / 2.6% (HDB) | 1-6% |
| Loan | Tenure | 25 years | 5 - 25/30 |
| Assets | CPF OA Balance | $100,000 | $0+ |
| Assets | Cash Available | $100,000 | $0+ |
| Grants | CPF Housing Grant | $0 | $0 - $80K |
| Grants | Enhanced Housing Grant | $0 | $0 - $80K |
| Grants | Proximity Housing Grant | $0 | $0 - $30K |

---

## Key Definitions

| Term | Definition |
|------|------------|
| **MSR** | Mortgage Servicing Ratio - max 30% of income for HDB/EC mortgage |
| **TDSR** | Total Debt Servicing Ratio - max 55% of income for ALL debts |
| **LTV** | Loan-to-Value - max 75% of purchase price (or valuation, whichever lower) |
| **Stress-test Rate** | 4% rate banks must use for qualification (not actual loan rate) |
| **BSD** | Buyer's Stamp Duty - progressive tax on property purchase |
| **MSR Utilization** | Actual monthly repayment as % of MSR cap |
| **TDSR Utilization** | (Repayment + existing debts) as % of TDSR cap |
| **Binding Constraint** | Whichever of MSR/TDSR/LTV produces the lowest max loan |

---

## Validation Sources

All calculations validated against official sources:
- **BSD**: IRAS Stamp Duty Calculator (iras.gov.sg)
- **MSR/TDSR**: MAS Notice 645 & MAS property loan guidelines
- **LTV**: MAS (75% since Aug 2024 for both HDB and bank loans)
- **HDB Loan Rate**: HDB official (CPF OA rate + 0.1% = 2.6%)
- **Grants**: HDB.gov.sg CPF Housing Grants page

---

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect GitHub repo
4. Set main file: `resale_hdb_calculator.py`
5. No secrets required (pure client-side calculator)

---

## Future Enhancements

- [ ] Age-based tenure calculation (max tenure = 65 - buyer_age, or 30, whichever lower)
- [ ] CPF OA monthly deduction simulation (auto-pay from OA)
- [ ] Cash-over-valuation (COV) handling
- [ ] Renovation loan add-on
- [ ] Comparison with renting (rent vs buy breakeven)
- [ ] Historical HDB resale price reference by town/flat type
- [ ] Multi-scenario slider (compare 5+ scenarios)
