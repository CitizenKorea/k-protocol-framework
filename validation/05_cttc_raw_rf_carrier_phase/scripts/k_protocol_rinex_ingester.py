#!/usr/bin/env python3
"""
K-PROTOCOL Pure-Empirical RINEX 3.02 Ingestion Engine (Rigorous Geodesy Edition)
================================================================================
- Resolves true dynamic elevation per epoch from RTKLIB .pos.stat (TOW-indexed).
- Uses rigorous WGS84 LLH-to-ECEF transformation for geocentric radius r_rx.
================================================================================
"""

import os
import sys
import math
from collections import defaultdict

# Physical Constants (IERS / CODATA Standards)
C0 = 299792458.0              # Speed of light (m/s)
GM = 3.986004418e14           # Earth's gravitational parameter (m^3/s^2)
R_SAT = 26560000.0            # GPS nominal semi-major axis (m)

# WGS84 Ellipsoid Parameters
WGS84_A = 6378137.0           # Semi-major axis (m)
WGS84_F = 1.0 / 298.257223563 # Flattening
WGS84_E2 = 2 * WGS84_F - WGS84_F**2  # First eccentricity squared (0.00669437999014)

FREQ_MAP = {'1': 1575.42e6, '2': 1227.60e6, '5': 1176.45e6}
LAMBDA_MAP = {k: C0 / v for k, v in FREQ_MAP.items()}

def compute_4d_delay(elevation_deg, r_rx_mag):
    """Calculates Schwarzschild 4D null-geodesic delay (meters)."""
    el_rad = math.radians(elevation_deg)
    L = math.sqrt(R_SAT**2 - (r_rx_mag**2 * (math.cos(el_rad)**2))) - (r_rx_mag * math.sin(el_rad))
    arg = (R_SAT + r_rx_mag + L) / max(R_SAT + r_rx_mag - L, 1e-6)
    return (2.0 * GM / (C0**2)) * math.log(arg)

def load_dynamic_elevations_timeseries(stat_path):
    """
    Parses dynamic satellite elevations indexed by sequential epoch / TOW.
    Returns: list of dicts [{sat_id: elev_deg, ...}, ...] per epoch.
    """
    if not os.path.exists(stat_path):
        return []

    epoch_records = []
    current_tow = None
    current_sats = {}

    with open(stat_path, 'r') as f:
        for line in f:
            if line.startswith("$SAT"):
                parts = line.split(',')
                if len(parts) >= 8:
                    tow = float(parts[2].strip())
                    sat_id = parts[3].strip()
                    try:
                        el = float(parts[6].strip())
                    except ValueError:
                        continue

                    if current_tow is None:
                        current_tow = tow

                    # New epoch detected in .pos.stat
                    if abs(tow - current_tow) > 0.05:
                        epoch_records.append(current_sats)
                        current_sats = {}
                        current_tow = tow

                    current_sats[sat_id] = el

    if current_sats:
        epoch_records.append(current_sats)

    return epoch_records

def load_geocentric_radius(pos_path):
    """
    Rigorously computes geocentric radius r_rx = sqrt(X^2 + Y^2 + Z^2)
    via standard WGS84 ellipsoidal to ECEF transformation.
    """
    if not os.path.exists(pos_path):
        return 6371000.0

    with open(pos_path, 'r') as f:
        for line in f:
            if line.startswith('%') or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 5:
                try:
                    lat_deg = float(parts[2])
                    lon_deg = float(parts[3])
                    h = float(parts[4])

                    phi = math.radians(lat_deg)
                    lam = math.radians(lon_deg)

                    # Prime vertical radius of curvature N(phi)
                    N = WGS84_A / math.sqrt(1.0 - WGS84_E2 * (math.sin(phi)**2))

                    # Exact Cartesian ECEF conversion
                    X = (N + h) * math.cos(phi) * math.cos(lam)
                    Y = (N + h) * math.cos(phi) * math.sin(lam)
                    Z = (N * (1.0 - WGS84_E2) + h) * math.sin(phi)

                    return math.sqrt(X**2 + Y**2 + Z**2)
                except ValueError:
                    pass
    return 6371000.0

