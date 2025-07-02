#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import argparse
from tqdm import tqdm

def calculate_theta_deg(d1_cm, d2_cm, length_cm):
    """주어진 형상에 대해 콘의 각도(theta)를 계산합니다."""
    if length_cm <= 0: return np.inf
    delta_d = np.abs(d1_cm - d2_cm)
    if delta_d == 0: return 0.0
    return 2 * np.degrees(np.arctan(delta_d / (2 * length_cm)))

def create_bins_from_spec(spec):
    """(start, end, increment) 스펙으로부터 [low, high) 구간 리스트를 생성합니다."""
    start, end, step = spec
    edges = np.arange(start, end + step, step)
    if edges[-1] > end and not np.isclose(edges[-1], end):
        edges = np.append(edges, end)
    
    edges = np.unique(np.round(edges, 5)) # 부동소수점 오류 방지를 위한 반올림

    return [(edges[i], edges[i+1]) for i in range(len(edges)-1)]

def generate_structured_by_theta(
    item_type,
    d1_inch_spec,
    d2_inch_spec,
    length_mm_spec,
    theta_deg_range,
    samples_per_bin,
    seed=None
):
    """
    D1, D2, Length의 각 구간(bin) 조합을 순차적으로 탐색하며,
    지정된 단일 theta_deg 범위에 맞는 샘플을 `samples_per_bin` 개수만큼 찾습니다.
    """
    if seed is not None:
        np.random.seed(seed)

    d1_bins_in = create_bins_from_spec(d1_inch_spec)
    d2_bins_in = create_bins_from_spec(d2_inch_spec)
    len_bins_mm = create_bins_from_spec(length_mm_spec)
    
    theta_min, theta_max = theta_deg_range
    
    all_found_records = []
    max_attempts_per_bin = 50000

    total_combinations = len(d1_bins_in) * len(d2_bins_in) * len(len_bins_mm)
    pbar = tqdm(total=total_combinations, desc=f"Scanning bins for theta {theta_min:.1f}°-{theta_max:.1f}°", leave=False)

    for d1_low_in, d1_high_in in d1_bins_in:
        for d2_low_in, d2_high_in in d2_bins_in:
            for len_low_mm, len_high_mm in len_bins_mm:
                pbar.update(1)
                
                found_in_this_bin = []
                attempts = 0
                
                while len(found_in_this_bin) < samples_per_bin and attempts < max_attempts_per_bin:
                    attempts += 1
                    
                    d1_in_sample = np.random.uniform(d1_low_in, d1_high_in)
                    d2_in_sample = np.random.uniform(d2_low_in, d2_high_in)
                    len_mm_sample = np.random.uniform(len_low_mm, len_high_mm)

                    d1_cm = d1_in_sample * 2.54
                    d2_cm = d2_in_sample * 2.54
                    len_cm = len_mm_sample / 10.0

                    if item_type == 'reducer' and d1_cm <= d2_cm: continue
                    if item_type == 'expander' and d2_cm <= d1_cm: continue
                    
                    theta = calculate_theta_deg(d1_cm, d2_cm, len_cm)
                    
                    if theta_min <= theta < theta_max:
                        record = {
                            "D1_cm": round(d1_cm, 4),
                            "D2_cm": round(d2_cm, 4),
                            "Length_cm": round(len_cm, 4),
                            "theta_deg": round(theta, 4)
                        }
                        found_in_this_bin.append(record)

                if found_in_this_bin:
                    all_found_records.extend(found_in_this_bin)
    
    pbar.close()

    if not all_found_records:
        return pd.DataFrame(columns=["D1_cm", "D2_cm", "Length_cm", "theta_deg"])

    return pd.DataFrame(all_found_records)

def parse_spec(s):
    """'start,end,increment' 형식의 문자열을 파싱하는 함수"""
    parts = s.split(',')
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("Specification must be in 'start,end,increment' format.")
    try:
        return float(parts[0]), float(parts[1]), float(parts[2])
    except ValueError:
        raise argparse.ArgumentTypeError("Start, end, and increment must be numbers.")

