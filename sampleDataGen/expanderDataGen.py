#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import argparse

def generate_expander_samples(total_samples,
                              d1_bin_width_inch,  # D2 -> D1
                              d1_inch_min,        # D2 -> D1
                              d1_inch_max,        # D2 -> D1
                              d2_inch_min_overall,# D1 -> D2
                              d2_inch_max_overall,# D1 -> D2
                              length_mm_min,      # cm -> mm
                              length_mm_max,      # cm -> mm
                              seed=None):
    """
    Expander 샘플 생성 (D1 기준으로 binning, D2는 조건에 맞게 생성)
    조건: D2_cm > D1_cm, D1_cm < 0.7 * D2_cm
    """
    if seed is not None:
        np.random.seed(seed)

    length_mm_range = (length_mm_min, length_mm_max) # cm -> mm
    d2_cm_min_overall_converted = d2_inch_min_overall * 2.54 # D1 -> D2
    d2_cm_max_overall_converted = d2_inch_max_overall * 2.54 # D1 -> D2

    edges_d1_in = np.arange(d1_inch_min, d1_inch_max + 1e-8, d1_bin_width_inch) # D2 -> D1
    bins_d1_in = [(edges_d1_in[i], edges_d1_in[i+1]) for i in range(len(edges_d1_in)-1)] # D2 -> D1
    n_bins = len(bins_d1_in)

    if n_bins == 0:
        return pd.DataFrame(columns=["SampleID", "D1_cm", "D2_cm", "Length_cm"])

    base = total_samples // n_bins
    rem  = total_samples % n_bins
    counts = [base + (1 if i < rem else 0) for i in range(n_bins)]

    records = []
    sid = 1
    for (low_d1_in, high_d1_in), cnt in zip(bins_d1_in, counts): # D2 -> D1
        D1_in_samples = np.random.uniform(low_d1_in, high_d1_in, size=cnt) # D2 -> D1
        D1_cm_samples = D1_in_samples * 2.54 # D2 -> D1

        for d1_cm_val in D1_cm_samples: # d2_cm_val -> d1_cm_val
            d2_cm = -1.0 # d1_cm -> d2_cm
            max_attempts = 1000
            for _ in range(max_attempts):
                d2_cm_candidate = np.random.uniform(d2_cm_min_overall_converted, d2_cm_max_overall_converted) # d1_cm_candidate -> d2_cm_candidate
                # Expander 조건: D2_cm > D1_cm and D1_cm < 0.7 * D2_cm
                if d2_cm_candidate > d1_cm_val and d1_cm_val < (d2_cm_candidate * 0.7):
                    d2_cm = d2_cm_candidate # d1_cm -> d2_cm
                    break
            
            if d2_cm != -1.0: # d1_cm -> d2_cm
                length_mm = np.random.uniform(length_mm_range[0], length_mm_range[1]) # cm -> mm
                length_cm = length_mm / 10.0 # mm to cm
                records.append({
                    "SampleID": sid,
                    "D1_cm":    round(d1_cm_val, 4), # d2_cm_val -> d1_cm_val
                    "D2_cm":    round(d2_cm, 4),   # d1_cm -> d2_cm
                    "Length_cm":round(length_cm, 4)
                })
                sid += 1

    return pd.DataFrame(records)

def run(output_file, total_samples, d1_bin_width_inch, d1_inch_min, d1_inch_max, d2_inch_min_overall, d2_inch_max_overall, length_mm_min, length_mm_max, seed): # 파라미터명 변경
    """Expander 샘플 데이터를 생성하고 엑셀 파일로 저장합니다."""
    df = generate_expander_samples(
        total_samples=total_samples,
        d1_bin_width_inch=d1_bin_width_inch,     # D2 -> D1
        d1_inch_min=d1_inch_min,                 # D2 -> D1
        d1_inch_max=d1_inch_max,                 # D2 -> D1
        d2_inch_min_overall=d2_inch_min_overall, # D1 -> D2
        d2_inch_max_overall=d2_inch_max_overall, # D1 -> D2
        length_mm_min=length_mm_min,             # cm -> mm
        length_mm_max=length_mm_max,             # cm -> mm
        seed=seed
    )
    df.to_excel(output_file, index=False)
    print(f"완료: '{output_file}'에 {len(df)}개의 Expander 샘플을 저장했습니다.")

def main():
    parser = argparse.ArgumentParser(description="Expander 샘플 데이터 생성 (D1 기준, Length는 mm 입력).") # 설명 변경
    parser.add_argument("n", type=int, help="생성할 전체 샘플 수")
    parser.add_argument("-o","--output", default="expander_samples.xlsx", help="출력 엑셀 파일명")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드")
    parser.add_argument("--d1_bin_width_inch", type=float, required=True, help="D1 직경 bin 너비 (inch)") # D2 -> D1
    parser.add_argument("--d1_inch_min", type=float, required=True, help="D1 최소 직경 (inch) for binning") # D2 -> D1
    parser.add_argument("--d1_inch_max", type=float, required=True, help="D1 최대 직경 (inch) for binning") # D2 -> D1
    parser.add_argument("--d2_inch_min_overall", type=float, required=True, help="D2 전체 최소 직경 (inch)") # D1 -> D2
    parser.add_argument("--d2_inch_max_overall", type=float, required=True, help="D2 전체 최대 직경 (inch)") # D1 -> D2
    parser.add_argument("--length_mm_min", type=float, required=True, help="최소 길이 (mm)") # cm -> mm
    parser.add_argument("--length_mm_max", type=float, required=True, help="최대 길이 (mm)") # cm -> mm
    args = parser.parse_args()

    run(
        output_file=args.output,
        total_samples=args.n,
        d1_bin_width_inch=args.d1_bin_width_inch,         # D2 -> D1
        d1_inch_min=args.d1_inch_min,                     # D2 -> D1
        d1_inch_max=args.d1_inch_max,                     # D2 -> D1
        d2_inch_min_overall=args.d2_inch_min_overall,     # D1 -> D2
        d2_inch_max_overall=args.d2_inch_max_overall,     # D1 -> D2
        length_mm_min=args.length_mm_min,                 # cm -> mm
        length_mm_max=args.length_mm_max,                 # cm -> mm
        seed=args.seed
    )

if __name__ == "__main__":
    main()