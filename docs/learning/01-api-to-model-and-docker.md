# 학습 세션 01 — API 명세 → 데이터 모델 도출 & DevOps(Docker) 정합 구현 개념 내재화

> 이 문서는 **학습(개념 내재화) 세션**이다. 코드 생성 세션이 아니다.
> model을 실제로 생성하기 **전에**, Owner가 "API 명세에서 어떻게 모델/테이블을 도출하는가"와
> "DRF 모델·스캐폴딩 이후 Dockerfile / docker-compose를 어떻게 프로젝트에 정합하게 구성하는가"를
> 직접 설명할 수 있는 수준까지 이해하는 것이 목표다.
> 형식은 CLAUDE.md §14(리뷰 세션 규칙)를 학습용으로 각색했다.

---

## 0. 세션 메타

| 항목 | 내용 |
| --- | --- |
| 세션 종류 | 학습 / 개념 내재화 (코딩 아님) |
| 날짜 | 2026-06-23 |
| 선행 문서 | CLAUDE.md, docs/api.md(43 엔드포인트 확정본), docs/adr/ADR-001, ADR-002, ADR-003 |
| 산출물 | 본 문서 1건 (`docs/learning/01-api-to-model-and-docker.md`) |
| 다음 산출물(미생성) | `docs/model.md` + ERD 초안 → 이후 코드 스캐폴딩 |
| 본 세션에서 하지 않는 것 | 기존 문서 수정/삭제, `models.py`/`Dockerfile`/`docker-compose.yml` 등 실제 파일 생성, migration 실행 |

> **주의 (Owner 지시):** 본 문서 안의 모든 코드 블록은 **학습용 예시**다. 아직 프로젝트 파일로 만들지 않는다.
> 실제 구현은 본 세션으로 개념을 내재화한 뒤 별도 코딩 세션에서 진행한다.

---

## 1. 학습 목표 (체크리스트)

본 세션이 끝났을 때 Owner가 아래를 스스로 설명/판단할 수 있어야 한다.

* API 명세서 → model 작성 방법 & 개념 & 매커니즘 학습
  * [ ] 데이터 모델 초안 및 핵심 테이블 구조를 도출하는 방법
  * [ ] DRF model + 스캐폴딩 후 DevOps 영역에서 Dockerfile & Docker Compose 환경을 프로젝트와 정합하게 구현하는 방법 + 문법 + 개념 + 매커니즘 학습

> 체크박스는 Owner가 "설명할 수 있다"고 판단되면 직접 채운다. 본 세션은 그 판단을 돕는 자료다.

---

# Part A — API 명세서에서 데이터 모델을 도출하는 방법

## A.1 개념: 왜 API 명세가 모델의 1차 출처인가

REST API에서 **엔드포인트는 "자원(resource)"을 다루고, 자원은 대부분 DB 테이블 1개에 대응**한다.
따라서 API 명세를 잘 읽으면 모델의 80%가 이미 결정되어 있다.

명세에서 모델 신호를 읽는 4가지 위치:

1. **URI의 명사** → 엔티티 후보 (예: `concerns`, `advices`, `feedbacks`, `notifications`, `assignments`)
2. **Request 필드** → 사용자가 입력하는 컬럼 (예: `concern_summary`, `directional_guidance`)
3. **Response 필드** → 저장 또는 파생되어야 하는 컬럼 (예: `created_at`, `status`, `version`)
4. **Side Effect / 접근 제어 / 상태 전이 설명** → 관계, 상태 enum, 감사(audit) 테이블, 인덱스/제약 신호

> 핵심: Request·Response 필드를 그대로 1:1로 컬럼화하지 않는다. CLAUDE.md §8대로
> **응답 필드는 직렬화(Serializer) 단계에서 의도적으로 고르는 것**이고, 모델 컬럼은 "저장이 필요한 진짜 상태"만 둔다.
> 예: `has_approved_advice`, `unread_count`, `assignment_count`는 **응답 파생값(계산)** 이지 컬럼이 아니다.

## A.2 매커니즘: 도출 6단계

API 명세 1건을 모델로 바꾸는 반복 절차.

