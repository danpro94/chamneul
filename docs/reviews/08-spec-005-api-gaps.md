# 리뷰 노트 08 — SPEC-005 API 공백 3건 + accounts 회귀 기반

> 2026-10-22 작성 (SPEC-005/TASK-006). 판정 원칙은 리뷰 노트 07과 같다: **"이 명령의 이 출력이 근거다."**

## 1. 무엇이 바뀌었나

| 범위 | 내용 |
| --- | --- |
| 새 엔드포인트 | **#45** 비밀번호 재설정 요청 · **#46** 재설정 확정 · **#47** 고민 수정(`SUBMITTED`에서만) |
| 회귀 기반 | `accounts` 인증(#2·#3·#4·#7·#8·#9)과 Google OAuth(#5·#6) — 이 프로젝트에서 **검증 수단이 0개이던 유일한 영역**이 닫혔다 |
| 계약 정합 (TASK-006 결정) | 가입 중복 409(F-1 결함 수정 포함), 로그인 실패 401, 비활성 계정 = 틀린 비밀번호와 동일 401 |
| 보안 하드닝 | **F-5 사전 계정 탈취 방어**(Google 연결 순간 기존 비밀번호·세션 무효화), 재설정 대상 축소(S-2), 링크 fragment(S-5), 메일 타임아웃(S-1), 로그에서 주소 제거(S-4), 오류 리포트 가림 |

**근거**: URL 리졸버 실측 (경로, 메서드) 쌍 **47개** · `manage.py test` **404개 OK, expected failures 0** · `check` 0 issues · `makemigrations --check` No changes · `ruff check` passed. 마이그레이션 0건(토큰은 저장하지 않는다).

## 2. 왜 이렇게 구현했나

* **응답은 같게, 차이는 메일함에만.** #45는 가입·미가입·Google 전용·비활성·메일 실패 다섯 경우의 응답이 바이트 단위로 같다. #46은 만료·위조·재사용·없는 계정·깨진 uid 다섯 실패가 같은 400이다. 구분해 주는 순간 이 API가 "가입 여부 조회기"가 된다(CLAUDE.md §10).
* **토큰을 저장하지 않는다.** Django 토큰은 비밀번호 해시와 `last_login`으로 계산된다 — 비밀번호가 바뀌면 같은 토큰은 저절로 실패하므로 폐기 로직이 필요 없다.
* **상태를 읽고 바꾸는 함수는 잠근다**(`.claude/rules/coding.md`). #46은 사용자 행, #47은 고민 행. #47은 상대편인 #24 배정도 같은 행을 잠그는 것을 확인하고 나서야 의미가 있다.

## 3. 핵심 파일

`accounts/{emails,services,serializers,views,urls}.py` · `concerns/{services,serializers,views}.py` · `config/settings/{base,local,test}.py` · 테스트 `accounts/tests.py`(156개) · `concerns/tests.py`

## 4. 테스트 방법

```bash
uv run python manage.py test --settings=config.settings.test     # 404 OK
# 실환경 왕복 (토큰은 가린다 — smoke-test §6 경고)
docker compose up -d --build app
#  ① /api/v1/csrf → ② POST /auth/password-reset → ③ 로그에서 링크 확인
#  ④ POST /auth/password-reset/confirm → ⑤ 새 비밀번호로 /auth/login
```

TASK-003~005에서 실제 컨테이너로 확인한 것: 가입/미가입 응답 바이트·헤더 동일, 콘솔 링크로 확정 200 → 재사용 400 → 옛 세션 401 → 새 비밀번호 로그인 200, 고민 수정 200 → 배정 상태 409 → 원문 유지.

## 5. DevOps 설명 포인트

* **동기 메일 + 타임아웃 없음 = 워커 고갈.** 응답 없는 메일 서버 앞에서 gunicorn 워커(30초)가 먼저 죽는다. 그 종료는 `SystemExit`라 `except Exception`이 못 잡는다 → 가입된 주소에만 502. `EMAIL_TIMEOUT = 10`으로 막았고, 근본 해결(비동기 큐)은 Phase 3. *Django 코드만 봐서는 안 보이고 Dockerfile의 gunicorn 설정까지 함께 읽어야 보이는 문제다.*
* **로컬 로그는 비밀을 담을 수 있다.** 콘솔 메일 백엔드는 살아 있는 재설정 링크를 stdout에 쓴다. 로그 공유 전 가림 명령은 smoke-test §6.
* **진입점 기본값이 `local`이다**(smoke-test 갭 11) — Phase 3 배포 체크리스트 1번.

## 6. 보안 노트

* `security-reviewer`를 **구현과 병렬(백그라운드)**로 처음 돌렸다(#45 대상). Blocker·High 0, Medium 3 · Low 3 · Info 2 — 전건 처리 또는 결정(spec §12·§13).
* **F-5**는 리뷰어가 "범위 밖 관찰"로 낸 High 후보였다. 가입이 이메일 소유를 확인하지 않는데 Google 로그인은 같은 이메일의 기존 계정에 연결하므로, 먼저 가입해 둔 사람의 비밀번호가 연결 뒤에도 살아 있었다.
* **테스트가 방어 코드를 놓친 사례 3건**을 변이 검증으로 잡았다 — Django의 세션 해시 자동 무효화가 우리 세션 정리 코드를 가린 2건(§11, §13-1), 서비스 쪽 `sensitive_variables`가 뷰의 것에 가려진 1건. *"테스트가 통과한다"는 "테스트가 그 코드를 지킨다"가 아니다.*
* 남은 것: 브루트포스·레이트 리밋(Phase 3), 응답 시간 차이(비동기 발송), ADMIN 계정의 메일함 단독 재설정(2FA 후보).

## 7. 다음 개선

1. 레이트 리밋 — 로그인(#3)·재설정 요청(#45)·가입(#2). DRF 내장 throttling이면 패키지 추가 없음.
2. 메일 비동기 발송 + `DEFAULT_FROM_EMAIL`·SMTP(SES) 설정 — Phase 3, Owner의 SES 도메인 인증이 선행.
3. 진입점 기본값 / prod 설정 검사(갭 11) — 배포 전 필수.
4. `#8 UserMeView.patch`의 IntegrityError 처리에 savepoint 추가(spec §13-2, 현재 무해).
