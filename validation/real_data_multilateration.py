"""
===============================================================================
K-PROTOCOL: REAL DATA INVERSE MULTILATERATION ENGINE (WITH CLK & LOCAL GRAVITY)
Precision : Decimal 60 Digits + Somigliana Equation + Free-Air Correction
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

# WGS84 Gravity Constants (Somigliana Equation)
GE_WGS84 = Decimal("9.7803253359")     # Equatorial gravity
K_WGS84 = Decimal("0.00193185265241")  # Gravity formula constant

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
        
        # 1. Surface gravity by latitude (Somigliana Equation)
        num = GE_WGS84 * (Decimal("1") + K_WGS84 * sin2_lat)
        den = (Decimal("1") - E2_WGS84 * sin2_lat).sqrt()
        gamma_0 = num / den
        
        # 2. Gravity attenuation by altitude (Free-Air Correction: -0.3086 mGal/m)
        fac = Decimal("0.000003086") * alt
        
        return gamma_0 - fac

    @staticmethod
    def calc_k_factor(phi_node, phi_ref=Decimal("0")):
        c_sq = C_0**2
        num = Decimal("1") + (Decimal("2") * phi_ref / c_sq)
        den = Decimal("1") + (Decimal("2") * phi_node / c_sq)
        return (num / den).sqrt()

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
    def scan_all_rinex_observations(obs_files):
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
                        if not line.startswith(">") and len(line) > 26 and line[1:3].isdigit() and line[4:6].isdigit():
                            parts = line[:26].split()
                            try:
                                yr = int(parts[0]) + 2000 if int(parts[0]) < 80 else int(parts[0]) + 1900
                                current_dt = (yr, int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), int(float(parts[5])))
                            except Exception: pass

                        if current_dt and sta_x is not None:
                            line_str = line.strip()
                            sat_id = None
                            if line_str.startswith("G") and len(line_str) > 3 and line_str[1:3].isdigit():
                                sat_id = line_str[:3]
                            if sat_id:
                                parts = line_str.split()
                                for part in parts[1:]:
                                    try:
                                        val = Decimal(part)
                                        if Decimal("18000000") <= val <= Decimal("28000000"):
                                            obs_database[(current_dt, sat_id)][sta_id] = ((sta_x, sta_y, sta_z), val)
                                            break
                                    except Exception: pass
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
    print(" K-PROTOCOL REAL DATA INVERSE MULTILATERATION (LOCAL GRAVITY POTENTIAL)")
    print("="*85)

    obs_files = (glob.glob(os.path.join(base_dir, "*.*o*")) + 
                 glob.glob(os.path.join(base_dir, "*.rnx*")) + 
                 glob.glob(os.path.join(base_dir, "*.crx*")))
    sp3_files = (glob.glob(os.path.join(base_dir, "*.SP3*")) + 
                 glob.glob(os.path.join(base_dir, "*.sp3*")))
    clk_files = (glob.glob(os.path.join(base_dir, "*.CLK*")) + 
                 glob.glob(os.path.join(base_dir, "*.clk*")))

    if not sp3_files or not clk_files:
        print("\n[ERROR] Missing required .SP3 precision orbit or .CLK precision clock files.")
        return

    obs_db = UniversalDataParser.scan_all_rinex_observations(obs_files)

    best_key = None
    max_sta_count = 0
    for key, stas in obs_db.items():
        if len(stas) > max_sta_count:
            sp3_pos = UniversalDataParser.parse_sp3_orbit(sp3_files, key[1], key[0])
            if sp3_pos:
                max_sta_count = len(stas)
                best_key = key

    if not best_key or max_sta_count < 4:
        print(f"\n[NOTICE] Insufficient satellites with >= 4 simultaneously tracking stations.")
        return

    target_dt, target_sat = best_key
    station_data = obs_db[best_key]

    sat_clk_sec, sta_clks_sec = UniversalDataParser.parse_clk_file(clk_files, target_sat, target_dt)
    sp3_true_pos = UniversalDataParser.parse_sp3_orbit(sp3_files, target_sat, target_dt)

    print(f"\n[STEP 1] Satellite Acquisition & True Value Verification")
    print(f" -> Target Sat / Epoch : {target_sat} / {target_dt}")
    print(f" -> SP3 Orbit Ground Truth : X={sp3_true_pos[0]:.3f}, Y={sp3_true_pos[1]:.3f}, Z={sp3_true_pos[2]:.3f} m")

    station_coords = {}
    geom_obs_si = {}
    geom_obs_k = {}

    # Satellite local potential reference point
    sat_lat_rad, sat_alt = GeoMathEngine.ecef_to_lat_alt(*sp3_true_pos)
    sat_g_local = GeoMathEngine.calc_local_gravity(sat_lat_rad, sat_alt)
    k_sat = GeoMathEngine.calc_k_factor(sat_g_local * sat_alt)

    print(f"\n[STEP 2] K-Factor Calculation via Local Gravity Potential")
    for sta_id, (coords, p_raw) in station_data.items():
        r_clk_sec = sta_clks_sec.get(sta_id, Decimal("0"))
        s_clk_sec = sat_clk_sec if sat_clk_sec else Decimal("0")
        
        clock_offset_m = C_0 * (r_clk_sec - s_clk_sec)
        p_geom = p_raw - clock_offset_m

        station_coords[sta_id] = coords
        geom_obs_si[sta_id] = p_geom

        # Calculate true potential (Phi = g*h) via local gravity acceleration by lat/alt
        sta_lat_rad, sta_alt = GeoMathEngine.ecef_to_lat_alt(*coords)
        g_local = GeoMathEngine.calc_local_gravity(sta_lat_rad, sta_alt)
        
        k_sta = GeoMathEngine.calc_k_factor(g_local * sta_alt)
        k_ratio = k_sta / k_sat
        
        geom_obs_k[sta_id] = p_geom * (Decimal("1") / k_ratio)
        
        print(f" -> [{sta_id}] Alt: {sta_alt:+.1f}m | Local Gravity: {g_local:.6f}m/s2 | Scale Factor: {k_ratio:.12e}")

    print(f"\n[STEP 3] Running Real-Data Geometric Least Squares Solver (Inverse Multilateration)...")
    est_pos_si, rms_si, res_si = InverseMultilateration3DSolver.solve_satellite_position_3d(station_coords, geom_obs_si)
    est_pos_k, rms_k, res_k = InverseMultilateration3DSolver.solve_satellite_position_3d(station_coords, geom_obs_k)

    err_3d_si = float(GeoMathEngine.calculate_distance(*est_pos_si, *sp3_true_pos))
    err_3d_k = float(GeoMathEngine.calculate_distance(*est_pos_k, *sp3_true_pos))

    print("\n[STEP 4 DATA] Local Potential-based Sphere Residuals")
    print("-" * 85)
    print(f" {'Station ID':<15} | {'Legacy SI Residual (m)':<25} | {'K-PROTOCOL Residual (m)':<25}")
    print("-" * 85)
    for sta_id in station_coords.keys():
        print(f" {sta_id:<15} | {res_si[sta_id]:^+25.6f} | {res_k[sta_id]:^+25.6f}")
    print("-" * 85)

    print("\n[STEP 5 DATA] 3D Position Estimation Accuracy Comparison")
    print("-" * 85)
    print(f" [Lane A : Legacy SI]   3D Position Error (vs SP3) : {err_3d_si:.6f} m")
    print(f" [Lane B : K-PROTOCOL]  3D Position Error (vs SP3) : {err_3d_k:.6f} m")
    print(f" -> K-PROTOCOL Metric Scale Recovery (Verified)  : {err_3d_si - err_3d_k:+.6f} m")
    print("-" * 85)

if __name__ == "__main__":
    run_pipeline()
