# K-PROTOCOL: Local Gravitational Potential Empirical Baseline (Hawaii Network)

This directory provides real-world empirical validation of the **K-PROTOCOL conformal metric framework** using high-precision IGS GNSS observation data across a steep local gravitational potential gradient in Hawaii.

---

## 🏔️ Network Topography & Gravitational Differential

The experimental setup utilizes three co-located IGS tracking stations across significant elevation differentials ($\Delta h \approx 3,750\text{ m}$), subjecting raw carrier-phase and pseudorange observables to localized metric scale distortion:

* **`MKEA` (Mauna Kea)**: Altitude $\approx 3,755\text{ m}$ ($\Phi = 9.789 \times 3,755\text{ m}^2/\text{s}^2$)
* **`P041` (Intermediate)**: Altitude $\approx 1,655\text{ m}$ ($\Phi = 9.802 \times 1,655\text{ m}^2/\text{s}^2$)
* **`HNLC` (Honolulu Sea-Level)**: Altitude $\approx 5\text{ m}$ ($\Phi = 9.789 \times 5\text{ m}^2/\text{s}^2$)

---

## 📁 Directory Contents & Validation Engines

### 1. Analysis Scripts
* **`carrier_phase_variance.py`**: Evaluates double-difference L1 carrier-phase residual variance reduction without parameter fitting.
* **`timeseries_24h_analysis.py`**: Executes a 24-hour continuous (2,880 epochs) dynamic metric scale evaluation and outputs `k_protocol_24h_timeseries.png`.
* **`real_data_closed_loop.py`**: Performs a 3-station closed-loop integration test ($MKEA \rightarrow P041 \rightarrow HNLC \rightarrow MKEA$) to verify zero-residual loop closure.
* **`real_geometric_scale.py`**: Computes exact ECEF geometric metric scale shifts derived from station header coordinates.
* **`uncompress.py`**: Utility script to decompress CRINEX (`.24d`) observation files into standard RINEX (`.24o`) formats.

### 2. Observation Datasets & Artifacts
* **`mkea1000.24o`**, **`hnlc1000.24o`**, **`p0411000.24o`**: Standard IGS RINEX observation files (Day 100, 2024).
* **`k_protocol_24h_timeseries.png`**: High-resolution visualization chart of the 24-hour continuous metric shift.

---

## 🛠️ Reproduction & Execution Guide

### 1. Dependencies
Ensure the required geospatial and mathematical libraries are installed:

```bash
pip install georinex matplotlib pandas numpy hatanaka
