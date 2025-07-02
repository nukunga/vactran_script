import pandas as pd
import os # os 모듈 추가

# --- 설정 부분 ---
# 원본 데이터가 있는 CSV 파일 경로를 리스트로 입력하세요.
input_file_paths = [
    "pipe_preprocessed_n456_sNA.csv"
]

# 처리된 모든 결과를 통합하여 저장할 파일 경로를 지정하세요.
combined_output_file_path = 'pipe_0.1.csv' # <-- [수정] 통합 저장될 파일명

# 찾고자 하는 Pressure_Torr 값들을 리스트로 지정합니다.
target_pressures = [0.10007515, 0.099928543]

# 평균을 계산할 컬럼과 압력 컬럼의 이름을 지정합니다.
# **참고**: 이미지에는 'Conductance_L_per_min'이 없어 'Conductance_Average'로 작성했습니다.
#          실제 컬럼명에 맞게 수정해주세요.
pressure_col = 'Pressure_Torr'
conductance_col = 'Conductance_L_per_min' # <-- [확인] 'Conductance_L_per_min'이 맞다면 이 부분 수정

# --- 데이터 처리 로직 ---
all_processed_data = [] # 모든 파일의 처리 결과를 누적할 리스트

for input_file_path in input_file_paths:
    print(f"\n--- 처리 시작: {input_file_path} ---")
    try:
        # 1. CSV 파일 불러오기
        df = pd.read_csv(input_file_path, comment='#')
        print(f"'{input_file_path}' 파일을 성공적으로 불러왔습니다.")

        # (선택 사항) 컬럼 이름 앞뒤의 공백 제거
        df.columns = df.columns.str.strip()

        # 현재 파일에서 처리된 데이터를 저장할 빈 리스트 생성
        current_file_processed_data = []

        # 2. SampleID로 그룹화하여 데이터 처리
        for sample_id, group in df.groupby('SampleID'):
            # 3. 특정 Pressure_Torr 값을 가진 행들을 필터링
            filtered_group = group[group[pressure_col].isin(target_pressures)]

            # 조건에 맞는 데이터가 있을 경우에만 로직 실행
            if not filtered_group.empty:
                # 4. Conductance 값의 평균 계산
                avg_conductance = filtered_group[conductance_col].mean()

                # 5. 평균값으로 새로운 데이터 행(row) 생성
                #    그룹의 첫 번째 행을 복사하여 나머지 값들을 채움
                new_row = group.iloc[0].copy()

                #    요청사항에 맞게 Pressure와 Conductance 값 업데이트
                new_row[pressure_col] = 0.1
                new_row[conductance_col] = avg_conductance

                # 처리된 데이터를 현재 파일 결과 리스트에 추가
                current_file_processed_data.append(new_row)
            else:
                print(f"SampleID {sample_id} 에서는 target pressure 값을 찾을 수 없습니다.")

        if current_file_processed_data:
            all_processed_data.extend(current_file_processed_data) # 전체 결과 리스트에 추가
            print(f"'{input_file_path}' 처리 완료. {len(current_file_processed_data)}개의 데이터 포인트 추가됨.")
        else:
            print(f"\n{input_file_path}에서 처리할 데이터가 없습니다.")

    except FileNotFoundError:
        print(f"[오류] 파일을 찾을 수 없습니다. '{input_file_path}' 경로를 확인해주세요.")
    except KeyError as e:
        print(f"[오류] CSV 파일 '{input_file_path}'에서 '{e}' 컬럼을 찾을 수 없습니다. 코드의 컬럼 이름을 확인해주세요.")
    print(f"--- 처리 완료: {input_file_path} ---")

# 모든 파일 처리 후 통합 저장
if all_processed_data:
    combined_result_df = pd.DataFrame(all_processed_data)
    combined_result_df.to_csv(combined_output_file_path, index=False, encoding='utf-8-sig')
    print(f"\n--- 모든 처리 후 통합된 데이터 ---")
    print(combined_result_df.head())
    print(f"\n성공적으로 모든 데이터를 통합하여 '{combined_output_file_path}' 파일로 저장했습니다.")
else:
    print("\n처리된 데이터가 없어 통합 결과 파일을 생성하지 않았습니다.")

print("\n모든 파일 처리가 완료되었습니다.")