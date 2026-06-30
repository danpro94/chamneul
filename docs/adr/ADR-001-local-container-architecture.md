# ADR-001. 로컬 컨테이너 기반 MVP 개발 아키텍처 결정

## Status

Accepted

## Date

2026-06-14 (update 2026-06-22)

## Context

본 프로젝트는 **신뢰할 수 있는 인생 의사결정 가이드 서비스**를 목표로 한다.

MVP 단계에서는 사용자가 고민을 작성하고, 고민 목록을 조회하며, 이후 조언·평가·결과 기록으로 확장 가능한 최소 백엔드 API를 확보하는 것이 핵심이다.

현재 Phase 2의 목표는 AWS 배포 이전에 다음을 로컬 환경에서 먼저 검증하는 것이다.

- Django 기반 API 서버 실행
- 핵심 도메인 모델 구현
- PostgreSQL 연결
- `/healthz` Health Check 제공
- 고민 작성/조회 API 제공
- Django Admin을 통한 데이터 확인
- Docker Compose 기반 로컬 실행 환경 확보

따라서 본 ADR은 로컬 MVP 개발을 위한 주요 기술 선택과 그 이유, 트레이드오프, 보완 전략을 기록한다.

---

## Decision Summary

본 프로젝트의 로컬 MVP 아키텍처는 다음과 같이 결정한다.

| 항목 | 결정 |
| --- | --- |
| Backend Framework | Django + Django REST Framework |
| API 구현 방식 | 초기 MVP는 `ModelSerializer` + `ModelViewSet` 중심 |
| Database | PostgreSQL |
| Local Runtime | Docker Compose |
| Auth | Session(SSR) + HttpOnly Cookie 단일안. Google OAuth 콜백도 동일 세션을 발급. JWT/DRF Token/Knox 미사용. 세부 정책은 ADR-002. |
| Health Check | `/healthz` 제공 |
| 운영 확장 방향 | 로컬 Compose → AWS RDS/ECS 또는 EKS 확장 가능 구조 |

---

## Decision 1. Django REST Framework 사용

### 결정

초기 MVP API 구현에는 Django REST Framework를 사용한다.

특히 빠른 API 프로토타이핑을 위해 `ModelSerializer`와 `ModelViewSet`을 우선 사용한다.

### Why

MVP 단계의 핵심은 복잡한 비즈니스 로직보다 다음을 빠르게 확보하는 것이다.

- 고민 작성 API
- 고민 목록 API
- 고민 상세 조회 API
- 사용자 인증 API
- Admin 기반 데이터 확인
- 컨테이너 환경에서 API 동작 검증

`ModelSerializer`와 `ModelViewSet`은 Django 모델 기반 CRUD API를 빠르게 구성할 수 있어 초기 MVP 개발 속도에 적합하다.

또한 본 서비스의 초기 MVP는 복잡한 도메인 연산보다 **사용자 입력 데이터의 저장·조회·상태 관리** 비중이 높다. 따라서 초기에는 생산성을 우선하고, 복잡한 성능 이슈가 실제로 발생하는 지점에서 리팩토링하는 전략을 선택한다.

---

## DRF 사용에 따른 Trade-Offs

### 장점

- CRUD API를 빠르게 구성할 수 있다.
- Django 모델과 직렬화 구조를 자연스럽게 연결할 수 있다.
- 표준 REST API 형태를 빠르게 확보할 수 있다.
- MVP 단계에서 API 엔드포인트 수가 많지 않으므로 개발 효율성이 높다.
- Admin, ORM, Serializer, ViewSet을 함께 사용해 데이터 흐름을 빠르게 검증할 수 있다.

### 단점

- `ModelSerializer`는 불필요한 필드가 응답에 포함될 수 있다.
- 관계형 데이터가 늘어나면 N+1 쿼리 문제가 발생할 수 있다.
- 응답 구조를 세밀하게 제어하려면 오버라이딩 코드가 증가할 수 있다.
- 복잡한 비즈니스 로직이 많아질 경우 `ViewSet` 구조가 오히려 흐름을 숨길 수 있다.
- 커스텀 응답 포맷, 권한, 필터, 정렬, 집계 로직이 많아지면 보일러플레이트 코드가 증가할 수 있다.

---

## DRF 관련 보완 전략

초기에는 빠른 기능 구현을 위해 `ModelSerializer`와 `ModelViewSet`을 사용한다.

다만 다음 기준에 해당하면 `Serializer`, `APIView`, 커스텀 QuerySet, Service Layer 기반으로 리팩토링한다.

### 리팩토링 기준

