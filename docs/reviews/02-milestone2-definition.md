# Milestone 2 정의 — 런타임 승격(소유) + accounts 도메인 확장(위임)

> 성격: **마일스톤 계획 문서** (완료 후 리뷰 노트는 별도 작성).
> 근거: CLAUDE.md §1·§15, docs/learning/02 §3~§4, docs/reviews/01, docs/model.md §3.1~3.4, ADR-003.

| 항목 | 값 |
| --- | --- |
| 날짜 | 2026-07-02 |
| Owner 결정 | **통합형 M2** — Docker 소유권 승격 + accounts 모델 확장을 하나의 마일스톤으로 병행 |
| 선행 완료 | M1 스켈레톤 (docs/reviews/01) + ruff 도입 (`06c47a5`, pyproject.toml) |
| 다음 | M3 — 도메인 앱 모델/마이그레이션 (advisors·concerns·advice·notifications) |

---

## 0. 마일스톤 번호 정합 (충돌 해소 기록)

"M2"를 가리키는 두 문서가 달랐다. Owner 결정(2026-07-02)으로 아래와 같이 통합·확정한다.

| 출처 | 기존 "M2" | 확정 후 |
| --- | --- | --- |
| reviews/01 "다음" + `accounts/models.py` 주석 | accounts `UserRole` 등 모델 확장 | **M2 트랙 B**로 흡수 |
| learning/02 §4.1 게이트 테이블 | Dockerfile/compose [소유] 구간 | **M2 트랙 A**로 흡수 |

확정 로드맵 (Phase 2 잔여):

| 마일스톤 | 내용 | 라우팅 | 학습 게이트 |
| --- | --- | --- | --- |
| **M2 (본 문서)** | 런타임 승격 + accounts 확장 | A=[소유] / B=[위임] | 드릴#1 + 퀴즈 + **WB-1** |
| M3 | 도메인 앱 모델/마이그레이션 4종 | [위임], 마이그레이션 운영은 [소유] | 드릴#2 + 퀴즈 |
| M4 | API 구현 — 인증(signup/login/logout/OAuth) 포함 43개 엔드포인트 | [위임] | 드릴#3 + 퀴즈 |
| M5 | 스모크 테스트 + 문서 정리 (Phase 2 종료) | [읽기] | 드릴#4 + **WB-2** |

> 참고: 예시로 거론된 ruff 도입은 이미 완료(`06c47a5`) — M2 범위 아님.
> 인증 API 엔드포인트·도메인 앱 개발은 M3~M4 소속 — M2 범위 아님.

---

## 1. M2 목표 (한 줄)

**"로컬 컨테이너를 운영 형태(멀티스테이지·비루트·gunicorn)로 승격하고, 다중 역할 모델(UserRole/RoleGrant/GoogleIdentity)을 완성해 M4 인증 API의 토대를 만든다."**

---

## 2. 범위 — 트랙 A: 런타임 승격 `[소유]`

**작성 주체: Owner 손코딩. AI는 체크리스트·단계적 힌트·`ops-reviewer` 리뷰만** (learning/02 §2.1 Tier 1, §5 [소유 세션] 프롬프트 사용).

| # | 작업 | 근거 |
| --- | --- | --- |
| A-1 | Dockerfile **멀티스테이지** 전환 (builder / runtime 분리) | learning/02 §2.1, 이미지 슬림화 |
| A-2 | **비루트 실행** (전용 유저 생성, `USER` 지시자) | 컨테이너 보안 기본, EKS 대비 |
| A-3 | 운영 CMD를 **gunicorn**으로 교체, `runserver`는 로컬 dev 경로로 분리 (compose `command:` override 또는 dev 스테이지 — 방식은 Owner가 손코딩 중 결정) | reviews/01 follow-up #2 |
| A-4 | `.dockerignore` 재점검 (멀티스테이지 이후 불필요 복사 차단) | §11 |
| A-5 | (선택) readiness 엔드포인트 `/healthz/db` — 코드는 [위임] 가능하나 liveness/readiness 구분 설명은 [소유] 지식 | reviews/01 follow-up #3 |

**§16 승인 게이트:** `gunicorn` 은 서드파티 패키지 추가에 해당 → **본 문서를 Owner가 승인하는 시점에 함께 승인된 것으로 간주**한다. (dependencies에 추가, dev 그룹 아님)

## 3. 범위 — 트랙 B: accounts 도메인 확장 `[위임]`

**작성 주체: AI 생성 + "코드+설명 동시" + 이해 확인 질문 3개** (learning/02 §5 [위임 세션] 프롬프트 사용). 단 마이그레이션 **적용/운영**은 Owner가 직접 수행한다.

| # | 작업 | 근거 |
| --- | --- | --- |
| B-1 | `UserRole` 모델 — 사용자 다중 역할 보유 | model.md §3.2 |
| B-2 | `RoleGrant` 모델 — 역할 부여/회수 감사 기록 | model.md §3.3 |
| B-3 | `GoogleIdentity` 모델 — Google 계정 연결 (OAuth 플로우 자체는 M4) | model.md §3.4 |
| B-4 | `createsuperuser` → 첫 ADMIN `UserRole` 자동 생성 훅 | ADR-003, reviews/01 follow-up #1 |
| B-5 | 위 3종 Django Admin 등록 | §5, model.md §9 |
| B-6 | 마이그레이션 `accounts.0002` 생성 (적용은 Owner) | §12 |

**설계 주의점 (구현 세션에서 반드시 확인):**

