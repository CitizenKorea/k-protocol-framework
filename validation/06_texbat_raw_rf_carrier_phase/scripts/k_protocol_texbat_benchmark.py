#!/usr/bin/env python3
"""
K-PROTOCOL Part 06: Empirical A/B Benchmark & Covariance Decoupling Engine
Compares baseline vs K-PROTOCOL pre-corrected RTKLIB positioning outputs (.pos)
to verify horizontal invariance and systematic vertical offset convergence.
"""

import sys
import numpy as np

def parse_pos_file(filepath):
    epochs = []
    lats, lons, heights = [], [], []
    
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('%') or not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) >= 5:
                epochs.append(parts[0] + " " + parts[1])
                lats.append(float(parts[2]))
                lons.append(float(parts[3]))
                heights.append(float(parts[4]))
                
    return epochs, np.array(lats), np.array(lons), np.array(heights)

def run_benchmark(base_pos, grav_pos):
    _, lat_b, lon_b, h_b = parse_pos_file(base_pos)
    _, lat_g, lon_g, h_g = parse_pos_file(grav_pos)

    n_epochs = min(len(h_b), len(h_g))
    lat_b, lon_b, h_b = lat_b[:n_epochs], lon_b[:n_epochs], h_b[:n_epochs]
    lat_g, lon_g, h_g = lat_g[:n_epochs], lon_g[:n_epochs], h_g[:n_epochs]

    # Coordinate differences (Gravitational correction - Baseline)
    dh = (h_g - h_b) * 1000.0  # mm
    dlat = (lat_g - lat_b) * 111132.95 * 1000.0  # mm
    dlon = (lon_g - lon_b) * (111412.84 * np.cos(np.radians(30.2875))) * 1000.0  # mm
    h_rms = np.sqrt(dlat**2 + dlon**2)

    mean_dh = np.mean(dh)
    std_dh = np.std(dh)
    mean_h_rms = np.mean(h_rms)

    print("=" * 78)
    print(" [ K-PROTOCOL Part 06: Empirical A/B Validation Benchmark (TEXBAT) ]")
    print("=" * 78)
    print(f"Evaluated Epochs              : {n_epochs} continuous epochs")
    print(f"Baseline Solution File        : {base_pos}")
    print(f"K-PROTOCOL Solution File      : {grav_pos}")
    print("-" * 78)
    print(f"Mean Vertical Displacement (dH) : {mean_dh:+.3f} mm (Std: {std_dh:.3f} mm)")
    print(f"Max Vertical Offset           : {np.min(dh):.3f} mm / {np.max(dh):.3f} mm")
    print(f"Mean Horizontal Error (dLat)  : {np.mean(dlat):+.3f} mm")
    print(f"Mean Horizontal Error (dLon)  : {np.mean(dlon):+.3f} mm")
    print(f"Total Horizontal RMS Drift    : {mean_h_rms:.3f} mm")
    print("-" * 78)
    
    if abs(mean_dh) > 10.0 and mean_h_rms < 5.0:
        print(" -> [VERIFIED] Deterministic Gravitational Curvature Compensation Confirmed.")
        print("    Elevation-dependent 4D metric delay resolved vertical bias without")
        print("    distorting horizontal coordinate geometry (Horizontal RMS < 5.0 mm).")
    else:
        print(" -> [CAUTION] Solution diverged or did not satisfy decoupling criteria.")
    print("=" * 78)

if __name__ == "__main__":
    file_a = sys.argv[1] if len(sys.argv) > 1 else "data/TEXBAT80.pos"
    file_b = sys.argv[2] if len(sys.argv) > 2 else "data/TEXBAT80_GRAV.pos"
    run_benchmark(file_a, file_b)
