# Prompt — Notion API Spec Export Review and api.md v1 Generation

<role>
당신은 RESTful API 설계, Django/DRF 백엔드 개발, 제품 MVP 설계, 개인정보 보호, 접근 제어, DevOps 운영 가능성을 모두 고려하는 리드급 API 아키텍트입니다.

당신은 단순히 API 명세를 예쁘게 정리하는 역할이 아닙니다. 이 프로젝트의 비즈니스 의도, MVP 범위, 사용자 신뢰, 조언가 검증, 관리자 승인 흐름, 개인정보 최소 수집 원칙, 로컬 컨테이너 MVP 목표에 맞게 API 명세를 비판적으로 검토해야 합니다. </role>

<context>
프로젝트명: chamneul

서비스:
신뢰할 수 있는 인생 의사결정 가이드 서비스

서비스 핵심:
사용자가 고민을 작성하고, 조언가가 조언을 제공하며, 조언의 승인·피드백·결과 기록을 통해 장기적으로 신뢰도를 추적한다.

현재 단계:
Phase 2 — 로컬 컨테이너 기반 MVP 개발 전 API 명세 정합성 검토

현재 목표:
Notion DB로 작성된 API 명세 v0를 markdown으로 export한 뒤, 이를 검토하여 설계상 문제를 찾고, Owner의 확정 답변을 받아 docs/api.md v1을 생성한다.

중요:
코드 구현은 아직 하지 않는다. 먼저 API 명세와 데이터 모델 방향을 바로잡는다. </context>

<source_of_truth>
다음 파일을 반드시 읽어라.

1. CLAUDE.md
2. docs/0 README.md
3. docs/1 서비스기획_v1.md
4. docs/2 mvp-scope.md
5. docs/adr/ADR-001-local-container-architecture.md
6. Notion에서 export된 API 명세 markdown 파일

읽지 않은 파일에 근거하여 판단하지 마라.
파일이 없으면 없는 파일 목록을 먼저 알려라.
</source_of_truth>

<fixed_decisions>
다음은 이미 확정된 사항이다. 임의로 바꾸지 마라.

URI 규칙:

* URI 마지막에는 /를 포함하지 않는다.
* _는 사용하지 않는다. 대신 하이픈(-)을 사용한다.
* 행위 동사가 아닌 결과 자원 명사를 포함한다.
* 소문자로 작성한다.
* 파일 확장자는 URI에 포함하지 않는다.
* 도출된 api 명세는 v1으로 정하며, Prefix에 `/api/v1/`을 포함한다.

조언가 신청 Request:

* advisor_type은 Request Front Form에서 제외한다.
* real_name은 Request Front Form에서 제외한다.

조언가 신청 상태:

* PENDING
* REVIEWING
* APPROVED
* REJECTED
* WITHDRAWN
* WITHDRAWN은 MVP에서는 Model에만 추가할 수 있다.

조언 상태:

* PENDING
* REVIEWING
* APPROVED
* REJECTED
* DELETED
* 사용자는 APPROVED 조언만 볼 수 있다.

피드백 상태:

* SUBMITTED
* REVIEWED
* ARCHIVED

알림 생성 조건:

* 조언 승인 → 고민 작성자에게 알림 생성
* 조언 반려 → 조언가에게 알림 생성
* 조언가 신청 승인/반려 → 신청자에게 알림 생성
* 새 고민 배정 → 조언가에게 알림 생성

알림 Type:

* ADVICE_APPROVED
* ADVICE_REJECTED
* ADVISOR_APPLICATION_APPROVED
* ADVISOR_APPLICATION_REJECTED
* ASSIGNMENT_CREATED

고민 택소노미 v0:

* career_transition
* job_change
* burnout
* startup_failure
* leadership
* relationship
* life_direction
* major_life_decision
* education_choice
* relocation
* finance_major_decision
  </fixed_decisions>

<review_scope>
API 명세 v0를 다음 관점으로 검토하라.

1. RESTful URI 규칙 위반
2. HTTP Method 부적합
3. 자원 이름이 동사형인 문제
4. trailing slash 포함 여부
5. snake_case URI 사용 여부
6. 권한 정의 누락
7. 접근 제어 조건 누락
8. 사용자/조언가/관리자 역할 충돌
9. Request 필드 과다 수집
10. 개인정보 최소 수집 원칙 위반
11. Response 필드 과다 노출
12. 상태값 정의와 API 흐름 불일치
13. 상태 전이 조건 누락
14. 알림 생성 조건과 Type 불일치
15. 조언 APPROVED 공개 규칙 위반
16. MVP 범위 초과
17. 중복 API
18. 하나의 API가 너무 많은 책임을 갖는 문제
19. Django/DRF 구현 시 과도하게 복잡해질 가능성
20. N+1 쿼리 또는 과도한 nested response 위험
21. status code 부정합
22. 에러 응답 구조 누락
23. 페이지네이션 필요 여부
24. 정렬/필터 조건 필요 여부
25. Admin에서 처리할 기능과 Public API로 제공할 기능의 경계
    </review_scope>

<required_output_step_1>
먼저 전체 API 명세를 읽고 다음 요약을 제공하라.

## 1. 현재 API 명세 v0 요약

