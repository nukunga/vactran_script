#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import argparse
import itertools # itertools 추가

def generate_binned_samples(total_samples, 
                            diameter_inch_spec, # (min, max, num_intervals)
                            length_mm_spec,     # (min, max, num_intervals)
                            seed=None):
    if seed is not None:
        np.random.seed(seed)
    
    # 직경 구간 생성
    dia_min_in, dia_max_in, dia_intervals = diameter_inch_spec
    dia_edges_in = np.linspace(dia_min_in, dia_max_in, int(dia_intervals) + 1)
    dia_bins_in = [(dia_edges_in[i], dia_edges_in[i+1]) for i in range(int(dia_intervals))]

    # 길이 구간 생성
    len_min_mm, len_max_mm, len_intervals = length_mm_spec
    len_edges_mm = np.linspace(len_min_mm, len_max_mm, int(len_intervals) + 1)
    len_bins_mm = [(len_edges_mm[i], len_edges_mm[i+1]) for i in range(int(len_intervals))]

    # 모든 파라미터 조합 생성
    param_combinations = list(itertools.product(dia_bins_in, len_bins_mm))
    
    if not param_combinations:
        return pd.DataFrame(columns=["SampleID", "Diameter_cm", "Length_cm"])

    n_combinations = len(param_combinations)
    
    base_samples_per_combo = total_samples // n_combinations
    remainder_samples = total_samples % n_combinations
    
    counts_per_combo = [base_samples_per_combo + (1 if i < remainder_samples else 0) for i in range(n_combinations)]
    
    records = []
    sample_id = 1
    for combo_idx, ((dia_low_in, dia_high_in), (len_low_mm, len_high_mm)) in enumerate(param_combinations):
        num_samples_for_this_combo = counts_per_combo[combo_idx]
        if num_samples_for_this_combo == 0:
            continue

        diam_in_samples = np.random.uniform(dia_low_in, dia_high_in, size=num_samples_for_this_combo)
        diam_cm_samples = diam_in_samples * 2.54 # inch to cm
        
        lengths_mm_samples = np.random.uniform(len_low_mm, len_high_mm, size=num_samples_for_this_combo)
        lengths_cm_samples = lengths_mm_samples / 10.0 # mm to cm
        
        for d_cm, l_cm in zip(diam_cm_samples, lengths_cm_samples):
            records.append({
                "SampleID": sample_id,
                "Diameter_cm": round(d_cm, 4),
                "Length_cm": round(l_cm, 4)
            })
            sample_id += 1
    
    return pd.DataFrame(records)

def run(output_file, total_samples, diameter_inch_spec, length_mm_spec, seed):
    """Generates sample data and saves it to an Excel file."""
    df = generate_binned_samples(
        total_samples=total_samples,
        diameter_inch_spec=diameter_inch_spec,
        length_mm_spec=length_mm_spec,
        seed=seed
    )
    df.to_excel(output_file, index=False)
    print(f"완료: '{output_file}'에 {len(df)}개의 샘플을 저장했습니다.")

def parse_spec(s):
    parts = s.split(',')
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("Specification must be min,max,num_intervals")
    return float(parts[0]), float(parts[1]), int(parts[2])

def main():
    parser = argparse.ArgumentParser(
        description="파이프 샘플 데이터를 inch/mm 단위 스펙으로 받아 cm로 변환하여 생성. 각 파라미터는 (min,max,num_intervals) 형식으로 지정."
    )
    parser.add_argument("n", type=int, help="생성할 전체 샘플 수 (예: 1000)")
    parser.add_argument("-o", "--output", default="pipe_samples.xlsx", help="출력 엑셀 파일명")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드 (재현용)")
    parser.add_argument("--diameter_inch_spec", type=parse_spec, required=True, help="직경 스펙 (inch): min,max,intervals (예: '1.0,10.0,3')")
    parser.add_argument("--length_mm_spec", type=parse_spec, required=True, help="길이 스펙 (mm): min,max,intervals (예: '100,20000,5')")
    args = parser.parse_args()

    run(
        output_file=args.output,
        total_samples=args.n,
        diameter_inch_spec=args.diameter_inch_spec,
        length_mm_spec=args.length_mm_spec,
        seed=args.seed
    )

if __name__ == "__main__":
    main()