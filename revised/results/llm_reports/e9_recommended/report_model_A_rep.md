# Candidate A_rep (YOLO11n, base recipe, retrained) — FAIL

```
**[평가 보고서: 자동화 시나리오 기반 성능 검증 결과]**

**1. 개요**
본 보고서는 모델 `Candidate A_rep (YOLO11n, base recipe, retrained)`에 대한 NIST 및 COCO 기반 강건성(Robustness) 평가 결과를 기술합니다. 본 모델은 극한 환경 및 데이터 오염(Corruption) 상황에서의 운영 신뢰성을 검증받았습니다.

**2. 평가 결과 요약**
*   **최종 판정:** **FAIL (승인 불가)**
*   **CI/CD 배포 여부:** **Deployable: False**
*   **평가 정책:** NIST fit-for-purpose + COCO metrics + corruption robustness demo gate

**3. 세부 지표 분석**
평가 결과, 4가지 핵심 게이트 중 3개 항목에서 기준 미달로 판정되었습니다.

| ID | 평가 항목 | 목표치 | 측정치 | 결과 | 비고 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **G1** | **Clean mAP50** | $\ge$ 0.70 | **0.7279** | **PASS** | 기본 성능 기준 충족 |
| **G2** | **Adverse mAP50** | $\ge$ 0.50 | **0.3223** | **FAIL** | 열악한 환경에서의 최소 성능 저하 |
| **G3** | **RPC50** | $\ge$ 0.65 | **0.6367** | **FAIL** | 오염 대비 상대적 성능 유지 실패 |
| **G4** | **Critical Failure Count** | $\le$ 0 | **1.0** | **FAIL** | 임무 핵심 시나리오 내 치명적 결함 발생 |

**4. 주요 취약점 분석 (Worst Cases)**
시뮬레이션 결과, 특히 다음 시나리오에서 모델의 신뢰성이 급격히 저하됨을 확인하였습니다.
*   **SCN_011 (Extreme/Critical):** 안개, 야간, 노이즈, 위장(Camo) 결합 조건에서 mAP50이 **0.0039**로 측정됨 (Clean 대비 99.46% 성능 저하).
*   **SCN_012 (Extreme/Critical):** 우천, 야간, 노이즈 결합 조건에서 임무 핵심 시나리오 실패 기록.

**5. 종합 의견**
대상 모델은 일반적인 조건(Clean)에서는 요구 성능을 충족하나, **적대적 환경(Adverse/Critical)** 및 **데이터 오염(Corruption)** 상황에서 성능이 급격히 저하되는 취약성을 보였습니다. 특히 임무 핵심 시나리오(Critical Scenario)에서 치명적 결함이 발생하였으므로, 강건성(Robustness) 향상을 위한 재학습 또는 데이터 증강(Augmentation) 전략 보완 후 재평가가 필요합니다.
```