```
1) 자원 명사 추출      : URI에서 복수형 명사를 뽑는다 → 엔티티 후보
2) 소유/행위자 식별    : "누가 만드는가/누구 것인가" → FK(작성자, 수신자, 배정자)
3) 입력 필드 → 컬럼    : Request 필수/선택 필드를 컬럼으로. 길이 제한은 검증/컬럼 제약 후보
4) 상태/플래그 식별    : status enum, is_* 불리언, version 같은 수명주기 필드
5) 관계 카디널리티 결정: 1:N / N:M / 1:1 을 Side Effect와 접근 제어 문장에서 확정
6) 파생값 분리         : 응답에만 있고 저장은 불필요한 값(count, has_* 등)은 컬럼에서 제외
```

마지막에 **감사/이력 테이블**(누가·언제·무엇을 바꿨나)을 별도로 본다.
chamneul에는 명세상 이미 3개 신호가 있다: 역할 부여 이력, 조언 본문 버전 이력, 배정 비활성 보존.

## A.3 chamneul 실제 적용 — 엔드포인트 → 핵심 테이블 후보

docs/api.md의 43개 엔드포인트를 A.2로 훑으면 다음 핵심 테이블이 도출된다.

| # | 테이블(후보) | 근거 엔드포인트(예) | 비고 |
| --- | --- | --- | --- |
| 1 | `User` | 2,3,7,8 (signup/login/me) | 계정. 비밀번호 해시, 상태(active/suspended/withdrawn) |
| 2 | `UserRole` | 9,10,42,43 | User ↔ Role(USER/ADVISOR/ADMIN) **M:N** |
| 3 | `RoleGrant` | 15(승인 시 부여),42,43 | 역할 부여/회수 **감사 로그** (ADR-003) |
| 4 | `AdvisorApplication` | 11~15 | 신청. `intended_lane`은 admin 전용(노출 금지) |
| 5 | `Concern` | 16~23 | 고민. 소프트 삭제(`is_deleted`) |
| 6 | `Assignment` | 24,25,20,21 | Concern ↔ Advisor **M:N**, 비활성 보존(`is_active`) |
| 7 | `Advice` | 27~33 | 조언. `version`, `is_submitted` |
| 8 | `AdviceHistory` | 29(수정 시 +1) | 조언 본문 **버전 감사** (CLAUDE.md §6.7) |
| 9 | `Feedback` | 34~38 | 조언 1건당 1개 |
| 10 | `Notification` | 39~41 | 수신자별 알림 |
| (—) | (Django `Session`) | 4,6 | **자체 모델 아님.** Django 기본 DB 세션 사용(ADR-002) |

> 학습 포인트: `/healthz`(엔드포인트 1)는 **테이블이 없다.** 모든 엔드포인트가 모델을 만드는 건 아니다.
> 또 `auth/login`·`logout`도 새 테이블을 만들지 않고 Django 내장 세션·User를 쓴다 — 명세를 보고
> "이건 새 모델인가, 기존/내장으로 충분한가"를 판단하는 것이 도출의 핵심 기술이다.

## A.4 관계(카디널리티) 도출

명세의 Side Effect / 접근 제어 문장에서 관계를 확정한다.

| 관계 | 카디널리티 | 명세 근거 |
| --- | --- | --- |
| User → Concern | 1:N | "본인 고민만" (18) |
| User ↔ Role | M:N (`UserRole`) | "여러 role 보유 가능" (api.md §2) |
| Concern ↔ Advisor | M:N (`Assignment`) | "1 concern ↔ N advisor" (24, Q9) |
| Concern → Advice | 1:N | 고민에 여러 조언 |
| (Concern, Advisor) → Advice | **1 advisor당 1 advice** | "advisor 1명당 concern 1건은 advice 1개" (28, Q10) → `unique(concern, advisor)` |
| Advice → AdviceHistory | 1:N | 수정마다 이전 본문 보존 (29) |
| Advice → Feedback | 1:1 | "조언 1개당 1회" (34) → `unique(advice)` |
| User → Notification | 1:N | "본인 수신 알림만" (39) |

