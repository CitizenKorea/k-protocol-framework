"""
===============================================================================
K-PROTOCOL: ATMOSPHERE-CLEARED REAL DATA INVERSE MULTILATERATION ENGINE
Precision : Decimal 60 Digits + Dual-Freq Iono-Free (P3) + Saastamoinen Tropo
===============================================================================
"""

import os
import glob
import gzip
import math
from decimal import Decimal, getcontext
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

getcontext().prec = 60

C_0 = Decimal("299792458")
A_WGS84 = Decimal("6378137.0")
E2_WGS84 = Decimal("0.00669437999014")

GE_WGS84 = Decimal("9.7803253359")
K_WGS84 = Decimal("0.00193185265241")

# GPS Frequency definitions (Hz)
FREQ_L1 = Decimal("1575420000.0")
FREQ_L2 = Decimal("1227600000.0")

# Iono-Free Coefficients (C1 = f1^2 / (f1^2 - f2^2), C2 = -f2^2 / (f1^2 - f2^2))
C_IF1 = (FREQ_L1**2) / (FREQ_L1**2 - FREQ_L2**2)
C_IF2 = -(FREQ_L2**2) / (FREQ_L1**2 - FREQ_L2**2)

class GeoMathEngine:
    @staticmethod
    def ecef_to_lat_alt(x: Decimal, y: Decimal, z: Decimal):
        """Converts ECEF coordinates (X, Y, Z) to Geodetic Latitude and Altitude."""
        p = (x**2 + y**2).sqrt()
        if p == Decimal("0"):
            lat = Decimal(str(math.pi/2)) if z > 0 else Decimal(str(-math.pi/2))
            alt = abs(z) - A_WGS84 * (Decimal("1") - E2_WGS84).sqrt()
            return lat, alt
        
        lat_rad = (z / (p * (Decimal("1") - E2_WGS84))).copy_abs()
        if z < Decimal("0"): lat_rad = -lat_rad
        
        alt = Decimal("0")
        for _ in range(10):
            sin_lat = Decimal(str(math.sin(float(lat_rad))))
            N = A_WGS84 / (Decimal("1") - E2_WGS84 * sin_lat**2).sqrt()
            alt = p / Decimal(str(math.cos(float(lat_rad)))) - N
            lat_old = lat_rad
            lat_rad = Decimal(str(math.atan(float(z / p * (Decimal("1") + E2_WGS84 * N * sin_lat / z)))))
            if abs(lat_rad - lat_old) < Decimal("1e-15"):
                break
        return lat_rad, alt

    @staticmethod
    def calc_local_gravity(lat_rad: Decimal, alt: Decimal) -> Decimal:
        """Calculates true local gravitational acceleration (Somigliana + Free-Air Correction)."""
        sin_lat = Decimal(str(math.sin(float(lat_rad))))
        sin2_lat = sin_lat**2
        num = GE_WGS84 * (Decimal("1") + K_WGS84 * sin2_lat)
        den = (Decimal("1") - E2_WGS84 * sin2_lat).sqrt()
        gamma_0 = num / den
        fac = Decimal("0.000003086") * alt
        return gamma_0 - fac

    @staticmethod
    def calc_k_factor(phi_node, phi_ref=Decimal("0")):
        c_sq = C_0**2
        num = Decimal("1") + (Decimal("2") * phi_ref / c_sq)
        den = Decimal("1") + (Decimal("2") * phi_node / c_sq)
        return (num / den).sqrt()

    @staticmethod
    def saastamoinen_tropo_delay(sta_lat_rad: Decimal, sta_alt: Decimal, sat_pos, sta_pos) -> Decimal:
        """Tropospheric delay correction model (Saastamoinen Model)."""
        dx = sat_pos[0] - sta_pos[0]
        dy = sat_pos[1] - sta_pos[1]
        dz = sat_pos[2] - sta_pos[2]
        dist = (dx**2 + dy**2 + dz**2).sqrt()
        
        # Calculate elevation angle
        r_sta = (sta_pos[0]**2 + sta_pos[1]**2 + sta_pos[2]**2).sqrt()
        dot = (sta_pos[0]*dx + sta_pos[1]*dy + sta_pos[2]*dz) / (r_sta * dist)
        sin_el = max(Decimal("0.05"), dot) # Minimum 3-degree elevation angle cutoff
        
        # Standard sea-level pressure and temperature approximation
        p_mb = Decimal("1013.25") * (Decimal("1") - Decimal("0.000022557") * sta_alt)**Decimal("5.2568")
        zhd = Decimal("0.0022768") * p_mb / sin_el
        return zhd

    @staticmethod
    def calculate_distance(x1, y1, z1, x2, y2, z2):
        return ((x1 - x2)**2 + (y1 - y2)**2 + (z1 - z2)**2).sqrt()

