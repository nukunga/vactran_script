# VacTran 자동화 파이프라인

## 개요

이 파이프라인은 VacTran 시뮬레이션을 위한 전체 과정을 자동화합니다. 다음 단계를 포함합니다:
1.  형상 샘플 데이터 생성 (Excel 파일)
2.  VacTran 시리즈 파일 (.VTSER) 생성
3.  VacTran 시뮬레이션 자동 실행 및 결과 (.txt) 저장
4.  시뮬레이션 결과 데이터 전처리 및 최종 CSV 파일 생성

파이프라인은 Pipe, Elbow, Reducer, Expander 네 가지 컴포넌트 유형을 지원하며, `mainPipeline.py` 스크립트를 통해 전체 과정을 실행할 수 있습니다.

## 프로젝트 구조

-   `mainPipeline.py`: 전체 파이프라인을 실행하는 메인 스크립트.
-   `sampleDataGen/`: 형상 샘플 데이터(.xlsx) 생성 스크립트 폴더.
    -   `pipeDataGen.py`: 파이프 샘플 데이터 생성.
    -   `elbowDataGen.py`: 엘보 샘플 데이터 생성 (모든 각도 균등 샘플링).
    -   `reducerDataGen.py`: Reducer 샘플 데이터 생성 (D2 기준 샘플링, D1 > D2, 길이 mm 단위 입력).
    -   `expanderDataGen.py`: Expander 샘플 데이터 생성 (D1 기준 샘플링, D2 > D1, 길이 mm 단위 입력).
-   `genVtser/`: Excel 데이터를 기반으로 VacTran 시리즈 파일(.VTSER) 생성 스크립트 폴더.
    -   `pipeGenerate.py` (스크립트 내 실제 파일명: `pipeGenerate.py`)
    -   `elbowGenerate.py` (스크립트 내 실제 파일명: `elbowGenerate.py`)
    -   `reducerGenerate.py` (Reducer 및 Expander 공통 사용, CONE 타입으로 생성, 스크립트 내 실제 파일명: `reducerGenerate.py`)
-   `autoVacModule.py`: `.VTSER` 파일을 사용하여 VacTran 시뮬레이션을 자동 실행하고 결과를 `.txt` 파일로 저장하는 모듈.
-   `dataPreprosessor/`: VacTran 결과(.txt)를 전처리하여 최종 `.csv` 파일을 생성하는 스크립트 폴더.
    -   `pipePrepro.py`
    -   `elbowPrepro.py`
    -   `reducerPrepro.py` (Reducer 및 Expander 공통 사용)
-   `pipeline_output_data/`: `mainPipeline.py` 실행 시 기본적으로 생성되는 최상위 출력 디렉터리. 각 실행마다 아이템 타입, 스펙, 샘플 수, 시드, 타임스탬프가 포함된 하위 폴더가 생성됩니다.

## 요구사항

-   Python 3.x
-   필수 Python 라이브러리:
    -   `pandas`
    -   `numpy`
    -   `openpyxl` (Excel 파일 처리를 위해 pandas가 요구)
    -   `pywinauto` (`autoVacModule.py`에서 사용)
    -   `clipboard` (`autoVacModule.py`에서 사용)
-   VacTran 소프트웨어 설치 (버전 3 권장)
    -   `autoVacModule.py` 내의 `VACTRAN_PATH` 변수를 실제 설치 경로로 수정해야 할 수 있습니다.

## 설치

프로젝트 루트 디렉터리에서 다음 명령어를 사용하여 필요한 라이브러리를 설치합니다:

```bash
pip install pandas numpy openpyxl pywinauto clipboard
```

## 컴포넌트별 기본 생성 파라미터 (`mainPipeline.py` 기준)

`mainPipeline.py` 실행 시 각 컴포넌트 유형별로 사용되는 기본 생성 파라미터는 다음과 같습니다. (내부적으로 cm 변환 후 사용)

-   **Pipe**:
    -   직경 범위 (Diameter inch range): 1.0 - 10.0 inches
    -   길이 범위 (Length mm range): 100 - 20000 mm
    -   직경 Bin 너비 (Bin width inch): 1.0 inch
-   **Elbow**:
    -   직경 범위 (Diameter inch range): 1.0 - 5.0 inches
    -   직경 Bin 너비 (Bin width inch): 1.0 inch
    -   각도 목록 (Angles deg): [15, 20, 30, 45] (균등 샘플링)
    -   수량 (Quantity): 1
