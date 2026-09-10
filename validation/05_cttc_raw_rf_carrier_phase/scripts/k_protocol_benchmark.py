import argparse
import os
import sys
import numpy as np
from scipy.integrate import quad

# ==============================================================================
# 1. Path & CLI Configuration (Relative to Script Directory)
# ==============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "data", "benchmark_output.txt"))

parser = argparse.ArgumentParser(description="K-PROTOCOL 4D Analytic Benchmark")
parser.add_argument(
    "--save",
    action="store_true",
    help="Save benchmark output log to ../data/benchmark_output.txt"
)
parser.add_argument(
    "--output",
    type=str,
    default=DEFAULT_OUTPUT_PATH,
    help="Custom path to save benchmark log (default: ../data/benchmark_output.txt)"
)
args = parser.parse_args()

# ==============================================================================
# 2. Fundamental Physical Constants
# ==============================================================================
C0 = 299792458.0         # Speed of light in vacuum (m/s)
GM = 3.986004418e14      # Earth's gravitational parameter (m^3/s^2)

def get_potential(r_vec):
    """Compute gravitational potential Phi as a function of geocentric distance."""
    return -GM / np.linalg.norm(r_vec)

# ==============================================================================
# 3. Ground-Truth Universe: 4D Spacetime Path Integration
# ==============================================================================
class NatureUniverse:
    """
    Computes ground-truth Time of Flight (ToF) via numerical line integration
    along the null geodesic under the weak-field Schwarzschild metric.
    """
    @staticmethod
    def calculate_true_tof(sat_pos, rx_pos):
        L = np.linalg.norm(rx_pos - sat_pos)
        
        # Numerical integration: dt = dl / c_coord(r)
        def integrand(s):
            current_pos = sat_pos + s * (rx_pos - sat_pos)
            phi = get_potential(current_pos)
            c_coord = C0 * (1.0 + (2.0 * phi) / (C0**2))
            return L / c_coord

        tof_true, _ = quad(integrand, 0.0, 1.0, epsabs=1e-18)
        return tof_true

# ==============================================================================
# 4. Engine A: Legacy SI Standard (Iterative Joint Estimation)
# ==============================================================================
class LegacySIEngine:
    """
    Standard GNSS solver assuming flat Euclidean spacetime, invariant coordinate
    speed C0, and iterative Weighted Least Squares (WLS) state estimation.
    """
    @staticmethod
    def solve(sats, tofs_measured, initial_guess):
        x_state = np.zeros(4)
        x_state[:3] = initial_guess
        pseudoranges = tofs_measured * C0
        
        for _ in range(15):
            pos = x_state[:3]
            cb = x_state[3]
            ranges = np.linalg.norm(sats - pos, axis=1)
            dy = pseudoranges - (ranges + cb)
            
            H = np.zeros((len(sats), 4))
            H[:, :3] = -(sats - pos) / ranges[:, np.newaxis]
            H[:, 3] = 1.0
            
            delta = np.linalg.pinv(H.T @ H) @ H.T @ dy
            x_state += delta
            if np.linalg.norm(delta) < 1e-9:
                break
                
        final_pos = x_state[:3]
        clock_bias = x_state[3]
        residuals = pseudoranges - (np.linalg.norm(sats - final_pos, axis=1) + clock_bias)
        return final_pos, clock_bias / C0, residuals

