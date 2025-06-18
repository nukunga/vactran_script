#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import argparse
import itertools # itertools 추가

def generate_elbow_samples(total_samples,
                           diameter_inch_spec, # (min, max, num_intervals)
                           angles_deg_list,
                           seed=None):
    if seed is not None:
        np.random.seed(seed)

    # 직경 구간 생성
    dia_min_in, dia_max_in, dia_intervals = diameter_inch_spec
    dia_edges_in = np.linspace(dia_min_in, dia_max_in, int(dia_intervals) + 1)
    dia_bins_in = [(dia_edges_in[i], dia_edges_in[i+1]) for i in range(int(dia_intervals))]

    # 각도는 주어진 리스트 그대로 사용
    # 모든 파라미터 조합 생성 (직경 구간 * 각도)
    param_combinations = list(itertools.product(dia_bins_in, angles_deg_list))

    if not param_combinations:
        return pd.DataFrame(columns=["SampleID", "Diameter_cm", "BendAngle_deg", "Quantity"])

    n_combinations = len(param_combinations)
    
    base_samples_per_combo = total_samples // n_combinations
    remainder_samples = total_samples % n_combinations
    counts_per_combo = [base_samples_per_combo + (1 if i < remainder_samples else 0) for i in range(n_combinations)]

    records = []
    sid = 1
    for combo_idx, ((low_in, high_in), angle_deg) in enumerate(param_combinations):
        cnt = counts_per_combo[combo_idx]
        if cnt == 0:
            continue
            
        diam_in_samples = np.random.uniform(low_in, high_in, size=cnt)
        diam_cm_samples = diam_in_samples * 2.54

        for d_cm in diam_cm_samples:
            records.append({
                "SampleID":       sid,
                "Diameter_cm":    round(d_cm, 4),
                "BendAngle_deg":  int(angle_deg),
                "Quantity":       1
            })
            sid += 1

    return pd.DataFrame(records)

def run(output_file, total_samples, diameter_inch_spec, angles_deg_list, seed):
    """Generates elbow sample data and saves it to an Excel file."""
    df = generate_elbow_samples(
        total_samples=total_samples,
        diameter_inch_spec=diameter_inch_spec,
        angles_deg_list=angles_deg_list,
        seed=seed
    )
    df.to_excel(output_file, index=False)
    print(f"완료: '{output_file}'에 {len(df)}개의 Elbow 샘플을 저장했습니다.")

def parse_spec(s):
    parts = s.split(',')
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("Specification must be min,max,num_intervals")
    return float(parts[0]), float(parts[1]), int(parts[2])

def main():
    parser = argparse.ArgumentParser(description="Elbow 샘플 데이터를 inch 단위 스펙으로 받아 cm로 변환하여 생성. 직경은 (min,max,num_intervals) 형식.")
    parser.add_argument("n", type=int, help="생성할 전체 샘플 수")
    parser.add_argument("-o","--output", default="elbow_samples.xlsx", help="출력 엑셀 파일명")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드")
    parser.add_argument("--diameter_inch_spec", type=parse_spec, required=True, help="직경 스펙 (inch): min,max,intervals (예: '1.0,5.0,2')")
    parser.add_argument("--angles_deg", type=lambda s: [int(item) for item in s.split(',')], required=True, help="각도 리스트 (쉼표로 구분, 예: '15,30,45')")
    args = parser.parse_args()

    run(
        output_file=args.output,
        total_samples=args.n,
        diameter_inch_spec=args.diameter_inch_spec,
        angles_deg_list=args.angles_deg,
        seed=args.seed
    )

if __name__ == "__main__":
    main()