* `User.active_role` 은 보유 `UserRole` 중 하나여야 한다 — 서비스 레이어 제약 (model.md §5). M2에서는 모델+제약만, 전환 API는 M4.
* `UserRole` 유니크 제약은 model.md §3.2 명세를 따르되, 소프트 삭제 미적용 모델이므로 §6.6 부분 유니크 강제 대상 아님 — 일반 `UniqueConstraint` 사용.
* PK는 전 모델 `common.uuid7` 헬퍼 일관 적용 (model.md §1.2).

---

## 4. 명시적 비범위 (Out of Scope)

* 인증 API 엔드포인트 전부 (signup/login/logout, Google OAuth 플로우, 프로필, 역할 전환) → **M4**
* `advisors` / `concerns` / `advice` / `notifications` 앱 → **M3(모델)·M4(API)**
* admin 역할 grant/revoke API → **M4** (M2는 ADR-003 훅까지만)
* outcome tracking / trust score → Phase 3 (CLAUDE.md §5)
* AWS·Kubernetes·Terraform·CI/CD → Phase 3 (§16 게이트)

---

## 5. 수용 기준 (Acceptance Criteria)

### 트랙 A — 런타임

- [ ] `docker compose build` 성공, 최종 이미지가 멀티스테이지 runtime 스테이지 기반
- [ ] 컨테이너 내 프로세스가 비루트로 실행 (`docker compose exec app id` → uid ≠ 0)
- [ ] 운영 경로: gunicorn으로 서비스, `curl /healthz` → 200
- [ ] 로컬 dev 경로(코드 반영·runserver 또는 동등 수단)가 여전히 동작
- [ ] `ops-reviewer` 리뷰에서 **블로커 0** (코멘트는 학습 부채로 기록 가능)

### 트랙 B — accounts

- [ ] `uv run python manage.py check` → 0 issues
- [ ] `uv run python manage.py makemigrations --check --dry-run` → No changes (0002 커밋 후)
- [ ] Owner가 직접 `migrate` 적용 성공 (`showmigrations`로 확인)
- [ ] `createsuperuser` 실행 시 ADMIN `UserRole` row 자동 생성 확인 (shell 또는 Admin에서)
- [ ] Django Admin에서 `UserRole`/`RoleGrant`/`GoogleIdentity` 조회 가능
- [ ] 이해 확인 질문 3개에 Owner가 답변 완료 (미답 항목은 학습 부채 등록)

### 검증 명령 모음 (§12)

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
docker compose build && docker compose up -d && docker compose ps
docker compose exec app id                               # 비루트 확인
curl -s -w '%{http_code}' http://localhost:8000/healthz  # 200
docker compose exec -T app python manage.py migrate      # uv 미경유 — 아래 주 참조
docker compose exec -T app python manage.py showmigrations accounts
```

> 주 (Owner 결정 2026-07-05): runtime 이미지에 uv를 탑재하지 않는다 — uv는 패키지 설치/빌드 도구이므로 실행 단계에는 venv와 소스만 있으면 된다. 컨테이너 내 관리 명령은 이미지 `ENV PATH`(venv 우선)를 통해 `python manage.py ...`를 직접 사용한다.

---

## 6. 학습 게이트 (learning/02 §4 예산 준수)

| 게이트 | 내용 | 예산 |
| --- | --- | --- |
| Owner 선요약 | 리뷰 노트 작성 전 5줄 (explain-first, learning/02 §6) | 10분 |
| 퀴즈 | `drill-master` 3~5문 (트랙 A·B 혼합) | 15분 |
| 드릴 #1 | `chaos-coach` — DB 다운 (`docker compose stop db`) → 증상 관찰·로그 진단·복구·`/healthz` 한계 설명 | ≤30분 |
| **WB-1** | 빈 폴더에서 Dockerfile + compose + settings 분할 백지 재현 → `drill-master` 채점 | 45분 (별도 예산) |

합계: 마일스톤 게이트 ≤55분 + WB-1 45분 — learning/02 §4 예산 내.

---

## 7. 진행 순서 (세션 플랜)

```
1) [소유 세션]  트랙 A 손코딩 — learning/02 §5 소유 세션 프롬프트로 시작
2)              ops-reviewer 리뷰 → 블로커 해소
3) [위임 세션]  트랙 B 생성 — 코드+설명 동시, 이해 질문 3개
4)              Owner가 migrate 적용 + AC 체크리스트 검증
5) [드릴 세션]  chaos-coach 드릴 #1
6) [채점 세션]  drill-master 퀴즈 → 학습 부채 갱신
7)              WB-1 백지 재현 + 채점
8)              explain-first 리뷰 노트(03) 작성 + README_AIUSAGE.md 갱신
```

## 8. 리스크 & 열린 결정

| # | 리스크/결정 | 처리 |
| --- | --- | --- |
| 1 | dev/prod CMD 분기 방식 (compose override vs dev 스테이지) | Owner가 손코딩 중 결정, ops-reviewer가 트레이드오프 코멘트 |
| 2 | 비루트 전환 시 볼륨 마운트 권한 문제 (호스트 소스 `- .:/app` 소유권) | 드릴성 이슈 — 발생 시 Owner 진단이 곧 학습, chaos-coach 힌트 허용 |
| 3 | `active_role` ↔ `UserRole` 정합은 M2에서 DB 강제 불가 (서비스 레이어 제약) | M4 역할 전환 API에서 검증 로직 구현, M2 리뷰 노트에 갭 명시 |
| 4 | gunicorn worker 수/타임아웃 튜닝 | M2는 합리적 기본값만, 튜닝은 Phase 3 관측성과 함께 |

## 9. 완료 정의 (DoD)

§5 AC 전부 체크 + §6 게이트 통과(학습 부채 기록 포함) + 리뷰 노트 03 커밋 + README_AIUSAGE.md 갱신 → **M2 종료, M3 착수 가능.**
