# K-PROTOCOL Real-Data Validation Engines

This directory contains real-data validation scripts that process standard IGS (International GNSS Service) observation files to verify K-PROTOCOL's metric scale recovery performance against Legacy SI models.

## Scripts Overview

1. `real_data_multilateration.py`
   - **Focus**: Evaluates 3D positioning accuracy using local gravitational potential ($\Phi = g \cdot h$) derived from the Somigliana equation and Free-Air correction.
   - **Precision**: 60-digit Arbitrary Precision (`decimal.getcontext().prec = 60`).

2. `atmosphere_cleared_engine.py`
   - **Focus**: Eliminates external atmospheric noise (Dual-Frequency Ionosphere-Free combination $P_3$ + Saastamoinen Tropospheric delay model) prior to metric scale adjustment.
   - **Purpose**: Proves that the residual discrepancy originates from geometric metric scale distortion ($\hat{K} \neq 0$), not environmental atmospheric noise.

## Required Input Data Files

Place the raw IGS format data files directly in this directory (or the root execution path):

- **Observation Files**: `*.*o*`, `*.rnx*`, `*.crx*` (RINEX format)
- **Precision Orbit Files**: `*.SP3*`, `*.sp3*` (IGS Precise Orbit)
- **Precision Clock Files**: `*.CLK*`, `*.clk*` (IGS Satellite & Station Clock)

*Note: Gzip-compressed files (`.gz`, `.Z`) are supported automatically.*

## How to Run

Navigate to this directory and execute either script:

```bash
# Run Local Gravity Potential Validation
python real_data_multilateration.py

# Run Atmosphere-Cleared Dual-Frequency Validation
python atmosphere_cleared_engine.py
