#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import argparse
import itertools # itertools 추가

def generate_expander_samples(total_samples,
                              d1_inch_spec,     # (min, max, num_intervals)
                              d2_inch_spec,     # (min, max, num_intervals)
                              length_mm_spec,   # (min, max, num_intervals)
                              seed=None):
    """
    Expander 샘플 생성 (D1, D2, Length 각 구간 조합 기반)
    조건: D2_cm > D1_cm, D1_cm < 0.7 * D2_cm
    """
    if seed is not None:
        np.random.seed(seed)

    # D1 구간 생성
    d1_min_in, d1_max_in, d1_intervals = d1_inch_spec
    d1_edges_in = np.linspace(d1_min_in, d1_max_in, int(d1_intervals) + 1)
    d1_bins_in = [(d1_edges_in[i], d1_edges_in[i+1]) for i in range(int(d1_intervals))]

    # D2 구간 생성
    d2_min_in, d2_max_in, d2_intervals = d2_inch_spec
    d2_edges_in = np.linspace(d2_min_in, d2_max_in, int(d2_intervals) + 1)
    d2_bins_in = [(d2_edges_in[i], d2_edges_in[i+1]) for i in range(int(d2_intervals))]

    # 길이 구간 생성
    len_min_mm, len_max_mm, len_intervals = length_mm_spec
    len_edges_mm = np.linspace(len_min_mm, len_max_mm, int(len_intervals) + 1)
    len_bins_mm = [(len_edges_mm[i], len_edges_mm[i+1]) for i in range(int(len_intervals))]
    
    param_combinations = list(itertools.product(d1_bins_in, d2_bins_in, len_bins_mm))

    if not param_combinations:
        return pd.DataFrame(columns=["SampleID", "D1_cm", "D2_cm", "Length_cm"])

    n_combinations = len(param_combinations)
    base_samples_per_combo = total_samples // n_combinations
    remainder_samples = total_samples % n_combinations
    counts_per_combo = [base_samples_per_combo + (1 if i < remainder_samples else 0) for i in range(n_combinations)]

    records = []
    sid = 1
    max_attempts_per_sample = 100 # 조건 만족 샘플 생성 재시도 횟수

    for combo_idx, ((d1_low_in, d1_high_in), (d2_low_in, d2_high_in), (len_low_mm, len_high_mm)) in enumerate(param_combinations):
        num_to_generate_for_combo = counts_per_combo[combo_idx]
        generated_for_combo = 0
        
        for _ in range(num_to_generate_for_combo * max_attempts_per_sample): # 충분한 시도
            if generated_for_combo >= num_to_generate_for_combo:
                break

            d1_in_sample = np.random.uniform(d1_low_in, d1_high_in)
            d1_cm_sample = d1_in_sample * 2.54

            d2_in_sample = np.random.uniform(d2_low_in, d2_high_in)
            d2_cm_sample = d2_in_sample * 2.54
            
            # Expander 조건: D2_cm > D1_cm and D1_cm < 0.7 * D2_cm
            # if not (d2_cm_sample > d1_cm_sample and d1_cm_sample < (d2_cm_sample * 0.7)):
            if not (d2_cm_sample > d1_cm_sample):
                continue # 조건 불만족시 다음 시도

            length_mm_sample = np.random.uniform(len_low_mm, len_high_mm)
            length_cm_sample = length_mm_sample / 10.0
            
            records.append({
                "SampleID": sid,
                "D1_cm":    round(d1_cm_sample, 4),
                "D2_cm":    round(d2_cm_sample, 4),
                "Length_cm":round(length_cm_sample, 4)
            })
            sid += 1
            generated_for_combo += 1

    return pd.DataFrame(records)

def run(output_file, total_samples, d1_inch_spec, d2_inch_spec, length_mm_spec, seed):
    """Expander 샘플 데이터를 생성하고 엑셀 파일로 저장합니다."""
    df = generate_expander_samples(
        total_samples=total_samples,
        d1_inch_spec=d1_inch_spec,
        d2_inch_spec=d2_inch_spec,
        length_mm_spec=length_mm_spec,
        seed=seed
    )
    df.to_excel(output_file, index=False)
    print(f"완료: '{output_file}'에 {len(df)}개의 Expander 샘플을 저장했습니다.")

def parse_spec(s):
    parts = s.split(',')
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("Specification must be min,max,num_intervals")
    return float(parts[0]), float(parts[1]), int(parts[2])

def main():
    parser = argparse.ArgumentParser(description="Expander 샘플 데이터 생성. 각 파라미터는 (min,max,num_intervals) 형식.")
    parser.add_argument("n", type=int, help="생성할 전체 샘플 수")
    parser.add_argument("-o","--output", default="expander_samples.xlsx", help="출력 엑셀 파일명")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드")
    parser.add_argument("--d1_inch_spec", type=parse_spec, required=True, help="D1 직경 스펙 (inch): min,max,intervals (예: '0.5,8.0,4')")
    parser.add_argument("--d2_inch_spec", type=parse_spec, required=True, help="D2 직경 스펙 (inch): min,max,intervals (예: '0.8,12.0,5')")
    parser.add_argument("--length_mm_spec", type=parse_spec, required=True, help="길이 스펙 (mm): min,max,intervals (예: '25,1000,3')")
    args = parser.parse_args()

    run(
        output_file=args.output,
        total_samples=args.n,
        d1_inch_spec=args.d1_inch_spec,
        d2_inch_spec=args.d2_inch_spec,
        length_mm_spec=args.length_mm_spec,
        seed=args.seed
    )

if __name__ == "__main__":
    main()