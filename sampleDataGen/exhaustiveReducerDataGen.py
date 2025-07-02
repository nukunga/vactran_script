#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import argparse

def generate_exhaustive_reducer_samples(d1_inch_spec, d2_inch_spec, length_mm_spec):
    """
    지정된 시작, 끝, 증가량에 따라 가능한 모든 Reducer 형상 조합을 생성합니다.
    (D1 > D2 조건 만족)
    
    :param d1_inch_spec: (start, end, increment) for D1 in inches.
    :param d2_inch_spec: (start, end, increment) for D2 in inches.
    :param length_mm_spec: (start, end, increment) for Length in mm.
    :return: pandas DataFrame containing all valid combinations.
    """
    d1_start_in, d1_end_in, d1_step_in = d1_inch_spec
    d2_start_in, d2_end_in, d2_step_in = d2_inch_spec
    len_start_mm, len_end_mm, len_step_mm = length_mm_spec

    # D1과 D2는 부동소수점일 수 있으므로 np.arange 유지
    d1_values_in = np.arange(d1_start_in, d1_end_in + d1_step_in / 2, d1_step_in)
    d2_values_in = np.arange(d2_start_in, d2_end_in + d2_step_in / 2, d2_step_in)
    
    # --- 이 부분이 수정되었습니다 ---
    # Length는 10mm와 같이 정수 단위로 증가하는 경우가 많으므로,
    # 정수 연산을 통해 부동소수점 오류를 방지합니다.
    try:
        # 모든 length 관련 스펙을 정수로 변환 시도
        start = int(len_start_mm)
        end = int(len_end_mm)
        step = int(len_step_mm)
        if len_start_mm != start or len_end_mm != end or len_step_mm != step:
            # 하나라도 정수로 변환되지 않으면 경고 출력 (소수점이 유실될 수 있음을 알림)
            print("경고: length 스펙에 소수점이 포함되어 있어 정수로 변환됩니다.")
            
        # 파이썬 내장 range 함수를 사용하여 명확한 정수 시퀀스 생성
        # end 값도 포함하기 위해 end + 1 로 설정
        length_values_mm = list(range(start, end + 1, step))

    except ValueError:
        print("오류: Length 스펙은 정수로 변환 가능한 숫자여야 합니다.")
        return pd.DataFrame()
    # --- 수정 끝 ---

    print(f"--- 생성 범위 ---")
    print(f"D1 (inch): {d1_values_in}")
    print(f"D2 (inch): {d2_values_in}")
    print(f"Length (mm): {length_values_mm}")
    print("-----------------")

    records = []
    sample_id = 1
    for d1_in in d1_values_in:
        for d2_in in d2_values_in:
            # Reducer 조건: D1 > D2
            if d1_in > d2_in:
                for length_mm in length_values_mm:
                    # 단위 변환: inch -> cm, mm -> cm
                    d1_cm = d1_in * 2.54
                    d2_cm = d2_in * 2.54
                    length_cm = length_mm / 10.0
                    
                    records.append({
                        "SampleID": sample_id,
                        "D1_cm":    round(d1_cm, 4),
                        "D2_cm":    round(d2_cm, 4),
                        "Length_cm":round(length_cm, 4)
                    })
                    sample_id += 1

    if not records:
        print("경고: 생성된 데이터가 없습니다. 입력 범위를 확인하세요 (D1 > D2 조건을 만족해야 합니다).")
        return pd.DataFrame(columns=["SampleID", "D1_cm", "D2_cm", "Length_cm"])

    return pd.DataFrame(records)

def parse_spec(s):
    """'start,end,increment' 형식의 문자열을 파싱하는 함수"""
    parts = s.split(',')
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("Specification must be in 'start,end,increment' format.")
    try:
        # 모든 부분을 float으로 변환하여 유연성 확보
        return float(parts[0]), float(parts[1]), float(parts[2])
    except ValueError:
        raise argparse.ArgumentTypeError("Start, end, and increment must be numbers.")

def main():
    parser = argparse.ArgumentParser(
        description="""
        Reducer 샘플 데이터를 Exhaustive (전수조사) 방식으로 생성합니다. 
        각 파라미터는 '시작값,종료값,증가량' 형식으로 지정합니다.
        (예: D1을 1, 2, 3인치로 지정하려면 --d1_spec "1,3,1")
        """
    )
    parser.add_argument("-o", "--output", default="reducer_exhaustive_samples.xlsx", help="출력 엑셀 파일명")
    parser.add_argument("--d1_spec", type=parse_spec, required=True, help="D1 직경 스펙 (inch): start,end,increment")
    parser.add_argument("--d2_spec", type=parse_spec, required=True, help="D2 직경 스펙 (inch): start,end,increment")
    parser.add_argument("--length_spec", type=parse_spec, required=True, help="길이 스펙 (mm): start,end,increment")
    args = parser.parse_args()

    df = generate_exhaustive_reducer_samples(
        d1_inch_spec=args.d1_spec,
        d2_inch_spec=args.d2_spec,
        length_mm_spec=args.length_spec
    )
    
    if not df.empty:
        df.to_excel(args.output, index=False)
        print(f"\n완료: '{args.output}'에 {len(df)}개의 Reducer 샘플을 저장했습니다.")

if __name__ == "__main__":
    main()