> **N:M은 거의 항상 중간 테이블(join table)로 푼다.** `Assignment`는 단순 연결이 아니라
> `assigned_by`, `assigned_at`, `triage_decision`, `priority`, `is_active` 같은 **자체 속성**을 가지므로
> 명시적 모델로 둔다(Django의 암묵적 ManyToMany가 아니라 `through` 모델 개념).

## A.5 상태/enum 도출

CLAUDE.md §6 + api.md의 상태 전이 문장에서 enum을 그대로 가져온다. 모델에 박제할 상태값:

| 모델 | status 값 | 전이 규칙 출처 |
| --- | --- | --- |
| `AdvisorApplication` | PENDING / REVIEWING / APPROVED / REJECTED / WITHDRAWN | §6.1, 15 |
| `Concern` | SUBMITTED / ASSIGNED / ANSWERED / CLOSED | §6.6, 24/25/33 |
| `Advice` | PENDING / REVIEWING / APPROVED / REJECTED / DELETED | §6.2, 29/30/33 |
| `Feedback` | SUBMITTED / REVIEWED / ARCHIVED | §6.3, 38 |
| `Notification` | (type) ADVICE_APPROVED / ADVICE_REJECTED / ADVISOR_APPLICATION_APPROVED / ADVISOR_APPLICATION_REJECTED / ASSIGNMENT_CREATED | §6.4 |

> 학습 포인트: 상태값은 임의로 늘리지 않는다(§16 승인 게이트). 비표준 값(`published`, `pending_review` 등)은
> api.md §7.4에서 이미 표준값으로 매핑되어 있다 — 모델 enum은 그 표준값만 쓴다.

## A.6 인덱스/제약 후보 도출

조회 패턴(목록 필터, 접근 제어)에서 인덱스를, 중복 방지 규칙에서 unique 제약을 읽는다.

* **Unique**: `User.email`, `User.nickname`, `AdvisorApplication.display_name`,
  `unique(Concern, Advisor)` on `Advice`/`Assignment(active)`, `unique(advice)` on `Feedback`.
* **인덱스 후보(조회 필터로 자주 쓰임)**: 모든 FK(`author_user`, `concern`, `advisor_user`, `recipient_user`),
  각 `status`, `created_at`, `Concern.is_deleted`, `Assignment.is_active`, `Notification.is_read`.
* **부분/복합 인덱스 후보**: "내 고민 목록(소프트삭제 제외)" → `(author_user, is_deleted, created_at)`.

> CLAUDE.md §8 / ADR-001대로 목록 API는 N+1을 피해야 한다 — 인덱스는 그 1차 수단이고,
> 직렬화 단계의 `select_related`/`prefetch_related`가 2차 수단이다.

## A.7 학습용 예시 (모델 스케치 — 파일로 만들지 않음)

> 아래는 **개념 설명용 스케치**다. 실제 `concerns/models.py`가 아니다.
> 필드명/길이/제약의 최종 확정은 `docs/model.md` 작성 단계에서 한다.

```python
# 학습용 예시 — 실제 프로젝트 파일 아님
class Concern(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED"
        ASSIGNED  = "ASSIGNED"
        ANSWERED  = "ANSWERED"
        CLOSED    = "CLOSED"

    author = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="concerns")
    concern_summary = models.CharField(max_length=100)          # api.md 16: ≤100자
    concern_type = models.CharField(max_length=40)              # §6.5 taxonomy enum 키
    decision_context = models.TextField(blank=True)
    is_anonymous = models.BooleanField(default=True)            # api.md 16: default true
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SUBMITTED)
    is_deleted = models.BooleanField(default=False)             # §6.6 소프트 삭제
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["author", "is_deleted", "created_at"])]
```

읽는 법(매커니즘 복습):
- `ForeignKey` = 1:N의 "N쪽"에 FK 컬럼이 생긴다. `on_delete=PROTECT`로 작성자 삭제 시 고민이 사라지지 않게 보호(감사 보존 의도).
- `TextChoices` = §6.6 상태 enum을 코드로 박제. DB에는 문자열로 저장되지만 잘못된 값 입력을 막는다.
- `is_deleted`는 status가 아니라 **별도 플래그**(§6.6 결정) — 도출 단계 A.4/A.5에서 이미 구분했다.
- `indexes`는 A.6에서 도출한 "내 고민 목록" 조회 패턴을 그대로 반영.