-   **Reducer** (D2 기준 샘플링, D1 > D2, D2 < 0.7 * D1):
    -   D2 직경 범위 (D2 inch range): 1.0 - 10.0 inches
    -   D2 Bin 너비 (D2 bin width inch): 1.0 inch
    -   D1 전체 최소 직경 (D1 inch min overall): 0.5 inches
    -   D1 전체 최대 직경 (D1 inch max overall): 14.3 inches (D2 최대값 10인치 / 0.7 근사)
    -   길이 범위 (Length mm range): 50.0 - 10000.0 mm
-   **Expander** (D1 기준 샘플링, D2 > D1, D1 < 0.7 * D2):
    -   D1 직경 범위 (D1 inch range): 1.0 - 10.0 inches
    -   D1 Bin 너비 (D1 bin width inch): 1.0 inch
    -   D2 전체 최소 직경 (D2 inch min overall): 0.5 inches
    -   D2 전체 최대 직경 (D2 inch max overall): 14.3 inches (D1 최대값 10인치 / 0.7 근사)
    -   길이 범위 (Length mm range): 50.0 - 10000.0 mm

## 파이프라인 실행 (`mainPipeline.py`)

전체 파이프라인은 `mainPipeline.py` 스크립트를 통해 실행하는 것이 권장됩니다.

### 명령어 형식

```bash
python mainPipeline.py <item_type> <num_samples> [options]
```

### 인자 설명

-   `item_type`: 처리할 컴포넌트 유형. 다음 중 하나를 선택합니다:
    -   `pipe`
    -   `elbow`
    -   `reducer`
    -   `expander`
-   `num_samples`: 생성할 샘플 데이터의 수량 (정수).
-   `--seed <int>`: 데이터 생성 시 사용할 난수 시드. 기본값: `42`.
-   `--base_output_dir <path>`: 모든 출력 파일이 저장될 최상위 기본 디렉터리. 기본값: 프로젝트 루트 내 `pipeline_output_data`.

### 실행 예시

```bash
# Pipe 샘플 1000개 생성 (기본 시드 42, 기본 출력 폴더 사용)
python mainPipeline.py pipe 1000

# Elbow 샘플 500개 생성 (시드 123 사용, 기본 출력 폴더 사용)
python mainPipeline.py elbow 500 --seed 123

# Reducer 샘플 200개 생성 (특정 출력 폴더 지정)
python mainPipeline.py reducer 200 --base_output_dir ./my_custom_outputs

# Expander 샘플 300개 생성
python mainPipeline.py expander 300
```

### 출력 디렉터리 구조

`mainPipeline.py`를 실행하면 지정된 `--base_output_dir` (기본값: `pipeline_output_data`) 아래에 다음과 같은 구조로 실행별 폴더가 생성됩니다. 폴더명에는 아이템 타입, 주요 스펙, 샘플 수, 시드, 생성 타임스탬프가 포함됩니다:

```
pipeline_output_data/
├── pipe_1000samples_seed42_20230315_120000
│   ├── sample_data_pipe.xlsx
│   ├── vtser_files
│   │   └── Pipe.vtser
│   ├── txt_results
│   │   └── VacTran_results_pipe.txt
│   └── csv_results
│       └── final_results_pipe.csv
├── elbow_500samples_seed123_20230315_120500
│   ├── sample_data_elbow.xlsx
│   ├── vtser_files
│   │   └── Elbow.vtser
│   ├── txt_results
│   │   └── VacTran_results_elbow.txt
│   └── csv_results
│       └── final_results_elbow.csv
├── reducer_200samples_seed42_20230315_121000
│   ├── sample_data_reducer.xlsx
│   ├── vtser_files
│   │   └── Reducer.vtser
│   ├── txt_results
│   │   └── VacTran_results_reducer.txt
│   └── csv_results
│       └── final_results_reducer.csv
└── expander_300samples_seed42_20230315_121500
    ├── sample_data_expander.xlsx
    ├── vtser_files
    │   └── Expander.vtser
    ├── txt_results
    │   └── VacTran_results_expander.txt
    └── csv_results
        └── final_results_expander.csv
```

## 수동 단계별 실행 (참고용)

