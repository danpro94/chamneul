# TEST_CRITERIA — 완료 판정 기준

> 변경이 "완료됐다"고 판단하는 기준을 정의한다.
> **AI의 "구현이 완료되었습니다"는 증거가 아니다.** 증거는 통과한 테스트, 스모크 통과, 실측한 응답이다.
> 근거: `CLAUDE.md` §12 · Owner 결정 G5 · ADR-005 §4.3

---

## 1. 도구 결정과 근거

| 항목 | 선택 | 근거 |
| --- | --- | --- |
| 테스트 러너 | **Django 기본 test runner** (`manage.py test`) | Owner 결정 G5, `pyproject.toml:17` 주석, CLAUDE.md §12 |
| API 테스트 | **DRF `APITestCase`** | DRF가 이미 설치되어 있다. 신규 패키지 아님 |
| pytest | **미도입** | G5. 운영에 불필요한 개발자 전용 패키지를 늘리지 않는다 |
| factory_boy | **미도입** | 같은 이유. `tests/factories.py`에 평범한 함수로 작성한다 |
| coverage 도구 | **미도입** | 같은 이유. 대체 지표는 §8 AC 커버리지 |
| DB | **PostgreSQL 전용** | CLAUDE.md §4. SQLite 인메모리 폴백 금지 |

> 새 테스트 패키지를 추가하려면 **CLAUDE.md §16 승인 게이트**를 통과해야 한다. AI가 임의로 `uv add` 하지 않는다.

## 2. 테스트 원칙

```
요구사항 (spec.md)
  → 수용 기준 (acceptance.md)
  → 실패하는 테스트를 먼저 작성
  → 실패를 눈으로 확인          ← 이 단계를 건너뛰지 않는다
  → 구현
  → 통과 확인
  → 회귀 테스트로 남긴다
```

실패를 확인하지 않은 테스트는 신뢰할 수 없다. 항상 통과하는 테스트(assert가 잘못됐거나 대상이 실행되지 않는 테스트)를 구별할 방법이 없기 때문이다.

## 3. 계층 정의

| 계층 | 위치 | 대상 | DB |
| --- | --- | --- | --- |
| **unit** | `tests/unit/` | 순수 로직 — taxonomy 불변, uuid7 형식, 상태 전이 규칙, 검증 함수, 경계값 | 불필요 |
| **integration** | `tests/integration/` | 엔드포인트 계약, 권한, 소유권, 부수효과, 매니저 동작 | 필요 |
| e2e | — | **Phase 2에 만들지 않는다.** 프론트도 브라우저도 없다 | — |

`tests/`를 앱별이 아니라 최상위에 두는 이유: API 테스트는 본질적으로 앱을 가로지른다(고민 테스트 하나에 User + UserRole + Concern이 필요하다). 그리고 테스트는 Django 앱이 아니라 **`acceptance.md`의 수용 기준에 매핑**된다.

## 4. 무엇을 테스트할지는 Owner가 지정한다

`docs/learning/02` §2.2: 테스트 **코드**의 대량 작성은 `[위임]`이지만, **무엇을 테스트할지**는 Owner가 정한다.

실무적으로: 케이스 목록은 `specs/SPEC-NNN/acceptance.md`에서 나온다. AI는 그 목록을 코드로 옮긴다. AI가 케이스를 발명하는 것은 허용되지만, `acceptance.md`에 없는 케이스는 **추가 제안**이지 완료 조건이 아니다.

## 5. 엔드포인트당 필수 케이스 매트릭스

이 문서의 핵심이다. 모든 `/api/v1/` 엔드포인트는 해당하는 축을 전부 덮어야 한다.