## A.8 자가 점검 질문 (Part A)

1. `assignment_count`, `has_approved_advice`, `unread_count`는 컬럼인가 파생값인가? 왜?
2. Concern ↔ Advisor가 M:N인데 왜 `Assignment`를 명시적 모델로 두는가?
3. `Advice.version`을 컬럼으로 두면서도 `AdviceHistory`를 따로 두는 이유는?
4. `auth/login`은 왜 새 테이블을 만들지 않는가?
5. `Feedback`이 advice당 1건임을 DB 수준에서 보장하려면 어떤 제약이 필요한가?

---

# Part B — DRF 모델 + 스캐폴딩 → Dockerfile & docker-compose 정합 구현

## B.1 개념: 스캐폴딩이란 무엇이고 어디까지인가

"스캐폴딩(scaffolding)"은 **뼈대 생성**이다. 코드 로직이 아니라 디렉터리·설정·빈 모듈을 만드는 단계.

Django/DRF 스캐폴딩의 표준 매커니즘(개념만):

```
django-admin startproject config .   # 프로젝트 설정 패키지(config/) 생성
python manage.py startapp concerns   # 도메인 앱(개념: 1 도메인 = 1 앱) 생성
# → models.py 작성 → settings.py의 INSTALLED_APPS에 등록
python manage.py makemigrations      # 모델 변경을 "마이그레이션 파일"로 기록
python manage.py migrate             # 마이그레이션을 실제 DB 스키마에 적용
```

핵심 개념 2가지:
- **migration = 스키마의 단일 진실원천(source of truth).** ADR-001/§12대로 DB를 직접 손대지 않고
  모델→makemigrations→migrate로만 스키마를 바꾼다. 마이그레이션 파일은 git에 커밋한다.
- **앱 분리 = 도메인 분리.** CLAUDE.md 예상 트리의 `accounts/ concerns/ advisors/ advice/ notifications/`가
  Part A에서 도출한 테이블 그룹과 대응한다.

## B.2 매커니즘: 모델이 PostgreSQL에 연결되는 경로

```
settings.py DATABASES  ← os.environ (.env 로 주입)
        │
   Django ORM (모델/마이그레이션)
        │  TCP 5432
   PostgreSQL 컨테이너
```

- `settings.py`의 `DATABASES["default"]`는 `HOST/PORT/NAME/USER/PASSWORD`를 **환경변수에서** 읽는다(하드코딩 금지, §10).
- 로컬에서 app과 db가 둘 다 컨테이너면 `HOST`는 `localhost`가 아니라 **compose 서비스명**(예: `db`)이다 — 이게 B.4의 정합 포인트.

## B.3 Dockerfile 문법 & 개념

Dockerfile = "앱 이미지를 어떻게 굽는가"의 레시피. 핵심 명령어:

| 명령 | 의미 | 정합 포인트 |
| --- | --- | --- |
| `FROM python:3.x-slim` | 베이스 이미지(런타임 고정) | ADR-001: Python 버전 명확히 고정. slim=가벼움 |
| `WORKDIR /app` | 작업 디렉터리 | 이후 명령의 기준 경로 |
| `COPY requirements.txt .` → `RUN pip install` | 의존성 먼저 설치 | **레이어 캐시**: 의존성과 소스를 분리 COPY해야 코드만 바뀔 때 재설치 안 함 |
| `COPY . .` | 소스 복사 | `.dockerignore`로 `.env`·`.git` 제외(§10/§11) |
| `EXPOSE 8000` | 포트 문서화 | 실제 공개는 compose `ports`가 함 |
| `CMD [...]` | 컨테이너 시작 명령 | 예: gunicorn/runserver |

개념: **레이어 캐시.** Docker는 명령 한 줄 = 한 레이어. 위에서부터 바뀐 줄 이후만 다시 빌드한다.
그래서 "잘 안 바뀌는 것(의존성)"을 위에, "자주 바뀌는 것(소스)"을 아래에 둔다.

