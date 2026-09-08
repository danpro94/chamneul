# GLOSSARY — 도메인 용어

> 한국어·영어 혼용 프로젝트다. 이 문서는 AI가 SPEC 12개를 가로지르며 **동의어를 지어내는 것**을 막는다.
> 상태값의 정본은 `CLAUDE.md` §6, 필드 정의의 정본은 `docs/model.md`다.

---

## 1. 핵심 명사

| 한국어 | 영어 / 모델 | 뜻 |
| --- | --- | --- |
| 고민 | `Concern` | 사용자가 제출한 인생 의사결정 사안. 공개 게시물이 **아니다** — 연결된 조언가와 검토 담당자만 본다 |
| 조언 | `Advice` | 조언가가 특정 고민에 대해 작성한 응답. **승인된 것만** 사용자에게 보인다 |
| 조언가 | `Advisor` | `USER` + ADVISOR 역할 보유자. 별도 계정이 아니라 역할이다 |
| 조언가 신청 | `AdvisorApplication` | 사용자가 조언가가 되겠다고 낸 신청서. 관리자가 심사한다 |
| 배정 | `Assignment` | 관리자가 고민에 조언가를 연결한 것. 고민당 여러 건 가능 |
| 피드백 | `Feedback` | 고민 작성자가 받은 조언 1건에 남기는 평가. **조언당 1회, 수정·삭제 불가** |
| 알림 | `Notification` | 시스템이 사용자에게 보내는 통지. 5종 고정 |
| 역할 부여 감사 | `RoleGrant` | 역할 부여·회수 이력. **append-only** — Admin에서도 수정·삭제 불가 |
| 조언 이력 | `AdviceHistory` | 조언 본문의 버전별 스냅샷. append-only, Phase 2에 공개 API 없음 |

## 2. 역할 (Role)

| 값 | 의미 |
| --- | --- |
| `USER` | 기본 역할. **`UserRole` row로 저장하지 않는다** — 암묵적 기본값이다 |
| `ADVISOR` | 조언 작성 권한. `UserRole` row로 저장 |
| `ADMIN` | 관리자. `UserRole` row로 저장 |

**`role` 보유와 `active_role`은 다르다.** 이 구분이 401/403 판정의 핵심이다.

* `roles[]` — 사용자가 **보유한** 역할 집합
* `active_role` — 지금 **전환해 둔** 상태. `USER` 또는 `ADVISOR`만 가능하다
* `ADMIN`은 활성 전환을 거치지 않고 권한 검사 시 항상 적용된다

> ADVISOR 역할을 보유했더라도 `active_role`이 `USER`이면 조언가 전용 리소스는 **403**이다(401이 아니다 — 인증은 성공했다).

## 3. Lane

| 값 | 의미 |
| --- | --- |
| `expert` | 전문가 계열 |
| `senior` | 경험 있는 연장자 계열 |
| `no_preference` | 고민 작성자가 선호를 두지 않음 |

`intended_lane`은 신청자가 **스스로 밝힌 의향**이지 자격 등급이 **아니다.**

* 공개 응답에 **절대 포함하지 않는다.** 다른 사용자에게 표시하지 않는다. 권한 키로 쓰지 않는다.
* 관리자 심사 도구와 내부 매칭 텔레메트리에서만 보인다. 최종 lane 판정은 관리자가 한다.

## 4. 고민 분류 (taxonomy v0) — 11종 고정

`common/taxonomy.py`의 `ConcernType`. **임의 추가 금지** (CLAUDE.md §6.5).

| 키 | 라벨 |
| --- | --- |
| `career_transition` | 경력 전환 |
| `job_change` | 직종 전환 |
| `burnout` | 번아웃 |
| `startup_failure` | 사업 실패 |
| `leadership` | 리더십 |
| `relationship` | 관계 |
| `life_direction` | 인생 방향성(설계) |
| `major_life_decision` | 인생의 중요한 의사결정 |
| `education_choice` | 학업 선택 |
| `relocation` | 이사 |
| `finance_major_decision` | 중요한 재무 의사결정 |

`common/`에 두는 이유: `advisors`가 `concerns`를 import하지 않게 하려는 것이다.

## 5. 상태값

### Concern — 4종