| 축 | 필수 케이스 | 기대 | 근거 |
| --- | --- | --- | --- |
| happy | 정상 요청 | 200 / 201 / 204 + **응답 필드가 명세와 정확히 일치** (초과 필드 노출 금지) | api.md §4, CLAUDE.md §8 |
| 인증 | 비로그인 접근 | **401** | api.md §1.8 · **부채 ④** |
| 인가 | 로그인했으나 역할 불일치 | **403** | api.md §1.8 · **부채 ④** |
| 활성 역할 | ADVISOR 역할 보유 + `active_role=USER` → 조언가 리소스 | **403** (401 아님) | GLOSSARY §2 |
| 소유권 | 타인 자원 접근 | **404 또는 403** — 엔드포인트별 api.md §4 "접근 제어 조건"이 정본 | api.md §4 |
| 검증 | 필수 필드 누락 / enum 위반 / 길이 초과 | **400** (형식) 또는 **422** (값) | api.md §1.5 |
| 부재 | 없는 id | **404** | — |
| 소프트 삭제 | 삭제된 고민 조회 | **404** — 기본 매니저에서 사라져야 한다 | CLAUDE.md §6.6 |
| 충돌 | 부분 유니크 위반 / 상태 전이 불가 | **409** | CLAUDE.md §6.1·6.2 · **부채 ④** |
| 버전 | `expected_version` 불일치 | **412** | UX §8-4 (SPEC-008에서 확정) |
| 페이지네이션 | 목록 응답 | `page_info` 포함, `size` 기본 20 / 최대 100 | api.md §1.6 |
| 에러 형태 | 모든 4xx/5xx | `{"error": {"code", "message", "details"}}`, `code`는 SCREAMING_SNAKE_CASE | api.md §1.5 |

### 응답 필드 검증은 화이트리스트로

`assertIn`만 쓰면 **초과 노출을 잡지 못한다.** CLAUDE.md §8은 "ModelSerializer로 모든 필드를 무심코 반환하지 말 것"을 요구한다. 따라서 키 집합을 통째로 비교한다.

```python
self.assertEqual(set(res.json()), {"user_id", "email", "nickname", "active_role", "created_at"})
```

민감 필드는 명시적으로 부재를 확인한다: `password`, `is_staff`, `is_superuser`, **`intended_lane`**(GLOSSARY §3 — 절대 공개 금지).

## 6. 부수효과 검증 규칙

**"상태가 바뀌었다"만으로 통과시키지 않는다.** 승인·거절·배정 API는 부수효과가 본체다.

| API | 상태 변경 외에 반드시 assert할 것 |
| --- | --- |
| 조언가 신청 승인 | `UserRole` row 생성 + `RoleGrant` 감사 row + `Notification`(APPROVED) |
| 조언 승인 | `Notification`(고민 작성자 수신) + 고민 상태 `ASSIGNED → ANSWERED` |
| 조언 거절 | `Notification`(조언가 수신) |
| 배정 생성 | `Notification`(조언가 수신) + 고민 `SUBMITTED → ASSIGNED` |
| 배정 전건 해제 | 고민 `ASSIGNED → SUBMITTED` |
| 조언 수정 | `version` +1 + `AdviceHistory` 스냅샷 append |

### 원자성 (부채 ⑤ 해소 조건)

부수효과 중 하나를 실패시켰을 때 **부분 커밋이 남지 않음**을 assert한다. 이것이 없으면 `transaction.atomic`이 실제로 동작하는지 증명되지 않는다.

```python
with self.assertRaises(SomeError), transaction.atomic():
    service.approve(application)
self.assertEqual(UserRole.objects.count(), 0)    # 아무것도 남지 않았다
self.assertEqual(RoleGrant.objects.count(), 0)
```

## 7. 실행

```bash
# 정본 — 컨테이너 안에서
docker compose exec app python manage.py test --settings=config.settings.test -v 2

# 반복 실행 (테스트 DB 재생성 생략)
docker compose exec app python manage.py test --settings=config.settings.test --keepdb -v 2

# 한 모듈만
docker compose exec app python manage.py test tests.integration.test_auth \
  --settings=config.settings.test --keepdb -v 2

# 호스트에서 (.env가 DB_HOST=localhost, DB_PORT=15432 여야 한다)
uv run python manage.py test --settings=config.settings.test -v 2
```

