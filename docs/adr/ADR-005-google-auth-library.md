# ADR-005. Google OAuth ID 토큰 검증에 `google-auth` 라이브러리 채택

## Status

Proposed (Owner 결정 2026-07-08 — M4-3 착수 전 승인 필요)

## Date

2026-07-08

## Context

Phase 2 인증은 세션 단일 전략(ADR-002)이며, Google OAuth 콜백도 동일 세션을 발급한다(CLAUDE.md §4). M4-3(OAuth 콜백 구현)은 다음 두 단계를 서버에서 수행해야 한다.

1. 인가 코드(authorization code)를 토큰으로 교환한다 (Google 토큰 엔드포인트에 HTTPS 요청).
2. 받은 ID 토큰(JWT)이 **진짜 Google이 발급했고 우리 client_id를 향한 것인지** 검증한다 (서명·발급자·audience·만료 검증).

CLAUDE.md §16은 서드파티 패키지 추가와 인증 전략 변경을 승인 게이트로 두며, §4는 "Google 외 OAuth 제공자·추가 auth 패키지 도입은 새 ADR을 요구한다"고 명시한다. 본 ADR은 그 게이트를 통과하기 위한 결정 기록이다.

Owner는 세 선택지 중 **C(google-auth)**를 선택했다. 본 문서는 그 결정과, 결정 과정에서 드러난 두 가지 사실관계 정정을 함께 기록한다.

---

## Decision

Google ID 토큰 검증에 **`google-auth`** 라이브러리를 사용한다. 표준 검증 함수 `google.oauth2.id_token.verify_oauth2_token(token, request, client_id)`로 서명·발급자·audience·만료를 한 번에 검증한다.

* 의존성 그룹: **dependencies** (dev 아님). 운영 이미지에 포함된다.
* 버전: `google-auth >= 2.x` (구현 세션에서 최신 안정 버전으로 lock).
* 코드 위치: `accounts/` (OAuth 콜백 뷰/서비스). 검증 결과(verified email, `sub`)로 GoogleIdentity를 링크한다(model.md §3.4).

### 검토 과정에서 정정된 사실 2건 (결정 유지, 사유 교정)

Owner 결정문의 사유 중 두 가지가 실제 라이브러리 특성과 어긋나므로, 오해를 남기지 않기 위해 명시한다.

1. **"추후 httpx 비동기 어댑터로 스위칭" 전략은 google-auth의 특성이 아니다.**
   `google-auth`의 표준 검증 경로는 자체 전송 계층(`google.auth.transport.requests.Request`)에 결합되어 있어, HTTP 클라이언트를 httpx로 자유롭게 교체하는 구조가 아니다. 비동기 전환의 유연성은 오히려 선택지 B(httpx 직접 호출)의 장점이었다. 따라서 본 결정의 실제 근거는 "비동기 유연성"이 아니라 **"ID 토큰 서명 검증을 직접 구현하지 않고 표준 라이브러리에 위임하는 안전성·정석성"**으로 확정한다.

2. **의존성은 1개가 아니라 사실상 2개다.**
   `verify_oauth2_token`은 `google.auth.transport.requests`를 통해 검증에 필요한 Google 공개키를 가져오며, 이 전송 계층은 `requests`에 의존한다. 따라서 `google-auth` 채택은 `requests`까지 함께 설치한다. `.env`/이미지 크기에 미치는 영향은 경미하나, "의존성 1개 추가"라는 인식은 정정한다.

이 두 사실을 인지한 상태에서도 Owner는 C를 유지한다(직접 서명 검증 구현의 위험 회피 > 의존성 최소화).

---

## Rationale (Why)

* **직접 구현 위험 회피**: ID 토큰은 JWT이며, 서명 검증을 순수 표준 라이브러리로 직접 구현하면 Google 공개키 회전(rotation)·알고리즘 검증·audience 확인에서 미묘한 보안 실수가 나기 쉽다. `verify_oauth2_token`은 이 전 과정을 표준으로 처리한다.
* **정석성**: `google-auth`는 Google이 관리하는 공식 라이브러리로, tokeninfo 엔드포인트 왕복(선택지 A) 대비 로그인마다의 외부 왕복이 없고(공개키 캐싱), 오프라인 서명 검증이 가능하다.
* **인증 전략 불변**: 세션 발급은 그대로 ADR-002 경로를 탄다. `google-auth`는 "ID 토큰 검증기"로만 쓰이고 세션/쿠키 로직을 대체하지 않는다.

## Alternatives Considered

* **A. urllib(내장) + Google tokeninfo 엔드포인트 검증** — 신규 패키지 0개. 단 로그인마다 Google에 검증 왕복 1회가 추가되고, tokeninfo는 디버그 용도 성격이 강해 프로덕션 검증 경로로는 정석이 아니다. "경량·의존성 최소" 사유에는 가장 부합.
* **B. httpx/requests 직접 호출 + 수동 JWT 검증** — HTTP 클라이언트 유연성(비동기 전환)은 최상이나 서명 검증을 직접 구현해야 해 보안 위험이 가장 크다.
* **C. google-auth (채택)** — 검증을 표준에 위임. `requests` 전이 의존을 수용.

## Consequences

### Positive

* ID 토큰 검증이 검증된 표준 코드 경로를 탄다.
* Google 공개키 회전이 라이브러리 내부에서 처리된다.

### Negative / 비용

* `google-auth` + 전이 의존 `requests`가 운영 이미지에 추가된다.
* 라이브러리 메이저 업그레이드 시 검증 API 변경 가능성 — 버전 lock으로 관리.
* 콜백 경로에 Google 공개키 조회를 위한 아웃바운드 HTTPS가 필요(캐싱되나 최초/회전 시 발생) — 로컬 개발 방화벽 환경에서 인지.

## Security Notes (CLAUDE.md §10)

* `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`은 `.env`로 분리하고 `.env.example`에는 키 이름만 둔다(값 금지). **`.env*`는 Owner 소유 구역이므로 키 이름 추가는 Owner가 직접 수행한다.**
* 검증 실패(서명·audience·만료 불일치) 시 세션을 발급하지 않고 인증 실패로 처리한다.
* 계정 링크는 **검증된 이메일** 기준(ADR-002 §7). Google이 assert한 이메일과 기존 User 이메일이 같을 때만 링크한다.
* Google `name` 원본은 저장하지 않는다(최소 수집 — GoogleIdentity는 `google_sub`+`email`만, model.md §3.4). 신규 가입 시 nickname 자동 산정은 C-11 확정안(ux/01)을 따른다.

## Validation

* `uv add google-auth` 후 `uv.lock`에 `google-auth`와 전이 의존 `requests` 등장 확인.
* 유효한 Google ID 토큰(테스트 계정) → `verify_oauth2_token` 통과 → 세션 발급 → GoogleIdentity 링크.
* 위조/만료 토큰 → 검증 예외 → 세션 미발급 → 인증 실패 응답.
* 동일 검증 이메일의 기존 로컬 계정 존재 시 → 링크만, 신규 User 미생성.

## Supersession

본 ADR은 CLAUDE.md §4의 "Google OAuth 콜백은 동일 세션 발급" 원칙을 구현 수단 차원에서 구체화할 뿐 대체하지 않는다. 향후 다른 OAuth 제공자(Kakao/Apple 등) 추가나 세션 외 인증(JWT 등) 도입은 별도 ADR을 요구한다(ADR-002 불변).