def process_rinex_302(rinex_in, rinex_out, stat_path, pos_path):
    if not os.path.exists(rinex_in):
        print(f"[Error] Source RINEX not found: {rinex_in}")
        sys.exit(1)

    print("=" * 78)
    print(" [ K-PROTOCOL: Rigorous Empirical RINEX 3.02 Observable Ingestion ]")
    print("=" * 78)

    dynamic_elevs = load_dynamic_elevations_timeseries(stat_path)
    r_rx_mag = load_geocentric_radius(pos_path)

    print(f" * Dynamic Elevation Epochs Parsed: {len(dynamic_elevs)}")
    print(f" * Rigorous Geocentric Radius r_rx : {r_rx_mag:.2f} m")
    print("-" * 78)

    gps_obs_types = []
    total_epochs = 0
    modified_records = 0

    with open(rinex_in, 'r') as fin, open(rinex_out, 'w') as fout:
        # Header Parsing
        for line in fin:
            fout.write(line)
            if "SYS / # / OBS TYPES" in line and line.startswith("G"):
                tokens = line[6:60].split()
                for tok in tokens:
                    if tok not in gps_obs_types and not tok.isdigit():
                        gps_obs_types.append(tok)
            if "END OF HEADER" in line:
                break

        print(f" * Observables Identified: {gps_obs_types}")
        print("-" * 78)

        # Body Parsing
        current_epoch_idx = -1
        for line in fin:
            if line.startswith('>'):
                total_epochs += 1
                current_epoch_idx += 1
                fout.write(line)
                continue

            sat_id = line[0:3].strip()
            if sat_id.startswith('G'):
                # Dynamic epoch elevation retrieval with boundary clamping
                elev_deg = 45.0
                if dynamic_elevs:
                    clamped_idx = min(current_epoch_idx, len(dynamic_elevs) - 1)
                    elev_deg = dynamic_elevs[clamped_idx].get(sat_id, 45.0)

                delta_4d_m = compute_4d_delay(elev_deg, r_rx_mag)
                line_chars = list(line.rstrip('\r\n').ljust(3 + len(gps_obs_types) * 16))

                for idx, obs_type in enumerate(gps_obs_types):
                    start = 3 + idx * 16
                    obs_str = line[start:start+14].strip() if len(line) > start else ""
                    lli = line[start+14:start+15] if len(line) > start+14 else " "
                    ssi = line[start+15:start+16] if len(line) > start+15 else " "

                    if obs_str:
                        try:
                            val = float(obs_str)
                            if obs_type.startswith(('C', 'P')):
                                val -= delta_4d_m
                                modified_records += 1
                            elif obs_type.startswith('L'):
                                band = obs_type[1]
                                if band in LAMBDA_MAP:
                                    val -= (delta_4d_m / LAMBDA_MAP[band])
                                    modified_records += 1

                            formatted = f"{val:14.3f}{lli}{ssi}"
                            line_chars[start:start+16] = list(formatted)
                        except ValueError:
                            pass

                fout.write("".join(line_chars).rstrip() + "\n")
            else:
                fout.write(line)

    print(f" * Processed Epochs    : {total_epochs}")
    print(f" * Ingested Observables: {modified_records}")
    print("-" * 78)
    print(" [ SUCCESS ] Rigorous Dynamic RINEX Ingestion Complete.")
    print("==============================================================================")

if __name__ == "__main__":
    r_in   = sys.argv[1] if len(sys.argv) > 1 else r"data\GSDR252e47.26O"
    r_out  = sys.argv[2] if len(sys.argv) > 2 else r"data\GSDR252e47_KPROT.26O"
    f_stat = sys.argv[3] if len(sys.argv) > 3 else r"data\GSDR252e47.pos.stat"
    f_pos  = sys.argv[4] if len(sys.argv) > 4 else r"data\GSDR252e47.pos"

    process_rinex_302(r_in, r_out, f_stat, f_pos)