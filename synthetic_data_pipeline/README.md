# 난파선 3d 모델 및 메타데이터 db 구축

상태: 진행 중
담당자: Kate Hwang
마감일: 07/24/2026
업데이트 시간: July 26, 2026 10:48 PM

## 1. Synthetic Data Generation Pipeline

- 한국 난파선 3D model을 기반으로 다양한 수중환경과 센서 조건을 자동 생성함
- HoloOcean에서 labeled synthetic data를 생성할 수 있는 pipeline을 구축함

## 2. Objective

여러 simulation scene을 생성하는 시스템을 구축하는 것이 목적

최종적으로 각 scene에 대응하는 RGB, depth, semantic segmentation, sonar, sensor pose 및 metadata를 함께 저장하는 synthetic dataset 생성을 목표로 한다

## 3. 핵심 이론

Simulation-based Data Augmentation

이미지 자체가 아니라 **이미지를 생성하는 조건을 변경한다.**

```
3D Wreck Model
+ Wreck Pose
+ Sensor Pose
+ Underwater Environment
+ Sonar Configuration
= New 2D Observation
```

즉, 동일한 난파선도 센서 거리, 관측 방향, 수심, 탁도 및 sonar 설정이 달라지면 서로 다른 2D sensor data로 생성된다.

## 4. Structure

Repository의 pipeline은 Korean shipwreck catalog와 FBX registry를 입력으로 사용하여 randomized scene manifest를 만들고, 이를 HoloOcean scenario 형식으로 변환하도록 설계하였다

## 5. 구축 내용

국립해양유산연구소 자료를 바탕으로 한국 또는 한국에서 발굴된 난파선 정보를 구조화하였다

현재 catalog에는 총 14건의 난파선 정보가 포함되어 있다. 각 record에는 다음 정보가 저장된다: 난파선 한글 및 영문 이름, 시대, 발굴 위치, 발굴 연도, 수심, 잔존 선체 크기, 추정 또는 복원 크기, 선박 및 적재물 설명, 공식 출처…

현재 repository에 존재하는 11개의 FBX model variant를 simulation asset으로 등록하였다

등록된 주요 난파선:

- 달리도선
- 마도 1호선
- 신안선
- 십이동파도선
- 완도선
- 거북선 reference model

** 잔존 선체와 추정 복원 모델이 별도 asset으로 등록되어 있다

** 거북선 모델은 실제 발굴 난파선이 아니기 때문에 historical reference로 분리하였다

## 6. Scene Randomization Logic

각 scene에서는 다음 parameter를 random sampling한다

| Category | Randomized Parameters |
| --- | --- |
| Wreck | model, variant, yaw, pitch, roll, burial |
| AUV | distance, height, orbit angle, sensor orientation |
| Sonar | maximum range, azimuth, elevation, additive noise, multiplicative noise |
| Environment | visibility, turbidity, current speed |

현재 설정 범위:

- Sensor distance: 6–25 m
- Sensor height: 1.5–10 m
- Orbit angle: 0–360°
- Wreck yaw: 0–360°
- Wreck roll: −8–8°
- Wreck pitch: −12–12°
- Sonar range: 20–50 m
- Visibility: 2–20 m
- Turbidity: 0–1
- Sediment burial: 0–0.35

구체적인 randomization 범위는 `config.json`에서 변경할 수 있다

## 7. 구현 결과

Randomized Manifest 생성

각 line이 하나의 simulation scene을 나타내는 `scene_manifest.jsonl`을 생성하였다
실제 HoloOcean을 실행하지 않고도 `scenario.json`과 `metadata.json`이 정상적으로 생성되는 것을 확인하였다

생성된 sample scene에서는 다음 asset이 자동 선택되었다.

```
Asset: dallido_reconstruction
Korean name: 달리도선
Variant: estimated_reconstruction
FBX file detected: true
Unreal actor: BP_DallidoReconstruction
```

database에서 model을 선택하고 scene별 sensor 및 environment 조건을 자동 생성할 수 있음을 보여준다

## 8. HoloOcean Scenario Definition

각 scene은 다음 sensor를 포함하는 HoloOcean scenario로 변환된다

HoloOcean 실행 후 scene별 출력은 다음 구조로 저장하도록 설계하였다.

```
scene_000001/
├── rgb.png
├── depth.npy
├── semantic.png
├── sonar.npy
├── sonar_preview.png
├── pose.npy
└── metadata.json
```

작업 필요: Custom Unreal world integration/Actual sonar/RGB rendering

본 pipeline이 HoloOcean custom world와 연결되면, 실제 데이터가 부족한 상황에서도 다양한 관측 조건을 포함한 labeled dataset을 대량 생성할 수 있다

## 지원 파일

난파선 3D Models: [shipwreck-sonar-ai/3d modeling at main · KateHwang0929/shipwreck-sonar-ai](https://github.com/KateHwang0929/shipwreck-sonar-ai/tree/main/3d%20modeling)

DB: [shipwreck-sonar-ai/synthetic_data_pipeline at main · KateHwang0929/shipwreck-sonar-ai](https://github.com/KateHwang0929/shipwreck-sonar-ai/tree/main/synthetic_data_pipeline)