- 응답 구조를 API별로 완전히 다르게 제어해야 하는 경우
- 불필요한 필드 직렬화로 응답 크기가 커지는 경우
- N+1 쿼리가 반복적으로 발생하는 경우
- `select_related`, `prefetch_related`, `annotate`가 필요한 경우
- ViewSet 내부 로직이 과도하게 복잡해지는 경우
- 비즈니스 규칙이 단순 CRUD 범위를 벗어나는 경우

### 보완 방식

- API 요구사항 작성 시 응답 필드 목록을 명시한다.
- AI 코드 생성 요청 시 N+1 쿼리 가능성을 반드시 점검하도록 요구한다.
- `select_related`, `prefetch_related`, `only`, `defer`, `annotate` 사용 여부를 코드 리뷰 항목에 포함한다.
- Django Debug Toolbar 또는 쿼리 로깅을 통해 API별 쿼리 수를 확인한다.
- 성능 이슈가 확인된 API는 `APIView` 또는 커스텀 Serializer로 전환한다.
- 커스텀 로직은 View 내부에 누적하지 않고 Service Layer로 분리한다.

### 개발 원칙

초기 MVP에서는 다음 원칙을 따른다.

```
빠른 구현: ModelSerializer + ModelViewSet
성능 이슈 발생: QuerySet 최적화
응답 구조 복잡화: Serializer 명시화
비즈니스 로직 증가: APIView + Service Layer 전환
```

---

## Decision 2. PostgreSQL 사용

### 결정 (Owner 갱신 2026-06-26)

로컬·개발·테스트·운영 데이터베이스는 **PostgreSQL 16+ 만** 사용한다. SQLite는 본 프로젝트의 어느 단계에서도 사용하지 않는다.

이유: PostgreSQL 전용 기능(`ArrayField`, `JSONB`, UUIDv7, 부분 unique 인덱스 등)을 모델 1차 결정부터 활용하기로 한 Owner 결정에 따라 호환성 비용보다 production 이점을 우선한다. 본 결정의 본문은 CLAUDE.md §4 Database 절에 흡수되었으므로, 향후 충돌 시 CLAUDE.md §4가 단일 진실원천이다.

### Why

PostgreSQL을 선택한 이유는 다음과 같다.

- 오픈소스이며 안정성과 확장성이 높다.
- 사용자 입력 데이터가 서비스의 핵심 자산이므로 신뢰성 있는 RDB가 필요하다.
- 향후 AWS RDS로 확장하기 쉽다.
- Docker Compose로 로컬 DB를 구성하면 팀원 간 동일한 DB 버전을 맞추기 쉽다.
- DevOps 관점에서 애플리케이션과 DB를 컨테이너 기반으로 함께 구성하는 경험이 중요하다.
- 로컬 개발 환경과 운영 환경의 구조적 차이를 줄일 수 있다.

본 서비스 도메인만 보면 MySQL도 충분히 적합하다.

그러나 본 프로젝트는 단순 서비스 구현이 아니라 DevOps 포트폴리오 목적을 포함한다. 따라서 로컬 개발용 인프라 오케스트레이션, 컨테이너 네트워크, 환경변수, 볼륨, DB 초기화, 운영 확장성을 함께 학습하기 위해 PostgreSQL을 선택한다.

---

## PostgreSQL Trade-Offs

### 장점

- 운영 환경과 유사한 RDB 기반 개발이 가능하다.
- Docker Compose로 DB 버전을 고정할 수 있다.
- 향후 RDS, 백업, 마이그레이션, 커넥션 풀링 학습으로 확장 가능하다.
- Django ORM과의 정합성이 높다.
- JSON 필드, 인덱스, 트랜잭션 등 확장 기능을 활용할 수 있다.

### 단점

- SQLite보다 초기 설정이 복잡하다.
- 로컬 컨테이너 실행 시 메모리와 디스크 리소스를 사용한다.
- 컨테이너 볼륨, 포트 충돌, 권한 문제를 관리해야 한다.
- 로컬 DB 설정이 운영 DB 설정과 완전히 동일하지는 않다.
- 운영 환경의 커넥션 수, 락 경합, 인덱스 병목, 풀 테이블 스캔 문제를 로컬에서 완전히 재현하기 어렵다.

---

## PostgreSQL 보완 전략

로컬 개발 환경에서는 다음 원칙을 따른다.