# ==============================================================================
# 5. Engine B: K-PROTOCOL 4D Path Integral Engine
# ==============================================================================
class KProtocol4DEngine:
    """
    Phase 2: A priori closed-form 4D null-geodesic delay ingestion.
    Phase 3: Single-pass deterministic linear algebraic trilateration closure.
    """
    @staticmethod
    def solve(sats, tofs_measured, rx_approx_pos):
        corrected_ranges = np.zeros(len(sats))
        r_rx = np.linalg.norm(rx_approx_pos)
        
        # [Phase 2] A Priori 4D Conformal Ingestion
        # Analytic path integral along weak-field Schwarzschild null geodesic:
        # delta_rho = (2*GM / c0^2) * ln((r_sat + r_rx + L) / (r_sat + r_rx - L))
        for i, sat in enumerate(sats):
            r_sat = np.linalg.norm(sat)
            L_approx = np.linalg.norm(sat - rx_approx_pos)
            
            # Analytic 4D spacetime geometric delay
            arg = (r_sat + r_rx + L_approx) / (r_sat + r_rx - L_approx)
            delta_rho_4d = (2.0 * GM / (C0**2)) * np.log(arg)
            
            # Metric recovery: Extracting true Euclidean range
            corrected_ranges[i] = (C0 * tofs_measured[i]) - delta_rho_4d

        r = corrected_ranges
        
        # [Phase 3] Deterministic Single-Pass Algebraic Trilateration
        # Exact linear system without iterative regression
        A = 2.0 * (sats[1:] - sats[0])
        b = (r[0]**2 - r[1:]**2) + (np.sum(sats[1:]**2, axis=1) - np.sum(sats[0]**2))
        
        x_0 = np.linalg.pinv(A) @ b
        
        # [Phase 4] Residual Field and Bounding Radius Evaluation
        calculated_ranges = np.linalg.norm(sats - x_0, axis=1)
        r_residuals = np.abs(calculated_ranges - r)
        R_0 = np.max(r_residuals)
        
        return x_0, R_0, r_residuals

# ==============================================================================
# 6. Execution and Verification Pipeline
# ==============================================================================
def run_benchmark():
    output_lines = []
    def log(msg=""):
        print(msg)
        output_lines.append(msg)

    log("=" * 75)
    log(" [ K-PROTOCOL 4D ANALYTIC BENCHMARK ] ")
    log(" Validation of 4D Spacetime Geodesic Ingestion and Algebraic Closure")
    log("=" * 75)

    # Ground station (CTTC Rover) and satellite position vectors (ECEF, meters)
    true_rx_pos = np.array([4789010.0, 176510.0, 4195015.0])
    sats_pos = np.array([
        [ 15600000.0,  16500000.0,  15000000.0],
        [-18000000.0,  12000000.0,  16000000.0],
        [ 12000000.0, -17000000.0,  17000000.0],
        [-13000000.0, -15000000.0,  18000000.0]
    ])

    # Ground-truth ToF generation via 4D spacetime numerical path integration
    nature_tofs = np.zeros(len(sats_pos))
    for i, sat in enumerate(sats_pos):
        nature_tofs[i] = NatureUniverse.calculate_true_tof(sat, true_rx_pos)

    # Receiver a priori approximate position (~10 m nominal initial offset)
    approx_rx_pos = true_rx_pos + np.array([5.0, -5.0, 8.0])

    log("\n[A] Legacy SI Engine (Conventional WLS Standard):")
    pos_A, drift_A, res_A = LegacySIEngine.solve(sats_pos, nature_tofs, initial_guess=np.array([0, 0, 0]))
    err_A_mm = np.linalg.norm(pos_A - true_rx_pos) * 1000.0
    log(f" - 3D Position Error : {err_A_mm:.4f} mm")
    log(f" - Receiver Clock Bias: {drift_A:.4e} s (geometric distortion absorbed into clock)")
    log(f" - Residual RMS       : {np.sqrt(np.mean(res_A**2)) * 1000.0:.4f} mm")

    log("\n" + "-" * 75)

    log("[B] K-PROTOCOL 4D Engine (A Priori Geodesic Ingestion):")
    pos_B, r0_B, res_B = KProtocol4DEngine.solve(sats_pos, nature_tofs, approx_rx_pos)
    err_B_mm = np.linalg.norm(pos_B - true_rx_pos) * 1000.0
    log(" - Solver State       : Single-pass deterministic linear system (Non-iterative)")
    log(f" - 3D Position Error : {err_B_mm:.4f} mm")
    log(f" - Bounding Radius R0 : {r0_B * 1000.0:.4f} mm")
    log(f" - Residual RMS       : {np.sqrt(np.mean(res_B**2)) * 1000.0:.4f} mm")
    log("=" * 75)

    # Save output log if requested
    if args.save:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines) + "\n")
        print(f"\n[Saved] Output log written to: {args.output}")

if __name__ == "__main__":
    run_benchmark()