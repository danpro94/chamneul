# SPEC-005 — tasks

프롬프트 3 루프(**실패 테스트 먼저 → 최소 구현 → 검증 4종 실행 출력 → 커밋 → STATUS.md 갱신 → 정지·확인**). 커밋 메시지에 `SPEC-005/TASK-00N`을 포함한다.

검증 4종 = `manage.py check` / `makemigrations --check` / `ruff check` / `manage.py test`.

**TASK-001·002는 성격이 다르다.** 이미 동작하는 것을 고정하는 작업이라 "실패 테스트 먼저"가 적용되지 않는다 — 대신 **구현을 바꾸지 않는다**를 지킨다. 테스트를 쓰다 결함이 나오면 고치지 말고 **분리 보고**한다(spec §8 리스크 1).

## TASK-001 — `accounts` 인증 회귀 기반 (#2·#3·#4·#7·#8·#9) — **완료 (2026-09-28)**

* [x] `#2` 가입: 201 + HttpOnly `sessionid` 발급 + 응답 필드 집합(비밀번호 미포함) + 이메일 소문자 저장 + PBKDF2 해싱
* [x] `#2` 중복 이메일 / 중복 닉네임 / 약한 비밀번호 / CSRF 없음 403
* [x] `#3` 로그인 성공 → 세션 발급 / **틀린 비밀번호·없는 계정 응답이 바이트 단위로 동일** / 비활성 계정 로그인 불가 / CSRF 403
* [x] `#4` 로그아웃 → **`Session` 레코드 실제 삭제** + 쿠키 `max-age=0` + **복사해 둔 쿠키도 무용지물**
* [x] `#7` 필드 집합 + `advisor_type`·password 미노출 / `#8` 부분 수정·email 변경 불가·닉네임 중복 409·짧은 닉네임 400 / `#9` 3필드 / 익명 401
* [x] **구현 변경 0건** — `git diff`에 `accounts/{views,services,serializers,models}.py` 없음
* [x] **계약 불일치 4건 발견 → 분리 보고**(spec §9, F-1~F-4). F-1은 **500 결함**. 계약 단언 테스트는 `@expectedFailure` 래칫으로 보존
* [x] 검증 4종 — check 0 issues / makemigrations No changes / ruff passed / **325 tests OK (expected failures=4)**

## TASK-002 — Google OAuth 회귀 (#5·#6) — **완료 (2026-09-30)**

* [x] `#5` authorize: 302 + `client_id`·`redirect_uri`·`state`·`scope` 포함 / URL의 state = HttpOnly 쿠키 값 / 매번 다른 state / 세션 미생성 / 미설정 시 500
* [x] `#6` 신규 사용자 생성 → 세션 발급 + 성공 리다이렉트 + state 쿠키 삭제 + **사용 불가 비밀번호**
* [x] `#6` 닉네임 산정(C-11): 구글 이름 → 이메일 앞부분 폴백 → 충돌 시 `_NNNN` 접미사(20자 이내)
* [x] `#6` 같은 이메일의 기존 로컬 계정에 **연결**(중복 생성 없음, 기존 비밀번호 유지, 이메일 대소문자 무시)
* [x] `#6` 이미 다른 Google 계정과 연결된 계정 → **409**, 세션 미발급
* [x] **보안 검증 3종**: `aud` 불일치 / 발급자 불일치 / **이메일 미인증** → 401, 계정 생성·연결 없음
* [x] state 불일치·쿠키 없음·사용자 취소 → 400 **+ 구글을 아예 부르지 않음** / code 없음 400
* [x] 구글 장애(토큰·tokeninfo 각각) → 502 / `id_token` 없는 응답 → 502 / 비활성 계정 → 401
* [x] **mock 경계는 `urlopen`** — 예상 밖 주소를 부르면 즉시 실패(실제 네트워크 유출 방지)
* [x] **변이 검증**: `aud`·이메일 인증·발급자 검사를 각각 지우면 **해당 테스트가 FAILED** — 테스트가 실제 코드를 검증한다는 증거
* [x] 구현 변경 0건 (`accounts/{views,services,serializers,oauth,models}.py` diff 없음)
* [x] **이 경로에서는 계약 불일치가 나오지 않았다** — 분리 보고 없음
* [x] 검증 4종 — check 0 issues / makemigrations No changes / ruff passed / **354 tests OK (expected failures=4)**

