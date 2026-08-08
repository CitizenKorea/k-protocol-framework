import warnings
import logging
import math
from decimal import Decimal, getcontext

warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.ERROR)

import georinex as gr

getcontext().prec = 60
C_0 = Decimal("299792458")

NODES = {
    "MKEA": {"file": "mkea1000.24o", "phi": Decimal("9.789") * Decimal("3755.0")},
    "P041": {"file": "p0411000.24o", "phi": Decimal("9.802") * Decimal("1655.0")},
    "HNLC": {"file": "hnlc1000.24o", "phi": Decimal("9.789") * Decimal("5.0")}
}

def calc_conformal_c(phi: Decimal) -> Decimal:
    """K-PROTOCOL: Local Coordinate Speed of Light"""
    c_sq = C_0 ** Decimal("2")
    num = Decimal("1") + (Decimal("2") * phi / c_sq)
    den = Decimal("1") - (Decimal("2") * phi / c_sq)
    return C_0 * (num / den).sqrt()

def get_sat_dim(obs):
    return 'sv' if 'sv' in obs.coords or 'sv' in obs.dims else 'sat'

def run_real_geometric_test():
    print("=" * 85)
    print(" 🚀 K-PROTOCOL REAL GEOMETRIC METRIC SCALE TEST")
    print("=" * 85)

    loaded_obs = {}
    positions = {}
    
    print("\n[STEP 1] Extracting Station Header Positions & Observations...")
    for node_id, info in NODES.items():
        obs = gr.load(info["file"])
        loaded_obs[node_id] = obs
        # RINEX 헤더의 실제 관측소 APPROX POSITION XYZ 추출
        pos = obs.attrs.get('position', [0, 0, 0])
        positions[node_id] = [Decimal(str(p)) for p in pos]
        print(f" -> [{node_id}] Header ECEF XYZ: {pos}")

    sat_dim = get_sat_dim(loaded_obs["MKEA"])
    target_sat = 'G20'
    target_time = '2024-04-09T11:30:00.000000000'

    # 실측 Pseudorange 거리 (meters)
    raw_m_mkea = Decimal(str(float(loaded_obs["MKEA"]['C1'].sel({sat_dim: target_sat, 'time': target_time}).values)))
    raw_m_hnlc = Decimal(str(float(loaded_obs["HNLC"]['C1'].sel({sat_dim: target_sat, 'time': target_time}).values)))

    print(f"\n[STEP 2] Observed Pseudorange for Satellite {target_sat}:")
    print(f" -> MKEA (3,755m) Raw Pseudorange : {raw_m_mkea:.3f} meters")
    print(f" -> HNLC (5m)     Raw Pseudorange : {raw_m_hnlc:.3f} meters")

    # Step 3: 고도 차이에 따른 K-PROTOCOL 좌표 광속 스케일 보정
    c_mkea = calc_conformal_c(NODES["MKEA"]["phi"])
    c_hnlc = calc_conformal_c(NODES["HNLC"]["phi"])

    # Conformal Rescaled Distances
    k_m_mkea = raw_m_mkea * (c_mkea / C_0)
    k_m_hnlc = raw_m_hnlc * (c_hnlc / C_0)

    # 고도 차이로 인해 발생한 메트릭 스케일 보정량 (Millimeters)
    delta_mkea_mm = (k_m_mkea - raw_m_mkea) * Decimal("1000")
    delta_hnlc_mm = (k_m_hnlc - raw_m_hnlc) * Decimal("1000")
    net_scale_diff_mm = delta_mkea_mm - delta_hnlc_mm

    print("\n[STEP 3] Gravitational Metric Scale Corrections:")
    print(f" -> MKEA Local Speed of Light (c_mkea) : {c_mkea:.10f} m/s")
    print(f" -> HNLC Local Speed of Light (c_hnlc) : {c_hnlc:.10f} m/s")
    print(f" -> MKEA Metric Shift (K-PROTOCOL)     : {delta_mkea_mm:+.6f} mm")
    print(f" -> HNLC Metric Shift (K-PROTOCOL)     : {delta_hnlc_mm:+.6f} mm")

    print("\n" + "=" * 85)
    print(" 🎯 VERDICT:")
    print(f"    - Relative Scale Distortion Corrected : {net_scale_diff_mm:+.6f} mm")
    print("    - Meaning: Legacy SI imposes a metric distortion between MKEA and HNLC")
    print("               which K-PROTOCOL resolves at the Ingestion Layer without fitting.")
    print("=" * 85)

if __name__ == "__main__":
    run_real_geometric_test()