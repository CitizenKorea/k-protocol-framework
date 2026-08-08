# K-PROTOCOL: A-B-C Metric Framework Validation Engine

This directory provides the theoretical, mathematical, and empirical validation suite for the **K-PROTOCOL conformal metric framework**. It quantitatively evaluates three distinct gravitational scale treatment paradigms under dynamic orbital geometries.

---

## 📸 Key Findings & Metric Comparison

The validation engine simulates a 24-epoch dynamic satellite pass ($20,000\text{ km} \sim 26,000\text{ km}$) under localized gravitational potential ($\Phi_{\text{MKEA}}$) to evaluate spatial residual convergence and receiver clock stability.

| Method | Treatment Mechanism | Spatial Residual | Clock State | Scientific Verdict |
| :--- | :--- | :---: | :---: | :--- |
| **[A] Legacy SI** | Forces invariant speed of light ($c_0$). Ignores local spatial curvature. | $\sim +0.0189\text{ mm}$ | Corrupted ($8.18 \times 10^{-13}\text{ s/s}$) | **FAILED:** Overfits spatial scale mismatch into receiver clock drift. |
| **[B] Post-hoc Patch** | Applies time-dilation factor ($gh/c_0^2$) to spatial ranges post-processing. | $\sim +0.0095\text{ mm}$ | Corrupted ($8.18 \times 10^{-13}\text{ s/s}$) | **FAILED:** Unresolves exactly 50% of spatial residual; clock remains polluted. |
| **[C] K-PROTOCOL** | Ingests conformal spatial metric scaling ($2gh/c_0^2$) **a priori** at data ingest. | **`0.0000 mm`** | **`0.00 Clean`** | **PROVEN:** Complete elimination of spatial residual and total clock purification (**Zero Free Parameters**). |

---

## 📁 Repository Contents

* **`k_protocol_abc.py`**: Self-contained Python script executing the mathematical engine, dynamic epoch calculations, Matplotlib visualization, and automated PDF report compilation.
* **`K_PROTOCOL_Empirical_Report.pdf`**: Publication-ready empirical proof report generated directly by `k_protocol_abc.py`.

---

## 🛠️ How to Reproduce & Run

This script requires zero external dataset downloads and runs as an independent deterministic engine.

### 1. Requirements
Ensure you have the required Python dependencies installed:

```bash
pip install numpy pandas matplotlib reportlab
