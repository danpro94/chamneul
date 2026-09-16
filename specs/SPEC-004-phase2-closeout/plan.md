# SPEC-004 — plan

## 1. 파일 계획

| 파일 | 작업 | TASK |
| --- | --- | --- |
| `docs/smoke-test.md` | **신규** — 실행 절차 + 실제 출력 + 갭 6건 | 001 |
| `docs/model.md` | drift 반영 | 002 |
| `docs/api.md` | §1.7 UTC 정책(결정 2), #21 404(결정 3) | 003 |
| `concerns/services.py` · `concerns/tests.py` | #21 403 → 404 | 003 |
| `README.md` | 스모크 절차 링크 + 실행 요약 | 001 |
| `README_AIUSAGE.md` | M4-1~M4-4 소급 4건 | 003 |
| `docs/reviews/03-milestone3-review.md` | **신규** | 003 |
| `docs/reviews/04-milestone4-review.md` | **신규** | 003 |
| `docs/00-project/STATUS.md` | §6 학습부채 종결, §7 문서부채 종결, Phase 2 판정 | 004 |

**마이그레이션 없음.** 모델 변경이 없다 — model.md 정합화는 **문서를 코드에 맞추는** 작업이다. 반대 방향(문서에 맞춰 모델을 고침)이 필요해 보이면 그 자체가 재검토 신호이므로 멈추고 보고한다.

## 2. TASK-001 — 스모크 테스트 설계

### 2-1. 맨바닥 기동

```bash
docker compose down -v          # named volume 삭제 (Owner 고지 후)
docker compose up -d --build
docker compose ps               # 두 서비스 healthy
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser
curl -i http://localhost:8000/healthz
```

`down -v`가 이 TASK의 핵심이다. 볼륨을 남기면 "이미 마이그레이션된 DB"를 재사용하게 되어 **지금까지와 같은 검증**이 된다.

### 2-2. 사용자 여정 (spec §3의 11단계)

**실행 방식**: `curl` 스크립트로 수행하고 실제 출력을 문서에 담는다. Playwright 스크린샷은 이미 SPEC-001~003에서 13장 확보했으므로 여기서는 **명령줄 재현 가능성**을 남기는 쪽이 가치가 크다 — Owner가 직접 복사해 실행할 수 있어야 한다(CLAUDE.md §11).

세션 쿠키와 CSRF 토큰을 쿠키 항아리(`-c jar -b jar`)로 이어붙인다. 각 단계는 **직전 응답의 id를 다음 요청에 쓰므로** 스크립트 하나로 이어진다.

### 2-3. 비정상 경로

| 시나리오 | 확인할 것 |
| --- | --- |
| `docker compose stop db` 후 `/healthz` | 응답 코드와 지연. 앱이 죽는지 버티는지 |
| 같은 상태에서 API 호출 | 500이 나가는지, 에러 봉투(§1.5) 형태를 유지하는지 |
| db 재기동 후 | 앱 재시작 없이 회복되는지(커넥션 풀 거동) |
| 마이그레이션 미적용 기동 | 어떤 오류가 나는지 — 운영 사고 시 판별 근거 |

이 4개가 CLAUDE.md §11의 "DB가 없을 때 무슨 일이 일어나는가"를 Owner가 설명할 수 있게 만드는 재료다.

### 2-4. 문서 구조 (`docs/smoke-test.md`)

```
1. 목적과 전제
2. 맨바닥 기동 절차 (복사 실행 가능)
3. 사용자 여정 11단계 — 명령 + 실제 응답
4. 비정상 경로 4종 — 명령 + 실제 응답
5. 알려진 갭 6건 (spec §4)
6. 운영 체크리스트 (로그 확인, DB 리셋, 포트 충돌)
```

## 3. TASK-002 — model.md 정합화

`data-modeler` 서브에이전트를 **읽기 전용**으로 재실행해 drift 목록을 확정한다. 기록된 4건(taxonomy 위치, `reject_reason` Null 표기, §9 `search_fields`, §10 `created_at` 문구)은 M3 시점 측정이고, 그 뒤 M4에서 모델이 움직였다:

* `Notification`·`UserRole`·`RoleGrant`의 실제 사용 패턴이 확정됨(M4-7·M4-8)
* Admin 화면 3종이 view-only로 바뀜(SPEC-003 리뷰)
* 시각 정책이 UTC로 확정됨(결정 2 — model.md §1.1 대상)

**원칙**: 문서를 코드에 맞춘다. 코드가 틀린 것으로 보이는 항목이 나오면 별도로 분리해 보고한다.

## 4. TASK-003 — 이월 2건 + 문서 부채

### 결정 2 (시각 UTC)

api.md §1.7과 model.md §1.1의 "응답은 KST(`+09:00`)로 직렬화"를 교체한다. 예시 문자열(`"2026-06-22T14:06:00+09:00"`)도 UTC 표기로 고친다 — 예시가 낡으면 규칙보다 예시를 믿는 사람이 생긴다.

`config/settings/base.py`의 `TIME_ZONE = "UTC"`는 **건드리지 않는다.** 코드가 옳고 문서가 틀렸다.

### 결정 3 (#21 403 → 404)

```
concerns/services.py  get_assigned_concern()
  현재: 배정 없으면 PermissionDenied (403)
  변경: 쿼리셋을 배정으로 좁혀 get_object_or_404 (404)
```

알림 3종과 같은 형태 — **접근 제어를 쿼리셋 스코프로** 옮긴다. 기존 테스트의 403 단언을 404로 고치고, 커밋 메시지에 "결정이 바뀌어서 고친다"를 명시한다(테스트를 통과시키려고 고치는 것과 구분).

api.md #21의 Status 집합과 접근 제어 조건도 함께 정정한다.

## 5. TASK-004 — Phase 2 종료 판정

CLAUDE.md §1의 9개 조건을 **하나씩 증거와 함께** 대조한 표를 STATUS.md에 남긴다. "다 됐다"가 아니라 "이 명령의 이 출력이 근거다" 형태로.

Phase 3 인수인계 목록도 함께 남긴다 — 이월된 갭 6건, 부채(M4-1~M4-3 테스트, 실제 경합 재현), Phase 3 범위(AWS·CI/CD·아웃컴 추적·신뢰 점수).

## 6. 검증

TASK마다 검증 4종(`check` / `makemigrations --check` / `ruff` / `test`)을 실행한다. TASK-001·002는 코드 변경이 없을 수 있으나, **그렇더라도 실행해 회귀가 없음을 보인다**(문서 편집이 코드를 건드리지 않았다는 증거).

TASK-003은 코드 변경(#21)이 있으므로 실패 테스트 → 구현 순서를 지킨다.
