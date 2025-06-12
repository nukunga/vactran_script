#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import argparse

def generate_expander_samples(total_samples,
                              d2_bin_width_inch,  # D1 -> D2
                              d2_inch_min,        # D1 -> D2
                              d2_inch_max,        # D1 -> D2
                              d1_inch_min_overall,# D2 -> D1
                              d1_inch_max_overall,# D2 -> D1
                              length_cm_min,
                              length_cm_max,
                              seed=None):
    """
    Expander 샘플 생성 (D2는 inch 입력 후 cm 변환하여 binning, D1은 조건에 맞게 생성, Length는 cm 입력)
    조건: D2_cm > D1_cm, D1_cm < 0.7 * D2_cm
    """
    if seed is not None:
        np.random.seed(seed)

    length_cm_range = (length_cm_min, length_cm_max)

    # D1 inch 범위를 cm로 변환 (D1 샘플링 시 사용)
    d1_cm_min_overall_converted = d1_inch_min_overall * 2.54
    d1_cm_max_overall_converted = d1_inch_max_overall * 2.54

    # D2를 기준으로 binning
    edges_d2_in = np.arange(d2_inch_min, d2_inch_max + 1e-8, d2_bin_width_inch)
    bins_d2_in = [(edges_d2_in[i], edges_d2_in[i+1]) for i in range(len(edges_d2_in)-1)]
    n_bins = len(bins_d2_in)

    if n_bins == 0:
        print(f"Warning: No bins created for D2 with range [{d2_inch_min}, {d2_inch_max}] and bin_width {d2_bin_width_inch}. Returning empty DataFrame.")
        return pd.DataFrame(columns=["SampleID", "D1_cm", "D2_cm", "Length_cm"])


    base = total_samples // n_bins
    rem  = total_samples % n_bins
    counts = [base + (1 if i < rem else 0) for i in range(n_bins)]

    records = []
    sid = 1
    for (low_d2_in, high_d2_in), cnt in zip(bins_d2_in, counts):
        D2_in_samples = np.random.uniform(low_d2_in, high_d2_in, size=cnt)
        D2_cm_samples = D2_in_samples * 2.54 # D2 inch to cm

        for d2_cm_val in D2_cm_samples:
            d1_cm = -1.0
            max_attempts = 1000
            attempt = 0
            while attempt < max_attempts:
                # D1 샘플링은 변환된 cm 범위 사용
                d1_cm_candidate = np.random.uniform(d1_cm_min_overall_converted, d1_cm_max_overall_converted)
                if d2_cm_val > d1_cm_candidate and d1_cm_candidate < (d2_cm_val * 0.7):
                    d1_cm = d1_cm_candidate
                    break
                attempt += 1
            if d1_cm == -1.0:
                # 조건에 맞는 D1을 찾지 못한 경우, 이 D2 샘플은 건너뜁니다.
                # print(f"Warning: Could not find a suitable D1_cm for D2_cm={d2_cm_val:.2f} within D1_inch range [{d1_inch_min_overall}, {d1_inch_max_overall}] and constraints.")
                continue
            
            length_cm = np.random.uniform(length_cm_range[0], length_cm_range[1])

            records.append({
                "SampleID": sid,
                "D1_cm":    round(d1_cm, 4), # D1_cm이 먼저 오도록 순서 유지
                "D2_cm":    round(d2_cm_val, 4),
                "Length_cm":round(length_cm, 4)
            })
            sid += 1

    return pd.DataFrame(records)

def main():
    parser = argparse.ArgumentParser(
        description="Expander 샘플 데이터 생성 (D2 기준으로 샘플링, D1/D2: inch, Length: cm). D2_cm > D1_cm, D1_cm < 0.7*D2_cm"
    )
    parser.add_argument("n", type=int,
                        help="생성할 전체 샘플 수 (예: 1000)")
    parser.add_argument("-o","--output", default="expander_samples.xlsx",
                        help="출력 엑셀 파일명")
    parser.add_argument("--seed", type=int, default=42,
                        help="난수 시드 (재현용)")
    # D2 기준 인자로 변경
    parser.add_argument("--d2_bin_width_inch", type=float, required=True, help="D2 직경 bin의 너비 (inch)")
    parser.add_argument("--d2_inch_min", type=float, required=True, help="D2 최소 직경 (inch) for binning")
    parser.add_argument("--d2_inch_max", type=float, required=True, help="D2 최대 직경 (inch) for binning")
    # D1은 전체 범위로 받음
    parser.add_argument("--d1_inch_min_overall", type=float, required=True, help="D1 전체 최소 직경 (inch)")
    parser.add_argument("--d1_inch_max_overall", type=float, required=True, help="D1 전체 최대 직경 (inch)")
    
    parser.add_argument("--length_cm_min", type=float, required=True, help="최소 길이 (cm)")
    parser.add_argument("--length_cm_max", type=float, required=True, help="최대 길이 (cm)")

    args = parser.parse_args()

    df = generate_expander_samples(
        total_samples=args.n,
        d2_bin_width_inch=args.d2_bin_width_inch, # 변경
        d2_inch_min=args.d2_inch_min,             # 변경
        d2_inch_max=args.d2_inch_max,             # 변경
        d1_inch_min_overall=args.d1_inch_min_overall, # 변경
        d1_inch_max_overall=args.d1_inch_max_overall, # 변경
        length_cm_min=args.length_cm_min,
        length_cm_max=args.length_cm_max,
        seed=args.seed
    )
    df.to_excel(args.output, index=False)
    print(f"완료: '{args.output}'에 {len(df)}개의 Expander 샘플을 저장했습니다.")

if __name__ == "__main__":
    main()