def main():
    parser = argparse.ArgumentParser(
        description="""
        D1, D2, Length의 각 구간(bin)과 지정된 Theta 각도 구간을 순차적으로 탐색하여
        조건에 맞는 샘플을 체계적으로 생성합니다.
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("item_type", choices=['reducer', 'expander'], help="생성할 아이템 타입")
    parser.add_argument("-o", "--output", help="출력 엑셀 파일명. 지정하지 않으면 'item_type_structured_samples.xlsx'로 자동 설정됩니다.")
    parser.add_argument("--d1_spec", type=parse_spec, required=True, help="D1 직경 스펙 (inch): 'start,end,increment'")
    parser.add_argument("--d2_spec", type=parse_spec, required=True, help="D2 직경 스펙 (inch): 'start,end,increment'")
    parser.add_argument("--length_spec", type=parse_spec, required=True, help="길이 스펙 (mm): 'start,end,increment'")
    parser.add_argument("--theta_spec", type=parse_spec, required=True, help="찾고자 하는 Theta 각도 스펙 (deg): 'start,end,increment'")
    parser.add_argument("--samples_per_bin", type=int, default=5, help="각 파라미터 구간(bin) 조합 당 찾을 샘플 수")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드")
    
    args = parser.parse_args()

    output_filename = args.output if args.output else f"{args.item_type}_structured_samples.xlsx"

    print(f"--- Starting Structured Sample Generation for '{args.item_type}' ---")
    print(f"D1 Spec (in): {args.d1_spec}")
    print(f"D2 Spec (in): {args.d2_spec}")
    print(f"Length Spec (mm): {args.length_spec}")
    print(f"Target Theta Spec (deg): start={args.theta_spec[0]}, end={args.theta_spec[1]}, step={args.theta_spec[2]}")
    print(f"Samples to find per bin: {args.samples_per_bin}")
    print("-" * 20)

    # Theta 스펙에 따라 탐색할 각도 구간들 생성
    theta_start, theta_end, theta_step = args.theta_spec
    theta_ranges_to_scan = []
    current_theta = theta_start
    while current_theta < theta_end:
        theta_ranges_to_scan.append((current_theta, current_theta + theta_step))
        current_theta += theta_step

    all_found_dfs = []
    for theta_range in theta_ranges_to_scan:
        print(f"\n>>> Now searching for theta range: {theta_range[0]:.1f}° <= theta < {theta_range[1]:.1f}°")
        df_for_range = generate_structured_by_theta(
            item_type=args.item_type,
            d1_inch_spec=args.d1_spec,
            d2_inch_spec=args.d2_spec,
            length_mm_spec=args.length_spec,
            theta_deg_range=theta_range,
            samples_per_bin=args.samples_per_bin,
            seed=args.seed
        )
        if not df_for_range.empty:
            print(f">>> Found {len(df_for_range)} samples for this theta range.")
            all_found_dfs.append(df_for_range)
        else:
            print(f">>> No samples found for this theta range.")

    if not all_found_dfs:
        print("\n작업이 완료되었지만, 전체 Theta 범위에서 조건을 만족하는 샘플을 찾지 못했습니다.")
        return

    # 모든 결과를 합치고 최종 SampleID 부여
    final_df = pd.concat(all_found_dfs, ignore_index=True)
    final_df['SampleID'] = np.arange(1, len(final_df) + 1)
    
    # 컬럼 순서 재정렬 (SampleID를 맨 앞으로)
    cols = ["SampleID"] + [col for col in final_df.columns if col != "SampleID"]
    final_df = final_df[cols]
    
    final_df.to_excel(output_filename, index=False)
    print(f"\n\n완료: '{output_filename}'에 총 {len(final_df)}개의 샘플을 저장했습니다.")

if __name__ == "__main__":
    main()