class UniversalDataParser:
    @staticmethod
    def parse_clk_file(clk_files, target_sat, target_dt):
        sat_clk = None
        sta_clks = {}
        for filepath in clk_files:
            open_func = gzip.open if filepath.endswith(".gz") or filepath.endswith(".Z") else open
            try:
                with open_func(filepath, 'rt', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if line.startswith("AS ") or line.startswith("AR "):
                            parts = line.split()
                            if len(parts) >= 10:
                                rec_type = parts[0]
                                name = parts[1]
                                try:
                                    yr, mo, dy = int(parts[2]), int(parts[3]), int(parts[4])
                                    hr, mn, sc = int(parts[5]), int(parts[6]), int(float(parts[7]))
                                    dt = (yr, mo, dy, hr, mn, sc)

                                    if dt == target_dt:
                                        bias_sec = Decimal(parts[9].replace('D', 'E').replace('d', 'e'))
                                        if rec_type == "AS" and (name == target_sat or name == f"G{int(target_sat[1:]):02d}"):
                                            sat_clk = bias_sec
                                        elif rec_type == "AR":
                                            sta_id = name[:4].upper()
                                            sta_clks[sta_id] = bias_sec
                                except Exception: pass
            except Exception: pass
        return sat_clk, sta_clks

    @staticmethod
    def scan_dual_freq_observations(obs_files):
        """Extracts L1/L2 dual-frequency observations and computes Ionosphere-Free (P3/IF) combination."""
        obs_database = defaultdict(dict)
        for file_path in obs_files:
            sta_id = os.path.basename(file_path)[:4].upper()
            open_func = gzip.open if file_path.endswith(".gz") or file_path.endswith(".Z") else open
            try:
                with open_func(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
                    in_header = True
                    sta_x, sta_y, sta_z = None, None, None
                    current_dt = None
                    for line in f:
                        if "END OF HEADER" in line:
                            in_header = False
                            continue
                        if in_header:
                            if "APPROX POSITION XYZ" in line:
                                parts = line.split()
                                try:
                                    sta_x, sta_y, sta_z = Decimal(parts[0]), Decimal(parts[1]), Decimal(parts[2])
                                except Exception: pass
                            continue

                        if line.startswith(">"):
                            parts = line[1:].split()
                            try:
                                current_dt = (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), int(float(parts[5])))
                            except Exception: current_dt = None
                            continue

                        if current_dt and sta_x is not None:
                            line_str = line.strip()
                            sat_id = None
                            if line_str.startswith("G") and len(line_str) > 3 and line_str[1:3].isdigit():
                                sat_id = line_str[:3]
                            if sat_id:
                                parts = line_str.split()
                                # Extract multi-frequency pseudoranges (C1, C2 / P1, P2)
                                vals = []
                                for part in parts[1:]:
                                    try:
                                        v = Decimal(part)
                                        if Decimal("18000000") <= v <= Decimal("28000000"):
                                            vals.append(v)
                                    except Exception: pass
                                
                                if len(vals) >= 2:
                                    p1, p2 = vals[0], vals[1]
                                    # Ionosphere-Free (Iono-Free) linear combination formula
                                    p_if = C_IF1 * p1 + C_IF2 * p2
                                    obs_database[(current_dt, sat_id)][sta_id] = ((sta_x, sta_y, sta_z), p_if)
            except Exception: pass
        return obs_database

    @staticmethod
    def parse_sp3_orbit(sp3_files, target_sat, target_dt):
        for filepath in sp3_files:
            current_dt = None
            open_func = gzip.open if filepath.endswith(".gz") or filepath.endswith(".Z") else open
            try:
                with open_func(filepath, 'rt', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if line.startswith("*"):
                            parts = line[1:].split()
                            try:
                                current_dt = (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), int(float(parts[5])))
                            except Exception: current_dt = None
                        elif line.startswith("P") and current_dt == target_dt:
                            parts = line.split()
                            sat_id = parts[1] if parts[0] == "P" else parts[0][1:]
                            if not sat_id.startswith("G") and sat_id.isdigit():
                                sat_id = f"G{int(sat_id):02d}"
                            
                            if sat_id == target_sat:
                                x_idx = 2 if parts[0] == "P" else 1
                                try:
                                    x = Decimal(parts[x_idx].replace('D', 'E').replace('d', 'e')) * 1000
                                    y = Decimal(parts[x_idx+1].replace('D', 'E').replace('d', 'e')) * 1000
                                    z = Decimal(parts[x_idx+2].replace('D', 'E').replace('d', 'e')) * 1000
                                    return x, y, z
                                except Exception: pass
            except Exception: pass
        return None

class InverseMultilateration3DSolver:
    @staticmethod
    def solve_satellite_position_3d(station_coords, geom_distances):
        xs_est = Decimal("15000000.0")
        ys_est = Decimal("15000000.0")
        zs_est = Decimal("15000000.0")

        for _ in range(30):
            A = []
            L = []
            for sta_id, (st_x, st_y, st_z) in station_coords.items():
                p_geom = geom_distances[sta_id]
                r = GeoMathEngine.calculate_distance(st_x, st_y, st_z, xs_est, ys_est, zs_est)
                if r == Decimal("0"): continue
                
                dx = (xs_est - st_x) / r
                dy = (ys_est - st_y) / r
                dz = (zs_est - st_z) / r
                
                res = p_geom - r
                A.append([float(dx), float(dy), float(dz)])
                L.append(float(res))

            if len(A) < 3: return None, None, None

            AT = list(zip(*A))
            ATA = [[sum(AT[i][k] * A[k][j] for k in range(len(A))) for j in range(3)] for i in range(3)]
            ATL = [sum(AT[i][k] * L[k] for k in range(len(A))) for i in range(3)]
            
            M = [ATA[i] + [ATL[i]] for i in range(3)]
            try:
                for i in range(3):
                    pivot = M[i][i]
                    for j in range(i, 4): M[i][j] /= pivot
                    for k in range(3):
                        if k != i:
                            factor = M[k][i]
                            for j in range(i, 4): M[k][j] -= factor * M[i][j]
                
                dx_s = Decimal(str(M[0][3]))
                dy_s = Decimal(str(M[1][3]))
                dz_s = Decimal(str(M[2][3]))

                xs_est += dx_s
                ys_est += dy_s
                zs_est += dz_s

                if abs(dx_s) < Decimal("0.0001") and abs(dy_s) < Decimal("0.0001") and abs(dz_s) < Decimal("0.0001"):
                    break
            except Exception: return None, None, None

        sta_residuals = {}
        for sta_id, (st_x, st_y, st_z) in station_coords.items():
            r = GeoMathEngine.calculate_distance(st_x, st_y, st_z, xs_est, ys_est, zs_est)
            res = float(geom_distances[sta_id] - r)
            sta_residuals[sta_id] = res

        rms_residual = math.sqrt(sum(r**2 for r in sta_residuals.values()) / len(sta_residuals))
        return (xs_est, ys_est, zs_est), rms_residual, sta_residuals

def run_pipeline():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    print("="*85)
    print(" K-PROTOCOL ATMOSPHERE-CLEARED REAL DATA INVERSE MULTILATERATION ENGINE")
    print("="*85)

    obs_files = (glob.glob(os.path.join(base_dir, "*.*o*")) + 
                 glob.glob(os.path.join(base_dir, "*.rnx*")) + 
                 glob.glob(os.path.join(base_dir, "*.crx*")))
    sp3_files = (glob.glob(os.path.join(base_dir, "*.SP3*")) + 
                 glob.glob(os.path.join(base_dir, "*.sp3*")))
    clk_files = (glob.glob(os.path.join(base_dir, "*.CLK*")) + 
                 glob.glob(os.path.join(base_dir, "*.clk*")))

    obs_db = UniversalDataParser.scan_dual_freq_observations(obs_files)

    best_key = None
    max_sta_count = 0
    for key, stas in obs_db.items():
        if len(stas) > max_sta_count:
            sp3_pos = UniversalDataParser.parse_sp3_orbit(sp3_files, key[1], key[0])
            if sp3_pos:
                max_sta_count = len(stas)
                best_key = key

    if not best_key or max_sta_count < 4:
        print(f"\n[NOTICE] Insufficient stations tracking L1/L2 dual-frequency simultaneously.")
        return

    target_dt, target_sat = best_key
    station_data = obs_db[best_key]

    sat_clk_sec, sta_clks_sec = UniversalDataParser.parse_clk_file(clk_files, target_sat, target_dt)
    sp3_true_pos = UniversalDataParser.parse_sp3_orbit(sp3_files, target_sat, target_dt)

    print(f"\n[STEP 1] Ionosphere-Free (Iono-Free) Combination Satellite/Epoch Lock")
    print(f" -> Target Sat / Epoch : {target_sat} / {target_dt}")
    print(f" -> SP3 Orbit Ground Truth : X={sp3_true_pos[0]:.3f}, Y={sp3_true_pos[1]:.3f}, Z={sp3_true_pos[2]:.3f} m")

    station_coords = {}
    geom_obs_si = {}
    geom_obs_k = {}

    sat_lat_rad, sat_alt = GeoMathEngine.ecef_to_lat_alt(*sp3_true_pos)
    sat_g_local = GeoMathEngine.calc_local_gravity(sat_lat_rad, sat_alt)
    k_sat = GeoMathEngine.calc_k_factor(sat_g_local * sat_alt)

    print(f"\n[STEP 2] Atmospheric Noise (Ionosphere + Troposphere) Removal & K-Factor Calculation")
    for sta_id, (coords, p_if) in station_data.items():
        r_clk_sec = sta_clks_sec.get(sta_id, Decimal("0"))
        s_clk_sec = sat_clk_sec if sat_clk_sec else Decimal("0")
        
        # 1. Clock bias correction
        p_clean = p_if - C_0 * (r_clk_sec - s_clk_sec)

        # 2. Tropospheric delay correction deduction
        sta_lat_rad, sta_alt = GeoMathEngine.ecef_to_lat_alt(*coords)
        tropo_m = GeoMathEngine.saastamoinen_tropo_delay(sta_lat_rad, sta_alt, sp3_true_pos, coords)
        p_geom = p_clean - tropo_m

        station_coords[sta_id] = coords
        geom_obs_si[sta_id] = p_geom

        # 3. K-Factor scale adjustment
        g_local = GeoMathEngine.calc_local_gravity(sta_lat_rad, sta_alt)
        k_sta = GeoMathEngine.calc_k_factor(g_local * sta_alt)
        k_ratio = k_sta / k_sat
        
        geom_obs_k[sta_id] = p_geom * (Decimal("1") / k_ratio)
        
        print(f" -> [{sta_id}] Iono-Free Range = {p_if:.3f}m | Tropo Delay = {tropo_m:.3f}m | Clean Geometric Range = {p_geom:.3f}m")

    print(f"\n[STEP 3] Running 3D Inverse Multilateration post Atmospheric Noise Removal...")
    est_pos_si, rms_si, res_si = InverseMultilateration3DSolver.solve_satellite_position_3d(station_coords, geom_obs_si)
    est_pos_k, rms_k, res_k = InverseMultilateration3DSolver.solve_satellite_position_3d(station_coords, geom_obs_k)

    err_3d_si = float(GeoMathEngine.calculate_distance(*est_pos_si, *sp3_true_pos))
    err_3d_k = float(GeoMathEngine.calculate_distance(*est_pos_k, *sp3_true_pos))

    print("\n[STEP 4 DATA] Sphere Residuals post Atmospheric Removal")
    print("-" * 85)
    print(f" {'Station ID':<15} | {'Legacy SI Residual (m)':<25} | {'K-PROTOCOL Residual (m)':<25}")
    print("-" * 85)
    for sta_id in station_coords.keys():
        print(f" {sta_id:<15} | {res_si[sta_id]:^+25.6f} | {res_k[sta_id]:^+25.6f}")
    print("-" * 85)

    print("\n[STEP 5 DATA] 3D Absolute Position Estimation Error vs SP3 Truth (post Atmospheric Removal)")
    print("-" * 85)
    print(f" [Lane A : Legacy SI]   3D Position Error : {err_3d_si:.6f} m")
    print(f" [Lane B : K-PROTOCOL]  3D Position Error : {err_3d_k:.6f} m")
    print(f" -> K-PROTOCOL Actual Improvement (Post Atmosphere-Cleared) : {err_3d_si - err_3d_k:+.6f} m")
    print("-" * 85)

if __name__ == "__main__":
    run_pipeline()
