import os
from hatanaka import decompress

files = ["mkea1000.24d", "p0411000.24d", "hnlc1000.24d", "nlib1000.24d"]

print("📦 CRINEX (.24d) -> 표준 RINEX (.24o) 변환 시작...\n")
for f in files:
    if os.path.exists(f):
        out_f = f.replace(".24d", ".24o")
        try:
            # 1개 인자만 전달하여 압축 해제 데이터 추출
            decompressed_data = decompress(f)
            
            # 해제된 데이터를 .24o 파일로 저장
            with open(out_f, "wb") as out_file:
                if isinstance(decompressed_data, str):
                    out_file.write(decompressed_data.encode("utf-8"))
                else:
                    out_file.write(decompressed_data)
                    
            print(f" ✅ 변환 완료: {f} -> {out_f}")
        except Exception as e:
            print(f" ❌ 변환 실패 ({f}): {e}")

print("\n변환이 정상 완료되었습니다. 이제 py aa.py를 실행하세요.")