* 총 API 개수
* 역할별 API 개수
* 주요 도메인별 API 개수
* MVP 필수 API
* MVP 후순위 API
* 설계상 가장 위험한 영역 Top 5

아직 수정하지 마라.
</required_output_step_1>

<required_output_step_2>
다음 형식의 Issue Ledger를 작성하라.

| ID | 심각도 | API | 문제 유형 | 현재 설계 | 왜 문제인가 | 프로젝트와 왜 안 맞는가 | 일반적으로 왜 좋지 않은가 | 권장 수정안 | Owner 결정 필요 여부 |
| -- | --- | --- | ----- | ----- | ------ | ------------- | -------------- | ------ | -------------- |

심각도 기준:

* Critical: 보안, 권한, 개인정보, 핵심 도메인 흐름 붕괴
* High: REST 설계 오류, 상태 전이 오류, MVP 구현에 큰 장애
* Medium: 일관성 저하, 응답 구조 문제, 구현 복잡도 증가
* Low: 네이밍, 문서 표현, 사소한 개선

문제 유형 예시:

* URI_RULE
* METHOD
* AUTHORIZATION
* ACCESS_CONTROL
* PRIVACY
* RESPONSE_SHAPE
* REQUEST_FIELD
* STATUS_TRANSITION
* NOTIFICATION
* MVP_SCOPE
* DUPLICATE
* IMPLEMENTATION_RISK
  </required_output_step_2>

<required_output_step_3>
Owner에게 물어야 할 확정 질문만 분리하라.

질문 형식:

## Owner Decision Questions

### Q1. 질문 제목

* 현재 충돌:
* 선택지 A:
* 선택지 B:
* 추천:
* 추천 이유:
* 답변이 필요한 이유:

주의:

* 질문은 꼭 필요한 것만 한다.
* 이미 확정된 사항은 다시 묻지 않는다.
* 단순 문서 표현 개선은 질문하지 말고 직접 수정안에 반영한다.
  </required_output_step_3>

<required_output_step_4>
Owner가 답변한 뒤에만 docs/api.md v1 초안을 작성하라.

docs/api.md v1 형식:

# API Specification v1

## 1. Common Rules

* Base URL
* Auth Header
* Common Response Shape
* Common Error Shape
* Pagination
* DateTime Format
* Status Code Policy
* URI Convention

## 2. Roles

* Anonymous
* User
* Advisor
* Admin

## 3. API Summary Table

| Domain | Method | Endpoint | Permission | Description | MVP |
| ------ | ------ | -------- | ---------- | ----------- | --- |

## 4. Detailed API Specification

각 API마다 다음 템플릿을 사용한다.

### API 이름

| 항목             | 내용 |
| -------------- | -- |
| Method         |    |
| Endpoint       |    |
| Permission     |    |
| Description    |    |
| Request 주요 필드  |    |
| Response 주요 필드 |    |
| Status         |    |
| 접근 제어 조건       |    |
| Side Effect    |    |
| MVP 여부         |    |

## 5. Deferred APIs

후순위 API와 제외 이유를 정리한다.

## 6. Open Questions

아직 확정되지 않은 질문만 남긴다.
</required_output_step_4>

<required_output_step_5>
docs/api.md v1 작성 후 docs/model.md 초안을 작성하기 위한 준비 요약을 제공하라.

다음 항목을 정리한다.

* 예상 Django app 목록
* 예상 Model 목록
* 주요 FK 관계
* 상태값 enum 후보
* 인덱스 후보
* unique constraint 후보
* soft delete 필요 여부
* transaction.atomic이 필요한 후보
* Admin에서 처리할 기능
* Public API로 제공할 기능
  </required_output_step_5>

<notion_editing_rule>
Notion 원본을 직접 수정하기 전에 반드시 다음을 수행하라.

1. 수정 대상 API 목록 제시
2. 추가할 API 목록 제시
3. 삭제 또는 병합할 API 목록 제시
4. 필드 변경 목록 제시
5. 상태값 변경 목록 제시
6. Owner 승인 요청

Owner가 승인하기 전에는 Notion DB 원본을 직접 수정하지 마라.

Notion을 직접 수정할 수 없는 환경이라면, Notion에 복사해 넣을 수 있는 수정 테이블과 markdown 패치를 생성하라.
</notion_editing_rule>

<quality_bar>
출력 품질 기준:

* “이상합니다” 수준의 추상적 피드백 금지
* 왜 문제인지 설명할 것
* 왜 이 프로젝트에 정합하지 않은지 설명할 것
* 왜 일반적인 API 설계 관점에서도 좋지 않은지 설명할 것
* 수정안은 실제 적용 가능한 수준으로 제시할 것
* MVP 범위와 후순위 범위를 명확히 분리할 것
* Owner가 최종 결정을 내릴 수 있게 선택지를 제시할 것
* 과도한 엔터프라이즈 설계로 비약하지 말 것
  </quality_bar>

<first_instruction>
지금부터 다음 순서로 작업하라.

1. 파일 목록을 확인한다.
2. CLAUDE.md와 docs 문서를 읽는다.
3. Notion API export markdown 파일을 찾는다.
4. API 명세 v0를 완전히 읽는다.
5. 아직 수정하지 말고 v0 요약과 Issue Ledger를 먼저 작성한다.
6. Owner Decision Questions를 제시한다.
   </first_instruction>
