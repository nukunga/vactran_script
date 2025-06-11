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
                           angle_p45_prob,
                           seed=None):
    """
    Elbow 샘플 생성 (직경은 inch 입력, 내부에서 cm 변환)
      - total_samples: 전체 샘플 수
      - 직경: diameter_inch_min~diameter_inch_max inch 범위를 bin_width_inch 단위로 분할해 균등 분포 (cm 변환)
      - BendAngle_deg: angles_deg_list 에서 angle_p45_prob 확률에 따라 선택
      - Quantity = 1 고정
    """
    if seed is not None:
        np.random.seed(seed)

    edges_in = np.arange(diameter_inch_min, diameter_inch_max + 1e-8, bin_width_inch)
    bins_in = [(edges_in[i], edges_in[i+1]) for i in range(len(edges_in)-1)]
    n_bins = len(bins_in)

    # 각도 확률 설정
    if 45 in angles_deg_list:
        # 45도가 아닌 다른 각도들의 개수
        num_other_angles = len(angles_deg_list) - 1
        if num_other_angles > 0:
            p_others = (1.0 - angle_p45_prob) / num_other_angles
            probs = [p_others if angle != 45 else angle_p45_prob for angle in angles_deg_list]
            # 확률의 합이 1이 되도록 정규화 (부동소수점 오차 방지)
            probs = np.array(probs) / np.sum(probs)
        else: # 45도만 있는 경우
            probs = [1.0]
    else: # 45도가 리스트에 없으면 균등 확률
        probs = [1.0/len(angles_deg_list)] * len(angles_deg_list)


    records = []
    sid = 1
    for (low_in, high_in), cnt in zip(bins_in, counts):
        diam_in_samples = np.random.uniform(low_in, high_in, size=cnt)
        diam_cm_samples = diam_in_samples * 2.54 # inch to cm

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

def main():
    parser = argparse.ArgumentParser(
        description="Elbow 샘플 데이터를 inch 단위 스펙으로 받아 cm로 변환하여 생성"
    )
    parser.add_argument("n", type=int,
                        help="생성할 전체 샘플 수 (예: 1000)")
    parser.add_argument("-o","--output", default="elbow_samples.xlsx",
                        help="출력 엑셀 파일명")
    parser.add_argument("--seed", type=int, default=42,
                        help="난수 시드 (재현용)")
    parser.add_argument("--bin_width_inch", type=float, required=True, help="직경 bin의 너비 (inch)")
    parser.add_argument("--diameter_inch_min", type=float, required=True, help="최소 직경 (inch)")
    parser.add_argument("--diameter_inch_max", type=float, required=True, help="최대 직경 (inch)")
    parser.add_argument("--angles_deg", type=lambda s: [int(item) for item in s.split(',')], required=True, help="각도 리스트 (쉼표로 구분, 예: 15,20,30,45)")
    parser.add_argument("--angle_p45_prob", type=float, required=True, help="45도 각도의 샘플링 확률 (0.0 ~ 1.0)")

    args = parser.parse_args()

    df = generate_elbow_samples(
        total_samples=args.n,
        bin_width_inch=args.bin_width_inch,
        diameter_inch_min=args.diameter_inch_min,
        diameter_inch_max=args.diameter_inch_max,
        angles_deg_list=args.angles_deg,
        angle_p45_prob=args.angle_p45_prob,
        seed=args.seed
    )
    df.to_excel(args.output, index=False)
    print(f"완료: '{args.output}'에 {len(df)}개의 Elbow 샘플을 저장했습니다.")

if __name__ == "__main__":
    main()