`--settings=config.settings.test`를 **매번 붙여야 한다.** `manage.py`의 기본값은 `config.settings.local`이고 `app` 서비스도 local을 명시적으로 설정한다. `.claude/commands/verify.md`와 `.claude/rules/20-testing.md`에 박아 두어 잊지 않게 한다.

테스트 러너는 `test_chamneul` DB를 만들기 위해 `CREATEDB` 권한이 필요하다. `POSTGRES_USER=chamneul`이 `postgres:16` 인스턴스의 슈퍼유저이므로 별도 grant 없이 동작한다.

### CSRF 주의 — 조용한 오탐 지점

`APIClient()`의 기본값은 `enforce_csrf_checks=False`다. 즉 **평범한 테스트는 CSRF를 검사하지 않는다.** CSRF 계약을 검증하려면 명시적으로 켜야 한다.

```python
csrf_client = APIClient(enforce_csrf_checks=True)
```

이걸 모르면 "CSRF 테스트가 통과한다"는 잘못된 확신을 갖게 된다.

## 8. 커버리지 정의 — AC 커버리지

라인 커버리지 도구를 도입하지 않는다(§1 패키지 게이트). 대신:

> **`specs/SPEC-NNN/acceptance.md`의 모든 체크박스가 최소 1개 테스트에 연결되어야 한다.**

`acceptance.md`가 곧 커버리지 리포트다. 각 AC 항목 옆에 검증하는 테스트 경로를 적는다.

```markdown
- [x] AC-003 비로그인 `GET /api/v1/users/me` → 401
      `tests/integration/test_auth.py::AuthContractTests::test_me_anonymous_401`
```

## 9. Flaky 테스트

1. 원인을 기록한다
2. `LEARNING_DEBT.md` 또는 SPEC의 Open Questions에 등재한다
3. **임의로 skip하지 않는다**
4. 수정하거나 격리한다

"flake"는 원인이 아니다. 두 번째 실패는 진짜 실패로 취급한다.

## 10. AI Rules

* **실패하는 테스트를 삭제하거나 skip하지 않는다.** 통과시키려고 assert를 약화하지 않는다.
* **구현에 맞추려고 수용 기준을 바꾸지 않는다.** 수용 기준이 틀렸다고 판단되면 코드를 고치기 전에 그 사실을 말한다.
* 기존 테스트를 수정할 때는 **이유를 명시**한다.
* **통과 여부는 실제 실행 결과로만 증명한다.** 실행하지 않은 명령은 "권장 명령"으로 표기하고 완료로 위장하지 않는다 (CLAUDE.md §12).
* 실측 출력을 `specs/SPEC-NNN/evidence/`에 남긴다.

## 11. Definition of Test Complete

SPEC은 다음이 **전부** 참일 때만 닫힌다.

- [ ] `acceptance.md`의 모든 체크박스가 체크됨 + 각각 테스트 경로가 적힘
- [ ] `manage.py test --settings=config.settings.test` 전체 통과
- [ ] `manage.py check` 0 issues
- [ ] `makemigrations --check --dry-run` No changes
- [ ] `ruff check .` 통과
- [ ] §5 매트릭스의 해당 축이 전부 덮임
- [ ] 부수효과가 있으면 §6의 원자성 테스트 포함
- [ ] 회귀 없음 — 기존 테스트가 여전히 통과
- [ ] 실측 증거가 `evidence/`에 있음

## 12. 아직 하지 않는 것

| 항목 | 시점 |
| --- | --- |
| 성능 테스트 (p95, 처리량) | Phase 3 — 부하를 줄 트래픽이 없다 |
| 보안 스캔 (SAST, 의존성, IaC) | Phase 3 CI/CD 진입 시 |
| 인프라 테스트 (네트워크, IAM, LB, TLS) | Phase 3 |
| E2E | 프론트가 생길 때 |
| 스모크 테스트 문서 | M5 (`docs/smoke-test.md`) |

**테스트 데이터에 실제 개인정보를 쓰지 않는다.** `tests/factories.py`가 `user{n}@example.com` 형태로 생성한다.