```
SUBMITTED ──배정──▶ ASSIGNED ──APPROVED 조언 1건 이상──▶ ANSWERED ──사용자 종료──▶ CLOSED
    ▲                    │
    └──배정 전건 해제─────┘
```

**삭제는 상태가 아니다.** 사용자의 "내 고민 삭제"는 `deleted_at = now()` 소프트 삭제다.

### Advice — 5종

`PENDING` → `REVIEWING` → `APPROVED` / `REJECTED`, 그리고 `DELETED`.
**사용자는 `APPROVED`만 볼 수 있다.**

### AdvisorApplication — 5종

`PENDING` → `REVIEWING` → `APPROVED` / `REJECTED`, 그리고 `WITHDRAWN`.
`WITHDRAWN`은 **모델에만 존재**한다 — 철회 API는 Phase 3다.

### Feedback — 3종

`SUBMITTED` → `REVIEWED` → `ARCHIVED`. 단방향이다.

### Notification 타입 — 5종 고정

| 타입 | 수신자 |
| --- | --- |
| `ADVICE_APPROVED` | 고민 작성자 |
| `ADVICE_REJECTED` | 조언가 |
| `ADVISOR_APPLICATION_APPROVED` | 신청자 |
| `ADVISOR_APPLICATION_REJECTED` | 신청자 |
| `ASSIGNMENT_CREATED` | 조언가 |

## 6. 규약

| 용어 | 뜻 |
| --- | --- |
| **소프트 삭제** | `deleted_at` DateTime(null 허용). 활성 조건은 `deleted_at IS NULL`. 프로젝트 전역 규약이며 `is_deleted` boolean을 쓰지 않는다 |
| **부분 유니크 인덱스** | `UniqueConstraint(..., condition=Q(...))`. 소프트 삭제 모델의 유니크 제약은 **반드시** 부분 인덱스여야 한다. 평범한 `unique=True`는 코드 리뷰에서 반려된다 |
| **`with_deleted()`** | 소프트 삭제 포함 조회. 기본 매니저 `Concern.objects`는 제외한다 |
| **`version`** | 조언의 감사용 정수. 생성 시 1, 조언가 수정마다 +1. `PENDING`/`REVIEWING`에서만 수정 가능 |
| **`display_alias`** | 익명 고민에서 사용자를 가리키는 별칭 |
| **`is_anonymous`** | 고민의 익명 여부. **기본 True** |

## 7. 프로세스 용어

| 용어 | 뜻 |
| --- | --- |
| `[소유]` | Owner가 직접 손코딩한다. AI는 코치·리뷰어·출제자 역할만 |
| `[위임]` | AI가 생성하고 Owner가 검수한다 |
| `[읽기]` | 작성은 안 해도 흐름을 설명할 수 있어야 한다 |
| **SPEC** | 하나의 작업 단위. 요구사항 → 완료조건 → 구현 → 테스트 → 리뷰가 한 루프에 닫히는 크기 |
| **AC** | Acceptance Criteria. `acceptance.md`의 체크박스. 이것이 커버리지 리포트다 |
| **학습 부채** | 퀴즈나 리뷰에서 설명하지 못한 항목. merge는 막지 않되 원장에 남긴다 |
| **explain-first** | AI가 리뷰 노트를 쓰기 **전에** Owner가 기억만으로 5줄 요약을 먼저 쓰는 규칙 |
| **백지 재현 (WB)** | 문서·과거 코드를 닫고 빈 폴더에서 재현하는 훈련 |

## 8. 상태 코드 사전

`docs/api.md` §1.8이 정본이다. 학습 부채 ④의 대상이므로 여기 병기한다.

| 코드 | 언제 |
| --- | --- |
| 400 | 입력 **형식** 오류 |
| 401 | 인증이 **없거나 실패** — 로그인하지 않았다 |
| 403 | 인증은 됐으나 **권한 없음** — 로그인했지만 역할이 맞지 않는다 |
| 404 | 자원 없음. 소프트 삭제된 자원 포함 |
| 409 | **비즈니스 규칙 위반** — 상태 전이 불가, 중복 |
| 412 | 버전 불일치 (`expected_version`) |
| 422 | 형식은 맞으나 **값이 부적합** |
