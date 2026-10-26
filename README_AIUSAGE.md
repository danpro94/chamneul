# README_AIUSAGE — AI 활용 기록

> CLAUDE.md §13에 따른 AI 사용 대장. 각 항목: 날짜 / 작업 / AI 도구 / 인간(Owner) 결정 / 생성 산출물 / 검증 결과 / 잔여 리스크.
> 이 프로젝트의 AI 협업 원칙(소유/위임/읽기 라우팅)은 `docs/learning/02-ai-collaboration-and-ownership-strategy.md` 참조.
> 2026-09-09: 과거 `docs/README_AIUSAGE.md`(2026-06-22~06-30, 4개 세션)를 이 파일로 병합하고 원본은 삭제했다(ADR-006 부트스트랩, Owner 결정). 기존 "~2026-07-01 — M1 스켈레톤 (소급 기록)" 압축 요약 항목은 병합된 06-29·06-30의 상세 기록으로 대체한다.

---

## 2026-10-25 — SPEC-005 최종 보안 리뷰 후속 (H-1 두 겹 방어 외 12건) [위임]

### 작업

PR 직전 `security-reviewer`(백그라운드, 약 19분)가 **High 1건**을 냈다. 이번 SPEC의 새 코드가 아니라 **기존 #8 프로필 수정**이 문제였다 — 인증 시점에 읽어 둔 사용자 객체를 통째로 저장해서, 그 요청이 처리되는 동안 일어난 Google 연결의 비밀번호 무효화(F-5)·비밀번호 재설정(#46)·역할 회수를 옛 값으로 되돌릴 수 있었다. 이번 SPEC이 세운 보장을 기존 쓰기 경로가 무너뜨리는 구조다.

### AI 도구

Claude Opus 5.5 — 리뷰는 `security-reviewer` 서브에이전트(읽기 전용), 수정·검증은 메인 세션.

### Owner 결정

H-1: "보안적으로 더 안전한 쪽(현업 표준 수준), 구조적 결함이면 같은 PR에서 고치되 무력화에 대한 **안전망을 함께**". L-3: (a) 배정 이력 있는 고민은 수정 불가. L-1: ASCII 제한 없이 권장안(정규화 통일).

### 생성 산출물

* `accounts/services.py` `update_profile()`(① 잠금 + 보낸 컬럼만) · `accounts/models.py` `User.save()` 안전망(② 바꾸지 않은 인증·권한 컬럼은 안 씀) · `accounts/managers.py` `canonical_email()`
* `accounts/views.py` — M-1(같은 사용자 브라우저 로그아웃), L-2(가입·로그인 오류 리포트 가림), I-5(경합 409 reason)
* `concerns/services.py` — L-3 배정 이력 판정
* 테스트 20개 추가(전체 **424개**) · api.md · model.md · spec §14 · 리뷰 노트 08 §6-1

### 검증 결과

* 선-실패: 새 테스트 대부분 실패 확인(L-1은 이 DB에서 `vıctim@` 가입이 진짜 `victim@` 가입을 **실제로 409로 막는 것**까지 재현).
* **두 겹 방어 검증**: ①만 지우면 ①의 SQL 테스트만 실패하고 공격 3종은 ②가 막는다. ②만 지우면 ②의 모델 테스트만 실패하고 공격은 ①이 막는다. **둘 다 지우면 공격 재현 3종 전부 실패** — 각 겹이 혼자서도 막고, 공격 재현이 진짜임을 함께 증명.
* 나머지 7건(M-1·L-1·L-2·L-3·I-2·I-4·I-5)도 변이 검증 전건 검출.
* `check` / `makemigrations --check`(No changes — 안전망은 컬럼 추가 없음) / `ruff check` / **424 tests OK**
* 실제 컨테이너: #8 수정 200, 로그인된 같은 브라우저에서 #46 → 200 + 이후 `/users/me` 401, 닮은꼴 주소와 진짜 주소 둘 다 가입 201.

### 이번에 드러난 것

1. **새 보안 조치는 그것을 되돌릴 수 있는 기존 쓰기 경로까지 봐야 완성된다.** F-5·#46은 각자 정확했지만 #8이 그 위에 옛 값을 덮을 수 있었다.
2. 테스트 하나의 실패 원인이 테스트 쪽이었다 — 로그인으로 `last_login`이 바뀐 뒤 옛 사용자 객체로 재설정 토큰을 만들어 토큰이 처음부터 무효였다. 토큰이 `last_login`을 포함한다는 Django 설계가 테스트에도 그대로 적용된다(단언은 바꾸지 않고 재조회만 추가).

### 잔여 리스크

* I-1(동시 콜백의 오해 소지 409)은 기록만 — 불변식은 지켜짐, 경합 전용 분기라 테스트 없이 넣지 않음.
* I-6(가입 API로 흔적 없는 가입 여부 조회)·레이트 리밋 — Phase 3 1순위.
* 가입 이메일 인증(F-5의 근본 해결)은 Phase 3 후보.

---

## 2026-10-22 — Owner 실행 가이드 + ADR-009 AI 도구 체계 (병렬 요청 2건) [위임 · 결정은 Owner]

### 작업

TASK-006과 **병렬로** Owner의 요청 2건을 백그라운드 에이전트(general-purpose ×2)에 맡겼다.
1. **OWNER-ACTIONS-GUIDE.md** — 개발 마무리·사업 운영 중 Owner만 할 수 있는 일(계정·결제·콘솔·법률)을 macOS + Chrome 클릭 단위로.
2. **ADR-009(Proposed) + AI-TOOLING-SETUP-GUIDE.md** — 이 프로젝트에 맞는 MCP·에이전트·Claude Code 기능 10개 선정과 init → 구성 → 검증 → 사용 → 롤백 절차.

### AI 도구

Claude Opus 5.5 — 작성은 백그라운드 에이전트(웹 검색으로 2026-10 기준 확인), **검수는 메인 세션**. 세션이 중간에 끊겨 두 에이전트를 저장된 대화에서 재개했다.

### Owner 결정

요청만 함. **ADR-009는 Proposed** — 승인 전에는 아무것도 설치·등록하지 않았다(`claude mcp add` 미실행). 항목 5~10은 승인되더라도 §16 승인을 항목별로 따로 받는다.

### 생성 산출물

* `docs/00-project/OWNER-ACTIONS-GUIDE.md` (A 지금 / B 계정·인프라 / C 한국 법·사업 / D 나중 결정)
* `docs/adr/ADR-009-ai-tooling-mcp-and-agents.md` · `docs/00-project/AI-TOOLING-SETUP-GUIDE.md`

### 검증 결과 (메인 세션 검수에서 고친 것)

* **틀린 테스트 명령 3곳**(`docker compose exec app python manage.py test`) → 이 프로젝트 표준 `uv run python manage.py test --settings=config.settings.test`로 교체.
* **Namecheap 메일 포워딩 함정**: Route 53으로 네임서버를 위임하면 Namecheap 무료 포워딩은 멈춘다. 그런데 DMARC 보고 주소를 그 포워딩에 기대도록 쓰여 있었다 → `rua` 없이 시작하는 안으로 수정, 위임 단계에 경고 추가.
* **ADR 본문과 hook 스크립트의 차단 목록 불일치**(CLAUDE.md·.dockerignore 누락) → 일치시킴.
* hooks 설정의 `"args": []` 필드는 처음 보는 형식이라 공식 문서를 직접 조회해 **유효함을 확인**했다.
* 저장소가 **공개**임을 `gh repo view`로 확인 — 두 가이드는 ADR-004 기준 Tier 3(운영 절차, 전략 IP·비밀 없음)로 판단해 `docs/00-project/`에 둔다.

### 잔여 리스크

* 콘솔 메뉴 라벨(AWS·GitHub·SES·Google)은 화면 개편으로 다를 수 있다 — 문서에 "(메뉴명이 다를 수 있음)"과 검색 키워드를 달았다.
* **[미검증]**: Semgrep 바이너리 내장 MCP 명령, GitHub MCP 툴셋 정식 이름, 통신판매업 면제 기준 수치, AWS Budgets 세부 요금. 각 문서 끝 "직접 확인하지 못한 것"에 목록화.
* C(법·사업) 절은 **법률 자문이 아니다** — 확정 전 전문가 검토.

---

## 2026-10-22 — SPEC-005/TASK-006: 결정 반영 + 마무리 [위임]

### 작업

TASK-001~005와 보안 리뷰에서 쌓인 결정 대기 항목을 **권고안대로** 반영하고 SPEC-005를 닫았다. 가장 무게 있는 것은 **F-5 사전 계정 탈취 방어** — 남이 내 이메일로 먼저 가입해 두면, 내가 나중에 Google로 들어와 그 계정에 연결돼도 그 사람의 비밀번호가 살아 있던 문제다.

### AI 도구

Claude Opus 5.5 (Claude Code, VS Code 확장). 같은 시간에 **백그라운드 에이전트 2개**가 Owner 요청 문서(OWNER-ACTIONS-GUIDE, ADR-009 + AI-TOOLING-SETUP-GUIDE)를 작성했다 — 별도 항목 참조. 중간에 세션이 끊겨 두 에이전트를 저장된 대화에서 이어서 재개했다.

### Owner 결정

"권고대로 승인" — F-1 수정 / F-2·F-3 코드를 계약에 / F-4 문서를 코드에 / I-1~I-3 확정 / S-2 대상 축소 / S-3 Phase 3 배포 체크리스트 / S-5 fragment / F-5 연결 순간 무효화.

### 생성 산출물

