# 04. BIPM Optical Clock Global Validation Pipeline

## Overview
This module implements an automated, **Zero-Assumption** validation pipeline for international primary and secondary frequency standards (PSFS) published by the **BIPM (Bureau International des Poids et Mesures)**. 

It demonstrates the algebraic cancellation of the relativistic metric gap ($u_{\text{redshift}}$) across disjoint national metrology institutes (KRISS, NIST, SYRTE) under **K-PROTOCOL**, evaluating the resulting systematic uncertainty ($u_B$) according to **ISO/IEC Guide 98-3 (GUM / RSS)** standards.

---

## Key Features

1. **Zero-Assumption Automated Data Filtering**
   - Ingests raw report data from the BIPM PSFS database.
   - Automatically filters out incomplete reports lacking essential physical sub-components (e.g., missing $u_{\text{Density}}$, $u_{\text{Lattice}}$, or $u_{\text{Redshift}}$) without post-hoc statistical tampering.
2. **GUM / RSS Evaluation Engine**
   - Re-evaluates combined systematic uncertainty ($u_B$) before and after applying K-PROTOCOL conformal rescaling ($u_{\text{redshift}} \to 0.00$).
3. **Automated Audit Report Generation**
   - Generates an executive, publication-ready 2-page PDF report (`K_PROTOCOL_Verification_Report_Clean.pdf`) containing the filtering log, full calculation matrix, and high-resolution comparison chart.

---

## Global Validation Results

| Metrology Institute | Altitude (m) | Legacy $u_{\text{redshift}}$ | Legacy Total $u_B$ | **K-PROTOCOL Total $u_B$** | **Absolute Reduction ($\Delta u_B$)** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **KRISS** (South Korea) | ~75m | $0.45 \times 10^{-18}$ | $1.477 \times 10^{-18}$ | **$1.407 \times 10^{-18}$** | **$-0.070 \times 10^{-18}$** |
| **NIST** (USA) | ~1,650m | $0.65 \times 10^{-18}$ | $1.204 \times 10^{-18}$ | **$1.014 \times 10^{-18}$** | **$-0.191 \times 10^{-18}$** |
| **SYRTE** (France) | ~60m | $0.42 \times 10^{-18}$ | $1.258 \times 10^{-18}$ | **$1.185 \times 10^{-18}$** | **$-0.072 \times 10^{-18}$** |

* **Key Observation**: High-altitude nodes (e.g., NIST Boulder at 1,650m) exhibit the largest uncertainty reduction ($-0.191 \times 10^{-18}$), confirming that K-PROTOCOL specifically resolves elevation-dependent relativistic metric distortions while preserving non-relativistic thermodynamic noises (e.g., BBR effect $u_{\text{BBR}}$).

---

## Requirements & Execution

### Prerequisites
```bash
pip install pandas numpy matplotlib reportlab
