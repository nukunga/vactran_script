import pandas as pd
import os
import argparse

# 엑셀 경로 및 저장 폴더 설정
parser = argparse.ArgumentParser(description="Generate VTSER files from Excel for pipes.")
parser.add_argument("excel_path", help="Path to the input Excel file.")
parser.add_argument("--output_dir", required=True, help="Directory to save VTSER files.") # 추가
args = parser.parse_args()

excel_path = args.excel_path
save_dir = args.output_dir # 수정: 인자로 받은 output_dir 사용

# 폴더가 없으면 생성 (main_pipeline에서 이미 생성하지만, 독립 실행을 위해 유지 가능)
os.makedirs(save_dir, exist_ok=True)

# 엑셀 불러오기
df = pd.read_excel(excel_path)


# 단위 변환: cm → meter로 저장하되, VACTRAN 내부는 cm 유지
def write_vtser_chunk(chunk_df, file_index):
    lines = []
    lines.append("[General]")
    lines.append(f"Total={len(chunk_df)}")
    lines.append("ModelMultiplier=1")
   
    for idx, row in chunk_df.iterrows():
        diameter_cm = float(row['Diameter_cm'])
        length_cm = float(row['Length_cm'])


        lines.append(f"[{idx % 50}]")
        lines.append("Description=PIPE")
        lines.append("Quantity=1")
        lines.append(f"Diameter={diameter_cm:.6f}")
        lines.append(f"ModelLength={length_cm:.6f}")
        lines.append("Volume=0")
        lines.append("EntranceLoss=0")
        lines.append("ExitLoss=0")
        lines.append("EdgeRadius=0")
        lines.append("Projecting=0")


    # 파일 저장
    # 파일명에 'pipe'를 명시적으로 추가
    output_filename = f"PIPE_SERIES_{file_index+1:03d}.VTSER"
    output_path = os.path.join(save_dir, output_filename) # save_dir 사용
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Saved: {output_path}")


# 50개씩 분할 저장
chunk_size = 50
chunks = [df[i:i+chunk_size] for i in range(0, len(df), chunk_size)]
for idx, chunk in enumerate(chunks):
    write_vtser_chunk(chunk.reset_index(drop=True), idx)