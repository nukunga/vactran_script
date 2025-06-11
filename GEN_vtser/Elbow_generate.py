import pandas as pd
import os
import argparse

# 엑셀 파일 경로 및 저장 폴더 설정
parser = argparse.ArgumentParser(description="Generate VTSER files from Excel for elbows.")
parser.add_argument("excel_path", help="Path to the input Excel file.")
parser.add_argument("--output_dir", required=True, help="Directory to save VTSER files.") # 추가
args = parser.parse_args()

excel_path = args.excel_path
save_dir = args.output_dir # 수정: 인자로 받은 output_dir 사용

os.makedirs(save_dir, exist_ok=True) # 독립 실행을 위해 유지

# 엑셀 파일 읽기
df = pd.read_excel(excel_path)


# VTSER 파일 생성 함수
def write_vtser_chunk(chunk_df, file_index):
    lines = []
    lines.append("[General]")
    lines.append(f"Total={len(chunk_df)}")
    lines.append("ModelMultiplier=1")


    for idx, row in chunk_df.iterrows():
        diameter_cm = float(row['Diameter_cm'])
        bend_angle = float(row['BendAngle_deg'])
        quantity = int(row['Quantity'])


        lines.append(f"[{idx % 50}]")
        lines.append("Description=ELBOW")
        lines.append(f"Quantity={quantity}")
        lines.append(f"Diameter={diameter_cm:.6f}")
        lines.append("ModelLength=1") # Elbow의 ModelLength는 일반적으로 1 또는 직경 기반 값
        lines.append("Volume=0")
        lines.append("EntranceLoss=0")
        lines.append("ExitLoss=0")
        lines.append(f"BendAngle={bend_angle}")


    # 파일로 저장
    # 파일명에 'elbow'를 명시적으로 추가하여 다른 유형의 파일과 구분
    output_filename = f"ELBOW_SERIES_{file_index+1:03d}.VTSER"
    output_path = os.path.join(save_dir, output_filename) # save_dir 사용
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Saved: {output_path}") # 이모티콘 제거

    # main_pipeline.py에서는 이 반환값을 직접 사용하지 않으므로 반환문은 선택사항
    # return output_path 


# 50개씩 분할 저장
chunk_size = 50
# output_paths = [] # main_pipeline.py에서 사용하지 않으므로 제거 또는 주석 처리 가능
chunks = [df[i:i+chunk_size] for i in range(0, len(df), chunk_size)]
for idx, chunk in enumerate(chunks):
    write_vtser_chunk(chunk.reset_index(drop=True), idx)
    # path = write_vtser_chunk(chunk.reset_index(drop=True), idx)
    # output_paths.append(path) # main_pipeline.py에서 사용하지 않으므로 제거 또는 주석 처리 가능

# output_paths[:3]  # 스크립트 직접 실행 시 디버깅용. main_pipeline.py에서는 영향 없음.