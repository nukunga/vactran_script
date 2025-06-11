#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import argparse
import pandas as pd
from pathlib import Path

def parse_reducer_file(path: Path, start_sample_id: int):
    """
    REDUCER(.txt) 파일을 파싱하여,
    각 'Data for Conductance' 블록마다 SampleID를 부여하고
    Entrance D, Exit D, L을 cm 단위로 추출하며,
    연관된 모든 Pressure, Conductance 데이터를 포함하여 rows 리스트로 반환.
    """
    rows = []
    sample_id = start_sample_id

    with path.open('r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        current_line_stripped = lines[i].strip()
        if re.match(r'Data for Conductance\s+\d+', current_line_stripped):
            conductance_block_start_line_idx = i

            header_found = False
            geom_details_line_idx = -1
            length_cm, d1_cm, d2_cm = None, None, None

            temp_search_idx = conductance_block_start_line_idx + 1
            for _ in range(3): # 다음 3줄까지 확인
                if temp_search_idx < len(lines):
                    header_candidate = lines[temp_search_idx].strip()
                    if not header_candidate: # 빈 줄이면 다음 줄로
                        temp_search_idx += 1
                        continue

                    m_geom = re.search(
                        r'L=\s*([\d\.E+-]+)\s*Cm,\s*Entrance D=\s*([\d\.E+-]+)\s*,\s*Exit D=\s*([\d\.E+-]+)\s*Cm',
                        header_candidate
                    )
                    if m_geom:
                        length_cm = float(m_geom.group(1))
                        d1_cm     = float(m_geom.group(2))
                        d2_cm     = float(m_geom.group(3))
                        header_found = True
                        geom_details_line_idx = temp_search_idx
                        break
                    else: # 패턴이 맞지 않으면 더 이상 탐색 안 함
                        break
                else: # 파일 끝
                    break
                temp_search_idx += 1 # 다음 후보 라인으로 (이 부분은 for 루프의 다음 반복에서 사용됨)


            if not header_found:
                print(f"Warning: header parse failed in {path} near line {conductance_block_start_line_idx + 1}. Could not find REDUCER header after 'Data for Conductance'.")
                i = conductance_block_start_line_idx + 1
                while i < len(lines) and not re.match(r'Data for Conductance\s+\d+', lines[i].strip()):
                    i += 1
                continue

            # 기하학적 헤더가 발견된 경우, 데이터 파싱 시작
            data_cursor = geom_details_line_idx + 1
            data_parsed_this_block = False
            
            while data_cursor < len(lines):
                line_content = lines[data_cursor].strip()
                if not line_content: 
                    data_cursor += 1
                    continue
                if re.match(r'Data for Conductance\s+\d+', line_content): 
                    break 

                m_data = re.match(r'\s*\d+\)\s*([\d\.E+-]+),\s*([\d\.E+-]+)', line_content)
                if m_data:
                    pressure = float(m_data.group(1))
                    conductance_val = float(m_data.group(2))
                    rows.append({
                        "SampleID": sample_id,
                        "D1_cm": round(d1_cm, 4),
                        "D2_cm": round(d2_cm, 4),
                        "Length_cm": round(length_cm, 4),
                        "Pressure_Torr": pressure,
                        "Conductance_L_per_min": conductance_val
                    })
                    data_parsed_this_block = True
                else: 
                    break 
                data_cursor += 1
            
            if data_parsed_this_block:
                sample_id += 1
            
            i = data_cursor 
        
        else: 
            i += 1
            
    return rows, sample_id


def main():
    parser = argparse.ArgumentParser(
        description='REDUCER 시리즈 텍스트 파일들을 파싱하여 CSV로 저장'
    )
    parser.add_argument(
        'input_path',
        help='REDUCER 텍스트 파일(.txt) 또는 디렉터리 경로'
    )
    parser.add_argument(
        '-o', '--output', default='reducer_output.csv',
        help='출력 CSV 파일명 (기본: reducer_output.csv)'
    )
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if input_path.is_dir():
        txt_files = sorted(input_path.glob('*.txt'))
    elif input_path.is_file():
        txt_files = [input_path]
    else:
        print(f"Error: invalid path {input_path}")
        sys.exit(1)

    all_rows = []
    sid = 1
    for p in txt_files:
        print(f"Parsing {p} …")
        rows, sid = parse_reducer_file(p, sid)
        all_rows.extend(rows)

    if not all_rows:
        print("No data parsed.")
        # 헤더만 있는 빈 CSV 파일을 생성할 수 있습니다.
        df_empty = pd.DataFrame(columns=[
            "SampleID", "D1_cm", "D2_cm", "Length_cm", "Pressure_Torr", "Conductance_L_per_min"
        ])
        df_empty.to_csv(args.output, index=False)
        print(f"No data parsed. Empty file with headers created: {args.output}")
        sys.exit(0)


    df = pd.DataFrame(all_rows, columns=[
        "SampleID", "D1_cm", "D2_cm", "Length_cm", "Pressure_Torr", "Conductance_L_per_min"
    ])
    df.to_csv(args.output, index=False)
    print(f"Completed: saved {len(df)} rows to {args.output}")

if __name__ == '__main__':
    main()
