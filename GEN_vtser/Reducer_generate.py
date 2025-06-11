import pandas as pd
import os
import argparse

# 파일 경로 및 저장 폴더 설정
parser = argparse.ArgumentParser(description="Generate VTSER files from Excel for reducers.")
parser.add_argument("excel_path", help="Path to the input Excel file.")
parser.add_argument("--output_dir", required=True, help="Directory to save VTSER files.") # 추가
args = parser.parse_args()

excel_path = args.excel_path
save_dir = args.output_dir # 수정: 인자로 받은 output_dir 사용

# 폴더 생성
os.makedirs(save_dir, exist_ok=True) # 독립 실행을 위해 유지

# 엑셀 불러오기 (열 이름 확인 필요)
df = pd.read_excel(excel_path)


# 열 이름 표준화 (오타 대응, 필요시 사용)
# df.columns = [col.replace("_ength_cm", "Length_cm") for col in df.columns]


# Reducer VTSER 형식 생성 함수
def write_reducer_vtser(chunk_df, file_index):
    lines = []
    lines.append("[General]")
    lines.append(f"Total={len(chunk_df)}")
    lines.append("ModelMultiplier=1")


    for idx, row in chunk_df.iterrows():
        # 엑셀 파일의 컬럼명이 D1_cm, D2_cm, Length_cm 라고 가정
        entrance_d = float(row['D1_cm']) 
        exit_d = float(row['D2_cm'])
        length_cm = float(row['Length_cm'])


        lines.append(f"[{idx % 50}]")
        lines.append("Description=CONE") # Reducer는 CONE으로 표현될 수 있음
        lines.append("Quantity=1")
        # Diameter는 일반적으로 더 작은 쪽 또는 기준이 되는 쪽을 따름. VacTran 문서를 확인 필요.
        # 여기서는 Entrance D를 기준으로 설정.
        lines.append(f"Diameter={entrance_d:.6f}") 
        lines.append(f"ModelLength={length_cm:.6f}")
        lines.append("Volume=0")
        lines.append("EntranceLoss=0") # 값은 예시이며, 실제 모델에 따라 다를 수 있음
        lines.append("ExitLoss=1")     # 값은 예시이며, 실제 모델에 따라 다를 수 있음
        lines.append(f"EntranceDiameter={entrance_d:.6f}")
        lines.append(f"ExitDiameter={exit_d:.6f}")


    # 저장
    # 파일명에 'reducer'를 명시적으로 추가
    output_filename = f"REDUCER_SERIES_{file_index+1:03d}.VTSER"
    output_path = os.path.join(save_dir, output_filename) # save_dir 사용
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Saved: {output_path}") # 이모티콘 제거


# 50개씩 분할 저장
chunk_size = 50
chunks = [df[i:i+chunk_size] for i in range(0, len(df), chunk_size)]
for idx, chunk in enumerate(chunks):
    write_reducer_vtser(chunk.reset_index(drop=True), idx)