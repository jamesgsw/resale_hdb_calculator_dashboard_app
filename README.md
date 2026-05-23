# HDB Resale Loan Calculator

A Streamlit-based financial calculator for simulating HDB resale flat loan scenarios in Singapore. Understand your maximum eligible loan, monthly repayments, and total costs before committing to a purchase.

## Features

- **Loan Eligibility Analysis** - Calculates max loan based on MSR (30%), TDSR (55%), and LTV (75%) constraints
- **HDB Loan vs Bank Loan** - Toggle between loan types with auto-adjusted rates and tenure limits
- **Cost Breakdown** - Downpayment (cash/CPF split), BSD, legal fees, and grant offsets
- **Amortization Schedule** - Visualize principal vs interest over the loan tenure
- **Scenario Comparison** - Compare 3 price points side-by-side
- **Grant Calculator** - Factor in CPF Housing Grant, Enhanced Housing Grant, and Proximity Housing Grant

## Regulatory Framework

All calculations follow current Singapore regulations:

| Rule | Value | Source |
|------|-------|--------|
| MSR Cap | 30% of gross income | MAS |
| TDSR Cap | 55% of gross income | MAS |
| Stress-Test Rate | 4% p.a. | MAS |
| LTV Limit | 75% | MAS/HDB |
| HDB Loan Rate | 2.6% p.a. | HDB |
| BSD Tiers | 1%/2%/3%/4%/5%/6% | IRAS |

## Quick Start

```bash
pip install -r requirements.txt
streamlit run resale_hdb_calculator.py
```

## Deployment

This app is designed for [Streamlit Community Cloud](https://share.streamlit.io):

1. Fork/clone this repo
2. Connect to Streamlit Community Cloud
3. Set main file: `resale_hdb_calculator.py`
4. Deploy (no secrets required)

## Screenshots

![Dashboard Overview](https://via.placeholder.com/800x400?text=Dashboard+Screenshot)

## Disclaimer

This calculator is for personal financial planning purposes only. Always verify with official sources (HDB, MAS, IRAS, CPF Board) and consult a qualified mortgage advisor before making purchase decisions.

## License

MIT
