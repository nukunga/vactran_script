#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import argparse

def generate_elbow_samples(total_samples,
                           bin_width_inch, 
                           diameter_inch_min, 
                           diameter_inch_max, 
                           angles_deg_list,
                           seed=None):
    if seed is not None:
        np.random.seed(seed)

    edges_in = np.arange(diameter_inch_min, diameter_inch_max + 1e-8, bin_width_inch)
    bins_in = [(edges_in[i], edges_in[i+1]) for i in range(len(edges_in)-1)]
    n_bins = len(bins_in)

    base = total_samples // n_bins
    rem = total_samples % n_bins
    counts = [base + (1 if i < rem else 0) for i in range(n_bins)]

    # 모든 각도가 균등하게 샘플링되도록 확률 설정
    probs = [1.0/len(angles_deg_list)] * len(angles_deg_list)

    records = []
    sid = 1
    for (low_in, high_in), cnt in zip(bins_in, counts):
        diam_in_samples = np.random.uniform(low_in, high_in, size=cnt)
        diam_cm_samples = diam_in_samples * 2.54

        bends = np.random.choice(angles_deg_list, size=cnt, p=probs)

        for d_cm, a in zip(diam_cm_samples, bends):
            records.append({
                "SampleID":       sid,
                "Diameter_cm":    round(d_cm, 4),
                "BendAngle_deg":  int(a),
                "Quantity":       1
            })
            sid += 1

    return pd.DataFrame(records)

def run(output_file, total_samples, bin_width_inch, diameter_inch_min, diameter_inch_max, angles_deg_list, seed):
    """Generates elbow sample data and saves it to an Excel file."""
    df = generate_elbow_samples(
        total_samples=total_samples,
        bin_width_inch=bin_width_inch,
        diameter_inch_min=diameter_inch_min,
        diameter_inch_max=diameter_inch_max,
        angles_deg_list=angles_deg_list,
        seed=seed
    )
    df.to_excel(output_file, index=False)
    print(f"완료: '{output_file}'에 {len(df)}개의 Elbow 샘플을 저장했습니다.")

def main():
    parser = argparse.ArgumentParser(description="Elbow 샘플 데이터를 inch 단위 스펙으로 받아 cm로 변환하여 생성")
    parser.add_argument("n", type=int, help="생성할 전체 샘플 수")
    parser.add_argument("-o","--output", default="elbow_samples.xlsx", help="출력 엑셀 파일명")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드")
    parser.add_argument("--bin_width_inch", type=float, required=True, help="직경 bin 너비 (inch)")
    parser.add_argument("--diameter_inch_min", type=float, required=True, help="최소 직경 (inch)")
    parser.add_argument("--diameter_inch_max", type=float, required=True, help="최대 직경 (inch)")
    parser.add_argument("--angles_deg", type=lambda s: [int(item) for item in s.split(',')], required=True, help="각도 리스트 (쉼표로 구분)")
    args = parser.parse_args()

    run(
        output_file=args.output,
        total_samples=args.n,
        bin_width_inch=args.bin_width_inch,
        diameter_inch_min=args.diameter_inch_min,
        diameter_inch_max=args.diameter_inch_max,
        angles_deg_list=args.angles_deg,
        seed=args.seed
    )

if __name__ == "__main__":
    main()