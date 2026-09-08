# 테스트 규칙 (1화면 요약)

> 정본: `docs/testing/TEST_CRITERIA.md`. 여기는 매 세션 기억해야 할 것만.

## 실행

```bash
docker compose exec app python manage.py test --settings=config.settings.test -v 2
docker compose exec app python manage.py test --settings=config.settings.test --keepdb -v 2   # 반복
```

**`--settings=config.settings.test`를 매번 붙인다.** 기본값은 `config.settings.local`이라 빠뜨리면 개발 DB로 돈다.

## 도구

Django 기본 test runner + DRF `APITestCase`. **끝.**
pytest · factory_boy · coverage 전부 미도입 (Owner 결정 G5, §16 패키지 게이트). `uv add`를 실행하지 않는다.

## 순서

```
acceptance.md 체크박스 → 실패하는 테스트 → 실패를 눈으로 확인 → 구현 → 통과
```

**실패 확인을 건너뛰지 않는다.** 항상 통과하는 테스트(assert가 잘못됐거나 대상이 안 도는 테스트)를 구별할 방법이 없어진다.

## 엔드포인트마다 반드시

| 축 | 기대 |
| --- | --- |
| 정상 | 200/201/204 + **응답 키 집합을 통째로 비교** (초과 노출 금지) |
| 비로그인 | **401** |
| 역할 불일치 | **403** |
| `active_role` 불일치 (ADVISOR 보유하나 USER로 전환됨) | **403** |
| 타인 자원 | 404 또는 403 — api.md §4 "접근 제어 조건"이 정본 |
| 잘못된 입력 | 400(형식) / 422(값) |
| 소프트 삭제된 자원 | **404** |
| 중복·상태 전이 불가 | **409** |

`assertIn`으로 끝내지 않는다. `self.assertEqual(set(res.json()), {...})`로 초과 필드를 잡는다.
민감 필드는 부재를 명시적으로 assert: `password`, `is_staff`, `is_superuser`, **`intended_lane`**.

## 부수효과

승인·거절·배정 API는 상태 변경만 확인하고 끝내지 않는다. `Notification` row, `RoleGrant` 감사 row, `AdviceHistory` append를 각각 assert한다.
**원자성**: 중간 실패를 주입했을 때 부분 커밋이 남지 않음을 assert한다.

## CSRF 함정

`APIClient()`는 기본이 `enforce_csrf_checks=False`다. CSRF를 검증하려면 명시적으로 켠다.

```python
csrf_client = APIClient(enforce_csrf_checks=True)
```

모르면 "CSRF 테스트가 통과한다"는 잘못된 확신을 갖게 된다.

## 금지

* 실패하는 테스트를 삭제하거나 skip
* 통과시키려고 assert를 약화
* 구현에 맞추려고 `acceptance.md`를 수정
* 실행하지 않은 명령을 통과로 보고 — "권장 명령"으로 표기한다
