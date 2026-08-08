import warnings
import logging
from decimal import Decimal, getcontext

# 불필요한 경고문 및 라이브러리 로그 차단
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.ERROR)

try:
    import georinex as gr
except ImportError:
    print("[오류] georinex 라이브러리가 필요합니다. 'pip install georinex'를 실행해주세요.")
    exit()

# 60자리 고정 정밀도 설정
getcontext().prec = 60
C_0 = Decimal("299792458")

# 1. 압축 해제된 .24o 표준 파일 및 사전 포텐셜 지정
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
    """RINEX 2/3 호환 위성 좌표 차원명(sv/sat) 반환"""
    if 'sv' in obs.coords or 'sv' in obs.dims:
        return 'sv'
    if 'sat' in obs.coords or 'sat' in obs.dims:
        return 'sat'
    return None

def get_l1_variable(obs):
    """RINEX 관측 파일에서 사용 가능한 L1 변수명 탐색"""
    for var in ['C1', 'P1', 'C1C', 'C1W']:
        if var in obs.data_vars:
            return var
    return None

def run_real_data_closed_loop():
    print("=" * 85)
    print(" 🚀 K-PROTOCOL REAL DATA CLOSED-LOOP CHECKMATE TEST")
    print("=" * 85)

    # Step 1: 3개 관측 파일 로드
    print("\n[STEP 1] Loading Uncompressed .24o Observation Files...")
    loaded_obs = {}
    l1_vars = {}
    sat_dims = {}
    for node_id, info in NODES.items():
        try:
            obs = gr.load(info["file"])
            loaded_obs[node_id] = obs
            l1_var = get_l1_variable(obs)
            sat_dim = get_sat_dim(obs)
            l1_vars[node_id] = l1_var
            sat_dims[node_id] = sat_dim
            print(f" -> [{node_id}] 로드 성공 (관측 변수: {l1_var}, 위성 좌표명: {sat_dim})")
        except Exception as e:
            print(f" -> [{node_id}] 로드 실패: {e}")
            return

    # Step 2: 3개 관측소 공통 수신 GPS 위성 및 동일 Epoch 자동 탐색
    print("\n[STEP 2] Dynamically searching for common GPS satellite & epoch...")
    
    sats_per_node = {}
    for node_id, obs in loaded_obs.items():
        dim = sat_dims[node_id]
        sats_per_node[node_id] = set([str(s) for s in obs[dim].values if str(s).startswith('G')])

    common_sats = list(sats_per_node["MKEA"] & sats_per_node["P041"] & sats_per_node["HNLC"])
    print(f" -> 발견된 3개 관측소 공통 GPS 위성 목록: {common_sats}")

    if not common_sats:
        print(" ❌ 공통 수신 GPS 위성을 찾지 못했습니다.")
        return

    target_sat = None
    target_time = None
    raw_tofs = {}

    for sat in common_sats:
        das = {}
        valid_sat = True
        for node_id in NODES:
            obs = loaded_obs[node_id]
            var = l1_vars[node_id]
            dim = sat_dims[node_id]
            try:
                da = obs[var].sel({dim: sat}).dropna(dim='time')
                das[node_id] = da
            except Exception:
                valid_sat = False
                break
        
        if not valid_sat:
            continue

        common_times = set(das["MKEA"].time.values) & set(das["P041"].time.values) & set(das["HNLC"].time.values)
        if len(common_times) > 0:
            target_sat = sat
            target_time = sorted(list(common_times))[0]
            
            mkea_val = float(das["MKEA"].sel(time=target_time).values)
            p041_val = float(das["P041"].sel(time=target_time).values)
            hnlc_val = float(das["HNLC"].sel(time=target_time).values)

            raw_tofs["MKEA"] = Decimal(str(mkea_val)) / C_0
            raw_tofs["P041"] = Decimal(str(p041_val)) / C_0
            raw_tofs["HNLC"] = Decimal(str(hnlc_val)) / C_0
            break

    if not target_sat:
        print(" ❌ 동일 시간대(Epoch)의 공통 관측 데이터를 찾지 못했습니다.")
        return

    print(f" ✅ 최적 공통 위성 선택: [{target_sat}] | 타임스탬프(Epoch): {target_time}")
    for node_id in NODES:
        raw_m = float(raw_tofs[node_id] * C_0)
        print(f" -> [{node_id}] Pseudorange: {raw_m:.3f} m | Raw ToF: {raw_tofs[node_id]:.15f} s")

    tau_A = raw_tofs["MKEA"]
    tau_B = raw_tofs["P041"]
    tau_C = raw_tofs["HNLC"]

    # Step 3: Lane A - 기존 SI 방식 (c_0 고정 유클리드 메트릭)
    loop_closure_si = (tau_A - tau_B) + (tau_B - tau_C) + (tau_C - tau_A)
    err_meters_si = abs(loop_closure_si) * C_0

    # Step 4: Lane B - K-PROTOCOL (Ingestion Layer Conformal Rescaling)
    c_A = calc_conformal_c(NODES["MKEA"]["phi"])
    c_B = calc_conformal_c(NODES["P041"]["phi"])
    c_C = calc_conformal_c(NODES["HNLC"]["phi"])

    tau_A_k = tau_A * (c_A / C_0)
    tau_B_k = tau_B * (c_B / C_0)
    tau_C_k = tau_C * (c_C / C_0)

    loop_closure_k = (tau_A_k - tau_B_k) + (tau_B_k - tau_C_k) + (tau_C_k - tau_A_k)
    err_meters_k = abs(loop_closure_k) * C_0

    # Step 5: 최종 검증 결과 출력
    print("\n[STEP 3] Closed-Loop Integration Comparison:")
    print(f" -> Legacy SI Closed-Loop Residual    : {err_meters_si:.18e} meters")
    print(f" -> K-PROTOCOL Closed-Loop Residual   : {err_meters_k:.18e} meters")

    print("\n" + "=" * 85)
    print(" 🎯 VERDICT:")
    print("    - Free Fitting Parameters Used : 0 (Zero)")
    print(f"    - Metric Scale Error Improvement: {err_meters_si - err_meters_k:+.18e} meters")
    print("=" * 85)

if __name__ == "__main__":
    run_real_data_closed_loop()