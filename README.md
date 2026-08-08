# K-PROTOCOL: Universal Conformal Framework for Precision Metrology

[![ORCID](https://img.shields.io/badge/ORCID-0009--0004--3627--6997-A6CE39?logo=orcid&logoColor=white)](https://orcid.org/0009-0004-3627-6997)
[![DOI](https://img.shields.io/badge/DOI-10.5281/zenodo.21768477-blue?logo=zenodo&logoColor=white)](https://doi.org/10.5281/zenodo.21846407)
![Patent Pending](https://img.shields.io/badge/Status-Patent_Pending-red?style=flat-square)

> **"Breaking the $10^{-18}$ Metrological Wall of Despair"**  
> A deterministic software architecture that replaces legacy post-hoc statistical filtering with a priori conformal scale alignment.

---

## The Metrological Blind Spot (The Problem)

Modern precision metrology relies on a "Triple Lock" framework: enforcing UTC globally and fixing the standard speed of light ($c_0$) as a rigid constant on a flat Cartesian grid ($g_{ij}=\delta_{ij}$).

While computationally convenient, this enforces a mathematical contradiction when fusing multi-point datasets across disjoint gravitational potentials ($\Phi$). The legacy SI system inadvertently forces relativistic spacetime distortions to be absorbed by spatial coordinates.

When tracking stations attempt to merge data using traditional Kalman filters or Least-Squares regression, the geometric scale mismatches are merged with environmental noise, completely **obfuscating physical causality**.

---

## The K-PROTOCOL (The Solution)

The K-PROTOCOL does not rely on ad-hoc statistical overfitting. Instead, it extracts the exact non-linear principles of General Relativity and injects them directly into the **Data Ingestion Layer**.

By mapping the localized gravitational potential ($\Phi_i \approx g_i \cdot h_i$) as an operational proxy, the core engine executes a single scalar transformation:

$$c_{coord} = c_0 \sqrt{\frac{1+\frac{2\Phi}{c_0^2}}{1-\frac{2\Phi}{c_0^2}}}$$

This conformal rescaling effectively eliminates the geometric metric error term ($\hat{K}=0$) *before* baseline processing begins.

---

## Universal 4-Stage Architecture

1. **Phase 1: Ingestion** - Binds raw Time-of-Flight (ToF) / Phase data with local $\Phi$.
2. **Phase 2: Conformal Rescaling** - Neutralizes metric distortion ($\hat{K}=0$) via the Math Engine.
3. **Phase 3: Single-Pass Algebraic Solver** - Bypasses heavy filtering loops, converging to a deterministic Bounding Circle.
4. **Phase 4: Residual Decoupling** - Isolates stochastic hardware noise ($N_{stochastic}$) from structural environmental modulations ($S_{env}$).

---

## Quick Start & Demo Execution

```bash
# 1. Clone the repository
git clone [https://github.com/CitizenKorea/k-protocol-framework.git](https://github.com/CitizenKorea/k-protocol-framework.git)
cd k-protocol-framework

# 2. Run the core pipeline demo
python k_protocol_framework.py
```

### Expected Terminal Output

```text
===================================================================
K-PROTOCOL DEMO: Overcoming 10^-18 Metrological Wall of Despair
===================================================================

[STEP 1] Data Ingestion (Raw ToF & Metadata via Ingest Layer)
  -> Node: KRISS_Daejeon  | Alt:      70.0m | Phi: 686.4655
  -> Node: NIST_Boulder   | Alt:    1655.0m | Phi: 16230.0058
  -> Node: GNSS_Sat_01    | Alt: 35786000.0m | Phi: 350940788.0700

[STEP 2] A Priori Conformal Rescaling (Core Engine)
-------------------------------------------------------------------
  Target Node : KRISS_Daejeon (Optical_Clock)
    - Legacy SI Assumption Error : 1.725341e-13 meters
    - K-PROTOCOL Action          : Rescaled ToF based on potential
    - Geometric Metric Status    : [ K = 0.0 ] (Neutralized)
-------------------------------------------------------------------
  Target Node : NIST_Boulder (Optical_Clock)
    - Legacy SI Assumption Error : 4.079234e-12 meters
    - K-PROTOCOL Action          : Rescaled ToF based on potential
    - Geometric Metric Status    : [ K = 0.0 ] (Neutralized)
-------------------------------------------------------------------

[STEP 3] Inverse Environmental Tracking
  By eliminating structural metric errors (K=0), causality is achieved.

  [+] Total Input Residual  : 0.125 ns
  [-] Hardware Noise Floor  : 0.050 ns (Stochastic Boundary)
  [=] Pure Environment Sig  : 0.075 ns -> Tropospheric/Solar Wind

===================================================================
CONCLUSION:
Legacy statistical smoothing (Kalman Filters) obfuscates causality.
K-PROTOCOL's scalar transformation is a strict prerequisite for
next-gen mega-constellations, 6G, and interplanetary baselines.
===================================================================
```

---

## Empirical Validation Suites (`validation/`)

The `validation/` directory provides complete, reproducible empirical verification pipelines for K-PROTOCOL across different observational scales:

* **`validation/01_igs_real_data/`**: Global multi-lateration processing engine using international IGS tracking station networks and precise orbit/clock files (SP3/CLK).
* **`validation/02_abc_framework/`**: Theoretical & numerical A-B-C metric scaling framework generating the publication-ready PDF report (`K_PROTOCOL_Empirical_Report.pdf`).
* **`validation/03_hawaii_local_baseline/`**: Empirical proof across dynamic Mauna Kea elevation differentials ($\Delta h \approx 3,750\text{ m}$), demonstrating L1 carrier-phase noise reduction and zero-residual loop closure.