## B.4 docker-compose.yml 문법 & 개념

compose = "여러 컨테이너를 한 단위로 띄우는" 선언. ADR-001 §Decision 3 / §11 정합 요건을 그대로 반영해야 한다.

핵심 키 개념:

| 키 | 의미 | 프로젝트 정합 요건 |
| --- | --- | --- |
| `services:` | 컨테이너 목록 | **app + db 분리** (§11) |
| `image:` / `build:` | 이미지 출처 | db는 `postgres:16`처럼 버전 고정(ADR-001) |
| `environment` / `env_file` | 환경변수 주입 | `.env`에서 읽고 `.env.example`만 커밋(§10) |
| `ports: "15432:5432"` | 호스트:컨테이너 포트 | **호스트 포트 충돌 회피** 매핑(ADR-001) |
| `volumes:` (named) | 데이터 영속화 | **postgres 데이터는 named volume**(§11) |
| `depends_on` + `healthcheck` | 기동 순서/준비 대기 | app이 db 준비 후 떠야 함(B.6) |
| `networks` (기본) | 서비스 간 통신 | app이 db를 **서비스명 `db`** 로 접속(B.2) |

개념: compose는 기본적으로 **하나의 사용자 정의 네트워크**를 만들고, 서비스명이 곧 DNS 호스트명이 된다.
그래서 app 컨테이너의 `DB_HOST=db`가 동작한다(localhost가 아님). 이게 B.2와 맞물리는 "정합"의 정체다.

## B.5 "프로젝트와 정합하게"의 의미 — 정합성 체크리스트

Dockerfile/compose를 ADR·CLAUDE.md 결정과 어긋나지 않게 맞추는 점검표. (실구현 세션에서 검증)

* [ ] db 서비스 이미지가 **PostgreSQL**이고 버전이 고정돼 있다 (ADR-001 Decision 2)
* [ ] app·db가 **별도 서비스**로 분리돼 있다 (§11)
* [ ] postgres 데이터가 **named volume** 에 저장된다 (§11)
* [ ] `settings.DATABASES`가 **환경변수**로 주입되고 `DB_HOST`가 compose 서비스명과 일치한다 (B.2/B.4)
* [ ] 호스트 포트 매핑이 충돌을 피한다 (`15432:5432` 등, ADR-001)
* [ ] `.env`는 커밋 제외, `.env.example`만 존재, `.dockerignore` 존재 (§10/§11)
* [ ] `/healthz`가 200을 반환하고 compose/운영의 health check 근거가 된다 (§11)
* [ ] DEBUG 기본값, ALLOWED_HOSTS, `Secure` 쿠키가 비로컬에서 안전하게 동작 (§10, ADR-002)

## B.6 매커니즘: 요청 1건이 흐르는 경로 (DevOps 설명 포인트, §11)

```
curl http://localhost:8000/healthz
        │  (호스트 8000 → compose ports → app 컨테이너 8000)
   app 컨테이너 (Django/DRF)
        │  ORM, DB_HOST=db:5432  (compose 네트워크 DNS)
   db 컨테이너 (PostgreSQL, named volume)
```

장애 시나리오(설명 가능해야 함, §11):
- db 컨테이너가 안 떠 있으면? → app의 DB 쿼리는 connection error. `/healthz`를 **DB 비의존**으로 두면(api.md 1)
  앱 살아있음은 확인되지만 DB 장애는 안 잡힘 → 그래서 `/healthz/db`를 후속 검토로 남겨둠.
- `depends_on`만으로는 "db 프로세스 시작"만 보장하고 "db 접속 준비 완료"는 보장 못 함 → `healthcheck` 필요.

## B.7 학습용 예시 (Dockerfile / compose 골격 — 파일로 만들지 않음)

> **학습용 스케치**다. 실제 `Dockerfile`/`docker-compose.yml`이 아니다. 값은 실구현 세션에서 확정.

```dockerfile
# 학습용 예시 — 실제 파일 아님
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt   # 의존성 먼저 → 레이어 캐시
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]  # 운영은 gunicorn으로 교체 예정
```

