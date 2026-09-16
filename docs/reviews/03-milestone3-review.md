# 리뷰 노트 03 — M3 (도메인 모델 7종) *(2026-09-17 소급 작성)*

> **소급 기록임을 밝힌다.** M3는 2026-07-08에 끝났으나 리뷰 노트가 작성되지 않았고(STATUS.md §7 문서 부채 #2), SPEC-004/TASK-003에서 청산한다.
> 아래는 **코드·마이그레이션·git 이력에서 실측한 사실**과, M4를 거치며 **사후에 드러난 것**을 구분해 적었다. 당시의 판단 근거를 지어내지 않았다 — 기록에 없는 것은 "미기록"으로 표시한다.
> 계획 문서: [03-milestone3-definition.md](03-milestone3-definition.md)

## 무엇이 바뀌었나

도메인 모델 7종 + 마이그레이션 + Django Admin 등록. 엔드포인트는 하나도 없다 — M3는 **스키마를 확정하는 마일스톤**이었다.

| 앱 | 모델 |
| --- | --- |
| `accounts` | `User`(커스텀) · `UserRole` · `RoleGrant` · `GoogleIdentity` |
| `advisors` | `AdvisorApplication` |
| `concerns` | `Concern` · `Assignment` |
| `advice` | `Advice` · `AdviceHistory` · `Feedback` |
| `notifications` | `Notification` |

## 왜 이렇게 구현했나

### 1. UUIDv7을 앱 레벨에서 생성한다

전 모델의 PK가 `UUIDField(default=uuid7)`다. PostgreSQL 네이티브 `uuidv7()`(`pg_uuidv7` extension)이 아니라 `common/uuid7.py`의 파이썬 헬퍼를 쓴다.

UUIDv7은 **시간순으로 정렬된다**. 랜덤 UUID(v4)를 PK로 쓰면 인덱스가 매 삽입마다 무작위 위치에 쓰여 페이지가 흩어지는데, v7은 시간순이라 그 문제가 없다. 부수 효과로 **`ORDER BY id`가 곧 생성순**이 되며, SPEC-003에서 `-created_at, -id` 정렬의 tiebreaker로 실제로 쓰였다.

extension을 쓰지 않은 이유는 로컬 컨테이너에서 extension 설치 단계가 하나 늘기 때문이다(§1 Phase 2는 "맨바닥에서 뜨는 최소 단위"가 목표였다). 재검토 시점은 O-8로 남겼다.

### 2. 소프트 삭제를 `Concern` 하나에만 적용

CLAUDE.md §6.6이 `deleted_at` 컬럼 + 부분 유니크를 프로젝트 규약으로 못 박았지만, **실제로 적용한 모델은 `Concern` 하나다.** 다른 모델은 `status`나 `is_active`로 생명주기를 표현한다.

규약을 전 모델에 기계적으로 적용하지 않은 것이 옳았다 — 소프트 삭제는 "조회할 때마다 빼야 하는 것"을 하나 늘리는 일이고, 필요 없는 곳에 두면 비용만 남는다.

### 3. `on_delete`의 기본값은 `PROTECT`

FK 대부분이 `PROTECT`고, `CASCADE`는 2건(`Notification.recipient`, `GoogleIdentity.user`), `SET_NULL`은 1건(`Notification.actor_user`)이다.

기본을 `PROTECT`로 둔 것은 **"지우려면 왜 지워도 되는지 설명하게 만들겠다"**는 선택이다. `CASCADE`가 기본이면 사용자 한 명을 지웠을 때 무엇이 함께 사라지는지 아무도 모르는 상태가 된다.

### 4. 감사 테이블 2종

`RoleGrant`(역할 부여/회수 이력)와 `AdviceHistory`(조언 본문 스냅샷). 둘 다 append-only이며 공개 API로 노출하지 않는다.

`AdviceHistory`가 **직전 본문을 직전 버전 번호로** 저장하는 형태인 점이 중요하다. "버전 N의 내용"이 아니라 "버전 N에서 N+1로 갈 때 사라진 내용"을 남긴다.

## 핵심 파일

| 파일 | 내용 |
| --- | --- |
| [accounts/models.py](../../accounts/models.py) | 커스텀 `User`(email 로그인) + 역할 모델 3종 |
| [concerns/models.py](../../concerns/models.py), [concerns/managers.py](../../concerns/managers.py) | 소프트 삭제 매니저 |
| [advice/models.py](../../advice/models.py) | 조언 + 히스토리 + 피드백 |
| [common/uuid7.py](../../common/uuid7.py) | PK 생성기 |
| [common/taxonomy.py](../../common/taxonomy.py) | `ConcernType` 정본 — `concerns`·`advisors` 공용 |
| [docs/model.md](../model.md) | 명세 (2026-09-16 정합화됨) |

## 어떻게 테스트하나

```bash
uv run python manage.py makemigrations --check --dry-run   # No changes
uv run python manage.py migrate                             # 빈 DB에서 성공
uv run python manage.py test                                # 291개
```

부분 유니크가 실제로 `WHERE` 절로 들어갔는지 확인:

```bash
grep -rn "condition=models.Q" */migrations/*.py
```

## DevOps 설명 포인트

**마이그레이션 순서가 왜 중요한가.** `accounts.0001_initial`이 `admin.0001_initial`보다 **먼저** 와야 한다. 커스텀 User 모델을 쓰면 `django.contrib.admin`이 `settings.AUTH_USER_MODEL`을 참조하는데, 그 테이블이 없으면 마이그레이션이 깨진다. 그래서 `AUTH_USER_MODEL` 선언은 **첫 마이그레이션 전에** 끝나 있어야 한다.

맨바닥 기동에서 이 순서가 실제로 지켜지는 것을 확인했다 — [smoke-test.md](../smoke-test.md) §2-1.

## 보안 노트

* 비밀번호는 Django 기본 PBKDF2. 모델에 평문/가역 저장 필드 없음.
* `AdvisorApplication`에 `real_name`·`advisor_type` 컬럼이 **없다** — CLAUDE.md §6.1이 요구한 대로 애초에 만들지 않았다. 나중에 빼는 것보다 처음부터 없는 편이 안전하다.
* `intended_lane`은 저장하되 공개 응답에서 제외한다(관리자 심사 참고용).

## 다음 개선 *(M4 이후 시점에서 본 것)*

| # | 항목 | 상태 |
| --- | --- | --- |
| 1 | **`base_manager_name = "all_objects"`의 함의가 문서화되지 않았다** | **2026-09-16 해소** — FK 역참조가 소프트 삭제를 우회한다는 사실이 model.md §1.4에 들어갔다. M3 당시엔 소비하는 코드가 없어 드러나지 않았다 |
| 2 | **Admin 등록이 도메인 규칙을 우회할 수 있었다** | **2026-09-16 해소**(B-01~B-04) — 배정·조언 본문·피드백 상태·고민 상태가 전부 자유 편집 가능했다. 모델만 만들고 서비스 레이어가 없던 M3 시점엔 "Admin으로 운영한다"가 자연스러웠고, M4에서 서비스 레이어가 생기면서 우회 경로가 됐다 |
| 3 | `Feedback.score`에 DB 체크 제약이 없다 | 미해소 — `validators`만 있어 Admin/shell에서 범위 밖 값 저장 가능. Phase 3 후보 |
| 4 | `UserRole.clean()`이 사실상 死코드 | 2026-09-16 인지 — 실효 방어는 서비스 레이어 화이트리스트로 옮겨졌다 |

## 이 마일스톤에서 배운 것 *(사후)*

**모델만 만들고 소비하는 코드가 없으면, 설계가 맞는지 알 수 없다.** M3는 스키마를 완전하게 확정했고 실제로 M4 내내 **스키마 변경이 한 번도 필요하지 않았다**(마이그레이션은 `advisors.0002` 하나뿐 — `domain_category` enum 확정). 그 점에서 M3는 성공이다.

그러나 2026-09-16 정합성 점검에서 나온 drift 22건은 **전부 서술 계층**이었다. "무엇을 저장하는가"는 정확했고 "그것으로 무엇을 하는가"가 낡아 있었다. 같은 일이 `Notification`에서도 있었다 — 모델은 M3에 확정됐지만 읽는 코드가 SPEC-003까지 없어서, `target_url` 규약이 **옳다는 사실 자체가 미확인**이었다.

교훈: **모델 문서의 절반은 모델이 아니라 그것을 쓰는 규칙이고, 그 절반은 소비자가 생길 때마다 낡는다.**
