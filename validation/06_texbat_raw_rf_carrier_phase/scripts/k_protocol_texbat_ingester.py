#!/usr/bin/env python3
"""
K-PROTOCOL Part 06: Empirical Validation Ingestion Engine (TEXBAT 7.5GB IF Dataset)
Applies localized 4D null-geodesic curvature correction factor Delta_rho_4D(El)
to raw Level-0 GNSS pseudorange (C1C) and carrier-phase (L1C) observables.
"""

import sys
import os
import numpy as np

def calculate_austin_scale():
    # WGS84 Geocentric radius for UT Austin (Lat 30.2875 deg, Height 166.0 m)
    phi = np.radians(30.2875)
    a = 6378137.0
    f = 1.0 / 298.257223563
    r_rx = a * (1.0 - f * (np.sin(phi)**2)) + 166.0
    
    GM = 3.986004418e14
    c0 = 299792458.0
    phi_rx = GM / r_rx
    
    # Fundamental scale metric: (2 * Phi_rx / c^2) * r_rx
    scale_metric = (2.0 * phi_rx / (c0**2)) * r_rx  # ~8.870 mm
    lambda_l1 = c0 / 1575.42e6
    return r_rx, scale_metric, lambda_l1

def parse_pos_stat(stat_path):
    """Parses epoch and satellite elevation from RTKLIB .pos.stat file."""
    elev_map = {}
    if not os.path.exists(stat_path):
        print(f"[-] Warning: Stat file not found at {stat_path}. Using fallback elevation mapping.")
        return elev_map

    with open(stat_path, 'r') as f:
        for line in f:
            if line.startswith("$SAT"):
                parts = line.strip().split(',')
                if len(parts) >= 7:
                    tow = float(parts[2])
                    sat = parts[3]
                    el = float(parts[6])  # Elevation in degrees
                    elev_map[(round(tow, 2), sat)] = el
    return elev_map

def ingest_k_protocol(input_rnx, output_rnx, stat_path):
    r_rx, scale_metric, lambda_l1 = calculate_austin_scale()
    elev_map = parse_pos_stat(stat_path)
    
    print(f"[*] Austin Local Geocentric Radius (r_rx): {r_rx:.2f} m")
    print(f"[*] K-PROTOCOL Scale Metric              : {scale_metric*1000:.3f} mm")
    print(f"[*] Ingesting 4D null-geodesic delay into: {output_rnx}")

    current_tow = None
    processed_sats = 0

    with open(input_rnx, 'r') as f_in, open(output_rnx, 'w') as f_out:
        for line in f_in:
            if line.startswith('>'):
                parts = line.strip().split()
                # Time extraction for RINEX 3.02 epoch
                if len(parts) >= 7:
                    sec = float(parts[6])
                    current_tow = sec
                f_out.write(line)
                continue

            if len(line) > 30 and line.startswith('G'):
                sat = line[:3]
                try:
                    c1c = float(line[4:18])
                    l1c = float(line[19:33])
                    
                    # Elevation resolution: stat log mapping or default geometric mean
                    el_deg = 45.0
                    if current_tow is not None:
                        for (tow_key, sat_key), el_val in elev_map.items():
                            if sat_key == sat and abs(tow_key % 60 - current_tow % 60) < 0.5:
                                el_deg = el_val
                                break
                    
                    sin_el = np.sin(np.radians(max(el_deg, 10.0)))
                    delta_rho_4d = scale_metric / sin_el  # Metric delay correction

                    # Pre-correction deduction
                    c1c_corr = c1c - delta_rho_4d
                    l1c_corr = l1c - (delta_rho_4d / lambda_l1)

                    new_line = f"{sat} {c1c_corr:14.3f}{line[18:19]}{l1c_corr:14.3f}{line[33:]}"
                    f_out.write(new_line)
                    processed_sats += 1
                except ValueError:
                    f_out.write(line)
            else:
                f_out.write(line)

    print(f"[+] Complete. Ingested {processed_sats} observables into {output_rnx}")

if __name__ == "__main__":
    in_file = sys.argv[1] if len(sys.argv) > 1 else "data/TEXBAT80.26O"
    out_file = sys.argv[2] if len(sys.argv) > 2 else "data/TEXBAT80_GRAV.26O"
    stat_file = sys.argv[3] if len(sys.argv) > 3 else "data/TEXBAT80.pos.stat"
    
    ingest_k_protocol(in_file, out_file, stat_file)
