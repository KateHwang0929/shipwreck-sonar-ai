# Korean Shipwreck 3D Model Database

이 폴더는 `3d modeling/` 안의 GLB, FBX, 참고 이미지를 하나의 데이터베이스로 관리합니다.

## 포함된 데이터

- 6개 선박/선박 유형
- 11개 3D 모델 변형
- GLB, FBX, 참고 이미지 경로
- 실제 잔존 크기 또는 추정 복원 크기
- 시대, 발굴 위치, 수심, 자료 출처
- 파일 크기, SHA-256 해시
- GLB vertex/triangle/material/texture 수
- GLB bounding-box 크기
- 실제 길이에 맞추기 위한 권장 uniform scale
- Blender 및 시뮬레이션 준비 상태

거북선 2개 모델은 고고학적 난파선이 아니므로 `historical_ship_reference`로 따로 분류합니다.

## 권장 폴더 구조

```text
3d modeling/
├── 거북선/
├── 달리도선/
├── 마도1호선/
├── 신안선/
├── 십이동파도선/
├── 완도선/
└── database/
    ├── README.md
    ├── source_metadata.csv
    ├── schema.sql
    ├── build_shipwreck_db.py
    └── generated/
        ├── shipwreck_catalog.csv
        ├── shipwreck_catalog.json
        └── shipwrecks.sqlite
```

## 실행 방법

PowerShell에서 저장소의 `3d modeling/database` 폴더로 이동한 뒤 실행합니다.

```powershell
cd "F:\Artemis Lab\shipwreck-sonar-ai\3d modeling\database"
python build_shipwreck_db.py
```

정확한 파일 크기와 해시가 채워지지 않으면 `--models-root`를 직접 지정합니다.

```powershell
python build_shipwreck_db.py `
  --models-root "F:\Artemis Lab\shipwreck-sonar-ai\3d modeling"
```

모든 GLB, FBX, 이미지가 존재하지 않으면 실패하도록 검사하려면:

```powershell
python build_shipwreck_db.py --strict
```

## 생성 파일

### `shipwreck_catalog.csv`

Notion, Excel, pandas에서 바로 확인하기 위한 평면형 목록입니다.

### `shipwreck_catalog.json`

각 모델의 메타데이터와 검사 결과를 프로그램에서 읽기 위한 JSON입니다.

### `shipwrecks.sqlite`

실제 관계형 데이터베이스입니다. 다음 테이블을 포함합니다.

- `ships`: 선박 단위 정보
- `models`: 모델 변형 및 geometry 정보
- `files`: GLB, FBX, 참고 이미지의 크기와 해시
- `sources`: 공식 연구 페이지와 이용조건

SQLite Viewer 또는 DB Browser for SQLite로 열 수 있습니다.

## 크기와 방향 처리

공식 크기가 있는 모델은 GLB bounding box의 가장 긴 축을 선박 길이로 가정하여 권장 scale을 계산합니다.

```text
recommended_uniform_scale
= target_length_m / bbox_longest_units
```

이 계산은 초기 자동 보정값입니다. 최종 적용 전 Blender에서 반드시 확인합니다.

- `+X`: 선수 방향
- `+Y`: 좌현 또는 선체 폭 방향
- `+Z`: 위쪽
- 단위: metre
- `Ctrl + A`: Rotation & Scale 적용
- origin: 선체 중심 또는 해저 접촉 기준점
- collision mesh: 시뮬레이터용으로 별도 점검

## 데이터 정확도

역사적 크기와 시대 정보는 국립해양유산연구소 페이지를 기준으로 정리했습니다.  
3D 모델은 단일 이미지 기반 AI 생성 모델이므로 정밀 실측 복원과 동일하지 않습니다.  
`source_metadata.csv`의 `target_measurement_type`에서 잔존 크기와 추정 복원 크기를 구분합니다.