각 단계를 개별적으로 실행할 수도 있습니다. 이는 디버깅이나 특정 단계만 재실행할 때 유용할 수 있습니다. 모든 경로는 프로젝트 루트 디렉터리 기준입니다.

### 1단계: 샘플 형상 데이터 생성 (Excel)

형상 데이터 생성을 위한 스크립트를 직접 실행하여 샘플 데이터를 생성할 수 있습니다.

-   **Pipe 샘플 생성:**
    ```bash
    python sampleDataGen/pipeDataGen.py <생성할 샘플 수> -o <출력_Excel_경로_pipe.xlsx> --seed <시드값>
    ```

-   **Elbow 샘플 생성:**
    ```bash
    python sampleDataGen/elbowDataGen.py <생성할 샘플 수> -o <출력_Excel_경로_elbow.xlsx> --seed <시드값>
    ```

-   **Reducer 샘플 생성 (D1 > D2):**
    ```bash
    python sampleDataGen/reducerDataGen.py <생성할 샘플 수> -o <출력_Excel_경로_reducer.xlsx> --seed <시드값>
    ```

-   **Expander 샘플 생성 (D2 > D1):**
    ```bash
    python sampleDataGen/expanderDataGen.py <생성할 샘플 수> -o <출력_Excel_경로_expander.xlsx> --seed <시드값>
    ```

### 2단계: VTSER 파일 생성

생성된 Excel 파일을 기반으로 VacTran 시리즈 파일(.VTSER)을 생성합니다.

-   **Pipe VTSER 생성:**
    ```bash
    python genVtser/Pipe_generate.py <입력_Excel_경로_pipe.xlsx> --output_dir <VTSER_저장_폴더_pipe>
    ```

-   **Elbow VTSER 생성:**
    ```bash
    python genVtser/Elbow_generate.py <입력_Excel_경로_elbow.xlsx> --output_dir <VTSER_저장_폴더_elbow>
    ```

-   **Reducer VTSER 생성:**
    ```bash
    python genVtser/Reducer_generate.py <입력_Excel_경로_reducer.xlsx> --output_dir <VTSER_저장_폴더_reducer>
    ```

-   **Expander VTSER 생성:**
    (Reducer와 동일한 `Reducer_generate.py` 스크립트 사용)
    ```bash
    python genVtser/Reducer_generate.py <입력_Excel_경로_expander.xlsx> --output_dir <VTSER_저장_폴더_expander>
    ```

### 3단계: VacTran 자동 실행 및 TXT 결과 생성

생성된 VTSER 파일을 사용하여 VacTran 시뮬레이션을 자동으로 실행하고 결과를 TXT 파일로 저장합니다.

예 (Reducer의 경우):
`python auto_vac_module.py ./vtser_files/reducer ./txt_results/reducer`

예 (Expander의 경우):
`python auto_vac_module.py ./vtser_files/expander ./txt_results/expander`

### 4단계: TXT 파일 전처리 및 CSV 생성

생성된 TXT 결과 파일을 전처리하여 최종 CSV 파일을 생성합니다.

-   **Pipe 결과 전처리:**
    ```bash
    python dataPreprosessor/pipePrepro.py <TXT_입력_폴더_pipe> -o <출력_CSV_경로_pipe.csv>
    ```

-   **Elbow 결과 전처리:**
    ```bash
    python dataPreprosessor/elbowPrepro.py <TXT_입력_폴더_elbow> -o <출력_CSV_경로_elbow.csv>
    ```

-   **Reducer 결과 전처리:**
    ```bash
    python dataPreprosessor/reducerPrepro.py <TXT_입력_폴더_reducer> -o <출력_CSV_경로_reducer.csv>
    ```

-   **Expander 결과 전처리:**
    (Reducer와 동일한 `reducerPrepro.py` 스크립트 사용)
    ```bash
    python dataPreprosessor/reducerPrepro.py <TXT_입력_폴더_expander> -o <출력_CSV_경로_expander.csv>
    ```

## 중요 참고사항

-   각 단계별 스크립트 실행 시, `<...>`로 표시된 부분은 실제 경로 및 파일명으로 대체해야 합니다.
-   Excel 파일, VTSER 파일, TXT 결과 파일, CSV 파일 등은 프로젝트 구조에 맞게 적절한 폴더에 저장되어야 합니다.
-   `main_pipeline.py` 스크립트를 사용하는 것이 전체 파이프라인을 자동으로 실행하는 가장 간편한 방법입니다.