- PostgreSQL은 Docker Compose 서비스로 실행한다.
- DB 접속 정보는 `.env`로 분리한다.
- `.env.example`에는 예시 값만 제공한다.
- 개발 DB 포트는 호스트 충돌을 피하기 위해 `15432:5432` 형태로 매핑할 수 있다.
- migration은 Django ORM을 기준으로 관리한다.
- 모델 변경 시 `makemigrations`, `migrate` 결과를 문서화한다.
- 운영 전환 시 RDS 버전과 로컬 PostgreSQL 버전을 최대한 맞춘다.
- 성능 검증이 필요한 API는 쿼리 로그와 실행 계획을 확인한다.

---

## Decision 3. Docker Compose 사용

### 결정

로컬 개발 환경은 Docker Compose 기반으로 구성한다.

구성 대상은 최소 다음과 같다.

- Django API 서버
- PostgreSQL DB
- 필요 시 Redis, Celery, Mailhog 등 추가 의존성

### Why

본 프로젝트는 단순 개인 개발 연습이 아니라 DevOps 관점의 협업 프로젝트이자 커리어 포트폴리오 목적을 가진다.

따라서 로컬 네이티브 실행에만 의존하지 않고, 의도적으로 컨테이너 기반 개발 환경을 선택한다.

Docker Compose를 사용하는 이유는 다음과 같다.

- 앱과 DB를 하나의 실행 단위로 관리할 수 있다.
- 팀원 간 개발 환경 차이를 줄일 수 있다.
- 로컬 환경에서 운영 환경과 유사한 구조를 경험할 수 있다.
- 환경변수, 네트워크, 볼륨, 포트, 의존성 관리를 학습할 수 있다.
- 이후 ECS, EKS, Kubernetes로 확장할 때 개념 전환이 쉽다.

단, Docker Compose가 로컬과 운영 환경의 차이를 완전히 제거하는 것은 아니다.

정확한 표현은 다음과 같다.

```
Docker Compose는 로컬과 운영 환경의 차이를 완전히 제거하지는 못하지만,
애플리케이션 실행 방식, 의존성 구성, 네트워크 구조의 차이를 크게 줄여준다.
```

---

## Docker Compose Trade-Offs

### 장점

- `docker compose up`으로 앱과 DB를 함께 실행할 수 있다.
- Python, PostgreSQL 버전을 명확하게 고정할 수 있다.
- 로컬 환경 오염을 줄일 수 있다.
- 신규 팀원이 빠르게 동일 환경을 구성할 수 있다.
- DevOps 관점에서 컨테이너 실행 단위의 기본기를 확보할 수 있다.

### 단점

- 호스트 OS와 컨테이너 간 파일 권한 문제가 발생할 수 있다.
- Windows, macOS, Linux 간 볼륨 마운트 성능 차이가 있을 수 있다.
- 다중 컨테이너 실행 시 리소스 사용량이 증가한다.
- Compose 파일이 커질수록 네트워크, 볼륨, 환경변수 관리가 복잡해진다.
- 운영 환경의 오토스케일링, 로드밸런싱, 보안그룹, IAM까지는 재현할 수 없다.

---

## Docker Compose 보완 전략

- 개발용 Compose와 운영용 배포 설정을 분리한다.
- `.env.example`을 제공해 필수 환경변수를 명시한다.
- `.dockerignore`를 작성해 불필요한 파일이 이미지에 포함되지 않게 한다.
- 컨테이너 이름, 포트, 볼륨 이름을 명확하게 관리한다.
- DB 데이터는 named volume으로 유지한다.
- 초기화가 필요한 경우 `docker compose down -v` 사용 기준을 문서화한다.
- Health Check API를 먼저 만들어 컨테이너 정상 동작 여부를 확인한다.

---

## Decision 4. 인증 전략

### 결정 (Owner 확정 2026-06-22)

Phase 2부터 **Session-based 인증 단일 전략**을 채택한다. JWT, DRF Token, Knox는 사용하지 않는다.

구현 우선순위:

1. 이메일/비밀번호 회원가입·로그인 — 가입 즉시 자동 로그인(Set-Cookie 응답).
2. 로그아웃 — 서버 세션 레코드 삭제 + 클라이언트 쿠키 만료(`Max-Age=0`).
3. Google OAuth 콜백 — 같은 세션 모델로 통합. 동일 검증 이메일이면 기존 계정에 링크.
4. 세션 정책(쿠키 속성, TTL, 슬라이딩 갱신, 로그아웃 시맨틱) — `ADR-002-session-authentication-policy.md`에 별도 분리.

인증도 Phase 2 구현 범위이며, 고민 코어 API 와 함께 v1 명세에 포함된다.

---

## Auth Why

