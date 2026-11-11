# Candidate D (YOLO11s, base recipe) — FAIL

```
**[테스트 및 평가(T&E) 분석 보고서]**

**1. 분석 개요**
*   **대상 모델:** Candidate D (YOLO11s, base recipe)
*   **평가 정책:** NIST fit-for-purpose + COCO metrics + corruption robustness demo gate (nist_coco_robustness_demo_v1)
*   **평가 목적:** 기본 성능(Clean mAP50) 및 적대적/열악한 환경(Adverse)에서의 강건성(Robustness) 검증

**2. 주요 평가 지표 분석**
| 지표 ID | 평가 항목 | 목표치 (Threshold) | 측정치 (Value) | 결과 |
| :--- | :--- | :--- | :--- | :--- |
| **G1** | Clean mAP50 | $\ge$ 0.7 | **0.7650** | **PASS** |
| **G2** | Adverse mAP50 | $\ge$ 0.5 | **0.3695** | **FAIL** |
| **G3** | RPC50 (상대 성능) | $\ge$ 0.65 | **0.6643** | **PASS** |
| **G4** | Critical Failure Count | $\le$ 0 | **1.0** | **FAIL** |

**3. 상세 분석 결과**
*   **기본 성능:** Clean 환경에서의 mAP50은 0.765를 기록하여 운영상 신뢰성을 확보하는 기준을 충족함.
*   **강건성 결함:** 열악한 환경(Adverse)에서의 mAP50이 0.3695로 기준치(0.5)에 미달함. 특히 **SCN_011(안개+야간+노이즈+위장)** 시나리오에서 mAP50이 0.0138로 급락하며 98% 이상의 성능 저하를 보임.
*   **치명적 실패:** 임무 수행에 필수적인 Critical 시나리오에서 허용치 이상의 실패 사례(Count: 1)가 발생함. 이는 특정 환경 조합에서 모델의 탐지 능력이 완전히 상실됨을 의미함.

**4. CI/CD Gate 결정**
*   **최종 판정:** **FAIL (불합격)**
*   **배포 가능 여부:** **False (배포 불가)**
*   **조치 사항:** 
    *   Adverse/Critical 시나리오에서의 강건성 향상을 위한 추가 학습 데이터 확보 필요.
    *   특히 SCN_011과 같은 극한 환경(Extreme)에서의 탐지 성능 개선을 위한 모델 튜닝 또는 데이터 증강 전략 재수립 요망.
```
