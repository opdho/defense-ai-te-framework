# Candidate B (YOLO11s, robust recipe) — FAIL

```
**[방위산업 AI 모델 평가 결과 보고서]**

**1. 평가 개요**
*   **모델명:** Candidate B (YOLO11s, robust recipe)
*   **모델 ID:** model_B
*   **평가 정책:** NIST fit-for-purpose + COCO metrics + corruption robustness demo gate (nist_coco_robustness_demo_v1)

**2. 주요 평가 지표 (Metrics)**
*   **Clean mAP50:** 0.7695 (임계치 0.70 이상 - **PASS**)
*   **Adverse mAP50:** 0.5487 (임계치 0.50 이상 - **PASS**)
*   **Relative Performance (RPC50):** 0.8243 (임계치 0.65 이상 - **PASS**)
*   **Critical Failure Count:** 1.0 (임계치 0.0 이하 - **FAIL**)

**3. 상세 분석 결과**
본 모델은 일반적인 탐지 성능(Clean mAP50) 및 열악한 환경에서의 상대적 성능(RPC50) 측면에서는 요구되는 기술적 기준을 충족하였습니다. 그러나 **안전 필수(Safety-Critical) 시나리오**에서의 검증 결과, 치명적 실패(Critical Failure)가 1건 발생하였습니다.

특히 시나리오 **SCN_011 (안개/야간/노이즈/위장)** 환경에서 mAP50 수치가 **0.1087**로 급락하며, Clean 성능 대비 **85.88%의 성능 저하**를 기록하였습니다. 이는 해당 조건에서 모델의 신뢰성이 보장되지 않음을 의미합니다.

**4. CI/CD 배포 결정**
*   **최종 판정:** **FAIL (배포 불가)**
*   **결정 사유:** 
    *   임무 핵심 시나리오(Mission-critical scenario)에서 최소 성능 하한선(Critical failure floor)을 하회하는 사례가 식별됨.
    *   방위 산업의 요구되는 신뢰성 및 안전성 기준을 충족하지 못하므로, 모델의 재학습 또는 데이터 증강(Augmentation) 전략 수립을 통한 성능 개선 후 재평가를 권고함.
```