인증 전략이 필요한 이유는 다음과 같다.

- 고민 데이터는 사용자 개인 정보와 강하게 연결된다.
- 사용자의 고민, 조언 요청, 결과 기록은 반드시 사용자 단위로 분리되어야 한다.
- 향후 조언자, 신뢰 점수, 결과 추적 기능은 사용자 식별을 전제로 한다.
- Google OAuth는 초기 사용자 가입 장벽을 낮출 수 있다.
- 세션 기반 인증은 폐쇄형 웹 플랫폼+사용자의 민감정보를 다루는 현 프로젝트 도메인에 보안성 측면에서 적합하다.

---

## Auth Trade-Offs

### 자체 인증의 장점

- 서비스 내부 사용자 모델을 명확하게 제어할 수 있다.
- 이메일, 닉네임, 역할, 프로필 필드 확장이 쉽다.
- 권한 모델을 서비스 요구사항에 맞게 설계할 수 있다.

### 자체 인증의 단점

- 비밀번호 저장, 인증 실패 처리, 토큰 만료, 보안 정책 구현 부담이 있다.
- 초기 MVP 개발 속도를 늦출 수 있다.
- 보안 실수가 발생할 위험이 있다.

### Google OAuth의 장점

- 사용자의 가입 진입 장벽을 낮출 수 있다.
- 검증된 외부 인증 프로토콜을 활용할 수 있다.
- 비밀번호 관리 부담을 줄일 수 있다.

### Google OAuth의 단점

- OAuth redirect URI, client secret, callback 처리 등 설정 복잡도가 있다.
- 로컬 개발 환경과 배포 환경의 설정이 달라질 수 있다.
- 외부 인증 제공자 장애나 정책 변경에 영향을 받을 수 있다.

### 보완 방향

- 인증 관련 Secret(`SECRET_KEY`, `GOOGLE_OAUTH_CLIENT_SECRET` 등)은 `.env`로 분리하고 운영에서는 Secret Manager 계열로 옮긴다.
- 세션 저장소는 Phase 2에서는 Django 기본(DB 세션)을 사용한다. 트래픽 증가 시 Redis 세션으로 확장하는 것을 ADR-002 후속 결정으로 둔다.
- CSRF 보호는 모든 상태 변경 엔드포인트에서 활성화한다.

---

## Alternative Options Considered

### 1. Pure Django without DRF

초기 구현 복잡도는 낮출 수 있지만, REST API 표준화와 Serializer 구조를 직접 구현해야 한다.

MVP API가 16개 수준으로 예상되므로 DRF를 사용하는 편이 더 적합하다고 판단했다.

### 2. SQLite (기각, 2026-06-26)

초기 부팅 확인 용도로도 채택하지 않는다. PG 전용 필드(ArrayField, JSONB)와 UUIDv7 PK 전략을 모델 1차 결정부터 사용하기로 했기 때문에, SQLite를 함께 지원하면 모델 정의에 분기 비용이 발생한다. 본 결정의 본문은 CLAUDE.md §4 Database 절에 흡수되어 있다.

### 3. 로컬 네이티브 실행

설정이 단순하고 실행 속도가 빠르지만, 팀원 간 환경 차이와 운영 환경과의 차이가 커질 수 있다.

DevOps 포트폴리오 목적상 컨테이너 기반 개발 경험을 남기는 것이 더 중요하므로 채택하지 않는다.

### 4. 처음부터 Kubernetes 사용

운영 확장성 측면에서는 좋지만, MVP 단계에서는 과도하다.

현재 목표는 서비스 핵심 API와 로컬 컨테이너 실행 단위 확보이므로 Kubernetes는 이후 Phase에서 검토한다.

---

## Consequences

이 결정으로 인해 다음 결과를 기대한다.

### Positive

- 로컬에서 앱과 DB를 한 번에 실행할 수 있다.
- MVP API를 빠르게 구현할 수 있다.
- Django Admin으로 데이터 확인이 가능하다.
- AWS 배포 이전에 최소 실행 단위를 검증할 수 있다.
- DevOps 관점의 컨테이너 실행, 환경변수, DB 의존성 관리 경험을 확보할 수 있다.
- 이후 CI/CD, RDS, ECR, ECS/EKS, ALB Health Check로 확장하기 쉽다.

### Negative

- 초기 코드에 DRF ViewSet 의존성이 생긴다.
- 복잡한 비즈니스 로직이 생기면 리팩토링 비용이 발생한다.
- PostgreSQL과 Docker Compose 설정으로 인해 SQLite 대비 초기 복잡도가 증가한다.
- 로컬 컨테이너 환경과 실제 AWS 운영 환경은 완전히 같지 않다.
- 인증 구현 시 보안 고려사항이 추가된다.

