#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import argparse
import pandas as pd
from pathlib import Path

def parse_file(path, start_sample_id):
    """
    주어진 파일을 파싱하여,
    각 'Data for Conductance' 블록마다 sample_id를 부여하고
    (너비 변환: in -> cm, 길이: 이미 cm 단위)
    200개의 pressure/conductance 데이터를 리턴.
    """
    rows = []
    sample_id = start_sample_id
    diameter_cm = None
    length_cm = None

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        # 블록 헤더 찾기
        m = re.match(r'Data for Conductance\s+(\d+)', lines[i])
        if m:
            # header 라인 바로 다음 줄에 PIPE, L=..., D=... In
            header_line_index = i + 1
            # 다음 줄이 파일의 끝을 넘지 않는지 확인
            if header_line_index < len(lines):
                header = lines[header_line_index]
                # 예: "1 PIPE, L= 1373.0878 Cm, D= 4.7501 Cm, no exit, no entrance"
                m2 = re.search(r'\d+\s*PIPE,\s*L=\s*([\d\.E+-]+)\s*Cm,\s*D=\s*([\d\.E+-]+)\s*Cm', header) # In을 Cm으로 변경
                if not m2:
                    # 다음 줄도 확인 (빈 줄이나 다른 형식의 줄이 있을 수 있음)
                    if header_line_index + 1 < len(lines):
                        header = lines[header_line_index + 1]
                        m2 = re.search(r'\d+\s*PIPE,\s*L=\s*([\d\.E+-]+)\s*Cm,\s*D=\s*([\d\.E+-]+)\s*Cm', header) # In을 Cm으로 변경
                        if m2:
                            i +=1 # 한 줄 더 건너뛰었으므로 인덱스 조정
                        else:
                            # 두 번째 시도에서도 못 찾으면 에러 대신 다음 블록으로 건너뛰도록 처리하거나 로깅
                            print(f"Warning: Could not parse L and D from header in {path} near line {i+1}. Skipping block.")
                            # 다음 'Data for Conductance'를 찾기 위해 i를 증가시키고 continue
                            i += 1
                            while i < len(lines) and not re.match(r'Data for Conductance\s+(\d+)', lines[i]):
                                i += 1
                            continue # 다음 Data for Conductance 블록으로
                    else:
                        print(f"Warning: Could not parse L and D from header in {path} near line {i+1} (EOF). Skipping block.")
                        i +=1
                        continue


                if not m2: # 여전히 m2가 None이면 이 블록은 스킵
                    i +=1
                    continue

                length_cm = float(m2.group(1))
                # diameter_in = float(m2.group(2)) # 이 줄은 Cm 단위를 사용하므로 주석 처리 또는 삭제
                # diameter_cm = diameter_in * 2.54 # 이 줄은 Cm 단위를 사용하므로 주석 처리 또는 삭제
                diameter_cm = float(m2.group(2)) # Diameter 값을 직접 사용

                # 그 다음 줄들(1) ... (200) 파싱
                j = i + 2 # L, D 정보가 있는 줄 다음부터 데이터 시작
                count = 0
                while j < len(lines) and count < 200:
                    # 데이터 라인 형식: "1) 3.6926950E+02, 1.1192903E+06"
                    m3 = re.match(r'\s*\d+\)\s*([\d\.E+-]+),\s*([\d\.E+-]+)', lines[j])
                    if m3:
                        pressure = float(m3.group(1))
                        conductance = float(m3.group(2))
                        rows.append({
                            'SampleID': sample_id,
                            'Diameter_cm': diameter_cm,
                            'Length_cm': length_cm,
                            'Pressure_Torr': pressure,
                            'Conductance_L_per_min': conductance,
                        })
                        count += 1
                    j += 1

            sample_id += 1
            i = j
        else:
            i += 1

    return rows, sample_id

def main():
    parser = argparse.ArgumentParser(
        description='텍스트 파일들을 파싱하여 CSV로 저장합니다.'
    )
    parser.add_argument(
        'input_path',
        help='입력할 텍스트 파일 또는 파일들이 있는 디렉터리 경로'
    )
    parser.add_argument(
        '-o', '--output', default='output.csv',
        help='출력 CSV 파일명 (기본: output.csv)'
    )
    args = parser.parse_args()

    input_path_obj = Path(args.input_path)
    paths_to_process = []

    if input_path_obj.is_file():
        paths_to_process.append(input_path_obj)
    elif input_path_obj.is_dir():
        # 디렉터리 내 .txt 파일들을 대상으로 함
        paths_to_process.extend(list(input_path_obj.glob('*.txt')))
        if not paths_to_process:
            print(f"경고: 디렉터리 '{input_path_obj}'에서 처리할 .txt 파일을 찾을 수 없습니다.")
    else:
        print(f"오류: 잘못된 경로입니다: '{args.input_path}'. 파일 또는 디렉터리여야 합니다.")
        sys.exit(1)

    # 파일명 오름차순 정렬
    paths = sorted(paths_to_process)

    if not paths:
        print("처리할 파일을 찾을 수 없습니다.")
        # 처리할 파일이 없을 경우, 헤더만 있는 빈 CSV 파일을 생성할 수 있습니다.
        df_empty = pd.DataFrame(columns=[
            'SampleID', 'Diameter_cm', 'Length_cm', 'Pressure_Torr', 'Conductance_L_per_min'
        ])
        df_empty.to_csv(args.output, index=False)
        print(f"처리할 파일이 없어 빈 파일 '{args.output}'이(가) 생성되었습니다(헤더 포함).")
        return

    all_rows = []
    sample_id = 1

    for p in paths:
        print(f"파일 처리 중: {p}")
        rows, new_sample_id = parse_file(p, sample_id)
        if rows: # 파싱된 데이터가 있을 경우에만 sample_id 업데이트
            all_rows.extend(rows)
            sample_id = new_sample_id
        else:
            print(f"경고: 파일 '{p}'에서 데이터를 파싱하지 못했거나 데이터가 없습니다.")


    if not all_rows:
        print("파싱된 데이터가 없습니다. 출력 파일이 비어 있거나 헤더만 포함될 수 있습니다.")
        # all_rows가 비어있어도 헤더가 있는 CSV를 생성합니다.
        df_empty = pd.DataFrame(columns=[
            'SampleID', 'Diameter_cm', 'Length_cm', 'Pressure_Torr', 'Conductance_L_per_min'
        ])
        df_empty.to_csv(args.output, index=False)
        print(f"파싱된 데이터가 없어 빈 파일 '{args.output}'이(가) 생성되었습니다(헤더 포함).")
        return

    # DataFrame으로 변환하여 CSV로 저장
    df = pd.DataFrame(all_rows, columns=[
        'SampleID', 'Diameter_cm', 'Length_cm', 'Pressure_Torr', 'Conductance_L_per_min'
    ])
    df.to_csv(args.output, index=False)
    print(f"완료: {args.output}에 저장되었습니다.")

if __name__ == '__main__':
    main()
