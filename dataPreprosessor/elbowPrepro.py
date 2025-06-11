#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import argparse
import pandas as pd
from pathlib import Path

def parse_elbow_file(path: Path, start_sample_id: int):
    """
    ELBOW 텍스트 파일을 파싱해서,
    각 'Data for Conductance' 블록마다 SampleID를 부여하고
    D(cm), 각도, Quantity=1 고정하며,
    연관된 모든 Pressure, Conductance 데이터를 포함하여 반환.
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
            angle_deg, diameter_cm, quantity = None, None, 1 # Quantity is fixed

            temp_search_idx = conductance_block_start_line_idx + 1
            for _ in range(3): # 다음 3줄까지 확인
                if temp_search_idx < len(lines):
                    header_candidate = lines[temp_search_idx].strip()
                    if not header_candidate: # 빈 줄이면 다음 줄로
                        temp_search_idx += 1
                        continue

                    m_geom = re.search(
                        r'\d+\s+ELBOW\(s\),\s*(\d+)\s+Degrees,\s*D=\s*([\d\.E+-]+)\s*Cm',
                        header_candidate
                    )
                    if m_geom:
                        angle_deg   = int(m_geom.group(1))
                        diameter_cm = float(m_geom.group(2))
                        header_found = True
                        geom_details_line_idx = temp_search_idx
                        break
                    else: 
                        break 
                else: 
                    break
                temp_search_idx += 1


            if not header_found:
                print(f"Warning: header parse failed in {path} near line {conductance_block_start_line_idx + 1}. Could not find ELBOW header after 'Data for Conductance'.")
                i = conductance_block_start_line_idx + 1
                while i < len(lines) and not re.match(r'Data for Conductance\s+\d+', lines[i].strip()):
                    i += 1
                continue

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
                        "SampleID":      sample_id,
                        "Diameter_cm":   round(diameter_cm, 4),
                        "BendAngle_deg": angle_deg,
                        "Quantity":      quantity,
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
        description='ELBOW 시리즈 텍스트 파일들을 파싱하여 CSV로 저장'
    )
    parser.add_argument(
        'input_path',
        help='ELBOW 텍스트 파일(.txt) 또는 디렉터리 경로'
    )
    parser.add_argument(
        '-o', '--output', default='elbow_output.csv',
        help='출력 CSV 파일명 (기본: elbow_output.csv)'
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
        rows, sid = parse_elbow_file(p, sid)
        all_rows.extend(rows)

    if not all_rows:
        print("No data parsed.")
        df_empty = pd.DataFrame(columns=[
            "SampleID", "Diameter_cm", "BendAngle_deg", "Quantity", "Pressure_Torr", "Conductance_L_per_min"
        ])
        df_empty.to_csv(args.output, index=False)
        print(f"No data parsed. Empty file with headers created: {args.output}")
        sys.exit(0)

    df = pd.DataFrame(all_rows, columns=[
        "SampleID", "Diameter_cm", "BendAngle_deg", "Quantity", "Pressure_Torr", "Conductance_L_per_min"
    ])
    df.to_csv(args.output, index=False)
    print(f"Completed: saved {len(df)} rows to {args.output}")

if __name__ == '__main__':
    main()
