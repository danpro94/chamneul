# SPEC-001 — Acceptance Criteria

> **이 파일이 커버리지 리포트다** (`docs/testing/TEST_CRITERIA.md` §8).
> 체크할 때 검증하는 테스트 경로를 함께 적는다. **경로 없는 체크는 체크가 아니다.**

## 하네스

- [ ] **AC-001** `tests/` 하네스가 PostgreSQL 테스트 DB에 붙어 실행되고 최소 1개 통과
      `tests/integration/test_healthz.py`

## 인증 계약 (학습 부채 ④)

- [ ] **AC-002** 비로그인 `GET /api/v1/users/me` → **401** (404 아님)
- [ ] **AC-011** ADVISOR 보유 + `active_role=USER` → 권한 클래스가 **403** 판정
      `tests/unit/test_permissions.py`

## 가입

- [ ] **AC-003** 201 + `Set-Cookie: sessionid` + 응답 키 집합이 spec.md §5와 정확히 일치
- [ ] **AC-004** 이메일 중복 → 409, `User.objects.count()` 불변
- [ ] **AC-005** 닉네임 중복 → 409
- [ ] **AC-012** 중간 실패 주입 시 `User` row 미잔존 (부채 ⑤)
      `tests/integration/test_signup_atomicity.py`

## 로그인 / 로그아웃

- [ ] **AC-006** 올바른 자격 증명 → 200 + 세션 발급
- [ ] **AC-007** 틀린 비밀번호 → 401 **AND** 존재하지 않는 이메일 → **동일한 401·동일 메시지**
- [ ] **AC-008** `is_active=False` → 403
- [ ] **AC-009** 로그아웃 → 200 + **서버 세션 레코드 삭제 확인** + 같은 쿠키 재사용 시 401

## 응답 노출

- [ ] **AC-010** `users/me` 응답에 `password`·`is_staff`·`is_superuser` 부재 (키 집합 전체 비교)

## 횡단

- [ ] **AC-013** CSRF 토큰 없이 POST → 403 (`APIClient(enforce_csrf_checks=True)`)
- [ ] **AC-014** 모든 에러 응답이 api.md §1.5 봉투 형식

---

## 검증 명령

```bash
docker compose exec app python manage.py test --settings=config.settings.test --keepdb -v 2
uv run ruff check .
docker compose exec app python manage.py check
docker compose exec app python manage.py makemigrations --check --dry-run   # No changes 유지
```

실측 출력은 `evidence/`에 저장한다. **AI가 "통과했습니다"라고 말한 것은 증거가 아니다.**

## 진행

**0 / 14**
