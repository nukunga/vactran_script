#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import argparse

def generate_binned_samples(total_samples, bin_width_inch, 
                            diameter_inch_min, diameter_inch_max,
                            length_mm_min, length_mm_max,
                            seed=None):
    if seed is not None:
        np.random.seed(seed)
    
    length_mm_range = (length_mm_min, length_mm_max)

    edges_in = np.arange(diameter_inch_min, diameter_inch_max + 1e-8, bin_width_inch)
    bin_ranges_in = [(edges_in[i], edges_in[i+1]) for i in range(len(edges_in)-1)]
    n_bins = len(bin_ranges_in)
    
    base = total_samples // n_bins
    remainder = total_samples % n_bins
    counts = [base + (1 if i < remainder else 0) for i in range(n_bins)]
    
    records = []
    sample_id = 1
    for (low_in, high_in), cnt in zip(bin_ranges_in, counts):
        diam_in_samples = np.random.uniform(low_in, high_in, size=cnt)
        diam_cm_samples = diam_in_samples * 2.54 # inch to cm
        
        lengths_mm_samples = np.random.uniform(length_mm_range[0],
                                               length_mm_range[1],
                                               size=cnt)
        lengths_cm_samples = lengths_mm_samples / 10.0 # mm to cm
        
        for d_cm, l_cm in zip(diam_cm_samples, lengths_cm_samples):
            records.append({
                "SampleID": sample_id,
                "Diameter_cm": round(d_cm, 4),
                "Length_cm": round(l_cm, 4)
            })
            sample_id += 1
    
    return pd.DataFrame(records)

def run(output_file, total_samples, bin_width_inch, diameter_inch_min, diameter_inch_max, length_mm_min, length_mm_max, seed):
    """Generates sample data and saves it to an Excel file."""
    df = generate_binned_samples(
        total_samples=total_samples,
        bin_width_inch=bin_width_inch,
        diameter_inch_min=diameter_inch_min,
        diameter_inch_max=diameter_inch_max,
        length_mm_min=length_mm_min,
        length_mm_max=length_mm_max,
        seed=seed
    )
    df.to_excel(output_file, index=False)
    print(f"완료: '{output_file}'에 {len(df)}개의 샘플을 저장했습니다.")

def main():
    parser = argparse.ArgumentParser(
        description="파이프 샘플 데이터를 inch/mm 단위 스펙으로 받아 cm로 변환하여 생성"
    )
    parser.add_argument("n", type=int, help="생성할 전체 샘플 수 (예: 1000)")
    parser.add_argument("-o", "--output", default="pipe_samples.xlsx", help="출력 엑셀 파일명")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드 (재현용)")
    parser.add_argument("--bin_width_inch", type=float, required=True, help="직경 bin의 너비 (inch)")
    parser.add_argument("--diameter_inch_min", type=float, required=True, help="최소 직경 (inch)")
    parser.add_argument("--diameter_inch_max", type=float, required=True, help="최대 직경 (inch)")
    parser.add_argument("--length_mm_min", type=float, required=True, help="최소 길이 (mm)")
    parser.add_argument("--length_mm_max", type=float, required=True, help="최대 길이 (mm)")
    args = parser.parse_args()

    run(
        output_file=args.output,
        total_samples=args.n,
        bin_width_inch=args.bin_width_inch,
        diameter_inch_min=args.diameter_inch_min,
        diameter_inch_max=args.diameter_inch_max,
        length_mm_min=args.length_mm_min,
        length_mm_max=args.length_mm_max,
        seed=args.seed
    )

if __name__ == "__main__":
    main()