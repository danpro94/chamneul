# ADR-003. 관리자(ADMIN) 역할 부여 및 해제

## Status

Accepted

## Date

2026-06-22

## Context

회원가입은 USER 역할만 생성한다. ADMIN 권한이 필요한 API들(조언가 신청 심사, 고민 배정, 조언 승인 등)을 사용하려면 누군가가 ADMIN 권한을 부여받아야 한다. Notion v0 명세에는 이 흐름이 정의되어 있지 않았다.

본 ADR은 다음 두 가지를 정의한다.

1. 최초 ADMIN의 부트스트랩 방식.
2. 이후 ADMIN 추가 부여 / 해제 API.

---

## Decision

### 1. 최초 ADMIN 부트스트랩

`python manage.py createsuperuser` 명령으로 생성된 Django superuser 가 ADMIN 역할을 가진 첫 사용자가 된다.

* Superuser 플래그(`is_superuser=True`)는 그 자체로 ADMIN 권한을 의미한다.
* 본 결정은 트래픽 발생 시점에 자동화로 대체될 수 있는 임시 부트스트랩이며, 그 자동화는 별도 ADR로 분리한다.

### 2. ADMIN 부여 / 해제 API

| Method | Endpoint | 권한 | 설명 |
| --- | --- | --- | --- |
| POST | `/api/v1/admin/users/{user-id}/roles` | ADMIN | 대상 사용자에게 역할을 부여한다. Body: `{ "role": "ADMIN" }` |
| DELETE | `/api/v1/admin/users/{user-id}/roles/{role}` | ADMIN | 대상 사용자에게서 해당 역할을 회수한다. |

* 부여 가능한 역할: `ADMIN`, `ADVISOR`.
  * `ADVISOR`는 정상 경로(조언가 신청 → 관리자 승인)로 부여되는 것이 원칙. 관리자가 직접 부여하는 경우는 예외(이벤트성, 초청 advisor) 한정.
* 회수 시 `USER` 역할은 회수 대상이 아니다 (사용자 자체를 비활성화하려면 별도 계정 정지 흐름을 사용한다 — Phase 3+).
* 자기 자신의 ADMIN 역할은 회수할 수 없다. (`granted_user_id == requesting_admin_id` 이면서 `role == ADMIN` → 409).
* 마지막 남은 ADMIN의 ADMIN 역할은 회수할 수 없다 (시스템 잠금 방지).

### 3. 감사 추적 (audit)

부여/회수마다 다음을 별도 `RoleGrant` 테이블에 기록한다.

| 필드 | 설명 |
| --- | --- |
| id | PK |
| user_id | 대상 사용자 |
| role | `ADMIN` 또는 `ADVISOR` |
| action | `GRANT` 또는 `REVOKE` |
| acted_by | 수행한 관리자 user_id |
| acted_at | 시각 |
| reason | 선택 텍스트(권장) |

이 테이블은 Phase 2에서는 Django Admin으로만 열람하며, 공개 API로 노출하지 않는다.

### 4. 알림

본 ADR의 두 API는 알림을 발송하지 않는다 (`ADMIN_GRANTED` / `ADMIN_REVOKED` 타입은 추가하지 않음). 추후 필요성이 확인되면 CLAUDE.md §6.4 알림 타입에 추가 결정한다.

---

## Rationale (Why)

* **계층적 분리**: `/admin/users/{user-id}/roles` 패턴은 사용자 자원의 하위 컬렉션 의미가 명확하다.
* **감사 추적**: REVOKE를 별도 메서드(DELETE)로 분리해 의도가 분명히 드러난다. GRANT/REVOKE 모두 별도 audit 레코드가 남는다.
* **자기 잠금 방지**: 마지막 ADMIN/자기 자신의 권한 회수 방지 룰은 운영 사고의 가장 흔한 원인 중 하나를 차단한다.
* **최초 부트스트랩 단순화**: createsuperuser는 Django 표준 흐름이며 추가 코드 부담이 없다. 자동화 ADR로 대체 가능한 단계.

## Trade-offs

* createsuperuser는 사람이 로컬에서 한 번 실행해야 한다 — CI/CD 자동화 단계에서 제약. 운영 진입 시점에 재검토.
* 역할이 ADMIN/ADVISOR 두 종이므로 RBAC라 부르기엔 단순함 — 의도된 단순성.

## Consequences

* `accounts` 앱에 `UserRole` (Many-to-Many 관계 모델) 또는 `User` 모델 위의 `roles` 필드가 필요하다. 구현은 `docs/model.md`에서 확정.
* `RoleGrant` 감사 테이블 필요.
* DRF Custom Permission `IsAdmin` 이 모든 `/api/v1/admin/*` 엔드포인트에 적용된다.

## Validation

* `python manage.py createsuperuser` → 결과 사용자가 ADMIN 권한으로 `/api/v1/admin/concerns` 호출 가능.
* `POST /api/v1/admin/users/{user-id}/roles` body `{"role":"ADVISOR"}` → 대상이 ADVISOR 역할로 즉시 사용 가능.
* `DELETE /api/v1/admin/users/{user-id}/roles/ADMIN` 호출자 본인 → 409.
* 마지막 ADMIN 회수 시도 → 409.

## Review Triggers

* ADMIN 자동 부여 자동화(이메일 도메인 기반 등) 요구 시 → 별도 ADR.
* 역할 종류가 ADMIN/ADVISOR 외로 늘어날 때.
* 사용자 계정 정지/탈퇴 흐름 도입 시.