## TASK-003 — 재설정 요청 (#45)

* [ ] 가입된 이메일 → 200 + 메일 1통 — 실패 테스트
* [ ] **가입되지 않은 이메일 → 200, 응답이 가입된 경우와 바이트 단위 동일** — 실패 테스트
* [ ] 메일 미발송 확인(`mail.outbox` 길이 0)
* [ ] Google 전용 계정 → 200, **메일 본문이 다름** — 실패 테스트
* [ ] 이메일 형식 오류 → 400 / CSRF 없음 → 403
* [ ] `settings`에 `EMAIL_BACKEND`(local·test = console) · `PASSWORD_RESET_URL` 추가
* [ ] `accounts/emails.py` 신설 + `request_password_reset` 서비스
* [ ] 검증 4종 실행 결과 첨부

## TASK-004 — 재설정 확정 (#46) ★

* [ ] 유효 토큰 → 200 + **새 비밀번호로 로그인 성공** — 실패 테스트
* [ ] 같은 토큰 재사용 → 400, **비밀번호 불변** — 실패 테스트
* [ ] 만료 토큰 → 400 (`override_settings`로 `PASSWORD_RESET_TIMEOUT=0`)
* [ ] 위조 토큰 → 400 — **위 셋의 응답이 서로 구분되지 않는지** 확인
* [ ] 약한 비밀번호 → 400, 비밀번호 불변
* [ ] **기존 세션 무효화**: 재설정 전 로그인해 둔 세션으로 `/users/me` → **401**
* [ ] **다른 사용자의 세션은 살아 있는지** 함께 확인 (spec §8 리스크 4)
* [ ] `PASSWORD_RESET_TIMEOUT = 1800` 설정
* [ ] **콘솔 링크 왕복**: 실제로 출력된 링크를 복사해 #46에 넣어 통과시키고 출력 첨부
* [ ] 검증 4종 실행 결과 첨부

## TASK-005 — 고민 수정 (#47)

* [ ] `SUBMITTED` + 본인 → 200, 필드 갱신 — 실패 테스트
* [ ] 부분 필드만 전송 → 그 필드만 바뀌고 **나머지 불변** — 실패 테스트
* [ ] `ASSIGNED`/`ANSWERED`/`CLOSED` → **409, 어느 필드도 불변** — 실패 테스트
* [ ] 타인의 고민 → 404 / 소프트 삭제된 고민 → 404 / 비로그인 → 401
* [ ] `status`·`author`·`deleted_at` 섞어 전송 → 200이되 **무시**(결정 3)
* [ ] `update_own_concern` — `atomic` + `select_for_update(of=("self",))` + 받은 필드만 `update_fields`
* [ ] **발행 SQL 실측** — 잠금이 실재하고 `UPDATE`가 지정 컬럼만 싣는지
* [ ] 검증 4종 실행 결과 첨부

## TASK-006 — 마무리

* [ ] SPEC-005 전체 AC 재실행 + 테스트 1:1 대조
* [ ] TASK-001·002에서 나온 **분리 보고 항목** 정리 및 결정 요청
* [ ] `docs/api.md` — 결정 1·2 반영(재설정 링크 설정값, Google 계정의 #46 처리)
* [ ] STATUS.md **47/47** + README_AIUSAGE.md 항목
* [ ] `docs/reviews/`에 SPEC-005 리뷰 노트
* [ ] `docs/smoke-test.md` §5 갭 9 갱신 — OAuth가 더 이상 무검증 영역이 아님
* [ ] PR → 서브에이전트 리뷰(`security-reviewer`) → 머지