* `accounts/{serializers,services,views,emails}.py` — 가입 409(+경합 savepoint), 로그인 401, `_reset_allowed`, Google 연결 하드닝, fragment 링크
* `accounts/tests.py` — 7개 추가, `@expectedFailure` 4개 해소, 계약이 바뀐 단언 3곳 갱신
* `docs/api.md`(#2·#3·#6·#45·#46·#47) · `docs/smoke-test.md`(갭 9 해소, 갭 10·11, 로그 공유 경고) · `docs/reviews/08-spec-005-api-gaps.md` · spec §13 · acceptance 전항 판정

### 검증 결과

* 선-실패 확인 후 구현 → **404 tests OK, expected failures 0** / `check` / `makemigrations --check` / `ruff check` 통과
* URL 리졸버 실측 (경로, 메서드) **47쌍**
* **변이 검증 8건 전건 검출**(F-5 비밀번호·세션, S-2 양쪽, F-1, F-3, S-5, 경합 409)

### 이번에 드러난 것

1. **F-5 세션 정리 제거를 테스트가 두 번 놓쳤다.** 한 번은 Django의 세션 해시 자동 무효화 때문, 또 한 번은 **침입자의 확인 요청 자체가 세션 행을 지워버렸기** 때문이다. 행 개수를 침입자 요청 *전에* 세도록 바꿔서야 잡혔다 — 관찰이 상태를 바꾸면 관찰 순서도 테스트의 일부다.
2. **IntegrityError를 잡는 것만으로는 부족했다** — 바깥 트랜잭션 안에서는 연결이 망가진다. INSERT를 savepoint로 감싸는 Django 정석으로 고쳤다.
3. F-5는 사용자 경험을 바꾼다: 이메일로 가입한 뒤 같은 주소로 Google 로그인을 하면 **기존 비밀번호가 더 이상 통하지 않고** "비밀번호 찾기"로 다시 만들어야 한다. 베타 안내 문구가 필요하다(OWNER-ACTIONS-GUIDE A-5).

### 잔여 리스크

1. 레이트 리밋 부재(로그인·재설정·가입) — Phase 3 1순위.
2. 진입점 기본값 `local`(smoke-test 갭 11) — 배포 전 필수.
3. 실제 Google 왕복은 secret 회전 때 1회 확인 필요.

---

## 2026-10-14 — SPEC-005/TASK-005: 고민 수정 (#47) [위임]

### 작업

조언가가 배정되기 전(`SUBMITTED`)에만 고민을 고칠 수 있게 했다. 배정 뒤에 원문이 바뀌면 조언가가 답하던 질문이 조용히 달라지므로 409로 막는다. **이로써 47개 엔드포인트가 모두 구현됐다.**

### AI 도구

Claude Opus 5.5 (Claude Code, VS Code 확장).

### Owner 결정

TASK-004에서 연속 진행 승인(중간 정지 생략). 신규 결정 없음 — 결정 3(서버 관리 필드 무시)은 2026-09-28 승인분.

### 생성 산출물

* `concerns/services.py` `update_own_concern` · `serializers.py` `ConcernUpdateSerializer`(#16 시리얼라이저 상속, partial) · `views.py` `ConcernDetailView.patch`
* `concerns/tests.py` — `ConcernEditTests` 11개

### 검증 결과

* 선-실패 9/11(통과한 2개는 엔드포인트 부재 405에서도 참인 "익명 401"·"부수효과 없음")
* `check` / `makemigrations --check` / `ruff check` 통과 / **397 tests OK (expected failures=4)**
* **변이 검증 6건 전건 검출**: 잠금·`update_fields`·상태 게이트·작성자 스코프·소프트 삭제·서버 필드 쓰기 허용.
* **실제 컨테이너**: 작성 → 수정 200(`status: "CLOSED"`를 섞어 보내도 `SUBMITTED` 유지) → 상태를 `ASSIGNED`로 전환 → 수정 409 `NOT_EDITABLE` → 재조회 시 원문 유지 → 없는 id 404. *배정 상태 전환은 관리자 API(#24) 대신 `manage.py shell`로 DB를 직접 바꿨다(관리자 계정 비밀번호를 쓰지 않기 위해).*

### 이번에 드러난 것

`#24` 배정이 이미 같은 고민 행을 잠그고 있었다(SPEC-001). 그래서 이번 잠금 하나로 "확인 직후 배정"의 틈이 닫힌다 — 한쪽만 잠그면 효과가 없으므로 상대편을 먼저 확인했다.

### 잔여 리스크

* 409의 `details.reason = "NOT_EDITABLE"`은 api.md #47에 아직 없다 — TASK-006에서 반영.
* 빈 본문 `PATCH {}`는 200이고 `updated_at`만 갱신된다(내용 변화 없음). 계약상 문제는 없으나 기록.

---

## 2026-10-14 — SPEC-005 보안 리뷰 후속: #45 지적 3건 수정 [위임]

### 작업

TASK-004와 병렬로 돌린 `security-reviewer`(#45 대상) 결과 중 **결정이 필요 없는 3건**을 테스트 먼저 쓰고 고쳤다. 결정이 필요한 4건은 spec §12에 기록하고 TASK-006으로 넘겼다.

### AI 도구

Claude Opus 5.5 — 리뷰는 `security-reviewer` 서브에이전트(읽기 전용, 코드만 읽고 실행 안 함), 수정은 메인 세션.

### Owner 결정

리뷰 병행 승인. 3건은 계약·범위 변경이 없는 설정 1줄·로그 문구·단언 보강이라 사후 보고.

### 생성 산출물

* `config/settings/base.py` `EMAIL_TIMEOUT = 10` · `accounts/emails.py` 로그 문구 · `accounts/tests.py` 테스트 2개 + 단언 3개 · spec §12

### 검증 결과

* 선-실패 2/2 확인 — **리뷰어가 "현재 구현에서 실패할 것"이라 예측한 S-4가 실제로 실패**했다(리뷰어는 실행 권한이 없어 코드 읽기만으로 예측).
* `check` / `makemigrations --check` / `ruff` 통과 / **386 tests OK (expected failures=4)**

### 이번에 드러난 것

**S-1은 TASK-003에서 내가 "Phase 3 갭(응답 시간 차이)"으로 적어 둔 것이 실제로는 더 나쁜 문제였다.** 타임아웃이 없으면 시간 차이가 아니라 워커 강제 종료 → 가입된 주소에만 502 — 계약("상태 코드 동일")을 정면으로 깨는 경로다. gunicorn의 워커 종료가 `SystemExit`라 `except Exception`이 못 잡는다는 점은 Django 코드만 봐서는 보이지 않고, Dockerfile까지 함께 읽어야 보인다.

### 잔여 리스크

* 결정 대기 4건 — S-2(Google 분기 범위), S-3(진입점 기본값 = local), S-5(토큰을 쿼리 대신 fragment로), **F-5 사전 계정 탈취(High 후보, 기존 M4-3 동작)**.

---

## 2026-10-14 — SPEC-005/TASK-004: 비밀번호 재설정 확정 (#46) [위임]

### 작업

메일로 받은 링크(uid + token)와 새 비밀번호로 변경을 확정한다. 성공하면 그 사용자의 **모든 세션을 끊는다** — 비밀번호를 되찾는 상황은 계정이 탈취됐을 수 있는 상황이라, 침입자의 세션이 살아 있으면 비밀번호만 바뀌고 침입자는 그대로 남는다.

### AI 도구

Claude Opus 5.5 (Claude Code, VS Code 확장). **처음으로 서브에이전트를 구현과 병렬로 썼다** — `security-reviewer`가 백그라운드에서 #45를 리뷰하는 동안 #46을 구현했다.

### Owner 결정

TASK-004 승인 + `security-reviewer` 백그라운드 병행 + TASK-005 연속 진행(중간 정지 생략).

### 생성 산출물

* `accounts/services.py` `confirm_password_reset` · `_purge_sessions_of` · `views.py` `PasswordResetConfirmView` · `serializers.py` · `urls.py`
* `accounts/tests.py` — `PasswordResetConfirmTests` 16개

### 검증 결과

* 선-실패 14/15(통과한 1개는 "확정해도 로그인되지 않는다" — 엔드포인트가 없어도 참)
* `check` 0 issues / `makemigrations --check` No changes / `ruff check` passed / **384 tests OK (expected failures=4)**
* **변이 검증 8건 전건 검출**: 세션 행 삭제·잠금·비활성 필터·`update_fields`·토큰 검사·사용자 필터·POST 가림·지역 변수 가림.
* **실제 컨테이너 왕복**: 콘솔에 찍힌 링크로 확정 200 → 같은 링크 재사용 400 → 옛 세션 401 → 새 비밀번호 로그인 200 → 옛 비밀번호 실패. 출력에서 토큰은 가렸다.

### 이번에 드러난 것

1. **계획의 만료 테스트 방법(`TIMEOUT=0`)은 불안정했다.** Django 만료 판정이 `>`라서 같은 초 안에 만든 토큰은 0초 설정에서도 유효하다. 발급 시각을 31분 전으로 돌리는 방식으로 바꿨고, 29분은 통과하는 짝 테스트를 뒀다.
2. **"옛 세션 → 401" 테스트는 세션 삭제 코드를 검증하지 못했다.** Django가 비밀번호 해시로 세션을 자동 무효화하기 때문이다. 변이 검증으로 이를 실측했고, "세션 행이 사라졌는가"를 별도 테스트로 고정했다.
3. **오류 화면 가림은 DEBUG=False에서만 동작한다.** 처음 쓴 테스트(DEBUG=True 화면)는 Django 설계상 절대 통과할 수 없는 테스트였다. 운영 오류 리포트를 직접 만들어 검증하도록 바꿨다. 그 과정에서 **시리얼라이저 repr에도 비밀번호가 실린다**는 것이 드러나 뷰 지역 변수를 전부 가렸다. 서비스 쪽 가림은 변이 검증에서 "지워도 아무 테스트도 실패하지 않음"이 나와 원리를 확인한 뒤 제거했다(가장 가까운 호출자의 가림이 아래 프레임까지 덮는다).

### 잔여 리스크

1. 세션 삭제가 전체 세션 행을 훑는다(O(N)). Phase 2 규모에선 허용, 커지면 사용자 인덱스 필요(plan §2).
2. `security-reviewer`의 #45 지적(S-1~S-8) 처리는 별도 커밋/결정으로 다룬다 — 아래 항목 참조.

---

## 2026-10-14 — SPEC-005/TASK-003: 비밀번호 재설정 요청 (#45) [위임]

### 작업

ADR-008의 첫 신규 엔드포인트. "비밀번호를 잊었어요"를 누르면 재설정 링크를 메일로 보낸다. **이 API의 핵심은 무엇을 하느냐보다 무엇을 알려주지 않느냐다** — 가입되지 않은 주소에도 똑같이 200을 돌려줘서, 남의 가입 여부를 캐는 도구가 되지 않게 했다.

### AI 도구

Claude Opus 5.5 (Claude Code, VS Code 확장).

### Owner 결정

TASK-003 착수 승인. 구현 중 판단 3건(I-1~I-3, spec §10)은 계약을 바꾸지 않는 범위라 먼저 구현하고 **사후 확인**을 요청했다.

### 생성 산출물

* `accounts/emails.py` (신규) — 메일 본문 2종(로컬 계정 / Google 전용 계정)
* `accounts/services.py` `request_password_reset` · `serializers.py` · `views.py` `PasswordResetView` · `urls.py`
* `config/settings/base.py` (`PASSWORD_RESET_TIMEOUT` 30분 · `PASSWORD_RESET_URL`) · `local.py` (console 메일)
* `accounts/tests.py` — `PasswordResetRequestTests` 14개

### 검증 결과

* 선-실패: 14개 중 12개 실패 확인(엔드포인트 부재 404). 나머지 2개는 "두 응답이 같다"는 비교라 둘 다 404여도 통과 — 구현 후에도 의미가 유지된다.
* `check` 0 issues / `makemigrations --check` No changes / `ruff check` passed / **368 tests OK (expected failures=4)**
* **변이 검증 5건 전건 검출**: 비활성 필터·메일 실패 처리·CSRF·Google 분기·소문자화를 하나씩 지우면 각각 해당 테스트 1개가 정확히 FAILED.
* **실제 컨테이너**: 재빌드 후 curl로 가입/미가입 요청 → 둘 다 200, 본문 바이트 동일, 헤더도(Date 제외) 동일, CSRF 없으면 403. `docker compose logs app`에 메일이 **1통만**(가입된 주소분) 찍히고 링크가 들어 있음을 확인.

### 이번에 드러난 것

계약은 "응답이 같다"였지만, 구현해 보니 **응답이 갈라질 수 있는 길이 두 개 더** 있었다. ① 메일 서버가 죽으면 가입된 주소에서만 500이 난다 → 그 500이 곧 "가입됨" 신호. 실패를 로그로만 남기도록 막았다(Django 기본 폼도 같은 선택). ② 비활성 계정. 둘 다 테스트로 고정했다.

### 잔여 리스크

1. **응답 시간 차이** — 메일 발송이 동기라, 실제 SMTP를 붙이면 가입된 주소의 응답이 눈에 띄게 느려진다. 비동기 발송과 레이트 리밋은 Phase 3.
2. 보내는 주소가 `webmaster@localhost`(`DEFAULT_FROM_EMAIL` 미설정) — SMTP 연결 때 함께 정한다.
3. `.env.example`에 `PASSWORD_RESET_URL` 키가 아직 없다 — §16 승인 대기.
4. `ruff format --check`가 기존 파일 3개(`accounts/models.py`·`services.py`·`tests.py`)에서 걸린다. HEAD에서도 동일한 기존 상태이고 이번 변경분은 정렬돼 있다. 별도 정리 커밋 후보.

---

## 2026-09-30 — SPEC-005/TASK-002: Google OAuth 회귀 (#5·#6) [위임]

### 작업

**이 프로젝트에서 자동 테스트도 스모크도 없던 유일한 영역**(Google OAuth)에 회귀 테스트 29개를 깔았다. 이미 동작하는 것을 고정하는 작업이라 구현은 바꾸지 않았다.

### AI 도구

Claude Opus 5.5 (Claude Code, VS Code 확장).

### Owner 결정

TASK-002 착수 승인. 신규 결정 없음.

### 생성 산출물

* `accounts/tests.py` — `GoogleAuthorizeRegressionTests`(5) · `GoogleCallbackRegressionTests`(24) + 가짜 구글 `FakeGoogle`

### 검증 결과

* `check` 0 issues / `makemigrations --check` No changes / `ruff` passed / **354 tests OK (expected failures=4 — TASK-001의 F-1~F-3)**
* 구현 변경 0건
* **mock 경계를 네트워크(`urlopen`)에 뒀다.** `accounts.oauth`의 함수를 mock하면 그 함수가 검증되지 않는다. 구글 응답 바이트만 가짜로 주고, 발급자·audience·이메일 인증 검증과 계정 연결·생성·닉네임 산정은 실제 코드가 돈다. 예상 밖 주소를 부르면 즉시 실패하게 해서 테스트가 실제 네트워크로 새지 않게 했다.
* **변이 검증**: "통과했다"만으로는 mock이 검증 코드까지 가렸는지 알 수 없다. `aud`·이메일 인증·발급자 검사를 **하나씩 지우고** 돌려서 **세 번 모두 해당 테스트가 FAILED**가 나는 것을 확인했다(원본은 git으로 복구).

### 이번에 드러난 것

OAuth 경로에서는 **계약 불일치가 나오지 않았다.** TASK-001(가입·로그인)에서 4건이 나온 것과 대조적이다 — OAuth는 M4-3 직후 보안 리뷰(S1/S2/S8)와 409 연결 충돌 하드닝을 한 번 거쳤던 코드다.

작은 함정 하나: tokeninfo 주소(`…/tokeninfo`)가 토큰 주소(`…/token`)로 **시작**한다. 가짜 라우터에서 순서를 반대로 두면 모든 호출이 토큰 교환으로 잘못 가서, 테스트가 엉뚱한 이유로 통과하거나 실패한다. 주석으로 남겼다.

### 잔여 리스크

1. **실제 구글과의 통신은 여전히 미검증이다.** 이 테스트는 "구글이 이런 응답을 주면 우리는 이렇게 한다"까지다. 구글 쪽 응답 형식이 바뀌면 잡지 못한다 — 실제 로그인 1회 확인은 secret 회전(리뷰 노트 07 §3-5-1) 때 함께 하면 된다.
2. tokeninfo 방식은 로그인마다 구글 왕복 1회가 든다(D-5에서 수용). 로컬 서명 검증은 Phase 3.

---

## 2026-09-28 — SPEC-005/TASK-001: `accounts` 인증 회귀 기반 (#2·#3·#4·#7·#8·#9) [위임]

### 작업

SPEC-005(ADR-008의 #45~#47)에 앞서, 그 엔드포인트들이 건드릴 **인증 경로에 회귀 테스트를 먼저 깔았다.** #46은 성공 시 기존 세션을 전부 무효화하는데, `accounts`의 기존 테스트 55개는 전부 역할 관련이었고 **인증 경로는 0건**이었다. 이미 동작하는 것을 고정하는 작업이라 **구현은 한 줄도 바꾸지 않았다.**

### AI 도구

Claude Opus 5 / Opus 5.5 (Claude Code, VS Code 확장).

### Owner 결정

SPEC-005 §7 결정 3건 권고안대로 승인 — (1) 재설정 링크는 설정값 `PASSWORD_RESET_URL` (2) Google 전용 계정도 유효 토큰이면 비밀번호 설정 (3) #47의 서버 관리 필드는 무시.

### 생성 산출물

* `accounts/tests.py` — `SignupRegressionTests`·`LoginRegressionTests`·`LogoutRegressionTests`·`ProfileRegressionTests` 33개
* `specs/SPEC-005-api-gaps/spec.md` §9 — 분리 보고 4건

### 검증 결과

* `check` 0 issues / `makemigrations --check` No changes / `ruff` passed / **325 tests OK (expected failures=4)**
* **구현 변경 0건** — `git diff`에 `accounts/{views,services,serializers,models}.py` 없음
* 테스트를 쓰기 전에 **실측부터 했다.** 계약(api.md)과 코드를 눈으로 대조해 의심 지점을 찾은 뒤, 임시 프로브 테스트로 실제 응답을 확인하고 나서 단언을 썼다.
* 세션 관련 테스트는 `force_authenticate`를 쓰지 않고 실제 로그인으로 검증했다 — 그건 인증기를 건너뛰어 세션 발급·삭제를 검증하지 못한다. 로그아웃 후 **복사해 둔 쿠키로도 401**이 나오는지까지 확인(서버 레코드 삭제의 실효성).

### 이번에 드러난 것

**회귀 테스트가 구현을 건드리기 전에 결함을 찾았다.** 기존 이메일을 대소문자만 바꿔 가입하면(`ALPHA@example.com`) **500**이 난다(F-1). 가입 serializer의 중복 검사는 입력값 그대로 비교하는데 저장 시 매니저가 소문자로 바꿔서, 검사를 통과한 뒤 DB 제약에 걸린다. 같은 종류의 문제를 `#8`(프로필 수정)은 이미 409로 고쳐뒀는데 **가입 쪽만 빠져 있었다**(F-2). 그 외 로그인 실패 상태 코드(F-3), 비활성 계정 처리(F-4)가 api.md와 다르다.

규칙대로 **고치지 않고 분리 보고**했다. 계약을 단언하는 테스트는 `@expectedFailure`로 두었다 — 스위트는 녹색을 유지하되, 고치는 순간 "예상치 못한 성공"으로 떠서 데코레이터를 떼라고 알려주는 래칫이다.

### 잔여 리스크

1. **F-1은 실제 500 경로다.** 로컬 전용이라 지금 노출은 없지만 TASK-006 전에 결정이 필요하다.
2. OAuth(#5·#6)는 여전히 테스트 0건 — TASK-002.
3. 검증기 메시지가 영문(`LANGUAGE_CODE = "en-us"`)이라 한 응답에 두 언어가 섞인다.

---

## 2026-09-16~17 — SPEC-004 (M5): 스모크 테스트 + 문서 정리 — **Phase 2 종료** [위임]

### 작업

신규 엔드포인트 없이 CLAUDE.md §1의 Phase 2 완료 조건 9개 중 **열려 있던 2개**(스모크 문서 부재, model.md drift)를 닫았다. 결과적으로 그 과정에서 코드 결함 6건이 함께 나왔다.

### AI 도구

Claude Opus 5 (Claude Code, VS Code 확장). 서브에이전트 `data-modeler` 1회.

### Owner 결정

착수 전 5건 승인: (1) 산출물은 `specs/`(ADR-006 §30·§59) (2) **백엔드 전 구간 UTC** — DB 저장·API 전송 모두 ISO 8601 UTC, 현지 변환은 클라이언트 책임 (3) **#21을 403→404** (4) 학습 부채 14건 폐기 (5) 고민 종료는 Django Admin으로만.
진행 중 추가 승인: **B-01~B-05**(Admin 우회 경로 차단) 권고안대로.

결정 2·3은 §16 승인 게이트(동작·상태 코드 변경)라 착수 전에 받았다. CLAUDE.md에 시각 직렬화 규정이 없어 ADR은 불필요.

### 생성 산출물

* `docs/smoke-test.md` (신규) — 맨바닥 기동 절차 + 실제 출력 + 갭 9건 + 운영 체크리스트
* `docs/reviews/03-milestone3-review.md`(소급) · `04-milestone4-review.md` · `07-phase2-closeout.md` (신규 3건)
* `docs/model.md` drift 22건 반영 / `docs/api.md` 결정 2·3 + AR-01 잔여 정정
* `concerns/admin.py` · `advice/admin.py` — Admin 우회 차단 5건 / `concerns/services.py` — #21 쿼리셋 스코프 전환
* `README_AIUSAGE.md` M4-1~M4-4 소급 / STATUS.md 부채 전항 종결 + Phase 2 판정표

### 검증 결과

* 검증 4종 TASK마다 실행 — 최종 `check` 0 issues / `makemigrations --check` No changes / `ruff` passed / **291 tests OK**
* **맨바닥 기동**: 볼륨 백업(92K, 정상 종료 마커 확인) → `down -v` → 재기동 → 마이그레이션 25건 → `createsuperuser`(ADMIN `UserRole` 행 생성 확인) → **사용자 여정 12단계 전항 통과**
* **DB 장애 거동 실측**: `/healthz`는 DB가 죽어도 200(설계된 liveness) / 쓰기 API는 500 `OperationalError` / **DB 재기동 시 앱 재시작 불필요**(`StartedAt` 불변, 여정 전체 재통과)
* **Phase 2 조건 9/9** 증거 대조. 라우트 44개를 (경로, 메서드) 쌍으로 실측(패턴은 37개 — 6개 경로가 메서드 공유)
* 결정 2·3이 **실행 중인 시스템**에 반영됨을 라이브 확인: 응답 시각 `…Z`(`+09:00` 0회), #21 미배정 조언가 404 / `active_role≠ADVISOR` 403

### 이번에 드러난 것

1. **model.md drift가 기록된 6건이 아니라 22건이었다.** SPEC 작성 시 적어둔 리스크가 적중했다. 중요한 건 성격이다 — **스키마는 완전히 일치했고 drift는 전부 서술 계층**이었다. "무엇을 저장하는가"는 정확했고 "그것으로 무엇을 하는가"가 낡았다.
2. **문서대로 하면 막히는 절차가 두 달간 정본에 남아 있었다.** model.md §9가 "Django Admin으로 신청 승인/배정/조언 승인"을 안내했는데 전부 `status` readonly라 불가능했다.
3. **Django Admin이 서비스 레이어를 우회하고 있었다**(B-01~B-05). 배정 추가 시 상태 전이·알림 누락, 조언 본문 편집 시 히스토리·버전 누락, 피드백 상태 역전이 가능, 배정 삭제 시 감사 기록 물리 소멸.
4. **`REVIEWING` 상태는 도달 불가**이고 **승인된 조언의 철회 경로는 어디에도 없다.** 둘 다 문서는 "가능하다"고 적고 있었다.
5. **테스트 픽스처 오류 3곳** — `reflective_questions`를 배열로 넘기고 있었다(실제는 `TextField`). 스모크 스크립트가 같은 실수를 해서 API가 400으로 잡아냈고, 그 김에 발견했다.
6. **#21 구현 중 TASK-002가 이틀 전 문서화한 함정을 바로 밟을 뻔했다** — `base_manager_name = "all_objects"` 때문에 FK 역참조가 소프트 삭제를 우회한다. 문서에 적어두지 않았으면 놓쳤을 것이다.

### 잔여 리스크

1. **운영 설정(`DEBUG=False`) 경로를 Phase 2 내내 한 번도 띄워보지 않았다.** "override 없음 = 운영 경로"가 기본값인데 그 경로가 실제로 뜨는지 미확인이다. **Phase 3 최우선.**
2. **실제 경합은 여전히 미재현.** 잠금의 존재는 SQL 검사 테스트로 고정했으나 동시 실행은 `TestCase`로 만들 수 없다.
3. **M4-1~M4-3 자동 테스트 0건.** 스모크가 실환경에서 한 번 덮었을 뿐 회귀 방어가 없다.
4. 브루트포스 방어 부재, 정적파일 미구성, `/healthz`의 DB 비인지 — 전부 갭으로 기록만 했다.
5. 에러 메시지가 모델명을 노출한다(`"No Assignment matches the given query."`). 전 엔드포인트 공통 패턴이라 개별 수정이 아니라 메시지 정책 수립 시 일괄 처리가 맞다.

---

## 2026-09-16 — SPEC-003/TASK-005: 교차 검증 + 마무리 — M4 구현 종료 [위임]

### 작업

SPEC-003의 마지막 구간. 새 엔드포인트는 없고 **기능 사이의 틈**을 검증했다. SPEC-002가 AC 전항 통과 + 168개 테스트 상태에서 서브에이전트 리뷰에 데이터 유실 1건과 500 크래시 1건을 들킨 이유가 그 틈이었기 때문에, 이번에는 그 검증을 AC에 미리 넣어두고 여기서 실행했다.

### AI 도구

Claude Opus 5 (Claude Code, VS Code 확장).

### Owner 결정

TASK-005 진행 승인. 신규 결정 없음.

### 생성 산출물

* `notifications/tests.py` — `NotificationTargetUrlRoundTripTests`(6) 추가, 앱 누적 34개
* `accounts/tests.py` — `RoleRevokeEndToEndTests`(6) 추가, 앱 누적 51개
* `docs/api.md` — #40 `actor` 삭제, #40·#41 Status에서 403 제거 + #41 멱등 명시, #43 배정 잔존 명시, 개정 이력 1건
* `docs/reviews/06-spec003-notifications-roles.md` (신규)
* `specs/SPEC-003-notifications-roles/acceptance.md` — AC-1~AC-10 판정 완료 기록

### 검증 결과

* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* `manage.py test` → **272개 통과**
* **AC-8 `target_url` 왕복**: 알림 5종을 실제 서비스 경로(`assign_advisor`·`review_advice`·`review_application`)로 발생시키고 각 `target_url`을 수신자 본인 세션으로 GET → **전부 200**. 경로가 전부 옳았다 — 다만 그동안 **아무도 호출해 본 적이 없었으므로** 옳다는 사실 자체가 미확인 상태였다.
* **AC-7 end-to-end 자동화**: 대조군(회수 전 #20·#29=200)을 포함해 6개. 회수 후 403, 조언 데이터 보존, concern `ASSIGNED` 유지, 알림 미발생.
* `RoleGrant` append-only 정적 확인: 프로덕션 코드에 `create` 3곳뿐, `update`/`delete` 없음.

### 이번에 찾은 것 2건

1. **AC 전수 대조에서 미커버 1건.** AC-8의 "payload에 C-10 표의 키가 들어 있다"가 5종 중 ASSIGNMENT_CREATED 하나에만 적용돼 있었다. 메우고 실행했더니 통과 — **코드는 이미 옳았고 검증이 비어 있었다.** 대조를 실제로 하지 않았으면 AC 문서에는 체크 표시가 남았을 항목이다. AC 전항 통과가 "검증했다"를 뜻하지 않는다는 사례를 하나 더 얻었다.
2. **`force_authenticate`는 DB를 다시 읽지 않는다.** AC-7 테스트를 처음 돌렸을 때 회수 후에도 200이 나왔다. 제품 결함이 아니라 테스트 도구의 성질이었다 — 실제 요청은 세션에서 사용자를 매번 DB에서 읽지만 `force_authenticate`는 넘겨준 파이썬 객체를 그대로 `request.user`로 쓴다. 브라우저 실증에서는 이미 403이 나와 있었다. `refresh_from_db()`로 실제 동작을 모사하고, 지우면 이 클래스의 403 검사가 전부 무의미해진다는 주석을 남겼다.

### 잔여 리스크

1. **실제 경합은 여전히 미재현.** 발행 SQL로 잠금의 *존재*는 고정했지만 동시 실행은 `TestCase`(트랜잭션 내부)로 만들 수 없다. `TransactionTestCase` + 스레드로 "관리자 0명" 시나리오를 실제로 돌려보는 것이 M5 이후 과제다.
2. **서브에이전트 리뷰 미실행.** SPEC-002의 교훈상 이것이 남은 가장 큰 미검증 구간이다. PR 직후 `security-reviewer`·`api-architect` 2종을 돌린다.
3. **문서 부채 잔존**: M4-1~M4-4 AIUSAGE 소급, 리뷰 노트 2건(M3·M4 전반), model.md drift 6건. M5로 이월.
4. **`accounts` 앱의 M4-1~M4-3 테스트 여전히 0건** — 이번 SPEC은 #10·#42·#43만 커버했다.

---

## 2026-09-15 — SPEC-003/TASK-004: 역할 회수 (api.md #43) — A-3 양방향 해소 [위임]

### 작업

`DELETE /api/v1/admin/users/{user-id}/roles/{role}` 구현. **44/44 엔드포인트**가 되어 M4의 구현 구간이 끝났다. Owner가 "가장 위험하니만큼 리더급 수준으로 신중히"를 요구한 구간이라, 구현보다 **판정 순서·잠금·실증**에 시간을 더 썼다.

### AI 도구

Claude Opus 5 (Claude Code, VS Code 확장).

### Owner 결정

TASK-004 착수 승인 + 최고 수준의 신중함 요구. 설계는 ADR-003·SPEC-003 확정 범위 내 — 신규 결정 없음.

### 생성 산출물

* `accounts/services.py` — `revoke_role()` 신규, **`set_active_role()` 잠금 추가**
* `accounts/views.py` — `AdminUserRoleDetailView` / `accounts/urls.py` — `GrantableRoleConverter` + path
* `accounts/tests.py` — `RoleRevokeTests`(22) + `ActiveRoleSwitchTests`(4) + `StateTransitionLockingTests`(3) 추가, 앱 누적 45개
* `docs/00-project/STATUS.md` — A-3 2개 행 및 §5 미결 항목을 해소 완료로 갱신

### 검증 결과

* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* `manage.py test` → **260개 통과**. 회수 22개 중 구현 전 **14개 실질 실패** 확인 후 착수.
* **발행 SQL 실측**: ADMIN 회수 = `FOR UPDATE OF "accounts_user"` → `role='ADMIN' ORDER BY id ASC FOR UPDATE` → DELETE → INSERT. ADVISOR 회수 = User 잠금 → DELETE → INSERT → `UPDATE accounts_user SET active_role='USER', updated_at=...`(2개 컬럼만).
* **AC-7(A-3 end-to-end)을 TASK-005에서 앞당겨 실증**: 회수 전 #20=200·#29=200 → 회수(204) → 회수 후 #20=403·#29=403, 조언 데이터는 #27=200으로 보존, concern은 `ASSIGNED` + 배정 1건 유지(결정 3 의도대로). `/roles/USER`는 404(URL 미매칭), 재회수는 409.

### 설계 판단 4건 (기록 목적)

1. **판정 순서 = 자기회수 → 미보유 → 마지막관리자.** 순서를 바꾸면 관리자가 1명일 때 ADMIN을 갖지도 않은 사용자를 회수 시도했을 때 "마지막 관리자"라는 **사실이 아닌** 오류가 나간다. 테스트로 고정했다.
2. **`count()` 대신 `list()`.** PostgreSQL은 집계 위의 `FOR UPDATE`를 거부한다. 잠기지 않은 count가 바로 이 가드가 막으려는 경합이므로, 행을 실제로 잠그고 파이썬에서 센다.
3. **잠금 순서 고정.** `User` → ADMIN `UserRole`(`order_by("pk")`). `grant_role`·`set_active_role`은 `User`만 잠그므로 순환이 없다. 순서를 고정하지 않으면 두 회수가 반대 순서로 잠가 교착(500)할 수 있다.
4. **"마지막 ADMIN"은 `UserRole` 행 기준, superuser 미포함.** `IsAdmin`은 superuser도 통과시키지만(ADR-003 §1), 잘못 막으면 재시도로 끝나고 잘못 허용하면 시스템이 잠긴다. 이 비대칭이 보수적 판정의 근거다.

### 범위를 한 항목 넘어선 부분 (명시)

TASK-004 체크리스트에는 없었으나 **`set_active_role`(#10)도 수정했다.** STATUS.md §7의 A-3 정의가 원래 이 함수의 경합을 가리키고 있었고, 회수 쪽만 고치면 *"전환이 역할을 읽음 → 회수가 지움 → 전환이 씀"* 순서로 동일한 위험 상태(역할 없이 ADVISOR 착용)에 그대로 도달한다. 한쪽만 닫고 "A-3 해소"로 보고하면 사실과 다르므로 양쪽을 닫았다. 시그니처는 불변이며, 이 함수의 첫 테스트 4개를 함께 추가했다.

### 잔여 리스크

1. **동시성은 단일 스레드 테스트로 증명할 수 없다.** Django `TestCase`가 트랜잭션 안에서 돌기 때문이다. 대신 **발행 SQL을 검사하는 테스트**(`StateTransitionLockingTests`)로 잠금·순서·`update_fields` 범위를 고정했다 — 규칙을 문서가 아니라 기계가 지킨다. 실제 경합 재현(`TransactionTestCase` + 스레드)은 M5 이후 과제.
2. **ADMIN 집합 전체를 잠근다.** Phase 2의 관리자 수가 한 자리라 비용이 무시할 수준이고 ADMIN 회수끼리만 막지만, 관리자가 수백 명이 되면 advisory lock 등으로 재검토해야 한다.
3. **회수 후에도 `advisor_status`는 `APPROVED`로 남는다**(#9). 신청이 승인됐던 것은 사실이므로 거짓은 아니나, 화면에서 "역할 없음 + 승인됨"이 함께 보이면 혼동될 수 있다. 현재 동작을 유지하되 M5 UX 검토 항목으로 남긴다.
4. **회수된 조언가의 배정이 남는다** — 결정 3(a)에 따른 의도된 동작. #23 admin 상세에서 식별 가능함을 실증했고, M5 스모크 항목으로 남긴다.

---

## 2026-09-15 — SPEC-003/TASK-003: 역할 부여 (api.md #42) [위임]

### 작업

`POST /api/v1/admin/users/{user-id}/roles` 구현. **`accounts` 앱의 첫 테스트 파일**이 생긴 지점이다 — M4-1~M4-3이 test-first 도입 전에 구현돼 이 앱만 테스트 0건이었다. 범위는 #42/#43으로 한정했고, 회원가입·로그인·OAuth·프로필의 소급 테스트는 문서 부채로 유지한다.

### AI 도구

Claude Opus 5 (Claude Code, VS Code 확장).

### Owner 결정

TASK-003 착수 승인. 설계는 ADR-003·SPEC-003 확정 범위 내 — 신규 결정 없음.

### 생성 산출물

* `accounts/tests.py` (**신규, 16개**) — `AdminRoleTestBase` + `RoleGrantTests`
* `accounts/services.py` — `grant_role()` 추가 (`held_roles`·`set_active_role` 시그니처 불변)
* `accounts/serializers.py` — `RoleGrantRequestSerializer` 추가
* `accounts/views.py` — `AdminUserRolesView` 추가 / `accounts/urls.py` — path 추가

### 검증 결과

* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* `manage.py test` → **231개 통과**(accounts 16개 신규). 구현 전 16개 중 **12개 실질 실패** 확인 후 착수 — 나머지 4개는 부정 단언(알림 미생성·`active_role` 불변·중복 시 감사행 미생성·없는 user 404)이라 아무 일도 일어나지 않는 상태에서 자동 성립했고, 구현 후 재실행에서 의미를 갖는다.
* **발행 SQL 실측**: `FOR UPDATE OF "accounts_user"`가 `exists()` 검사보다 **먼저** 걸린다. 대상 `User` 행을 잠근 뒤 검사·생성하므로 동시 부여가 직렬화되고, 중복은 유니크 제약(500)이 아니라 409로 떨어진다.
* Mock-Up UI: 대상 본인 시점 `/api/v1/users/me/roles` 부여 전(`["USER"]`) / 후(`["USER","ADVISOR"]`) 2장. 실제 브라우저 왕복으로 **409**(중복 부여) · **400**(`role="USER"`) · **403**(비관리자) 동시 확인.

### 잔여 리스크

1. **`USER` 역할 차단을 serializer의 choices에 뒀다.** 서비스 레이어가 아니라 입력 검증 단계에서 막으므로, 앞으로 `grant_role()`을 API 밖에서(관리 커맨드·데이터 마이그레이션 등) 호출하면 이 가드를 우회한다. 모델의 `UserRole.clean()`이 남아 있지만 `create()`는 `full_clean()`을 부르지 않는다 — 호출부가 늘어나면 서비스 레이어로 옮겨야 한다.
2. **`IsAdmin`은 superuser도 통과시킨다**(ADR-003 §1). #43의 "마지막 ADMIN" 판정과 기준이 어긋날 수 있어, TASK-004에서 보수적 판정(UserRole 행 기준)을 테스트로 고정한다.
3. **A-3 미해소.** TASK-004에서 구현·검증.
4. **부여는 `active_role`을 바꾸지 않는다** — 의도된 동작이나, 초청 조언가가 "역할은 받았는데 왜 활동이 안 되지"로 혼동할 여지가 있다. M5 스모크 문서에 안내 문구가 필요하다.

---

## 2026-09-15 — SPEC-003/TASK-002: 알림 읽음 처리 (api.md #41) — M4-7 종료 [위임]

### 작업

`PATCH /api/v1/notifications/{notification-id}/read` 구현. 이로써 M4-7(알림 3개)이 끝나고 **42/44 엔드포인트**가 됐다. 남은 것은 M4-8 역할 부여·회수(#42·#43) 2개뿐이다.

### AI 도구

Claude Opus 5 (Claude Code, VS Code 확장).

### Owner 결정

TASK-002 진행 승인. 설계 결정은 SPEC-003 §4에서 이미 확정된 범위 내(멱등 200) — 신규 결정 없음.

### 생성 산출물

* `notifications/services.py` — `mark_read()` 추가
* `notifications/serializers.py` — `NotificationReadResultSerializer`(3필드) 추가
* `notifications/views.py` — `NotificationReadView` 추가 / `notifications/urls.py` — `/read` path 추가
* `notifications/tests.py` — `NotificationReadTests` 8개 추가

### 검증 결과

* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* `manage.py test` → **215개 통과**(notifications 28개). 구현 전 8개 중 **5개가 실질 실패**함을 확인하고 착수 — 나머지 3개는 라우트 부재로 404가 우연히 기대값과 일치해 무의미 통과했고, 구현 후 재실행에서 비로소 의미를 갖는다(부정 테스트의 성질).
* **발행 SQL 실측**: `.claude/rules/coding.md` 상태 전이 규칙의 3종 가드가 장식이 아닌지 직접 확인 — `FOR UPDATE OF "notifications_notification"` 실재, UPDATE는 `is_read`·`read_at` **2개 컬럼만** 기록.
* Mock-Up UI 3장: 읽음 전(unread_count=3) → 후(2, 해당 알림만 `is_read=true`) → 상세 `read_at` 기록. **실제 브라우저에서 csrftoken 쿠키를 `X-CSRFToken` 헤더로 되돌려 보내는 왕복**으로 확인(CLAUDE.md §10). 같은 알림에 PATCH를 2회 보내 **200 + `read_at` 동일값**(멱등) 실측.

### 잔여 리스크

1. **읽음 처리의 멱등성이 `read_at` 보존에 의존한다.** api.md #41에 409가 없어 재호출은 성공해야 하는데, 성공시키려고 타임스탬프를 덮어쓰면 "처음 본 시각"이 조용히 사라진다. 가드를 응답이 아니라 **쓰기 쪽**에 둔 이유이며, 테스트로 고정했다.
2. **일괄 읽음 API 없음.** api.md 비범위(UX §8-6), M5에서 재검토.
3. **A-3 미해소.** TASK-004에서 구현·검증.
4. **`accounts` 앱 테스트 여전히 0건.** TASK-003에서 첫 파일이 생긴다.

---

## 2026-09-15 — SPEC-003 작성 + TASK-001: 알림 목록/상세 (api.md #39·#40) [위임]

### 작업

M4-7(알림 3개)과 M4-8(역할 2개)을 **SPEC-003 하나로 묶어** 명세 4종을 작성하고, TASK-001(#39 목록 + #40 상세)을 프롬프트 3 루프로 구현했다. `notifications` 앱은 M3 이후 `models.py`·`admin.py`만 있는 껍데기였다 — SPEC-001/002/M4-4가 알림 행을 **쓰기만** 하고 읽는 코드가 없었으므로, 이번이 알림 필드 설계의 첫 소비자 검증이다.

### AI 도구

Claude Opus 5 (Claude Code, VS Code 확장).

### Owner 결정

**§7 결정 3건 전부 승인 (권고안대로):**

1. **알림 응답에 `actor`(관리자 신원) 미노출.** api.md #40은 `actor?: {user_id?, display_name?}`를 명세했으나, Phase 2 알림 5종의 actor가 전부 관리자여서 그대로 구현하면 일반 사용자에게 관리자 계정 id가 샌다. SPEC-002 보안 리뷰가 "SPEC-003 응답 필드 설계 시 재검토"로 지목했던 지점.
2. **타인 알림 조회는 404(403 아님).** Owner 근거: *"애초에 이 앱 서비스는 개인화 앱이므로 남의 알림을 열 수 없어야 함. 알림은 나에게만."* 이에 따라 구현은 쿼리셋을 `recipient=user`로 좁히는 형태만 쓴다 — 객체를 꺼낸 뒤 소유자를 비교하는 형태는 403/404 분기 실수를 낳으므로 배제.
3. **ADVISOR 회수 시 활성 배정은 자동 해제하지 않음.** 관리자가 #25로 명시 해제한다. 역할 회수 한 번이 배정 해제·상태 전이·알림까지 연쇄하면 부수효과가 과도하게 숨는다.

세 결정 모두 CLAUDE.md 조항과 충돌하지 않아 **ADR 불필요**(§16, ADR-007 교훈 적용 확인).

### 생성 산출물

* `specs/SPEC-003-notifications-roles/{spec,plan,tasks,acceptance}.md` — 결정 3건, `revoke_role` 잠금 설계, TASK-001~005, AC-1~AC-10
* `notifications/{serializers,services,views,urls,tests}.py` (신규 5종), `config/urls.py` include 추가
* `docs/00-project/STATUS.md` 갱신 (41/44)

### 검증 결과

* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* `manage.py test` → **207개 통과**(notifications 20개 신규). 구현 전 20개 전부 실패(404) 확인 후 착수 — TDD 순서 준수
* `assertNumQueries`는 **추정하지 않고 실측**했다(3건: 페이지 COUNT + 페이지 행 + unread_count 집계). SPEC-001·002에서 추정으로 쓴 3회가 전부 틀렸던 항목
* Mock-Up UI 4장(DRF Browsable API): 목록(3건·unread_count=2) / `?is_read=true` 필터(total=1인데 unread_count는 2 유지) / 상세(read_at 있음·관리자 신원 없음) / 타인 알림 → 404

### 잔여 리스크

1. **`target_url` 규약(C-10)이 아직 실제로 호출되지 않았다.** 5개 타입의 경로가 urlconf에 실재함은 확인했으나, 수신자 세션으로 GET → 200 왕복은 TASK-005의 AC-8에서 검증한다.
2. **#41 미구현.** 목록·상세만 있어 사용자가 알림을 읽음 처리할 수단이 아직 없다(TASK-002).
3. **A-3 미해소.** 역할 회수 시 `active_role` 강등은 TASK-004에서 구현하며, 권한이 실제로 닫히는지는 AC-7 end-to-end로 판정한다.
4. **`accounts` 앱 테스트 여전히 0건.** TASK-003에서 #42/#43 경로에 한해 첫 테스트 파일이 생긴다. M4-1~M4-3(회원가입·로그인·OAuth·프로필)의 소급 테스트는 이번 SPEC 범위가 아니다.

---

## 2026-09-14 — 동일 유형 결함 전수 점검 (A-1 수정, A-2·A-3 기록) [위임]

### 작업

SPEC-002 리뷰가 찾은 M-1(잠금 없는 read-modify-write)이 **다른 앱에도 있는지** 전 서비스 레이어를 점검했다. PR #4 머지 직후 우선순위 2번 항목.

1. `grep`으로 전 앱의 `.save()` 호출과 `select_for_update`/`transaction.atomic` 사용 위치를 대조 → 후보 3건 식별.
2. 각 후보의 뷰-서비스 경계를 읽어 실제 영향 판정.
3. A-1만 수정, A-2·A-3은 근거와 함께 기록.
4. 재발 방지 규칙을 `.claude/rules/coding.md`에 신설.

### 점검 결과

| # | 위치 | 영향 | 처리 |
| --- | --- | --- | --- |
| **A-1** | `advisors.review_application` | 호출자가 건넨 스냅샷으로 전이를 검사 → 동시 승인 시 **`RoleGrant` 감사 행 2개 + 알림 2건**. ADR-003 §3이 세운 감사 추적이 오염된다 | **수정** |
| A-2 | `concerns.soft_delete_concern` | 동시 삭제 2건이 둘 다 409 검사 통과 → 결과는 멱등, 409 가드만 신뢰 불가 | 기록만 |
| A-3 | `accounts.set_active_role` | 역할 회수와 동시 실행 시 회수된 역할로 전환 가능 | M4-8 선행 조건과 통합 |

**M-1과 결정적으로 다른 점**: 셋 다 `update_fields`를 쓰고 있어 **컬럼 덮어쓰기는 없었다.** 남은 위험은 "검사를 통과한 뒤 두 번 실행되는" 쪽이라 데이터 손실이 아니다. 그래서 A-1만 고치고 나머지는 기록으로 남기는 판단이 가능했다.

### 부수 성과: advisors 앱 테스트 0 → 7건

M4-4는 test-first 결정(D-7, 2026-09-09) **이전**에 구현돼 테스트가 하나도 없었다. A-1 회귀 테스트를 쓰려면 픽스처가 필요했으므로, 같은 파일에 #15 리뷰 전이의 기본 커버리지(승인 시 역할+감사+알림, 사유 없는 반려 422, 반려 시 사유 저장, 권한 403, 404)도 함께 넣었다. #11~#14 커버리지는 여전히 부채로 남는다.

### 재발 방지 규칙 신설

`.claude/rules/coding.md`에 **"상태 전이 함수는 예외 없이 `atomic` + `select_for_update(of=("self",))` + `update_fields`"** 를 규칙으로 올렸다. 같은 결함이 3개 앱에서 반복된 이상 개별 수정보다 규칙이 싸다. 규칙 본문에 실제로 일어난 3건을 근거로 적어, 왜 이 규칙이 있는지가 규칙과 함께 남게 했다.

함께 적은 "자주 틀리는 지점" 3가지:
* 낙관적 잠금은 **한쪽만** 지킨다 — 두 방향을 각각 따져야 한다.
* `save()`의 기본은 전 컬럼 UPDATE — `update_fields`는 성능 최적화이기 이전에 **권한 경계**다.
* soft delete는 **FK 역방향 조회에 자동 적용되지 않는다**.

### 사용 도구

* Claude Code (VS Code Extension)

### 인간 결정 (Owner, 2026-09-14)

| 결정 | 내용 |
| --- | --- |
| 점검 범위 | **A-1만 수정, A-2·A-3은 기록** — 비유로 확인받음("출석부에 두 번 적히는 것" vs "이미 꺼진 불을 또 끄는 것" vs "아직 달지도 않은 문의 자물쇠") |

### 생성된 산출물

신규: `advisors/tests.py`(7건). 수정: `advisors/{services,views}.py`, `.claude/rules/coding.md`, `docs/00-project/STATUS.md`.

### 검증 결과 (전부 실행 완료)

* `manage.py test advisors` → 구현 전 **1 error**(A-1 회귀 테스트만 실패, 나머지 6건은 기존 동작이 이미 옳아 통과) → 수정 후 **7/7 OK**
* `manage.py test` (전체) → **187/187 OK** (180 → 187)
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed

### 잔여 리스크

1. **advisors #11~#14 테스트 부재** — 이번에 #15만 커버했다. M4-1~M4-3(accounts)도 여전히 0건.
2. **A-2·A-3 미수정** — 근거와 함께 STATUS.md §7-1에 기록. A-3은 M4-8 착수 시 반드시 함께 처리해야 한다.
3. **동시성은 여전히 단일 스레드 테스트로만 검증** — A-1 회귀 테스트도 "서비스가 호출자 스냅샷을 믿지 않는다"를 결정적으로 확인할 뿐, 실제 경합 재현은 아니다.

### 다음 단계 권장

1. M4-7·M4-8을 SPEC-003 하나로 묶을지 판단(총 5개 엔드포인트) — 묶는다면 A-3을 그 SPEC의 AC로 편입.

---

## 2026-09-14 — SPEC-002 서브에이전트 리뷰 실행 및 지적 사항 전량 반영 [위임 + 검증]

### 작업

1. PR #3 생성 후 **`security-reviewer`·`api-architect` 두 서브에이전트를 병렬 실행**(각각 읽기 전용, 파일 수정 금지 조건).
2. 두 리뷰의 지적을 **직접 코드를 읽어 재확인**한 뒤(관행상 에이전트 결과를 그대로 수용하지 않음) Owner에게 정책 결정 4건을 질의·확정.
3. 실패 테스트 12건 선작성 → 코드 6건 수정 → advice 118/118, 전체 **180/180** 통과.
4. 문서: **ADR-007 신설**, CLAUDE.md §6.7·§16 개정, api.md 정정 8건, `docs/reviews/05-spec002-subagent-review.md` 작성.

### 리뷰가 찾아낸 것 (AC 전항 통과 상태에서)

TASK-007에서 AC-1~AC-11을 전수 대조해 미커버 6건까지 메웠고 168개 테스트가 통과하던 상태였다. 그런데 리뷰가 **실제 버그 2건**을 찾았다:

| 발견 | 심각도 | 내용 |
| --- | --- | --- |
| 보안 M-1 | 데이터 손실 | **조언가의 수정이 관리자의 반려를 되돌릴 수 있었다.** 잠금 없는 읽기 + `update_fields` 없는 `save()`가 전 컬럼을 stale 값으로 덮어써, 반려 사실·사유·반려자 기록이 전부 소멸 |
| 보안 M-2 / API BL-1 | 500 크래시 | 소프트 삭제된 고민의 조언을 리뷰하면 `Concern.DoesNotExist`(APIException 아님) → 500. `DEBUG=True`에서 트레이스백 전문 노출 |

**왜 AC로 못 잡았나**: 둘 다 *기능 간 상호작용*이다. M-1은 "조언가 수정"과 "관리자 리뷰"가 **동시에** 일어나는 경우, M-2는 "고민 삭제"와 "조언 리뷰"의 교차점. AC는 내가 생각한 시나리오의 목록이고, 두 기능을 각각 구현할 때는 그 조합을 떠올리지 못했다. **AC 전항 통과는 "버그 없음"과 다르다**는 것을 이번에 실물로 확인했다.

그 외 메이저 4건(REJECTED 막다른 길, 소프트 삭제된 고민의 조언이 사용자 경로에 계속 노출, #32 status 미검증, 잠금 범위 과다)과 마이너 다수.

### 가장 값진 발견: 헌법 충돌

`api-architect`가 코드 버그가 아닌 것을 하나 잡았다. CLAUDE.md §6.7은 `version`을 "**every** advice update"마다 +1로 규정했는데, 2026-09-11 Owner 결정은 "본문 변경 시에만"으로 좁혔다. 구현·명세·테스트는 일관됐지만 **ADR이 없었다** — §16 constitutional lock 위반 상태로, 코드가 헌법을 앞서 있었다.

ADR-006이 만들어진 이유가 정확히 이런 drift를 막자는 것이었는데 바로 다음 SPEC에서 재발했다. ADR-007로 메우고 §16에 재발 방지 문구를 남겼다: *"CLAUDE.md 조항과 충돌하는 SPEC 결정은 리뷰 때가 아니라 결정 시점에 ADR이 필요하다."*

### 인간 결정 (Owner, 2026-09-13~14)

| 결정 | 내용 |
| --- | --- |
| 리뷰 실행 | PR 생성 직후 서브에이전트 리뷰 2종 실행 승인 |
| 정책 1 | 삭제된 고민의 조언 리뷰 → **409 차단 + #32 큐에서도 제외** |
| 정책 2 | §6.7 충돌 → **ADR-007 신설**(구현 원복 아님) |
| 정책 3 | REJECTED 막다른 길 → **삭제 허용**으로 재작성 경로 확보 |
| 정책 4 | 삭제된 고민의 조언 → **#26/#27/#34에서도 감춤**(조언가·관리자 경로는 불변) |

### 사용 도구

* Claude Code (VS Code Extension) + 서브에이전트 `security-reviewer`, `api-architect`

### 생성된 산출물

신규: `docs/adr/ADR-007-advice-version-counts-body-revisions.md`, `docs/reviews/05-spec002-subagent-review.md`.
수정: `advice/{services,serializers,views,tests}.py`, `CLAUDE.md`(§6.7·§16), `docs/api.md`(정정 8건 + 개정 이력), `docs/00-project/STATUS.md`.

### 검증 결과 (전부 실행 완료)

* 리뷰 대응 실패 테스트 12건 선작성 → 8건 실패 확인 → 수정 후 전부 통과
* `manage.py test` → **180/180 OK** (advice 118)
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed

### 잔여 리스크

1. **SPEC-001은 이 리뷰를 건너뛰고 머지됐다** — `update_advice`와 같은 "잠금 없는 read-modify-write"가 concerns 서비스(특히 `soft_delete_concern`)에도 있는지 별도 점검 필요. 리뷰 노트 §6-2에 기록.
2. **M4-8 선행 조건** — 역할 회수 시 `active_role` 강등이 없으면 회수된 조언가가 #29~#31을 계속 통과(STATUS.md §5에 미결로 등록).
3. **상태 전이 함수 규칙화 미적용** — "`atomic` + `select_for_update` + `update_fields`"를 `.claude/rules/coding.md`로 승격할지 미정.
4. 동시성 부하 테스트는 여전히 미수행 — M-1 수정도 단일 스레드 테스트로만 검증했다(결정적 재현이 가능한 형태로 작성했으나 실제 경합은 아님).

### 다음 단계 권장

1. PR #3 머지.
2. 잔여 리스크 1번(SPEC-001 동일 유형 점검)을 M4-7 착수 전에 처리.

---

## 2026-09-13 — SPEC-002/TASK-007: 마무리 — SPEC-002 종료 [위임]

### 작업

1. 브랜치 `feat/spec-002-advice-api`를 origin에 push(커밋 6개가 로컬에만 있던 상태 해소). PR은 규칙대로 SPEC 완료 후로 미룸.
2. **AC-1~AC-11을 실제 테스트 목록과 1:1 대조** → 미커버 6건 발견·보강(아래).
3. `docs/api.md` 정정 4건: #32/#33(초안 제외 규칙), #29(`submit` 토글은 version 미증가), #33(승인 시 concern 전이는 `ASSIGNED`에서만), #27(주체 판정 우선순위 + 비-APPROVED는 403). 상단 개정 이력에 2026-09-13 항목 추가.
4. `tasks.md` 전 항목 체크, `acceptance.md`에 종료 판정 절 추가, STATUS.md 갱신.
5. 4종 검증 — 전체 **168/168** 통과.

### AC 대조에서 발견한 미커버 6건 (전부 보강)

| # | 미커버였던 AC | 조치 |
| --- | --- | --- |
| 1 | **AC-11 전체** — §6.2 노출 6지점 전수 점검 자체가 없었음 | `PendingAdviceExposureSweepTests` 신설(6 테스트) |
| 2 | AC-2 DELETED 포함 미검증 | #31 목록을 5개 상태 전부로 확장 |
| 3 | AC-3 작성자 5개 상태 중 2개만 검증 | subTest 5종 추가 |
| 4 | AC-4 REJECTED 상태 수정 미검증 | 3개 상태 subTest 루프 |
| 5 | AC-7 REJECTED 재리뷰 미검증 | 2개 상태 subTest 루프 |
| 6 | AC-8 REVIEWING 미노출 미검증 | 4개 상태 전부로 확장 |

**중요한 관찰**: 6건 전부 *구현은 이미 옳았고 검증만 없던* 경우였다 — 보강한 테스트가 첫 실행에서 모두 통과했다. 즉 이 단계에서 잡은 것은 버그가 아니라 **증거의 공백**이다. 특히 AC-11은 §6.2가 두 앱 6곳에 흩어져 강제되는데, 각 지점의 단위 테스트는 있어도 *하나의 조언*에 대해 여섯 곳이 동시에 성립하는지는 아무도 확인하지 않고 있었다.

### 과정에서 있었던 오판 1건 (정정 기록)

AC 대조 중 `AdminAdviceListTests`의 테스트가 4개만 잡혀 "TASK-004에서 쓴 테스트 1개가 유실됐다"고 판단했으나, **오판이었다**. 실제로는 테스트 집계에 쓴 grep 파이프라인이 `Applying sessions.0001_initial...test_xxx`처럼 마이그레이션 출력과 붙어 나온 첫 줄을 놓친 것이었다. 코드에서 직접 세어 100개 전부 존재함을 확인했다. 교훈: 테스트 목록은 실행 로그 파싱이 아니라 소스에서 세는 편이 안전하다.

### 사용 도구

* Claude Code (VS Code Extension)

### 인간 결정 (Owner, 2026-09-13)

| 결정 | 내용 |
| --- | --- |
| push/PR 시점 | **push는 지금, PR은 TASK-007 후** — push는 백업이고 PR은 리뷰 요청이라 "하나의 SPEC = 하나의 PR" 규칙에 걸린다는 권고 승인 |

### 생성된 산출물

수정: `advice/tests.py`(보강 6건), `docs/api.md`(정정 4건 + 개정 이력), `specs/SPEC-002-advice-api/{tasks,acceptance}.md`, `docs/00-project/STATUS.md`.

### 검증 결과 (전부 실행 완료)

* `manage.py test advice` → **106/106 OK** / 전체 → **168/168 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed

### 잔여 리스크

1. **서브에이전트 리뷰 미실행** — SPEC-001 PR과 동일하게 `security-reviewer`·`api-architect`를 아직 돌리지 않았다. SPEC-002는 3주체 가시성·낙관적 잠금 등 보안 판단이 더 많으므로, SPEC-001 때보다 리뷰 가치가 크다.
2. **M4 전체 문서 부채 지속** — M4-1~M4-4 AIUSAGE 소급 기록, 리뷰 노트 2건, model.md drift 6건(STATUS.md §7).
3. **남은 모듈 2개**(M4-7 알림 3개, M4-8 역할 2개) — 둘 다 작아서 SPEC 하나로 묶을지 판단 필요.

### 다음 단계 권장

1. PR 생성 → (선택) 서브에이전트 리뷰 → 머지.
2. 이후 M4-7·M4-8을 하나의 SPEC-003으로 묶어 진행 검토.

---

## 2026-09-12 — SPEC-002/TASK-006: admin 피드백 3종 (api.md #36·#37·#38) — M4-6 구현 완료 [위임]

### 작업

1. `advice/tests.py`에 `AdminFeedbackListTests`·`AdminFeedbackDetailTests`·`AdminFeedbackTransitionTests` 18케이스를 먼저 작성(권한 401/403, `status`/`score_min`/`score_max` 필터, 잘못된 점수 필터 400, 관리자 전용 필드(`memo`·`author_nickname`) 노출, SUBMITTED→REVIEWED→ARCHIVED 정상 전이, 역방향·건너뛰기·동일 상태 409, memo 저장, 잘못된 status 400, 404) → 실행해 16개 실패 확인.
2. 최소 구현: `advice/services.py`에 `_ALLOWED_FEEDBACK_TRANSITIONS` 표 + `list_feedbacks_for_admin()`/`get_feedback_for_admin()`/`transition_feedback()`. 시리얼라이저 5종, 뷰 2종(#37·#38은 같은 경로라 한 클래스), URL 2개.
3. 쿼리 수는 이번에도 **먼저 실측**(3쿼리: IsAdmin 확인 + COUNT + 페이지, `select_related` 조인 덕에 행 수와 무관) 후 고정 → 한 번에 통과. 2회 연속 성공.
4. 4종 검증 — 전체 **162/162** 통과.
5. 시각 확인: 피드백 목록 → 건너뛰기 전이 409 → 정상 전이 후 상세에 `memo`·`reviewed_by`·`reviewed_at` 기록 확인, 스크린샷 3장.

### 사용 도구

* Claude Code (VS Code Extension)

### 인간 결정 (Owner, 2026-09-12)

TASK-006 진행 승인.

### 판단 기록 (AI가 정한 것, 이견 시 저렴하게 수정 가능)

* **`reviewed_by`/`reviewed_at`은 REVIEWED로 들어갈 때만 기록**하고, ARCHIVED로 넘어갈 때는 건드리지 않는다. 필드 이름이 "review" 사건을 가리키므로, 나중에 다른 관리자가 보관 처리했다고 해서 "누가 실제로 검토했는가"를 덮어쓰면 감사 정보가 사라진다. (api.md #38은 이 지점을 명시하지 않음)
* **동일 상태로의 전이도 409**로 막았다 — 전이표에 self-edge를 두지 않는 방식(advisors 앱의 신청 전이표와 동일한 형태).

### 생성된 산출물

수정: `advice/{services,serializers,views,urls,tests}.py`, `docs/00-project/STATUS.md`.

### 검증 결과 (전부 실행 완료)

* 해당 3클래스 → 구현 전 16 fail → 구현 후 **19/19 OK**(쿼리 고정 테스트 포함)
* `manage.py test` (전체) → **162/162 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 시각 확인: 스크린샷 3장 Owner 전송

### 잔여 리스크

1. **M4-6 코드는 끝났지만 SPEC-002는 미완** — TASK-007(AC-1~AC-11 전항 재검증, 특히 §6.2 노출 6지점 전수 점검 + api.md 문구 정정 4건)이 남아 있다. SPEC-001 때 이 마무리 단계에서 미커버 AC 2건이 나왔으므로 생략하지 않는다.
2. **피드백에 알림이 없다**(api.md #38 "알림 없음") — 조언가는 자기 조언이 어떤 평가를 받았는지 API로 알 수 없다. 의도된 Phase 2 범위지만, 실사용 시 조언가 경험의 빈 구멍이 될 수 있어 기록해 둔다.

### 다음 단계 권장

1. Owner 확인 후 TASK-007(SPEC-002 마무리 + PR) 착수.

---

## 2026-09-12 — SPEC-002/TASK-005: 받은 조언함 + 피드백 (api.md #26·#34·#35) [위임]

### 작업

1. `advice/tests.py`에 `ReceivedAdviceListTests`·`FeedbackCreateTests`·`MyFeedbackListTests` 총 16케이스를 먼저 작성(승인된 것만 노출·타인 고민 미노출·REJECTED/DELETED 미노출, `is_feedback_submitted` 정확도, 활동명 사용, keyword/날짜 필터, 피드백 403/409/400/404, 내 피드백만) → 실행해 15개 실패 확인.
2. 최소 구현: `advice/services.py`에 `list_received_advices()`(§6.2 노출 규칙을 필터 한 쌍으로 집약 + `Exists` annotate) / `create_feedback()` / `list_feedbacks_written_by()`. 시리얼라이저 5종, 뷰 3종, URL 3개 추가.
3. **쿼리 수 기대값을 이번엔 먼저 실측**(TASK-004 잔여 리스크 #2의 개선안 실행): 임시 스크립트로 `CaptureQueriesContext`를 돌려 #26=3쿼리(COUNT+페이지+활동명 벌크), #35=2쿼리임을 확인한 뒤 그 값으로 `assertNumQueries` 테스트 2종을 추가 → **한 번에 통과**(직전 3회 연속 있었던 기대값 오차 재발 없음).
4. 4종 검증 — 전체 143/143 통과.
5. 시각 확인: 역할 조회로 오염 없음 확인(`owner roles: []`) 후, 받은 조언함 → 피드백 작성 201 → 중복 409 → 받은 조언함 재조회 시 `is_feedback_submitted: true`로 전환 → 내 피드백 목록까지 스크린샷 5장.

### 사용 도구

* Claude Code (VS Code Extension)

### 인간 결정 (Owner, 2026-09-12)

TASK-005 진행 승인.

### 생성된 산출물

수정: `advice/{services,serializers,views,urls,tests}.py`, `docs/00-project/STATUS.md`.

### 검증 결과 (전부 실행 완료)

* `manage.py test` (해당 3클래스) → 구현 전 15 fail → 구현 후 **18/18 OK**
* `manage.py test` (전체) → **143/143 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 실측 쿼리 수: #26 = 3, #35 = 2 (행 수와 무관하게 고정)
* 시각 확인: 스크린샷 5장 Owner 전송

### 잔여 리스크

1. **`advisor_display_name` 벌크 조회 패턴이 이제 3곳에 존재**(`concerns.services.approved_advices_view_data`, `advice` #27 단건 mixin, #26 목록 context 주입). 규칙 자체는 한 함수(`display_names_by_advisor`)에 있으나 호출 방식이 제각각 — TASK-007에서 한 번 훑어보고 정리 여부 판단 권고.
2. **피드백 수정/삭제 API 부재는 의도된 것**(api.md #34 "제출 후 수정/삭제 불가") — 오타 신고 같은 실사용 요구가 생기면 Phase 3 논의 대상.

### 다음 단계 권장

1. Owner 확인 후 TASK-006(#36·#37·#38 admin 피드백 3종) 착수 — SPEC-002 구현의 마지막 구간.

---

## 2026-09-11 — SPEC-002/TASK-004: admin 리뷰 목록+승인/반려 (api.md #32·#33) [위임]

### 작업

1. `advice/tests.py`에 `AdminAdviceListTests`(4) + `AdviceReviewTests`(13) 총 17케이스 추가(초안 항상 제외, 승인 시 상태+concern 전이+알림, 반려 시 알림+concern 불변, 사유 없는 반려 422, 버전 불일치 412, 이미 종결된 advice/초안 리뷰 409, CLOSED/ANSWERED concern 불변, 실패 시 부분 상태 없음) → 실행해 14개 실패 확인.
2. 최소 구현: `common/exceptions.py`에 **`PreconditionFailed`(412) 신규 추가** — 이 프로젝트 첫 낙관적 잠금 예외(409와 구분: "요청 자체는 멀쩡한데 읽은 시점 이후 바뀌었다"). `advice/services.py`에 `list_advices_for_admin_review()`(초안 무조건 제외) + `review_advice()`(advice·concern 모두 `select_for_update()`, 404→409(초안/상태)→412(버전)→422(반려사유) 순서로 검사 후 상태 전이+알림을 한 트랜잭션에). `AdminAdviceListSerializer`·`AdviceReviewSerializer` + 뷰 2종 + URL 2개 추가.
3. 4종 검증 — 도중 `assertNumQueries` 기대값을 2로 예상했다가 `IsAdmin`이 관리자 확인용 쿼리 1개를 추가로 쓴다는 걸 실측하고 3으로 정정(TASK-003 이전에도 concerns 앱에서 동일 패턴 발생 — 이제 반복되는 실수임을 인지).
4. 시각 확인: **역할을 미리 조회·출력**하는 절차를 다시 적용해(`admin roles: ['ADMIN']`, `advisor roles: ['ADVISOR']`) 오염 없는 계정 확인 후 진행. 리뷰 대기열 → 버전 불일치 412 → 정상 승인 200(`concern_status: "ANSWERED"` 응답 포함) 스크린샷 3장 + DB로 `ADVICE_APPROVED` 알림 row 직접 확인.

### 사용 도구

* Claude Code (VS Code Extension)

### 인간 결정 (Owner, 2026-09-11)

TASK-004 진행 승인. (겸하여: 낙관적 잠금 개념 설명 요청에 답변, PR 시점은 SPEC-002 TASK-007 완료 후로 권고·확인)

### 생성된 산출물

수정: `common/exceptions.py`(`PreconditionFailed` 추가), `advice/{services,serializers,views,urls,tests}.py`, `docs/00-project/STATUS.md`.

### 검증 결과 (전부 실행 완료)

* `manage.py test advice.tests.AdminAdviceListTests advice.tests.AdviceReviewTests` → 구현 전 14 fail → 구현 후 **17/17 OK** (도중 쿼리 수 기대값 1건 보정)
* `manage.py test` (전체) → **125/125 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 시각 확인: 대기열 200 / 412(stale version) / 승인 200(concern_status=ANSWERED) 스크린샷 3장 + `Notification(type=ADVICE_APPROVED, recipient=고민 작성자)` DB 직접 확인

### 잔여 리스크

1. **동시성은 코드로만 방어, 부하 테스트 미수행** — SPEC-001 TASK-005와 동일한 한계. `select_for_update()`의 실제 경합 동작 검증은 Phase 2 스코프 밖.
2. **`assertNumQueries` 기대값을 매번 한 번 틀리고 보정하는 패턴이 3회째 반복**(concerns 앱 TASK-004, 여기)됨 — 원인은 매번 다른 permission 클래스가 DB 쿼리를 쓰는지 여부(`IsAdmin`은 쓰고 `IsActiveAdvisor`는 안 씀)를 사전에 확인하지 않고 추정한 것. TASK-005부터는 구현 직후 실제 쿼리 로그를 먼저 찍어보고 기대값을 정하는 순서로 바꾸는 것을 권고.

### 다음 단계 권장

1. Owner 확인 후 TASK-005(#26 받은 조언 목록 + #34·#35 피드백 작성/내 목록) 착수.

---

## 2026-09-11 — SPEC-002/TASK-003: 조언 수정+삭제 (api.md #29·#30) [위임]

### 작업

1. `advice/tests.py`에 `AdviceUpdateTests`(10) + `AdviceDeleteTests`(7) 총 17케이스 추가(본문 수정 시 version+히스토리, `submit` 단독 토글은 무변화, REVIEWING 허용, APPROVED/DELETED 409, 타인 403, 없는 advice 404, 삭제 204+상태전이, 삭제 후 재작성 가능(엔드포인트 경유)) → 실행해 15개 실패 확인(PATCH/DELETE 라우트 없음 → 405/404 혼재).
2. 최소 구현: `advice/services.py`에 `_get_own_editable_advice()`(조회+소유권 403+편집가능상태 409 공용 검사) / `update_advice()`(본문 변경 시에만 `AdviceHistory` 스냅샷 + `version` 증가, `transaction.atomic`) / `delete_advice()`. `advice/serializers.py`에 `AdviceUpdateSerializer`(`submit`→`is_submitted` source 매핑) + `AdviceUpdateResultSerializer`. `AdviceDetailView`에 `patch`/`delete` 추가, `get_permissions()`로 GET은 `IsAuthenticated`만·PATCH/DELETE는 `IsActiveAdvisor` 추가.
3. 4종 검증 — 전체 108/108 통과.
4. 시각 확인: **TASK-002의 계정 오염 교훈을 반영**해, 사용 전 역할을 명시적으로 조회·출력(`roles held: ['ADVISOR']`, `is_superuser: False`)한 신규 계정으로 재현. 본문 수정 → `version` 2 스크린샷, 삭제 → `status=DELETED` 스크린샷, 그리고 `AdviceHistory` row를 DB에서 직접 조회해 수정 **전** 본문이 정확히 `version=1`로 스냅샷됐음을 확인.

### 사용 도구

* Claude Code (VS Code Extension)

### 인간 결정 (Owner, 2026-09-11)

TASK-003 진행 승인.

### 생성된 산출물

수정: `advice/{services,serializers,views,tests}.py`, `docs/00-project/STATUS.md`.

### 검증 결과 (전부 실행 완료)

* `manage.py test advice.tests.AdviceUpdateTests advice.tests.AdviceDeleteTests` → 구현 전 15 fail → 구현 후 **17/17 OK**
* `manage.py test` (전체) → **108/108 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 시각 확인: PATCH 200(version 2) / DELETE 204 / 재조회 시 status=DELETED, `AdviceHistory.directional_guidance`가 수정 전 문구와 일치함을 DB에서 직접 확인 — 스크린샷 2장 Owner 전송

### 잔여 리스크

1. **없음 (이번 TASK 한정)** — TASK-002의 계정 오염 교훈을 실제로 적용해 재발 방지.
2. TASK-004(리뷰 승인/반려)부터는 `AdviceHistory`가 아니라 `Notification`·`Concern.status`가 얽히므로, 여기서 검증한 "본문 변경 여부로 트리거 분기" 패턴이 그대로 재사용되지는 않음 — 별도 판정 로직 필요.

### 다음 단계 권장

1. Owner 확인 후 TASK-004(#32 admin 리뷰 목록 + #33 승인/반려, 낙관적 잠금 412 최초 도입) 착수.

---

## 2026-09-11 — SPEC-002/TASK-002: 조언 상세 3주체 분기 (api.md #27) [위임]

### 작업

1. `advice/tests.py`에 `AdviceDetailTests` 11케이스 추가(작성자 전상태 200+`reject_reason`, 고민 작성자 APPROVED만 200/`reject_reason` 없음, 고민 작성자 PENDING·REJECTED 403, ADMIN 전상태 200, 무관 사용자·조언가 403, 없는 advice 404, advisor 신원 최소 노출) → 실행해 10개 실패 확인.
2. 최소 구현: `advice/services.py`에 `get_visible_advice()` — (작성자 → 관리자 → 고민 작성자+APPROVED) 우선순위 판정, 그 외 403. `_is_admin()` 헬퍼는 `common.permissions.IsAdmin`과 동일 로직을 의도적으로 별도 구현(객체 수준 판정과 DRF permission 클래스의 시그니처가 안 맞아 억지로 묶지 않음, 코드 주석에 사유 명시). `advice/serializers.py`에 `AdviceDetailSerializer`(고민 작성자용) + 상속받은 `AdviceDetailWithReasonSerializer`(작성자/관리자용, `reject_reason` 추가) — 필드 목록 중복을 상속으로 제거. `AdviceDetailView` + URL 1개 추가.
3. 4종 검증 — 전체 91/91 통과.
4. 시각 확인 중 **데모 계정 재사용 문제를 발견·정정**(아래).

### 데모 재현 중 발견한 것 (버그 아님, 데모 설계 실수)

첫 스크린샷 시도에서 `demo@example.com`(고민 작성자)이 심사중(PENDING) 조언을 열람했는데 403이 아니라 200이 나왔다. 원인은 코드가 아니라 데모 계정: `demo`는 **TASK-004에서 이미 ADMIN 역할을 부여받은 채로 영구 보존된 계정**이었다. `get_visible_advice()`의 판정 순서가 (작성자→관리자→고민 작성자) 이므로, admin이기도 한 고민 작성자는 관리자 시야로 응답받는다 — 이것 자체는 설계대로다. 다만 "순수 고민 작성자"를 보여주려던 데모가 실은 "관리자"를 보여주고 있었던 것. `plain.owner@example.com`(어떤 역할도 없는 신규 계정)을 새로 만들어 재현해 올바른 스크린샷 3장을 얻었다.

**교훈**: Docker Compose를 세션 간 재사용하면서 데모 계정에 역할을 누적 부여해 왔다(`demo`는 이제 ADVISOR는 아니지만 ADMIN). 앞으로 권한 분기를 시각 확인할 때는 매번 신선한 계정을 만들거나, 계정별 역할을 먼저 조회해 전제를 확인해야 한다.

### 사용 도구

* Claude Code (VS Code Extension)

### 인간 결정 (Owner, 2026-09-11)

TASK-002 진행 승인.

### 생성된 산출물

수정: `advice/{services,serializers,views,urls,tests}.py`, `docs/00-project/STATUS.md`.

### 검증 결과 (전부 실행 완료)

* `manage.py test advice.tests.AdviceDetailTests` → 구현 전 10 fail → 구현 후 **11/11 OK**
* `manage.py test` (전체) → **91/91 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 시각 확인(정정 후, 권한 없는 신규 계정 기준): 승인된 조언 200(`reject_reason` 필드 자체 없음) / 심사중 조언 403 / 작성자 본인은 심사중 조언도 200(`is_submitted`·`reject_reason` 노출) — 스크린샷 3장 Owner 전송

### 잔여 리스크

1. **판정 우선순위(작성자>관리자>고민 작성자)가 명시적 결정이 아니라 구현 중 자연스럽게 정해짐** — 세 조건이 동시에 참인 경우(예: 관리자가 자기 자신에게 조언을 배정하는 기형적 케이스)는 스펙에 없다. Phase 2 실사용에서 발생 가능성은 낮으나 기록해 둔다.
2. **개발용 Docker 컨테이너의 역할 오염** — `demo` 계정은 이제 ADMIN을 보유해 "평범한 사용자" 데모에 더 이상 적합하지 않다. 다음 세션에서 역할별 데모 계정을 명확히 분리(예: `owner.demo@`, `admin.demo@`, `advisor.demo@`)하는 것을 권고.

### 다음 단계 권장

1. Owner 확인 후 TASK-003(#29 조언 수정 + #30 삭제) 착수.

---

## 2026-09-10 — SPEC-001/TASK-006: 마무리 — SPEC-001 종료 [위임]

### 작업

1. **#20 `status` 필터 구현** — Owner 승인안(concern.status 기준)대로 실패 테스트 작성 → 구현 → 통과.
2. **api.md 문구 정정 2건**: (a) #20의 "(assignment 상태)"를 "(concern 상태 — SUBMITTED/ASSIGNED/ANSWERED/CLOSED)"로 교체. (b) #16·#18·#19·#24의 상태 서술에서 `is_deleted=true/false`를 실제 저장 컬럼 `deleted_at`으로 교체(#22의 **응답 필드** `is_deleted`는 C-1 규약대로 유지). 문서 상단에 2026-09-10 개정 이력 추가(기존 관례 준수).
3. **AC 전항 재검증** — acceptance.md의 AC-1~AC-10을 테스트 62개와 1:1 대조. **미커버 2건을 발견해 보강**(아래).
4. SPEC 문서 종료 처리: `tasks.md` 전 항목 체크, `acceptance.md`에 종료 판정 절 추가(실행 출력 포함), STATUS.md의 미결 항목 2건을 "종결됨"으로 전환.

### AC 대조에서 발견한 미커버 2건 (이번에 보강)

| # | 미커버였던 AC | 조치 |
| --- | --- | --- |
| 1 | AC-4 "연결된 Advice/**Assignment** 보존" — Advice만 검증하고 있었음 | 기존 테스트에 Assignment 보존 단언 추가 |
| 2 | TEST_CRITERIA §3 "**목록** API N+1 없음(assertNumQueries)" — 상세(#23)에만 있었음 | `test_list_query_count_is_bounded` 추가 — #20에 배정 6건이 있어도 쿼리 **2개 고정** 실증 |

두 번째 항목이 특히 의미가 있다: 목록 API의 N+1은 "구현할 때 신경 썼다"는 주장만 있었고 **판정 장치가 없었다**. 이제 쿼리 수가 상수로 고정돼 있어, 이후 누군가 `select_related`/`Subquery`를 걷어내면 테스트가 즉시 깨진다.

### 사용 도구

* Claude Code (VS Code Extension)

### 인간 결정 (Owner, 2026-09-10)

| 결정 | 내용 |
| --- | --- |
| 진행 순서 | M4-6 착수보다 **TASK-006 마무리 → PR → 그다음 M4-6** 순서 채택(브랜치에 미머지 커밋이 쌓인 상태에서 13개짜리 모듈을 얹지 않는다) |

### 생성된 산출물

수정: `concerns/{views,tests}.py`, `docs/api.md`, `docs/00-project/STATUS.md`, `specs/SPEC-001-concerns-api/{tasks,acceptance}.md`.

### 검증 결과 (전부 실행 완료)

* `manage.py test` → **62/62 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* AC-1~AC-10 전항 통과 (acceptance.md 종료 판정 절에 실행 출력 첨부)

### 잔여 리스크

1. **SPEC-001은 종료됐지만 M4 전체 문서 부채는 남음** — M4-1~M4-4 AIUSAGE 소급 기록, 리뷰 노트 2건, model.md drift 6건(STATUS.md §7).
2. **코드 리뷰 미수행** — 서브에이전트(`security-reviewer`, `api-architect`) 리뷰는 PR 단계에서 수행 예정.
3. **M4-6은 SPEC-002를 먼저 작성한 뒤 착수 권장** — advice는 §6.2 노출 규칙 + 버전 관리 + AdviceHistory 스냅샷이 얽힌 이 서비스의 핵심 도메인.

### 다음 단계 권장

1. PR 생성 → 리뷰 → main 머지.
2. SPEC-002 작성 후 M4-6 착수.

---

## 2026-09-10 — SPEC-001/TASK-005: 배정 생성+해제 (api.md #24·#25) — M4-5 완료 [위임]

### 작업

프롬프트 3 루프로 SPEC-001의 TASK-005 구현. SPEC-001에서 상태 전이·부수효과가 함께 걸리는 유일한 구간:

1. `concerns/tests.py`에 `AssignmentTests` 18케이스 추가(권한 401/403, SUBMITTED→ASSIGNED 전이+알림, 2번째 advisor 배정 시 상태 유지, 중복 활성 배정 409, 해제 후 재배정 허용(부분 유니크), CLOSED/삭제 concern 409, 비-advisor 422, 실패 시 부분 상태 없음, 마지막 해제 시 SUBMITTED 복귀, 잔여 배정 있으면 유지, ANSWERED는 되돌리지 않음, 이미 해제 409, 타 concern의 assignment 404) → 실행해 14개 실패 확인.
2. 최소 구현: `concerns/services.py`에 `assign_advisor`/`unassign_advisor` 추가 — 둘 다 `with transaction.atomic()` 안에서 concern row를 `select_for_update()`로 잠그고(동시 배정/해제 직렬화) Assignment 생성·상태 전이·알림 생성을 함께 수행. `AssignmentCreateSerializer`/`AssignmentCreateResultSerializer`, `AdminAssignmentCreateView`/`AdminAssignmentDetailView`, URL 2개 추가.
3. 4종 검증 — **전체 60/60** 통과.
4. 시각 확인: Playwright로 배정 전(SUBMITTED) → 배정 201(`concern_status: ASSIGNED`) → **조언가 계정으로 로그인해 본인 큐(#20)에 실제로 뜨는 것 확인** → 해제 후 SUBMITTED 복귀(배정 행은 `is_active=false` 보존) 스크린샷 4장 전송. 컨테이너 shell로 `Notification` row(type=ASSIGNMENT_CREATED, recipient=조언가, target_url, payload) 실측.

### 사용 도구

* Claude Code (VS Code Extension) / Playwright(1.48, 데모 전용 임시 설치)

### 인간 결정 (Owner, 2026-09-10)

| 결정 | 내용 |
| --- | --- |
| 학습 세션 | **종료** — 이해 확인 질문·퀴즈 없이 구현만 진행 |
| TASK-005 | 진행 승인 |

### 판단 기록 (AI가 정한 것)

* **비-advisor 지정은 422**(400/404 아님) — 형식은 맞으나 값이 부적합한 경우(api.md §1.8). 대상 사용자가 없는 경우와 advisor가 아닌 경우를 **같은 응답**으로 통일해, admin 도구가 사용자 존재 여부를 알아내는 수단이 되지 않게 했다.
* **`select_for_update()` 도입** — 배정/해제는 `concern.status`에 대한 read-modify-write라, 두 관리자가 동시에 마지막 배정을 해제하면 상태가 되돌아가지 않는 경합이 가능하다. CLAUDE.md §4가 허용한 범위 내에서 concern row를 잠가 직렬화.
* **ANSWERED 고민은 배정 전부 해제해도 SUBMITTED로 되돌리지 않음** — §6.6의 되돌림 규칙은 ASSIGNED에만 적용된다. 승인된 조언이 이미 붙은 고민을 "미배정"으로 표시하면 사실과 어긋난다.

### 생성된 산출물

수정: `concerns/{services,serializers,views,urls,tests}.py`, `docs/00-project/STATUS.md`.

### 검증 결과 (전부 실행 완료)

* `manage.py test concerns.tests.AssignmentTests` → 구현 전 14 fail → 구현 후 **18/18 OK**
* `manage.py test` (전체) → **60/60 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 실환경 실측: 상태 SUBMITTED→ASSIGNED→SUBMITTED 왕복, `Notification` row 1건 생성(ASSIGNMENT_CREATED, 수신자=배정된 조언가), 조언가 큐(#20)에 반영 — 스크린샷 4장 Owner 전송

### 잔여 리스크

1. **동시성은 코드로만 방어, 부하 테스트 미수행** — `select_for_update()`의 실제 경합 동작은 Phase 2 스코프 밖(테스트는 단일 스레드).
2. **알림 `target_url`이 API 경로 형태** — C-10 결정상 "프론트 라우트 키"가 되어야 하나 프론트가 없어 잠정적으로 API 경로를 넣었다(기존 advisors 승인 알림과 동일 관행). 프론트 착수 시 일괄 정정 필요.
3. **M4-5 완료 = SPEC-001의 코드 부분 완료**. 남은 TASK-006(문서 정정 2건 + #20 status 필터 구현 + 전체 AC 재실행)은 미착수.

### 다음 단계 권장

1. TASK-006(SPEC-001 마무리) 또는 곧바로 M4-6(advice+feedback, #26~38) 착수 — Owner 선택.

---

## 2026-09-10 — SPEC-001/TASK-004: admin 고민 목록+상세 (api.md #22·#23) [위임]

### 작업

프롬프트 3 루프로 SPEC-001의 TASK-004만 구현:

1. `concerns/tests.py`에 `AdminConcernTests` 12케이스 추가(권한 401/403, `include_deleted` 기본/명시, `status`·`keyword` 필터, `assignment_count`(비활성 제외), soft-deleted 상세 조회, assignments·advices 전량 노출, `assertNumQueries`로 N+1 부재) → 실행해 11개 실패 확인.
2. 최소 구현: `concerns/services.py`에 `display_names_by_advisor`(TASK-002의 벌크 조회를 재사용 가능한 헬퍼로 추출) / `list_concerns_for_admin` / `get_concern_for_admin` / `admin_concern_detail_view_data` 추가. `AdminConcernListSerializer` 추가. `AdminConcernListView`·`AdminConcernDetailView` + URL 2개 추가.
3. 4종 검증 실행 — 전체 concerns 42/42 통과.
4. 시각 확인: demo 계정에 ADMIN 역할 부여 + 삭제된 고민 fixture 생성 후 Playwright로 기본 목록/`include_deleted=true`/상세 스크린샷 3장 전송.

### 사용 도구

* Claude Code (VS Code Extension) / Playwright(1.48, 데모 전용 임시 설치)

### 인간 결정 (Owner, 2026-09-10)

| 결정 | 내용 |
| --- | --- |
| 모순 해결 | api.md #20의 `status?` 쿼리 파라미터를 **`concern.status` 필터로 재해석**(후보 B) 승인. 구현·api.md 문구 정정은 TASK-006에서 일괄 반영하도록 tasks.md에 명시 |
| TASK-004 | 진행 승인 |

### 판단 기록 (AI가 정한 것, 이견 시 저비용 수정 가능)

* `assignment_count`는 **활성 배정만** 집계(비활성 이력 제외) — 운영자가 "지금 몇 명이 붙어 있나"를 보는 숫자가 더 유용하다고 판단. 비활성 이력은 #23 상세에서 `is_active=false`로 전량 확인 가능.
* #23은 **soft-deleted concern도 200으로 조회**되게 구현 — #22의 `include_deleted=true`가 노출한 행이 상세에서 404가 되면 모순이므로.
* `assertNumQueries` 기대값은 처음 6으로 잡았다가 실측 5로 정정(`force_authenticate`가 세션 조회를 건너뜀). AC("쿼리 수 고정")는 그대로이며 상수만 실측값으로 맞춘 것.

### 생성된 산출물

수정: `concerns/{services,serializers,views,urls,tests}.py`, `docs/00-project/STATUS.md`, `specs/SPEC-001-concerns-api/tasks.md`(TASK-006에 #20 필터 항목 추가).

### 검증 결과 (전부 실행 완료)

* `manage.py test concerns.tests.AdminConcernTests` → 구현 전 11 fail → 구현 후 **12/12 OK**
* `manage.py test concerns` (전체) → **42/42 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed(E501 1건 즉시 수정)
* 시각 확인: admin 목록(기본/include_deleted)/상세 스크린샷 3장 Owner에게 전송

### 잔여 리스크

1. **`keyword` 필터는 `concern_summary`만 대상** — `decision_context` 본문 검색은 미포함(api.md가 대상 범위를 명시하지 않음). 실사용 시 범위 확장 필요할 수 있음.
2. **admin 목록에 본문(decision_context) 미노출** — 의도적(§8 목록 응답 최소화). 상세(#23)에서만 노출.
3. TASK-005는 상태 전이 + 알림 부수효과가 함께 걸리는 구간이라 `@transaction.atomic` 적용이 필수 — M2 학습 부채 ⑤(atomic)와 직결되므로 구현 후 이해 확인 권장.

### 다음 단계 권장

1. Owner 확인 후 TASK-005(#24 배정 생성 + #25 해제) 착수.

---

## 2026-09-10 — SPEC-001/TASK-003: advisor 배정 목록+상세 (api.md #20·#21) [위임]

### 작업

프롬프트 3 루프로 SPEC-001의 TASK-003만 구현:

1. `concerns/tests.py`에 `AssignedConcernTests` 14케이스 추가(role 게이트 401/403 3종, 목록 스코핑, `advice_status` 반영, 배정 안 됨/미존재/`requester_display_name` 3분기/이메일·user_id 미노출/`my_advice` 유무 등) → 실행해 7 fail + 6 error 확인(라우트 없음).
2. 최소 구현: `common/permissions.py`에 `IsActiveAdvisor`(active_role=ADVISOR 게이트, `IsAdmin`과 동일한 지연 import 패턴) 신설. `concerns/services.py`에 `list_assigned_concerns`(advisor 본인 활성 배정 + 본인 advice_status를 상관 서브쿼리로 annotate, N+1 없음) / `get_assigned_concern`(미존재 404, 미배정 403 — `django.core.exceptions.PermissionDenied`를 DRF가 자동 403 변환) / `requester_display_name` / `my_advice_view_data` / `assigned_concern_detail_view_data` 추가. `concerns/serializers.py`에 `AssignedConcernListSerializer`(plain Serializer — Assignment+Concern 혼합 소스) 추가. `concerns/views.py`에 `AssignedConcernListView`/`AssignedConcernDetailView` 추가. `concerns/urls.py`에 `/assigned-concerns`, `/assigned-concerns/<uuid:concern_id>` 추가.
3. 4종 검증 실행 — 테스트 14/14 한 번에 통과(구현 재시도 없음), 전체 concerns 30/30, check/migrations/ruff 전부 통과.
4. 시각 확인: `docker compose exec app python manage.py shell`로 advisor 계정+배정 fixture 생성 → Playwright로 advisor 로그인 → 배정 목록(#20) → 배정 상세(#21, `requester_display_name`="익명의 요청자", `my_advice`=null) → 존재하지 않는 concern-id 조회 시 404까지 스크린샷 3장 전송.

### 사용 도구

* Claude Code (VS Code Extension)
* Playwright(1.48, npx 임시 설치 — 데모 전용, 저장소 의존성 아님)

### 인간 결정 (Owner, 2026-09-10)

TASK-001에서 승인된 방식(테스트 + Mock-up 시각 확인)을 동일 적용 — 이번 턴은 TASK-003 진행 승인만.

### 발견한 문서 모순 (신규 1건, Owner 결정 대기)

api.md #20의 쿼리 파라미터 `status?`가 "(assignment 상태)"라고 되어 있으나, `Assignment` 모델(model.md §3.7, concerns/models.py)에는 상태 enum이 없고 `is_active`(bool)만 존재한다. tasks.md TASK-003 체크리스트에 이 필터에 대한 테스트가 없어 **구현하지 않고 미해결로 남김**(파라미터는 받되 무시) — STATUS.md §5에 후보안 3가지와 함께 기록.

### 생성된 산출물

수정: `common/permissions.py`(`IsActiveAdvisor` 추가), `concerns/{services,serializers,views,urls,tests}.py`(각 확장).

### 검증 결과 (전부 실행 완료)

* `manage.py test concerns.tests.AssignedConcernTests` → 구현 전 7 fail + 6 error → 구현 후 **14/14 OK**(재시도 없이 1차 구현으로 전부 통과)
* `manage.py test concerns` (전체) → **30/30 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 시각 확인: 배정 목록/상세/404 스크린샷 3장 Owner에게 전송

### 잔여 리스크

1. **api.md #20 `status?` 쿼리 필터 미구현** (위 모순 참조) — Owner 결정 후 TASK-006(SPEC-001 마무리)에서 일괄 반영 권장.
2. **`#21`의 403 vs 404 정책이 `#18`과 다름**(존재 자체를 숨기지 않음)을 코드 주석으로 명시했으나, 이 비대칭성 자체가 향후 보안 리뷰(security-reviewer) 대상으로 재확인 필요.
3. plan.md가 제안했던 `IsAssignedAdvisor`(객체 수준 배정 확인까지 포함한 단일 permission 클래스) 대신, role 게이트만 permission 클래스(`IsActiveAdvisor`)로 분리하고 배정 여부(403)는 서비스 함수 안에서 직접 판정하도록 설계를 변경했다 — 404/403 구분을 명확히 제어하기 위함(plan.md 대비 구현상 조정, 기능은 AC와 100% 일치).

### 다음 단계 권장

1. Owner 확인 후 TASK-004(#22 admin 전체 목록 + #23 admin 상세) 착수.

---

## 2026-09-10 — SPEC-001/TASK-002: concern 상세+소프트 삭제 (api.md #18·#19) [위임]

### 작업

프롬프트 3 루프로 SPEC-001의 TASK-002만 구현:

1. `concerns/tests.py`에 `ConcernDetailDeleteTests` 8케이스 추가(상세 APPROVED-only 노출, soft-delete/타인 자원 404, 삭제 204+자식 row 보존, 재삭제 409, 비로그인 401) → 실행해 5개 실패(라우트 없음) 확인.
2. 최소 구현: `concerns/services.py`에 `get_own_concern`(soft-deleted 제외 404) / `get_own_concern_including_deleted`(삭제 판정용) / `soft_delete_concern`(409 가드) / `approved_advices_view_data`(APPROVED만, N+1 없이 advisor_display_name 벌크 조회 — advisor의 최신 APPROVED `AdvisorApplication.display_name`, 없으면 `nickname` 폴백) 추가. `concerns/serializers.py`에 `ConcernDetailSerializer` 추가. `concerns/views.py`에 `ConcernDetailView`(GET/DELETE) 추가. `concerns/urls.py`에 `<uuid:concern_id>` 경로 추가.
3. 4종 검증 실행 — 전부 통과(테스트 16/16).
4. Owner 요청에 따른 시각 확인 지속: 앱 재빌드 후 Playwright로 (a) 상세 조회 화면(approved_advices 포함) (b) 삭제 버튼→확인 모달→204 (c) 재조회 시 404(우리 커스텀 에러 포맷 `{error:{code,message}}` 노출까지 확인) 스크린샷 3장 전송.

### 사용 도구

* Claude Code (VS Code Extension)
* Playwright(1.48, npx 임시 설치 — TASK-001과 동일하게 데모 전용, 저장소 의존성 아님)

### 인간 결정 (Owner, 2026-09-10)

TASK-001에서 승인된 방식(테스트 + Mock-up 시각 확인)을 동일하게 적용 — 이번 턴은 TASK-002 진행 승인만.

### 생성된 산출물

수정: `concerns/{services,serializers,views,urls,tests}.py`(각 확장).

### 검증 결과 (전부 실행 완료)

* `manage.py test concerns` → 구현 전 5 fail(3케이스는 라우트 부재로 우연히 404 일치) → 1차 구현 후 15/16(advice_id가 UUID 객체로 직렬화되어 문자열 비교 실패) → `str()` 캐스팅 수정 후 **16/16 OK**
* `manage.py check` → 0 issues / `makemigrations --check` → No changes / `ruff check` → All checks passed
* 시각 확인: 상세/삭제/재조회 스크린샷 3장 Owner에게 전송

### 잔여 리스크

1. **`advisor_display_name` 폴백 로직 미검증 상태(코드 리뷰 대상)**: 한 advisor가 여러 APPROVED 신청 이력을 가질 수 있는 실제 케이스는 Phase 2 도메인 규칙상 발생하지 않아야 하지만(승인 후 재신청 경로 없음), 서비스 함수는 `-submitted_at` 최신 것을 택하도록만 방어했다.
2. **TASK-003(#20·#21)부터 `active_role=ADVISOR` 게이트 등장** — accounts 모듈의 `active_role` 검사 패턴을 그대로 재사용할 예정.

### 다음 단계 권장

1. Owner 확인 후 TASK-003(#20 배정 목록 + #21 배정 상세) 착수.

---

## 2026-09-10 — SPEC-001/TASK-001: concern 생성+목록 (api.md #16·#17) [위임]

### 작업

프롬프트 3(SPEC 단위 구현 루프)로 SPEC-001의 TASK-001만 구현:

1. `concerns/tests.py` 작성(8개 케이스: 인증 필요, 생성 성공/실패 3종, 목록 필터링·soft-delete/타인 배제) → `manage.py test concerns` 실행해 전부 404로 실패하는 것을 먼저 확인(라우팅 자체가 없었으므로).
2. 최소 구현: `concerns/serializers.py`(Create/CreateResult/List 분리) + `concerns/services.py`(`create_concern`, `has_approved_advice` annotation 포함 `list_my_concerns`) + `concerns/views.py`(`ConcernListCreateView`, GET/POST 한 경로) + `concerns/urls.py` + `config/urls.py`에 include.
3. `check`/`makemigrations --check`/`ruff check`/`manage.py test` 4종 실행 — 전부 통과 확인(테스트 8/8 OK).
4. Owner 요청에 따라 추가로 시각적 확인: `docker compose up`으로 앱+DB 기동, Playwright(임시 설치)로 DRF Browsable API를 헤드리스 브라우저로 조작 — 로그인 → 빈 목록+POST 폼 스크린샷 → 고민 1건 제출(201) 스크린샷 → 재조회 시 목록에 반영됨 스크린샷. 3장을 Owner에게 전송.

### 사용 도구

* Claude Code (VS Code Extension)
* Playwright(1.48, npx로 임시 설치·실행 — 프로젝트 의존성에는 추가하지 않음, 데모 전용)

### 인간 결정 (Owner, 2026-09-10)

| 결정 | 내용 |
| --- | --- |
| 결정 1 | 착수 전 12살 눈높이 브리핑 요구 → 브리핑 제시 후 승인 |
| 결정 2 | 백엔드 테스트만으로는 부족, 가벼운 Mock-up 수준 UI/UX로 데이터/사용자 흐름을 시각적으로 확인 요청(화려함 불필요, 최소 구현 허용) |

### 생성된 산출물

신규: `concerns/{serializers,services,views,urls,tests}.py`. 수정: `config/urls.py`(concerns.urls include, `DEBUG`에서만 `api-auth/`(DRF 로그인) 추가).

### 검증 결과 (전부 실행 완료)

* `manage.py test concerns` → 구현 전 7 failures + 1 error(전부 404) → 구현 후 **8/8 OK**
* `manage.py check` → 0 issues
* `makemigrations --check --dry-run` → No changes detected
* `ruff check .` → All checks passed(신규 파일 전량; 기존 파일 7종의 `ruff format` drift는 이번 작업과 무관 — 미변경)
* 시각 확인: Playwright 스크린샷 3장(로그인+빈 목록 → POST 201 → 목록에 반영) Owner에게 전송, 육안 확인 요청

### 잔여 리스크

1. **DRF Browsable API 데모용 `api-auth/` 경로**: `settings.DEBUG`에서만 노출되도록 가드했으나, prod 설정(`config/settings/prod.py`)에서 `DEBUG=False`가 실제로 강제되는지는 이번 작업에서 재확인하지 않음(M2/M1에서 이미 설정된 것으로 추정 — M5 스모크에서 재검증 권장).
2. **Playwright는 프로젝트 의존성이 아님** — `pyproject.toml`/`uv.lock`에 추가하지 않았고, 데모 스크립트는 스크래치패드(`/private/tmp/...`)에만 존재해 저장소에 남지 않음. 다음 시각 확인이 필요하면 재설치 필요.
3. **TASK-002부터는 approved_advices 등 advice 연동이 등장** — `advice` 앱은 아직 views 없음(모델만 존재), #18 구현 시 빈 배열로 시작 가능(spec.md §5 Non-Goals에 이미 명시).

### 다음 단계 권장

1. Owner 확인 후 TASK-002(#18 상세 + #19 소프트 삭제) 착수.

---

## 2026-09-09 — VS Code 마이그레이션 부트스트랩: AI-Native/Spec-Driven 구조 전환 [위임]

### 작업

`docs/request/3-vscode-migration_prompt.md` §5 "프롬프트 1 — 부트스트랩" 지시를 실행:

1. 지정된 순서로 통독: CLAUDE.md → api.md §3 → model.md §5 → `docs/reviews/04-milestone4-definition.md` → `config/urls.py`/`accounts`/`advisors`(구현 완료분) → README_AIUSAGE.md.
2. 실제 코드(`urls.py`, `views.py`, `git ls-files`)를 근거로 생성 전 사전 보고(파일 목록/STATUS 초안/CLAUDE.md diff 미리보기/문서 모순 11건) 제시 → Owner 승인 수신.
3. `docs/adr/ADR-006-ai-native-spec-driven-skeleton.md` 작성(Status: Proposed) — CLAUDE.md §16 Constitutional lock에 따라 CLAUDE.md 직접 수정 없이 개정 diff만 제안.
4. `docs/00-project/STATUS.md` 신설 — 코드 실측 기준(16/44 엔드포인트 구현) 현황판.
5. 루트 `README.md` 신설 — "지도" 원칙(개요/스택/구조/Quick Start/문서 링크만).
6. `docs/testing/TEST_CRITERIA.md` 신설 — 테스트 0건 현실 명시 + M4 AC를 자동화 판정 기준으로 번역.
7. `specs/SPEC-001-concerns-api/{spec,plan,tasks,acceptance}.md` 신설 — api.md #16~25(M4-5 concerns) 대상.
8. `.claude/rules/{coding,security,testing,infrastructure}.md` 4종 신설 — CLAUDE.md §9~§12 원문을 내용 변경 없이 이동.
9. Owner 승인 결정 3건 실행: (a) SPEC-001 해석 2건(`is_deleted`=파생 필드, #16~19 active_role 게이트 없음) (b) 본 병합 작업 (c) `.claude/commands/` 슬래시 커맨드는 이번 범위에서 제외.

### 사용 도구

* Claude Code (VS Code Extension으로 마이그레이션 직후 첫 세션)

### 인간 결정 (Owner, 2026-09-09)

| 결정 | 내용 |
| --- | --- |
| 결정 1 | SPEC-001 해석 승인: api.md #16·#19·#22의 `is_deleted`는 DB 컬럼이 아니라 `deleted_at` 기반 파생 응답 필드로 해석 / #16~19(사용자 concern CRUD)는 `active_role` 게이팅 없음 |
| 결정 2 | `docs/README_AIUSAGE.md`(06-22~06-30 4항목)를 이 파일로 병합 후 원본 삭제 |
| 결정 3 | `.claude/commands/`(Pro Tip 3의 `/status`·`/spec-next`·`/gate`)는 이번 부트스트랩 범위에서 생성하지 않음 |

### 생성된 산출물

신규 12파일: `docs/adr/ADR-006-ai-native-spec-driven-skeleton.md`, `docs/00-project/STATUS.md`, `README.md`(루트), `docs/testing/TEST_CRITERIA.md`, `specs/SPEC-001-concerns-api/{spec,plan,tasks,acceptance}.md`(4), `.claude/rules/{coding,security,testing,infrastructure}.md`(4).

병합/삭제: `docs/README_AIUSAGE.md` 내용을 이 파일로 병합 후 삭제.

CLAUDE.md는 **수정하지 않음** — ADR-006이 Owner 승인으로 Accepted 전환된 뒤에만 개정 diff(사전 보고에서 제시한 초안)를 적용한다.

### 검증 결과

* 코드 변경 없음(문서/구조 전환만) — `manage.py check` 등 코드 검증 대상 없음.
* STATUS.md의 "구현됨 16개/미구현 28개"는 `config/urls.py`, `accounts/urls.py`, `advisors/urls.py` 실측으로 교차 확인.
* 문서 모순 11건을 발견 시점에 사전 보고로 전부 제시 → Owner가 그중 핵심 2건(SPEC-001 해석)만 명시 승인, 나머지(경로 drift, 43→44 등)는 ADR-006 Consequences에 반영해 승인 후 CLAUDE.md 개정과 함께 정정 예정.
* `.claude/agents/`가 이미 커밋되어 있음을 실측(요청 문서의 갭 #7 기술과 불일치 — 이미 해소된 상태였음), `.github/pull_request_template.md`도 기존재 확인.

### 잔여 리스크

1. **CLAUDE.md 미개정 상태**: ADR-006이 Proposed인 동안 CLAUDE.md §2/§3/§5/§16/§17은 여전히 옛 내용(43개 엔드포인트, 옛 경로명)이다. Owner가 ADR-006을 Accepted로 전환하기 전까지 CLAUDE.md와 STATUS.md/ADR-006 사이의 의도적 불일치가 존재한다.
2. **테스트 0건은 여전히 미해소** — TEST_CRITERIA.md는 판정 기준만 마련했을 뿐, 실제 테스트 코드는 SPEC-001 TASK-001부터 작성된다.
3. **M4-1~M4-4 AIUSAGE 미기록 갭 지속**(STATUS.md §7 문서 부채 #1) — 이번 세션은 이 갭을 메우지 않았다. 다음 세션에서 M4-1~M4-4(커밋 `855d1bf`~`b2eaf90`)를 소급 기록해야 한다.
4. **리뷰 노트 미작성**(`03-milestone3-review.md`, `04-milestone4-review.md`) 갭도 지속.
5. **SPEC 구조의 비용 재평가 필요**: ADR-006 Review Triggers에 명시된 대로, SPEC-001(M4-5) 완료 후 이 4파일 구조가 남은 M4-6~M4-8에도 유효한지 재평가해야 한다.

### 다음 단계 권장

1. Owner: ADR-006 승인(Accepted) 여부 결정 → 승인 시 CLAUDE.md 개정 diff 적용.
2. SPEC-001/TASK-001(concern 생성+목록, #16·#17) test-first 착수.
3. M4-1~M4-4 AIUSAGE 소급 기록(문서 부채 #1) — 별도 세션 권장(코드 검증 없이 로그만 재구성하는 작업이라 리스크 낮음).

---

## 2026-07-09 — M4-1~M4-4: 인증·프로필·OAuth·조언가 신청 (api.md #2~#15) [위임] *(2026-09-17 소급 기록)*

> **소급 기록임을 밝힌다.** 이 4개 모듈은 프로젝트가 test-first 루프(ADR-006, 2026-09-10)를 도입하기 **전에** 구현됐고, 당시 AIUSAGE 항목이 누락됐다. 아래 내용은 **git 이력(`git log`·`git show --stat`)에서 실측한 사실**이며, 당시의 판단 근거를 사후에 지어내지 않았다 — 기록에 남아 있지 않은 것은 "미기록"으로 표시한다.

### 작업

api.md #2~#15의 14개 엔드포인트를 4개 모듈로 나눠 구현했다. 커밋 7건이 하루에 몰려 있다.

| 커밋 | 모듈 | 엔드포인트 |
| --- | --- | --- |
| `9dc8df1` | M4-1 auth 최초 | #2 signup / #3 login / #4 logout / #44 csrf + DRF 공통(예외 핸들러·페이지네이션) |
| `855d1bf` | M4-1 정합 수정 | 응답 형태를 api.md에 맞춤 |
| `91ad8ff` | M4-2 users/me | #7 조회 / #8 수정 / #9 역할 목록 / #10 활성 역할 전환 |
| `0d355d2` | M4-3 Google OAuth | #5 authorize / #6 callback |
| `c89b263` | M4-3 하드닝 | OAuth 계정 연결 충돌 409 + 보안 리뷰 지적 3건(S1/S2/S8) |
| `b2eaf90` | M4-4 advisor applications | #11~#15 + `IsAdmin` 권한 클래스 |
| `8817ea8` | (부수) | ADR-005(google-auth 라이브러리) 폐기, ADR-002 세션 단일 전략 유지 |

### AI 도구

Claude (당시 세션 — 정확한 모델명 미기록).

### Owner 결정

* **D-5 번복**: Google OAuth에 `google-auth` 라이브러리를 쓰지 않고 **표준 라이브러리 `urllib` + Google `tokeninfo` 엔드포인트**로 구현. ADR-005를 작성했다가 폐기하고 ADR-002(세션 단일 전략)를 유지했다 — 서드파티 패키지 추가는 §16 승인 게이트이고, 검증 한 번에 라이브러리 하나를 들이는 것이 과했다.
* 나머지 판단 근거는 **미기록**.

### 생성 산출물

`accounts/`(views·serializers·services·urls·oauth), `advisors/`(전체), `common/`(exceptions·pagination·permissions·authentication), `config/settings`·`config/urls`.

### 검증 결과

* 당시 검증 기록이 **남아 있지 않다.** `check`/`ruff` 실행 여부 확인 불가.
* **자동 테스트 0건**으로 구현됐다 — `accounts` 앱의 첫 테스트 파일은 2026-09-15 SPEC-003/TASK-003에서야 생겼고, `advisors`는 2026-09-14 A-1 수정 때 생겼다.
* 사후 검증: 이 코드는 2026-09-17 현재 **291개 테스트가 도는 코드베이스의 일부**이며, 맨바닥 스모크 테스트에서 회원가입·로그인·로그아웃 경로가 실제로 통과했다([docs/smoke-test.md](docs/smoke-test.md) §3).

### 잔여 리스크

1. **M4-1~M4-3의 자동 테스트가 여전히 0건이다.** 회원가입·로그인·OAuth·프로필 수정은 스모크 테스트가 실환경에서 한 번 덮었을 뿐, 회귀 방어가 없다. Phase 3 과제.
2. **당시 보안 리뷰(S1/S2/S8)의 내용이 기록에 없다.** 커밋 메시지의 식별자만 남아 있고 무엇을 고쳤는지는 diff로만 확인 가능하다.
3. 소급 기록의 한계 — 위 내용은 git 이력에서 복원한 것이고, **왜 그렇게 결정했는지**는 D-5 외에는 남아 있지 않다. 이것이 ADR-006이 STATUS.md와 AIUSAGE 갱신을 구현 커밋의 의무로 못 박은 이유다.

---

## 2026-07-08 — M3: 도메인 앱 모델 4종 [위임] + UX 사양

* **작업**: advisors/concerns/advice/notifications 4개 앱 모델 7종 + Admin 등록 + 마이그레이션 생성(앱 단위 커밋 분할). 병렬로 Phase 2 화면 흐름·API-to-screen 매핑 UX 사양 작성
* **AI 도구**: Claude Code (코드+설명 동시) + 서브에이전트 `data-modeler`(모델 정합 리뷰), `frontend-ux-architect`(UX 사양)
* **인간 결정**: M3 정의 승인, taxonomy 공유 배치 수용, 마이그레이션 적용·AC 검증 전부 Owner 직접 수행(showmigrations·sqlmigrate WHERE 절 3종·Admin 7종 조회·soft delete shell 검증), 이해 질문 3개 답변(1·2 부분, 3 통과), 드릴#2·M3 퀴즈·리뷰 노트는 M4 이후로 이월
* **생성 산출물**: `common/taxonomy.py`, `advisors/`·`concerns/`·`advice/`·`notifications/` 앱, 마이그레이션 4종, `docs/ux/01-phase2-screen-flows.md` — 커밋 `e3db9c1`·`de2e3a7`·`7d5e2f0`·`82d5e6c`·`a3823d1`·`05f60b2`
* **검증 결과**: check 0 issues, makemigrations --check No changes, ruff 통과, 부분 유니크 3종 WHERE 절 확인, data-modeler 리뷰 블로커 0(메이저 1건 I-1은 admin status readonly로 즉시 해소), Owner migrate·shell 검증 성공(soft delete 기본 감춤 실측)
* **잔여 리스크**: Owner 결정 대기 — 비익명 표시명 정책(C-6/C-7)·O-1 DomainCategory 확정·UX발 API 개선 4건(M4 전 처리 권고). model.md 문서 drift 6건 기록 대기. 학습 부채 누적(드릴#2·M3 퀴즈 이월 포함)

## 2026-07-07 — M2 마감 문서화

* **작업**: M2 리뷰 노트 작성(explain-first: Owner 선요약 → AI diff 분석), README_AIUSAGE 신설, M3 정의 문서 번호 정리
* **AI 도구**: Claude Code (Fable 5)
* **인간 결정**: 문서 번호 체계 = 마일스톤 번호(`NN-milestoneN-{definition,review}`), M3 승인 보류, WB-1은 M3 착수 전 이월
* **생성 산출물**: `docs/reviews/02-milestone2-review.md`, `README_AIUSAGE.md`, `docs/reviews/03-milestone3-definition.md`(초안, 승인 대기)
* **검증 결과**: 문서 작업 — 코드 변경 없음
* **잔여 리스크**: M2 학습 부채 9건 (리뷰 노트 원장 참조), WB-1 미실시

## 2026-07-05~06 — M2 학습 게이트 (드릴 #1 + 퀴즈)

* **작업**: 장애 드릴 #1 "DB 다운"(chaos-coach 주입·힌트, 진단·복구는 Owner) / 이해 퀴즈 5문(drill-master 출제·채점)
* **AI 도구**: Claude Code 서브에이전트 `chaos-coach`, `drill-master`
* **인간 결정**: 복구 명령 선택(`docker compose up -d db`), 포스트모템 작성, WB-1 다음 세션 이월
* **생성 산출물**: 드릴 채점표·포스트모템, 퀴즈 채점표(42/100), 학습 부채 원장 9건
* **검증 결과**: 드릴 이수(핸즈온 43분, 예산 +13분), db 복구 실측(healthy, /healthz 200)
* **잔여 리스크**: 부채 ④(401/403/409)·⑤(atomic)는 M4 착수 전 재퀴즈 필수

## 2026-07-05 — M2 트랙 B: accounts 도메인 확장 [위임]

* **작업**: `UserRole`/`RoleGrant`/`GoogleIdentity` 모델, `create_superuser` ADMIN 부트스트랩 훅(ADR-003), Django Admin 3종 등록, 마이그레이션 `accounts.0002` 생성
* **AI 도구**: Claude Code (코드+설명 동시 생성, 이해 확인 질문 3개 출제·채점)
* **인간 결정**: 마이그레이션 적용은 Owner 직접 수행, AC 검증(showmigrations·createsuperuser→ADMIN row·Admin 조회) Owner 수행, 이해 질문 답변
* **생성 산출물**: `accounts/{models,managers,admin}.py` 확장, `accounts/migrations/0002_*.py` — 커밋 `76b664e`
* **검증 결과**: `manage.py check` 0 issues, `makemigrations --check` No changes, ruff 통과, sqlmigrate로 제약·인덱스 확인, Owner가 컨테이너에서 migrate 적용 성공
* **잔여 리스크**: M1 시절 생성된 기존 superuser에는 ADMIN UserRole이 소급 생성되지 않음(수동 추가 필요). `active_role`↔`UserRole` 정합은 M4 서비스 레이어에서 강제 예정

## 2026-07-03~05 — M2 트랙 A: 런타임 승격 [소유]

* **작업**: Dockerfile 멀티스테이지(builder/runtime)·비루트(uid 10001)·gunicorn 전환, docker-compose.override.yml dev 경로 분리 — **전량 Owner 손코딩**
* **AI 도구**: Claude Code — 코치 모드(시작 전 체크리스트, 막힘 시 단계적 힌트만) + `ops-reviewer` 서브에이전트 리뷰 3라운드 + gunicorn 버전/보안 사실 검증(PyPI·OSV 실측)
* **인간 결정**: dev/prod 분기 = override 병합 패턴(리스크 #1), runtime에 uv 미탑재, gunicorn 26.0.0 dependencies 추가(§16 승인), `.claude/agents/` 미커밋
* **생성 산출물**: (AI 생성 아님 — Owner 작성) `Dockerfile`, `docker-compose.override.yml`; AI는 리뷰 코멘트만. 커밋 `156ded9`
* **검증 결과**: 1차 블로커 5 → 2차 블로커 1 → 3차 **블로커 0·메이저 0 통과**. 운영 경로 gunicorn `/healthz` 200, `exec app id` uid=10001, 시크릿 전수 grep 무검출 (전부 실측)
* **잔여 리스크**: gunicorn 경로 정적파일 서빙 부재(/admin 정적 404 — M5 문서 명시 예정), FROM 버전 2곳 독립 표기, 브루트포스 방어 Phase 3 이월

## 2026-07-03 — M2 정의 및 승인

* **작업**: 마일스톤 번호 충돌 해소(reviews/01 vs learning/02), M2 통합 정의 문서 작성
* **AI 도구**: Claude Code
* **인간 결정**: 통합형 M2 승인(트랙 A [소유] + 트랙 B [위임]), gunicorn 서드파티 추가 승인(dependencies 그룹), 43개 엔드포인트 로드맵 유지
* **생성 산출물**: `docs/reviews/02-milestone2-definition.md` — 커밋 `8b2c0f8`
* **검증 결과**: 문서 작업 — Owner 승인으로 확정
* **잔여 리스크**: —

## 2026-06-30 — 독립 git 저장소 초기화 + 전략 IP 공개범위 분할 + ruff 도입

### 작업

1. 비밀정보 교차검증: chamneul이 상위 `personal` 저장소에 추적된 적 없음, `.env`/자격증명/하드코딩 비밀값 부재 확인.
2. Public 공개 전략 분석(Data-Driven): 코드/기술 문서는 공개 안전, 사업전략·평가 알고리즘 설계는 별도 IP 범주임을 분석.
3. `docs/1 서비스기획_v1.md` 전략 IP(ELO 점수 설계·조언자 평가 모델·승인 트리)를 공개 요약본 / 비공개 상세본으로 분할 (ADR-004).
4. ruff(lint+format) dev 의존성 도입. 운영 이미지 제외 구조 검증. 코드베이스 check/format 적용.
5. README_AIUSAGE 갱신 후 GitHub Public 저장소 생성·push.

### 사용 도구

* Claude Opus 4.8 (claude-opus-4-8)
* Claude Code CLI

### 인간 결정 (Owner, 2026-06-30)

| ID | 결정 |
| --- | --- |
| G1 | chamneul을 상위 `personal` 저장소에서 분리해 독립 git 저장소로 초기화 |
| G2 | 저장소는 Public 공개. 단 핵심 전략 IP는 비공개 처리 |
| G3 | 전략 문서 처리 = 옵션 B(분할 발행: 공개 요약본 + 비공개 상세본) + ADR-004 기록 |
| G4 | ruff(lint/format)는 dev 의존성으로 먼저 도입 |
| G5 | pytest 등 운영 불필요한 개발자 전용 테스트 패키지는 설치 제외 (테스트는 Django 기본 test runner 사용) |

### 생성된 산출물

신규:

* `docs/adr/ADR-004-strategy-doc-visibility-split.md` — 공개범위 3단계 분류 + 분할 발행 결정
* `docs/_private/1 서비스기획_v1_full.md` — 전략 IP 원본 보존 (gitignored, 비추적)
* `pyproject.toml` `[dependency-groups].dev` + `[tool.ruff]` 설정 블록

수정:

* `docs/1 서비스기획_v1.md` — 공개 요약본으로 교체 (ELO/평가/승인 로직 제거, ADR-004 참조 명시)
* `.gitignore` — `docs/_private/` 추가
* `pyproject.toml`/`uv.lock` — ruff dev 그룹 추가
* ruff format 적용: `accounts/models.py`, `common/uuid7.py`, `config/settings/{base,local,test,prod}.py`, `manage.py` (7개)

### 검증 결과 (전부 실행 완료)

* `git ls-files` → 추적 45→갱신, `.env`/`docs/_private` 추적 0건 ✅
* `git check-ignore` → `.env`·`docs/_private/`·`.venv` 모두 무시됨 ✅
* `uv export --no-dev` → 운영 의존성에 ruff 없음 (dev 그룹 격리 확인) ✅
* `uv run ruff check .` → All checks passed ✅
* `uv run ruff format .` → 7 files reformatted ✅
* `manage.py check` → 0 issues ✅
* `makemigrations --check --dry-run` → No changes detected ✅
* 공개 요약본 IP 누출 grep → ELO/Layer/점수설계/승인트리 키워드 부재 ✅

### 잔여 리스크

1. **`docs/_private/`는 git 백업 부재** — 별도 백업(private Notion/암호화) 권장 (ADR-004 trade-off 명시).
2. **중첩 저장소** — chamneul/.git이 상위 `personal` 저장소 디렉터리 내부에 위치. 상위가 chamneul을 커밋하지 않으므로 동작엔 무해하나, 장기적으로 chamneul을 별도 경로로 분리 이전하는 것이 깔끔.
3. **이전 리스크 해소**: 직전 Milestone 1의 "ruff 미도입"(§16 패키지 게이트) 리스크는 본 세션 G4로 해소됨.
4. **Notion drift 유지** — api.md §7 패치 미반영 상태 지속.

### 다음 단계 권장

1. Milestone 2 — `accounts`의 `UserRole` / `RoleGrant` / `GoogleIdentity` + createsuperuser→ADMIN 훅.
2. CI에 ruff check 게이트 추가 (Phase 3 CI/CD 진입 시).

## 2026-06-29 — Milestone 1: 실행 가능한 Django+PG 골격 + 커스텀 User

### 작업

1. 직전 두 세션(api.md/model.md) 통독 후 다음 단계 보고.
2. 런타임/툴링 결정 수신 및 적용 (아래 인간 결정).
3. uv 가상환경 셋업 가이드 제공 → Owner가 직접 `.venv`(Python 3.13) 생성·검증.
4. 의존성 `django-environ → python-dotenv` 교체 (`uv remove/add`).
5. Milestone 1 코드 작성: 프로젝트 골격(`manage.py`, `config/`), 설정 4분할(`base/local/test/prod`), `common/uuid7.py`, `accounts.User`(+ `UserManager`, admin), `/healthz`, Docker(`Dockerfile`, `docker-compose.yml`, `.dockerignore`), `.env.example`, `.gitignore` 보강.
6. 검증 실행 (아래 검증 결과).
7. `docs/reviews/01-milestone1-skeleton.md` 작성 (§14, 임베디드 학습 포함) + 본 로그 갱신.

### 사용 도구

* Claude Opus 4.8 (claude-opus-4-8)
* Claude Code CLI

### 인간 결정 (Owner, 2026-06-29)

| ID | 결정 |
| --- | --- |
| D1 | UUIDv7 구현 = `uuid_utils.uuid7` (Rust, 앱 레벨 생성; 관리형 RDS/Aurora의 `pg_uuidv7` 설치 차단 회피, 환경 drift 0) |
| D2 | 런타임 = Python 3.13 + Django 5.2 LTS |
| D3 | 의존성 관리 = `pyproject.toml` + uv (lockfile `uv.lock`) |
| D4 | 시스템 Python(`/usr/bin/python3`) 절대 호출 금지 — uv-managed venv 안에서만 작업 |
| D5 | `.env` 로딩 = `python-dotenv` (MVP 경량/직관 우선, 추후 `pydantic-settings` 전환 여지) |
| D6 | 코드 세션마다 `docs/reviews/`에 초급→고급 + DevOps 임베디드 학습 노트 작성 |

### 생성된 산출물

신규: `manage.py`, `config/{__init__,urls,health,wsgi,asgi}.py`, `config/settings/{__init__,base,local,test,prod}.py`, `common/{__init__,uuid7}.py`, `accounts/{__init__,apps,managers,models,admin}.py` + `accounts/migrations/0001_initial.py`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`, `docs/reviews/01-milestone1-skeleton.md`.

수정: `pyproject.toml`/`uv.lock`(django-environ→python-dotenv), `.gitignore`(보강).

### 검증 결과 (전부 실행 완료)

* `uv run` uuid7 → `uuid.UUID` version 7 ✅
* `manage.py check` → 0 issues ✅
* `makemigrations --check --dry-run` → No changes ✅
* `docker compose build` / `up` → db healthcheck healthy, app up ✅
* `migrate`(컨테이너 PG) → `accounts.0001_initial` 포함 전부 OK ✅
* `GET /healthz` → **HTTP 200** `{"status":"ok"}` ✅
* `createsuperuser`(email+nickname, noinput) → 성공, User PK UUIDv7, PBKDF2 해시 ✅

### 잔여 리스크

1. **createsuperuser ADMIN 역할 훅 미구현** — `UserRole` 모델이 없는 단계라 ADR-003의 "첫 superuser=ADMIN row" 훅은 Milestone 2로 이연(코드에 NOTE 명시).
2. **인증 로직 미구현** — login/logout/Google OAuth는 Milestone 3. 현재는 ADR-002 쿠키 정책 baseline만 설정.
3. **운영 서버** — Dockerfile CMD가 `runserver`(로컬 전용). gunicorn 전환 후속.
4. **ruff 미도입** — §16 패키지 게이트로 Owner 확인 후 도입 예정.
5. **Notion drift 유지** — api.md §7 패치 미반영(Owner 직접 작업 권장).
6. **로컬 `.env` 실파일 존재** — dev 값으로 생성됨(gitignore 제외). 운영 값과 무관.

### 다음 단계 권장

1. Milestone 2 — `accounts`의 `UserRole` / `RoleGrant` / `GoogleIdentity` + createsuperuser→ADMIN UserRole 훅.
2. 이후 Milestone 3 — 인증(signup/login/logout/OAuth) + DRF serializer/viewset/permission.

## 2026-06-26 — model.md v1 작성 + CLAUDE.md 헌법 갱신 (2차)

### 작업

1. 6/22 세션 종료 이후 docs 변경분 재확인: `2 mvp-scope.md` → `2 mvp-scope_v1.md` 파일명 변경, `docs/learning/01-api-to-model-and-docker.md` (Owner 학습 세션) 신설, `docs/api.md` 부분 수정 확인.
2. Owner의 model.md 작성 전 8가지 핵심 결정(M1~M8) 및 4가지 production-grade 보완사항(UUIDv7 / soft-delete + 부분 unique / 3단계 expand-contract 마이그레이션 / Read Replica + 인덱스 튜닝) 수신.
3. ADR-001 Decision 2 (SQLite 제거) 갱신.
4. `docs/model.md` v1 작성 — 12 섹션, 10 엔티티 + 1 audit 테이블, Mermaid ERD, DB / 서비스 제약, 인덱스 요약, EKS 인지 마이그레이션 가이드, Read Replica 라우팅, Django Admin 등록 패턴, 검증 체크리스트, 8건 Open Questions.
5. 초기 설계 ADR(ADR-004)를 별도로 도출했다가 Owner 지시에 따라 본문을 CLAUDE.md에 직접 흡수:
   * CLAUDE.md §4 — PG 16+ 전용 + 허용 PG 전용 기능 목록(ArrayField, JSONB, GIN, 부분 unique, UUIDv7, select_for_update) 추가.
   * CLAUDE.md §6.6 — soft-delete 컬럼을 `deleted_at` 로 명시 + partial unique 강제 패턴 코드 예시.
   * CLAUDE.md §16 — 헌법 잠금 허용 세션에 2026-06-26 추가, 해당 두 조항이 본문에 흡수되어 별도 supersession ADR 불요임을 명시.
6. ADR-004 파일 및 모든 참조 제거 (CLAUDE.md / model.md / ADR-001 에서 정리).
7. 본 항목 README_AIUSAGE.md 작성.

### 사용 도구

* Claude Opus 4.7 (claude-opus-4-7)
* Claude Code CLI

### 인간 결정 (Owner)

Owner가 직접 확정한 결정 (2026-06-26):

| ID | 결정 |
| --- | --- |
| M1 | 앱 레이아웃 = CLAUDE.md §3 5개 도메인 앱(`accounts`, `advisors`, `concerns`, `advice`, `notifications`) + `config` + `common`. Feedback은 `advice` 안에, Google OAuth/RoleGrant는 `accounts` 안에. |
| M2 | User 모델 = `AbstractBaseUser + PermissionsMixin` 완전 커스텀. 이메일 단일 로그인. |
| M3 | Soft delete = manager `objects` 가 자동 alive 필터 + `with_deleted()` 명시. |
| M4 | PG 전용 채택, `ArrayField`(고정 타입 배열) + `JSONField`(비정형). SQLite 비사용. ADR-001 수정 + CLAUDE.md §4 흡수 승인. |
| M5 | Enum = `TextChoices` 단일. |
| M6 | PK = UUID (EKS 분산 환경 / 스테이징↔프로덕션 이관 / 멀티 리전 대비). |
| M7 | AdviceHistory = 본문 필드 전체 snapshot per version. |
| M8 | ERD = Mermaid `erDiagram`. |
| 보완 #1 | PostgreSQL 16+ 환경의 **UUIDv7** 시계열 정렬 PK 채택 (B-Tree 페이지 무작위 플러시 회피). |
| 보완 #2 | Soft delete 모델의 unique 제약은 반드시 `WHERE deleted_at IS NULL` partial unique index 로 설계. |
| 보완 #3 | EKS 무중단 배포를 위한 3단계 expand-contract 마이그레이션 원칙을 model.md 마이그레이션 노트에 명시. |
| 보완 #4 | DB 라우팅 / Read Replica / Connection Pooling / 인덱스 튜닝 가이드를 model.md 에 명시. |

CLAUDE.md 직접 수정도 이번 세션에 한해 추가 승인(헌법 잠금 1회 추가 개방). ADR-004 본문은 CLAUDE.md 본문으로 흡수 + ADR-004 파일 및 모든 참조 제거 지시.

### 생성된 산출물

수정:

* `CLAUDE.md` — §4 (PG 16+ 전용 + 허용 PG 기능 목록 추가) / §6.6 (soft-delete `deleted_at` 컨벤션 + partial unique 강제 패턴 코드 예시) / §16 (헌법 잠금에 2026-06-26 세션 추가)
* `docs/adr/ADR-001-local-container-architecture.md` — Decision 2 본문 + Alternative §2 SQLite 항목 (PG 전용 + CLAUDE.md §4 단일 진실원천 명시)
* `docs/model.md` — ADR-004 참조 → CLAUDE.md §4/§6.6 로 치환, §12 References 정리 (이전 단계)

신규:

* `docs/model.md` v1 (이 세션 산출 — 12 섹션, 10 엔티티 + AdviceHistory, Mermaid ERD 포함)

삭제:

* `docs/adr/ADR-004-postgres-only-and-soft-delete-convention.md` (본문이 CLAUDE.md 에 흡수됨)

### 검증 결과

* 코드 변경 없음 — 본 세션은 명세/헌법 정렬.
* `grep -rn "ADR-004"` 잔존 참조 0건 확인.
* 문서 정합성은 M1~M8 + 보완 #1~#4 ↔ CLAUDE.md ↔ model.md 본문 매핑 표(직전 응답 §결정 반영 매트릭스)로 자체 교차 검증.
* 미수행 (다음 코드 세션에서 검증):
  * `python manage.py makemigrations --check --dry-run`
  * `python manage.py migrate` (빈 PG DB 대상)
  * `python manage.py createsuperuser` 후 첫 ADMIN UserRole row 생성 hook 확인
  * `docker compose up -d` + `curl /healthz`

### 잔여 리스크

1. **헌법 잠금 누적 변경**: 6/22 잠금 → 6/26 1회 추가 개방. 누적 형태로 lock-window가 늘어나면 헌법 잠금의 신뢰도가 떨어진다. 다음 변경은 반드시 새 ADR 절차로 가야 한다 (§16 갱신문 명시).
2. **UUIDv7 구현 의존성**: 앱 레벨 헬퍼(`common/uuid7.py`)가 RFC 9562 정확성/스레드 안전성을 보장해야 한다. `uuid_utils` 등 외부 패키지 채택 시 ADR 없이 진입 가능한지 경계가 모호 — 코드 세션 진입 전 1차 결정 필요.
3. **PG 전용 결정의 CI 영향**: 테스트 시 PG 컨테이너 부팅 시간이 CI 빌드를 늘릴 수 있다. testcontainer 최적화는 별도 ADR로 분리.
4. **Open Questions 8건** (model.md §11): `domain_category` enum 값 / `decision_context` 길이 / `ANSWERED → CLOSED` Public API / DELETED advice 재작성 / GIN 인덱스 / Notification URL 정책 / User 정지 흐름 / `pg_uuidv7` 채택 시점. 코드 세션 중 결정.
5. **Notion 원본 drift**: api.md §7 패치 + model 결정(특히 URI 변경, intended_lane 노출 정책) 미반영 상태. Owner 직접 갱신 권장.
6. **검증 미실행**: 모든 결정은 첫 마이그레이션/smoke test 단계에서 실 검증.

### 다음 단계 권장

1. Owner: Notion DB 갱신 (api.md §7 패치 + model.md 결정 반영).
2. UUIDv7 구현 패키지 결정 (자체 구현 vs `uuid_utils` 등).
3. Django scaffolding 세션 진입 — `config/settings/` 분리 + `accounts.User` 첫 마이그레이션부터.

## 2026-06-22 — Notion API v0 정합성 검토 + api.md v1 생성

### 작업

`docs/request/1-onboarding_prompt.md` 와 `docs/request/2-Notion-first_API 명세 검토_prompt.md` 의 지시에 따라:

1. 프로젝트 docs 전체 통독 (CLAUDE.md, ADR-001, mvp-scope.md, 서비스기획 v1, README).
2. Notion DB에서 export된 v0 API 명세 27개 markdown + 엔드포인트 CSV 통독.
3. CLAUDE.md / ADR-001 / MVP scope 기준으로 정합성 검토 (32개 이슈 식별).
4. Owner Decision Questions Q1~Q22 분리 제시 후 답변 수신.
5. 결정 반영을 위한 헌법 문서(CLAUDE.md) + ADR-001 + mvp-scope.md 패치를 항목별 승인 후 적용.
6. ADR-002 (Session 인증 정책), ADR-003 (ADMIN 역할 부여/회수) 신규 작성.
7. `docs/api.md` v1 작성 — 총 43 엔드포인트 (Notion v0 41건 − 토큰재발급 + `/healthz` + 관리자 역할 부여/회수 2건).
8. Notion 원본 갱신을 위한 패치 테이블을 `docs/api.md §7`에 동봉 (Notion DB는 직접 수정하지 않음).
9. `docs/model.md` 작성에 필요한 준비 요약(앱 목록, 모델 후보, FK, enum, 인덱스, unique, soft delete, transaction.atomic) 인라인으로 회신.

### 사용 도구

* Claude Opus 4.7 (claude-opus-4-7)
* Claude Code CLI

### 인간 결정 (Owner)

Owner가 직접 확정한 결정 (2026-06-22):

| ID | 결정 |
| --- | --- |
| Q1 | 인증 = Session(SSR) + HttpOnly Cookie 단일안. JWT/Token 미사용 |
| Q2 | Phase 2 v1 = 명세 전체(43건) 구현 |
| Q3 | `/api/v1/` prefix 유지, CLAUDE.md를 본 세션 한정 갱신 |
| Q4 | 사용자 소유 자원 URI를 `/users/me/{resource}` 로 통일 |
| Q5 | `intended_lane` 필드 유지하되 Public 응답 비노출 (관리자/시스템 참고용) |
| Q6 | 상태값을 CLAUDE.md §6.1/§6.2 5값으로 통일 (PENDING_REVIEW/published/draft/answered/REVIEWED 등 제거) |
| Q7 | 별도 ADMIN 부여 API 정의, grant + revoke 양쪽 |
| Q8 | 조언가의 `advisable_concern_types`는 taxonomy 영문 enum |
| Q9 | 배정 카디널리티 = 1 concern ↔ N advisor |
| Q10 | advisor 1명당 concern 1건은 advice 1개. version은 audit |
| Q11 | 내 고민 상세 조회 = 인증 필요 (본인만) |
| Q12 | 토큰 재발급 API 명세에서 제외 |
| Q13 | 회원가입 = 자동 로그인 (Set-Cookie sessionid) |
| Q14 | 가입 시 nickname 필수 (unique) |
| Q15 | 내 정보 조회 응답에서 `advisor_type` 제거 |
| Q16 | 조언가 신청 거부 사유는 신청자에게 노출 |
| Q17 | grant=POST `/admin/users/{user-id}/roles`, revoke=DELETE `/admin/users/{user-id}/roles/{role}` |
| Q18 | 최초 ADMIN = `python manage.py createsuperuser` |
| Q19 | concern_status = SUBMITTED → ASSIGNED → ANSWERED → CLOSED, soft delete는 별도 flag |
| Q20 | 세션 정책: cookie `sessionid`, HttpOnly + Secure + SameSite=Lax, 만료 14일, 매 요청 슬라이딩 갱신, 로그아웃 시 서버 세션 삭제 |
| Q21 | advice.version = 수정마다 +1, 응답 노출, 별도 audit 테이블 |
| Q22 | advisor `display_name` = nickname과 별개, 신청 시 입력, unique |

문서 수정도 항목별(A-1~A-8 / B-1~B-5 / C-1 / E-1 / E-2)로 Owner가 명시 승인.

### 생성된 산출물

수정:

* `CLAUDE.md` — §4 Auth / §5 MVP Scope / §6.1 intended_lane policy / §6.6 신설 Concern Status / §6.7 신설 Advice Versioning / §7 URI examples / §10 Auth security rules / §16 constitutional lock
* `docs/adr/ADR-001-local-container-architecture.md` — Decision Summary Auth 행 / Decision 4 본문 재작성 / DRF Token 한계 단락 제거 / Auth 구현 원칙 / Final Decision 블록
* `docs/2 mvp-scope.md` — Phase 2 v1 범위 = 43 엔드포인트 명시 한 줄 추가

신규:

* `docs/adr/ADR-002-session-authentication-policy.md`
* `docs/adr/ADR-003-admin-role-grant.md`
* `docs/api.md` v1 — 43 엔드포인트 전체 명세 + URI 변경 매핑 + Notion 갱신 패치 테이블

### 검증 결과

* 코드 변경 없음. 따라서 `python manage.py check` 등 코드 검증은 수행하지 않았다.
* 문서 정합성은 결정 매핑 표로 자체 교차 검증 (Q1~Q22 ↔ CLAUDE.md ↔ ADR-001/002/003 ↔ api.md).
* 미수행 항목(추후 단계에서 검증 필요):
  * `docker compose up -d` 기반 healthz 200 확인
  * `curl /api/v1/users/me/concerns` 흐름 검증
  * Django Admin 데이터 확인
  * Notion 원본 갱신(별도 작업)

### 잔여 리스크

1. **Notion 원본과의 drift**: `docs/api.md §7` 패치 테이블을 Notion에 반영하지 않은 상태로 코드 작업이 시작되면, 명세 source of truth가 분기될 수 있다. 코드 진입 전 Owner의 Notion 갱신이 권장된다.
2. **헌법 문서 잠금**: CLAUDE.md §16에 추가된 constitutional lock 조항에 따라, 이번 세션 이후 CLAUDE.md를 추가 수정하려면 새로운 ADR을 작성해야 한다. 향후 Claude 세션은 이 규칙을 인지하지 못할 수 있으므로, 매 세션 시작 시 CLAUDE.md 통독이 필수.
3. **Open Questions 8건**: `docs/api.md §6` 에 명시된 8개 비-차단 결정 (글자 수 상한, draft 모델링, CLOSED 전이 API, 페이지네이션 size 상한, OAuth nickname 산정 규칙 등)은 코드 작업 중 확정될 필요가 있다.
4. **세션 저장소**: ADR-002는 DB 세션을 Phase 2 기본으로 정함. 트래픽 발생 시 Redis 전환이 필요할 수 있으나 현 시점에서는 의도된 trade-off.
5. **계정 정지/탈퇴 흐름 부재**: 명세 v1은 가입/로그인/로그아웃까지만 다룸. 정지·탈퇴는 Phase 3+ 결정 사항.
6. **자동 알림 채널 없음**: 알림 model + 조회 API 만 v1에 포함. push/email/web socket은 명시적으로 제외.
7. **검증 미실행**: 코드 베이스가 아직 없어 실행 검증을 못함. `docs/model.md` 및 Django scaffolding 이후의 smoke test 단계에서 본 명세의 실현 가능성이 처음으로 검증된다.

### 다음 단계 권장

1. Owner: Notion DB 패치(`docs/api.md §7`) 반영.
2. 별도 세션에서 `docs/model.md` 작성 (본 세션의 model preparation summary를 입력으로 사용).
3. 모델 확정 후 Django scaffolding 시작 (앱 분리 → 모델 → 마이그레이션 → 권한/Serializer/ViewSet → URLConf → Admin 등록 → `/healthz` → smoke test).