---

## Implementation Guidelines

### API 구현 원칙

- 초기 CRUD API는 `ModelViewSet`을 사용한다.
- 응답 필드는 명시적으로 관리한다.
- 민감 정보는 Serializer에서 제외한다.
- 목록 API는 pagination을 고려한다.
- 관계형 데이터가 포함되는 경우 N+1 쿼리를 점검한다.
- 복잡한 로직은 ViewSet에 직접 누적하지 않고 Service Layer로 분리한다.

### DB 구현 원칙

- Django migration을 DB 스키마의 기준으로 삼는다.
- 모델 변경 후 migration 파일을 반드시 커밋한다.
- 기본 인덱스가 필요한 필드는 초기에 검토한다.
- 사용자 FK, 생성일, 상태값, 카테고리 필드는 조회 패턴을 고려한다.

### Docker 구현 원칙

- `Dockerfile`은 앱 실행에 필요한 최소 구성으로 작성한다.
- `docker-compose.yml`은 app, db 서비스를 분리한다.
- DB 데이터는 named volume에 저장한다.
- `.env.example`을 제공한다.
- 민감 정보는 Git에 커밋하지 않는다.
- `/healthz`로 앱 상태를 확인한다.

### Auth 구현 원칙

- Phase 2 v1에는 인증 전체 흐름(가입·로그인·로그아웃·Google OAuth·내 정보·역할)을 포함한다.
- 인증 방식은 Session-based 단일 전략이다. JWT/Token 기반 구현을 추가하지 않는다.
- 운영 환경에서는 HTTPS를 전제로 하며, `Secure` 쿠키 속성이 강제된다.
- 세션 정책 세부(쿠키명 `sessionid`, HttpOnly + Secure + SameSite=Lax, 만료 14일, 매 요청 슬라이딩 갱신, 로그아웃 시 서버 세션 삭제)는 `ADR-002-session-authentication-policy.md`로 분리한다.
- 관리자 역할 부여 흐름은 `ADR-003-admin-role-grant.md`로 분리한다.

---

## Validation Criteria

이 ADR의 결정이 올바르게 구현되었는지는 다음 기준으로 확인한다.

```bash
docker compose up -d
```

```bash
curl http://localhost:8000/healthz
```

```bash
curl http://localhost:8000/api/concerns/
```

```bash
docker compose exec app python manage.py migrate
```

```bash
docker compose exec app python manage.py createsuperuser
```

```
http://localhost:8000/admin/
```

완료 기준은 다음과 같다.

- Docker Compose로 Django 앱과 PostgreSQL이 함께 실행된다.
- `/healthz`가 200 OK를 반환한다.
- 고민 작성 API가 201 Created를 반환한다.
- 고민 목록 API가 저장된 데이터를 반환한다.
- Django Admin에서 고민 데이터를 확인할 수 있다.
- `.env.example`, `Dockerfile`, `docker-compose.yml`, `README.md`가 존재한다.

---

## Review Triggers

다음 상황이 발생하면 본 ADR을 재검토한다.

- API 엔드포인트가 20개 이상으로 증가하는 경우
- 복잡한 권한/역할 모델이 필요한 경우
- 조언자 매칭, 신뢰 점수, 결과 추적 로직이 본격적으로 추가되는 경우
- N+1 쿼리 또는 응답 지연 문제가 반복적으로 발생하는 경우
- Docker Compose만으로 로컬 환경 관리가 어려워지는 경우
- AWS RDS, ECS, EKS 등 운영 배포 구조가 확정되는 경우
- 인증 구조를 JWT, Knox, OAuth 중심으로 확정해야 하는 경우

---

## Final Decision

본 프로젝트는 Phase 2 로컬 MVP 단계에서 다음 구조를 채택한다.

```
Django + Django REST Framework
PostgreSQL
Docker Compose
/healthz
ModelSerializer + ModelViewSet 우선
성능·복잡도 증가 시 Serializer/APIView/Service Layer로 리팩토링
Session-based 인증 단일 전략 (자체 + Google OAuth 통합, ADR-002 참조)
```

이 결정은 초기 MVP의 빠른 구현과 DevOps 관점의 로컬 컨테이너 실행 경험을 동시에 확보하기 위한 선택이다.

현 단계에서는 과도한 최적화보다 **작동하는 최소 API, 명확한 실행 환경, 추후 리팩토링 가능한 구조**를 우선한다.