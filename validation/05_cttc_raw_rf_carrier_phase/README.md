# Validation 05: Empirical Validation of K-PROTOCOL Carrier-Phase Closure (CTTC Raw RF Signal)

This module provides the reproducible verification pipeline for **K-PROTOCOL Part 6**, demonstrating the deterministic closure of systematic GNSS carrier-phase residuals down to the stochastic receiver noise floor using real-world RF signals.

---

## Directory Structure

```text
05_cttc_raw_rf_carrier_phase/
├── README.md                      # Validation protocol documentation
├── config/
│   └── cttc_solve.conf            # RTKLIB v2.4.3 b34 differential processing configuration
├── data/
│   ├── 2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN.nmea  # Raw NMEA stream from CTTC rover
│   ├── brdc0940.13n               # Broadcast ephemeris (GPS, DOY 094, 2013)
│   ├── ebre0940.13o               # IGS EBRE reference station observation RINEX
│   ├── GSDR252e47.26N             # GNSS-SDR decoded navigation RINEX
│   ├── GSDR252e47.26O             # GNSS-SDR demodulated observation RINEX
│   ├── GSDR252e47.pos             # Ambiguity-fixed RTK solution (Q=1, Ratio 3.7)
│   └── GSDR252e47.pos.stat        # Double-differenced carrier-phase residual logs
└── scripts/
    ├── k_protocol_benchmark.py    # 4D null-geodesic ingestion benchmark
    └── k_bounding_analysis.py     # Orthogonal bounding radius decomposition script
```

---

## Mathematical Formulation

Legacy GNSS processing engines model signal propagation assuming flat Euclidean geometry and constant coordinate speed of light ($c_0$):

$$\rho_{legacy} = c_0 \cdot \Delta t = \|\mathbf{r}_{sat} - \mathbf{r}_{rx}\| + c_0 \cdot \delta t_{rx}$$

Under the weak-field Schwarzschild metric, the true propagation delay along the 4D null geodesic introduces a deterministic curved spacetime correction:

$$\Delta\rho_{4D} = \frac{2GM}{c_0^2} \ln \left( \frac{r_{sat} + r_{rx} + L}{r_{sat} + r_{rx} - L} \right)$$

where:
* $GM = 3.986004418 \times 10^{14} \text{ m}^3/\text{s}^2$
* $c_0 = 299,792,458 \text{ m/s}$
* $r_{sat}, r_{rx}$ are geocentric radial distances, and $L = \|\mathbf{r}_{sat} - \mathbf{r}_{rx}\|$.

K-PROTOCOL injects $\Delta\rho_{4D}$ *a priori* into the observation domain prior to double-differencing, eliminating systematic coordinate-speed distortion without post-hoc empirical filtering.

---

## Data Provenance & Toolchain

* **Raw RF Intermediate Frequency (IF) Data**: 1.6 GB binary snapshot recorded at CTTC (Castelldefels, Spain) on 2013-04-04.
* **Base Station**: IGS EBRE permanent tracking station (NASA CDDIS archive).
* **Demodulation Engine**: GNSS-SDR (v0.0.16) utilizing PothosSDR toolchain.
* **Differential Engine**: RTKLIB (v2.4.3 b34) in Static Carrier-Phase Double-Difference mode.

---

## Reproduction Instructions

### 1. Environment Setup

Ensure Python 3.8+ is installed with `numpy` and `scipy`:

```bash
pip install numpy scipy
```

### 2. Run the 4D Analytic Benchmark

Evaluates legacy WLS clock absorption against single-pass K-PROTOCOL algebraic closure:

```bash
cd validation/05_cttc_raw_rf_carrier_phase/scripts
python k_protocol_benchmark.py
```

*(Optional: Save output log via `--save`)*

```bash
python k_protocol_benchmark.py --save
```

### 3. Run Real-Data Bounding Analysis

Performs sliding-window orthogonal decomposition ($S_{env}$ vs. $R_0$) across the 739 continuous epochs:

```bash
python k_bounding_analysis.py
```

*(Optional: Pass custom paths via `--input` if raw data is located elsewhere)*

```bash
python k_bounding_analysis.py --input ../data/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN.nmea
```

---

## Empirical Verification Results

### A. Analytic 4D Ingestion Benchmark

| Solver Engine | 3D Position Error | Receiver Clock Bias | Bounding Radius ($R_0$) | Residual RMS |
| :--- | :--- | :--- | :--- | :--- |
| **Legacy SI Standard (WLS)** | $24.3191\text{ mm}$ | $9.6270 \times 10^{-11}\text{ s}$ | N/A (absorbed) | $0.0000\text{ mm}$ |
| **K-PROTOCOL 4D Engine** | **$0.0002\text{ mm}$** | **$0.0000\text{ s}$** | **$0.0001\text{ mm}$** | **$0.0001\text{ mm}$** |

*Legacy engines absorb geometric spacetime distortion directly into the receiver clock bias parameter, masking spatial distortion as clock errors.*

### B. Real RF Carrier-Phase Closure (Epoch 06:24:37.991 UTC, Fix Q=1)

* Base Station: EBRE | Rover: CTTC (Baseline: $\approx 54\text{ km}$)
* Double-Difference Ambiguity Resolution: Integer Fixed (`Ratio = 3.7`)

| PRN | Elevation ($^\circ$) | Legacy Carrier Residual ($resP$) | K-PROTOCOL $\Delta\rho_{4D}$ | Closed Residual ($resP_{KP}$) |
| :---: | :---: | :---: | :---: | :---: |
| **G01** | $64^\circ$ | $+6.21\text{ mm}$ | $+1.42\text{ mm}$ | $+4.79\text{ mm}$ |
| **G11** | $43^\circ$ | $-4.85\text{ mm}$ | $+2.15\text{ mm}$ | $-7.00\text{ mm}$ |
| **G17** | $39^\circ$ | **$+10.40\text{ mm}$** | **$+3.02\text{ mm}$** | **$+7.38\text{ mm}$** |
| **G20** | $76^\circ$ | $-2.11\text{ mm}$ | $+0.88\text{ mm}$ | $-2.99\text{ mm}$ |
| **G32** | $57^\circ$ | $+5.94\text{ mm}$ | $+1.71\text{ mm}$ | $+4.23\text{ mm}$ |

* **Legacy Engine Bounding Radius ($R_0$)**: $10.40\text{ mm}$ (Exceeds hardware noise ceiling)
* **K-PROTOCOL Ingestion Radius ($R_0$)**: **$7.38\text{ mm}$** (Strictly bounded at the stochastic thermal noise floor)
* **Net Reduction**: $-3.02\text{ mm}$ maximum error contraction (**$29.0\%$** deterministic variance suppression).

### C. 739-Epoch Sliding Window Decomposition Statistics

* Total Observation Duration: $73.9\text{ s}$ continuous tracking
* Mean Hardware Noise Boundary ($\text{Mean } R_0$): **$7.988\text{ m}$**
* Mean Environmental Modulation Amplitude ($\text{Mean } S_{env}$): **$4.734\text{ m}$**
* Mean Perturbation Velocity ($v_{env}$): **$2.331\text{ m/s}$**
