#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import argparse

def generate_reducer_samples(total_samples,
                             d1_bin_width_inch,
                             d1_inch_min,
                             d1_inch_max,
                             d2_inch_min_overall,
                             d2_inch_max_overall,
                             length_cm_min,
                             length_cm_max,
                             seed=None):
    """
    Reducer 샘플 생성 (D1/D2는 inch 입력 후 cm 변환, Length는 cm 입력)
    조건: D1_cm > D2_cm, D2_cm < 0.7 * D1_cm
    """
    if seed is not None:
        np.random.seed(seed)

    length_cm_range = (length_cm_min, length_cm_max)
    d2_cm_min_overall_converted = d2_inch_min_overall * 2.54
    d2_cm_max_overall_converted = d2_inch_max_overall * 2.54

    edges_d1_in = np.arange(d1_inch_min, d1_inch_max + 1e-8, d1_bin_width_inch)
    bins_d1_in = [(edges_d1_in[i], edges_d1_in[i+1]) for i in range(len(edges_d1_in)-1)]
    n_bins = len(bins_d1_in)

    base = total_samples // n_bins
    rem  = total_samples % n_bins
    counts = [base + (1 if i < rem else 0) for i in range(n_bins)]

    records = []
    sid = 1
    for (low_d1_in, high_d1_in), cnt in zip(bins_d1_in, counts):
        D1_in_samples = np.random.uniform(low_d1_in, high_d1_in, size=cnt)
        D1_cm_samples = D1_in_samples * 2.54

        for d1_cm_val in D1_cm_samples:
            d2_cm = -1.0
            max_attempts = 1000
            for _ in range(max_attempts):
                d2_cm_candidate = np.random.uniform(d2_cm_min_overall_converted, d2_cm_max_overall_converted)
                if d1_cm_val > d2_cm_candidate and d2_cm_candidate < (d1_cm_val * 0.7):
                    d2_cm = d2_cm_candidate
                    break
            
            if d2_cm != -1.0:
                length_cm = np.random.uniform(length_cm_range[0], length_cm_range[1])
                records.append({
                    "SampleID": sid,
                    "D1_cm":    round(d1_cm_val, 4),
                    "D2_cm":    round(d2_cm, 4),
                    "Length_cm":round(length_cm, 4)
                })
                sid += 1

    return pd.DataFrame(records)

def run(output_file, total_samples, d1_bin_width_inch, d1_inch_min, d1_inch_max, d2_inch_min_overall, d2_inch_max_overall, length_cm_min, length_cm_max, seed):
    """Reducer 샘플 데이터를 생성하고 엑셀 파일로 저장합니다."""
    df = generate_reducer_samples(
        total_samples=total_samples,
        d1_bin_width_inch=d1_bin_width_inch,
        d1_inch_min=d1_inch_min,
        d1_inch_max=d1_inch_max,
        d2_inch_min_overall=d2_inch_min_overall,
        d2_inch_max_overall=d2_inch_max_overall,
        length_cm_min=length_cm_min,
        length_cm_max=length_cm_max,
        seed=seed
    )
    df.to_excel(output_file, index=False)
    print(f"완료: '{output_file}'에 {len(df)}개의 Reducer 샘플을 저장했습니다.")

def main():
    parser = argparse.ArgumentParser(description="Reducer 샘플 데이터 생성 (D1/D2: inch, Length: cm).")
    parser.add_argument("n", type=int, help="생성할 전체 샘플 수")
    parser.add_argument("-o","--output", default="reducer_samples.xlsx", help="출력 엑셀 파일명")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드")
    parser.add_argument("--d1_bin_width_inch", type=float, required=True, help="D1 직경 bin 너비 (inch)")
    parser.add_argument("--d1_inch_min", type=float, required=True, help="D1 최소 직경 (inch)")
    parser.add_argument("--d1_inch_max", type=float, required=True, help="D1 최대 직경 (inch)")
    parser.add_argument("--d2_inch_min_overall", type=float, required=True, help="D2 전체 최소 직경 (inch)")
    parser.add_argument("--d2_inch_max_overall", type=float, required=True, help="D2 전체 최대 직경 (inch)")
    parser.add_argument("--length_cm_min", type=float, required=True, help="최소 길이 (cm)")
    parser.add_argument("--length_cm_max", type=float, required=True, help="최대 길이 (cm)")
    args = parser.parse_args()

    run(
        output_file=args.output,
        total_samples=args.n,
        d1_bin_width_inch=args.d1_bin_width_inch,
        d1_inch_min=args.d1_inch_min,
        d1_inch_max=args.d1_inch_max,
        d2_inch_min_overall=args.d2_inch_min_overall,
        d2_inch_max_overall=args.d2_inch_max_overall,
        length_cm_min=args.length_cm_min,
        length_cm_max=args.length_cm_max,
        seed=args.seed
    )

if __name__ == "__main__":
    main()