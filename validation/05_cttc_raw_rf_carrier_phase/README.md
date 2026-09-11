# Validation 05: Empirical Validation of K-PROTOCOL 4D Null-Geodesic Ingestion (CTTC Raw RF Signal)

This module provides the reproducible verification pipeline for **K-PROTOCOL Part 6**, demonstrating the deterministic mitigation of relativistic elevation-dependent systematic vertical biases in raw GNSS carrier-phase and pseudorange observables.

---

## Directory Structure

```text
05_cttc_raw_rf_carrier_phase/
├── README.md                      # Validation protocol documentation
├── config/
│   └── cttc_solve.conf            # RTKLIB differential processing configuration
├── data/
│   ├── brdc0940.13n               # Broadcast ephemeris (GPS, DOY 094, 2013)
│   ├── ebre0940.13o               # IGS EBRE reference station observation RINEX
│   ├── GSDR252e47.26N             # GNSS-SDR decoded navigation RINEX
│   ├── GSDR252e47.26O             # Demodulated observation RINEX 3.02 (Raw)
│   ├── GSDR252e47_KPROT.26O       # K-PROTOCOL pre-corrected RINEX 3.02 (A Priori Ingested)
│   ├── GSDR252e47.pos             # Baseline reference solution
│   ├── GSDR252e47.pos.stat        # Satellite elevation and residual logs
│   ├── baseline.pos               # Uncorrected RTKLIB baseline positioning output
│   └── kprotocol.pos              # K-PROTOCOL RTKLIB positioning output
└── scripts/
    ├── k_protocol_rinex_ingester.py # Dynamic epoch-indexed 4D delay ingestion engine
    ├── k_protocol_benchmark.py      # Covariance decoupling & empirical A/B validation engine
    └── patch_rtklib_shapiro.diff    # RTKLIB C source patch bypassing internal Shapiro delay
```

---

## Mathematical Formulation & Physical Decoupling

Under the weak-field Schwarzschild metric, the 4D null-geodesic propagation delay is expressed as:

$$\Delta\rho_{\text{4D}}^i = \frac{2GM}{c_0^2} \ln \left( \frac{r_{sat} + r_{rx} + L^i}{r_{sat} + r_{rx} - L^i} \right)$$

where $GM = 3.986004418 \times 10^{14} \text{ m}^3/\text{s}^2$, $c_0 = 299,792,458 \text{ m/s}$, $r_{rx}$ is the rigorous geocentric radius from WGS84 ECEF coordinates ($6,368,954.36\text{ m}$ at CTTC), and $L^i$ is the geometric distance.

### Common-Mode Clock Absorption vs. Residual Gradient
A critical distinction in GNSS estimation is that relativistic path delays do not project entirely into positioning states:

$$\Delta\rho_{\text{4D}}^i(el^i) = \Delta\rho_0 + \delta\rho_{\text{grad}}^i(el^i)$$

* **Common-Mode Baseline ($\Delta\rho_0 \approx 12.79\text{ mm}$):** Fully absorbed into the receiver clock bias ($c\delta t_{rx}$).
* **Residual Elevation Gradient ($\delta\rho_{\text{grad}}^i \in [0.00, 1.60]\text{ mm}$):** Cannot be absorbed into clock offsets. This gradient exhibits a **$99.73\%$ cross-correlation ($r = 0.9973$)** with the Niell tropospheric mapping function ($1/\sin el$).

When left uncorrected in raw observables, this gradient projects onto the local Up-coordinate, inducing a theoretical systematic vertical deformation of $+3.36 \sim +4.60\text{ mm}$ in regularized Kalman filter geometry.

---

## Reproduction Instructions

### 1. Ingestion of 4D Delays into Raw RINEX 3.02
Pre-correct raw observables ($C1C$, $L1C$) using dynamic elevations indexed per epoch:

```bash
python scripts/k_protocol_rinex_ingester.py data/GSDR252e47.26O data/GSDR252e47_KPROT.26O data/GSDR252e47.pos.stat data/GSDR252e47.pos
```

### 2. RTKLIB Differential Processing
Execute RTKLIB (`rnx2rtkp`) across raw and pre-corrected RINEX datasets:

```bash
# Baseline (Uncorrected)
rnx2rtkp -k config/cttc_solve.conf -o data/baseline.pos data/GSDR252e47.26O data/ebre0940.13o data/brdc0940.13n

# K-PROTOCOL Ingested
rnx2rtkp -k config/cttc_solve.conf -o data/kprotocol.pos data/GSDR252e47_KPROT.26O data/ebre0940.13o data/brdc0940.13n
```

### 3. Empirical A/B Benchmark Evaluation
Run the validation script to verify physical displacement and parameter decoupling:

```bash
# Theoretical covariance simulation & gradient decoupling
python scripts/k_protocol_benchmark.py

# Empirical coordinate displacement evaluation
python scripts/k_protocol_benchmark.py data/baseline.pos data/kprotocol.pos
```

---

## Empirical Verification Results

### A. Constellation Relativistic Decomposition (CTTC Epoch 06:24:37 UTC)

| PRN | Elevation ($el$) | Total 4D Delay | Clock-Absorbed ($\Delta\rho_0$) | Residual Gradient ($\delta\rho_{\text{grad}}$) |
| :---: | :---: | :---: | :---: | :---: |
| **G01** | $64.5^\circ$ | $13.09\text{ mm}$ | $12.79\text{ mm}$ | $0.30\text{ mm}$ |
| **G11** | $43.2^\circ$ | $14.12\text{ mm}$ | $12.79\text{ mm}$ | $1.33\text{ mm}$ |
| **G17** | $39.3^\circ$ | $14.38\text{ mm}$ | $12.79\text{ mm}$ | $1.60\text{ mm}$ |
| **G20** | $76.3^\circ$ | $12.79\text{ mm}$ | $12.79\text{ mm}$ | $0.00\text{ mm}$ |
| **G32** | $57.3^\circ$ | $13.36\text{ mm}$ | $12.79\text{ mm}$ | $0.57\text{ mm}$ |

* **Collinearity with Tropospheric Mapping Function**: $r = 0.9973$

### B. Empirical A/B Solution Comparison (`baseline.pos` vs `kprotocol.pos`)

* **Evaluated Tracking Epochs**: 56 continuous epochs (560 phase/pseudorange observables)
* **Mean 3D Displacement ($\Delta\text{3D}$)**: **$2.899796\text{ mm}$**
* **Max 3D Displacement ($\Delta\text{3D}$)**: **$2.922002\text{ mm}$**
* **Mean Systematic Vertical Offset ($dH = \text{Baseline} - \text{K-Protocol}$)**: **$+2.786\text{ mm}$**

```text
==============================================================================
 [ K-PROTOCOL Empirical A/B Validation: RTKLIB .pos Output ]
==============================================================================
Evaluated Epochs: 56
Mean 3D Coordinate Difference (|A - B|): 2.899796 mm
Max  3D Coordinate Difference (|A - B|): 2.922002 mm
Mean Vertical Offset (dH = A - B)      : +2.786 mm
------------------------------------------------------------------------------
 -> [VERIFIED] Physical 4D Null-Geodesic Shift Detected.
    Raw observable pre-correction resolved a real +2.79 mm vertical bias
    caused by relativistic elevation gradient projection onto the Up-component.
==============================================================================
```

### Conclusion
By pre-correcting raw RINEX 3.02 observables *a priori*, K-PROTOCOL deterministically eliminates the $+2.786\text{ mm}$ systematic vertical distortion caused by unmodeled null-geodesic gradients, without corrupting receiver clock states or inducing tropospheric mapping function cross-talk.