```yaml
# 학습용 예시 — 실제 파일 아님
services:
  app:
    build: .
    env_file: .env
    environment:
      DB_HOST: db          # ← compose 서비스명이 곧 호스트명 (B.2/B.4 정합)
    ports: ["8000:8000"]
    depends_on:
      db:
        condition: service_healthy   # ← db 준비 완료까지 대기 (B.6)
  db:
    image: postgres:16
    env_file: .env
    ports: ["15432:5432"]            # ← 호스트 포트 충돌 회피
    volumes: ["pgdata:/var/lib/postgresql/data"]   # ← named volume (§11)
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"]
      interval: 5s
      retries: 5
volumes:
  pgdata:
```

## B.8 자가 점검 질문 (Part B)

1. app 컨테이너의 `DB_HOST`는 왜 `localhost`가 아니라 `db`인가?
2. Dockerfile에서 `requirements.txt`를 소스보다 먼저 COPY하는 이유(레이어 캐시)를 설명해 보라.
3. `depends_on`만으로 부족하고 `healthcheck`가 필요한 이유는?
4. postgres 데이터를 named volume에 두지 않으면 무슨 일이 생기는가?
5. `.env`와 `.env.example`의 차이, 그리고 `.dockerignore`가 필요한 이유는?

---

## 2. 보안 노트 (§10 / ADR-002)

* Secret(`SECRET_KEY`, `GOOGLE_OAUTH_CLIENT_SECRET`, DB 비밀번호)은 `.env`로만 — 절대 커밋 금지.
* `.env.example`에는 **예시/placeholder 값만**. 실제 값 금지.
* 세션 쿠키는 HttpOnly + Secure + SameSite=Lax(ADR-002). `Secure`는 비-localhost에서 강제.
* DEBUG는 운영에서 false. ALLOWED_HOSTS는 로컬 밖에서 명시.
* 본 학습 세션은 코드를 만들지 않으므로 직접적 보안 변경 없음 — 위는 실구현 세션의 체크 항목.

## 3. 검증/실습 권장 명령 (실행 안 함 — §12 "recommended command")

> 본 세션에서는 아무 명령도 실행하지 않았다. 아래는 실구현 세션에서 쓸 검증 명령 목록이다.

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
docker compose up -d
docker compose ps
curl http://localhost:8000/healthz
docker compose logs app
```

## 4. 다음 단계

1. (본 세션) 개념 내재화 — Part A/B 자가 점검 질문에 막힘없이 답할 수 있으면 §1 체크박스를 채운다.
2. `docs/model.md` + ERD 초안 작성 (Part A의 테이블/관계/상태/인덱스 도출 결과를 정식 문서화).
3. Owner 확인 후 비로소 코드 스캐폴딩(앱 생성 → 모델 작성 → makemigrations/migrate) 시작.
4. Dockerfile / docker-compose.yml은 B.5 정합성 체크리스트를 기준으로 구현·검증.

> api.md §6 Open Questions(글자 수 상한, draft 모델링 방식 등)는 `model.md` 작성 전에 Owner가 확정하면 좋다.

---

## 5. §14 리뷰 세션 형식 매핑 (참고)

| §14 항목 | 본 학습 세션 대응 |
| --- | --- |
| 무엇이 바뀌었나 | 신규 학습 문서 1건 추가. 기존 문서/코드 변경 없음 |
| 왜 이렇게 했나 | model 생성 전 Owner의 개념 내재화가 목적(코딩 전 정합성 우선, §17) |
| 핵심 파일 | `docs/learning/01-api-to-model-and-docker.md` (본 문서) |
| 어떻게 검증 | §3의 권장 명령 + Part A/B 자가 점검 질문(개념 검증) |
| DevOps 설명 포인트 | B.2/B.4/B.6 — 요청 흐름, 서비스명 DNS, healthcheck, 장애 시나리오 |
| 보안 노트 | §2 — Secret 분리, Secure 쿠키, DEBUG/ALLOWED_HOSTS |
| 다음 개선 | `docs/model.md` + ERD 초안 → 코드 스캐폴딩 |
