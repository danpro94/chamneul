# 학습 세션 02 — AI 협업 역할 분담 & 소유권 전략 (Ownership Strategy)

> 목적: 2026-07-02 세션에서 확정한 처방 1~4(역할 재분배 / 백지 재현 / explain-first 노트 / 장애 드릴)를
> 이 프로젝트의 **실행 규칙**으로 전환한다.
> CLAUDE.md는 동결 상태(§16 헌법 락)이므로 **CLAUDE.md를 수정하지 않고**, 본 문서 + `.claude/agents/` 3종으로 분리 구현한다.
> 본 문서는 CLAUDE.md §0의 목표("Owner가 이해하고 설명할 수 있어야 한다")를 달성하기 위한 **메커니즘 계층**이며, 헌법 개정이 아니다.

---

## 0. 세션 메타

| 항목 | 내용 |
| --- | --- |
| 세션 종류 | 전략 수립 + 도구 구현 (코드 아님) |
| 날짜 | 2026-07-02 |
| 산출물 | 본 문서, `.claude/agents/drill-master.md`, `.claude/agents/chaos-coach.md`, `.claude/agents/ops-reviewer.md` |
| 근거 | 멘토 과제(운영 설명가능성·반복숙달), METR 2025 RCT, Anthropic 스킬 형성 연구, Osmani 70% 문제 |
| 최우선순위 | **Production 운영 가능 수준(Phase 3+, Managed EKS) 도달이 중요·긴급 1순위.** 학습 장치는 압축판으로 인라인 삽입 |

---

## 1. CLAUDE.md 갭 분석 → 구현 매핑

CLAUDE.md §0은 목표(운영 설명가능성)를 이미 선언하지만, **달성 메커니즘**이 없다. 갭 4개:

| # | 전략 요구 | CLAUDE.md 현황 | 갭 | 구현 위치 |
| --- | --- | --- | --- | --- |
| A | 처방1: 인프라 산출물은 Owner 손코딩 | §15는 Claude가 모든 편집 수행을 전제. §11은 산출물 "기준"만 정의, **작성 주체** 미정의 | 소유 구역(ownership zone) 규정 없음 | 본 문서 §2 + `ops-reviewer` + §5 [소유 세션] 프롬프트 |
| B | 처방2: 백지 재현을 합격선으로 | §12 검증은 **코드 정확성**만. §1 Phase 완료 기준에 Owner 이해 검증 없음 | "Owner가 재현·설명 가능"이라는 게이트 부재 | 본 문서 §4 게이트 + `drill-master` |
| C | 처방3: explain-first 노트 | §14 리뷰 노트는 **Claude가 작성** → Owner는 수동 소비(재인≠인출) | 노트 작성 순서 역전 규칙 없음 | 본 문서 §6 노트 규칙 |
| D | 처방4: 의도적 장애 주입 | §11에 "DB 불가 시 무슨 일이 일어나는가 설명" 요구는 **있음**(씨앗) — 훈련 메커니즘은 없음 | 드릴 시나리오·케이던스 부재 | 본 문서 §4 드릴 카탈로그 + `chaos-coach` |

> 선택 후속: 이 프로토콜을 미래 세션에도 구속력 있게 만들려면 ADR(예: "AI 협업·학습 프로토콜")로 승격 가능.
> §2 Source of Truth에서 ADR은 우선순위 2이므로, ADR화하면 모든 미래 Claude 세션이 자동으로 따른다. Owner 결정 사항.

---

## 2. 스킬 소유권 맵 (Skill Ownership Map)

### 2.0 라우팅 규칙 (한 줄 판정)

```
이 산출물/지식이 DevOps 면접 화이트보드에 나오는가?
  Yes → [소유] Owner 손코딩. AI는 코치·리뷰어·출제자만.
  No  → 시스템 흐름을 설명하는 데 필요한가?
          Yes → [읽기] AI 생성 + Owner가 설명 가능할 때까지 질문.
          No  → [위임] AI 생성 + Owner 검수.
```

### 2.1 [소유] 목표 스킬 — Owner 손코딩

**Tier 1 — 지금 (Phase 2, 로컬 컨테이너):**

* Dockerfile (레이어 캐시, 멀티스테이지, 비루트 실행)
* docker-compose.yml (네트워크/서비스명 DNS, named volume, healthcheck, depends_on)
* `.env` / `.env.example` / 시크릿 위생, `.dockerignore`
* 로컬 기동·재기동·초기화 절차 (`up/down/-v` 판단 포함)
* 로그 읽기 (`docker compose logs`, Django 에러 트레이스 따라가기)
* 마이그레이션 **운영** (적용/롤백/실패 시 조치 — 작성은 AI여도 운영은 Owner)
* `/healthz` 설계 의미와 한계 (무엇을 보장하고 무엇을 못 보는가)
* 포트/네트워크 디버깅 (`curl -v`, `docker compose exec`, `ps`, 포트 충돌)

**Tier 2 — AWS·EKS 본편 (Phase 3, 멘토 과제의 핵심):**

* 네트워킹: VPC/서브넷/라우팅/SG/NACL, DNS, TLS 종료 지점, ALB/NLB(L7/L4), Ingress
* IaC: Terraform (state 개념, plan/apply 읽기, 모듈화, drift)
* k8s 핵심: Pod/Deployment/Service/Ingress/ConfigMap/Secret, liveness·readiness probe(→ `/healthz`가 여기로 연결), requests/limits, HPA
* EKS 특수사항: IRSA/Pod Identity, aws-load-balancer-controller, EBS CSI, 노드그룹/Fargate 선택
* CI/CD: GitHub Actions 파이프라인 구조, ECR 푸시, 이미지 스캔, 배포 전략(rolling/blue-green/canary), GitOps(ArgoCD) 개념
* 관측성: 로그·메트릭·트레이스 3기둥, CloudWatch/Prometheus/Grafana, 알람 설계, SLI/SLO
* 장애 대응: 런북, 인시던트 절차, 포스트모템, RDS 백업/PITR, RTO/RPO
* 보안: IAM 최소권한, Secrets Manager, 이미지·의존성 스캔, NetworkPolicy, OIDC. (한국 시장: ISMS-P 존재 인지 수준)
* 비용: 태깅, 예산 알람, right-sizing (1인 스타트업 생존 기술)

**Tier 3 — 미래 대비 (2026+ 트렌드, 인지→점진 심화):**

* 플랫폼 엔지니어링 (IDP, golden path — SV 주류화)
* MSA 마이그레이션 판단력: 분리 기준, 도메인 경계, 데이터 분리, 이벤트/큐(SQS/Kafka), 서비스 메시 도입 판단
* FinOps, 공급망 보안(SBOM/SLSA) 기초
* AI 인프라 운영 기초(GPU 노드, 인퍼런스 서빙) + AIOps 도구를 **지휘**하는 능력

### 2.2 [위임] 비목표 스킬 — AI 생성, Owner 검수

* Django/DRF 앱 코드: 모델 선언, serializer, viewset, router, admin 등록
* 단위/통합 테스트 코드 대량 작성 (단, **무엇을 테스트할지**는 Owner가 지정)
* SQL 세부 최적화·복잡 쿼리 작성 (읽고 판단은 [읽기]로)
* 정규식, 유틸 함수, 데이터 변환 스크립트, 커밋 메시지·문서 초안
* 프론트엔드 구현 전반

### 2.3 [읽기] read-level 필수 — 작성은 안 해도 설명은 해야 함

* Django 요청 수명주기: WSGI/ASGI → 미들웨어 → view → ORM (커넥션이 어디서 열리고 닫히는지)
* N+1·슬로우쿼리·커넥션 고갈이 **인프라 장애로 전이되는 경로**
* HTTP/REST 시맨틱, 상태코드, 세션·쿠키·CSRF (ADR-002 수준)
* 트랜잭션/락/인덱스의 운영 영향
* git 워크플로

> "[위임] = 몰라도 됨"이 아니다. 위임 코드도 [읽기] 수준(흐름 설명 가능)은 유지한다. 포기하는 것은 **백지 작성 숙련**뿐이다.

---

## 3. 소유권 루프 (작업 단위 운영 체계)

모든 작업 단위(마일스톤/모듈)에 적용하는 6단계:

```
1) 설계 선언  — Owner가 무엇을/왜/수용기준(AC)을 선언. AI에게 "이 설계의 약점을 공격하라"(pre-mortem) 요청.
2) 라우팅    — §2.0 규칙으로 [소유]/[위임]/[읽기] 태그 부여.
3) 생산      — [위임]: AI가 코드+설명 동시 생성(연구 고득점 패턴).
              [소유]: Owner 손코딩, AI는 체크리스트/힌트만 (ops-reviewer).
4) 이중 검증 — 기술 검증(§12 명령) + 이해 검증(drill-master 퀴즈 3~5문).
              퀴즈에서 설명 못 한 항목 = "학습 부채"로 기록 (merge는 막지 않되 부채는 남긴다).
5) 운영 드릴 — 마일스톤당 1개만 (§4 카탈로그, chaos-coach). 이미 띄운 것을 죽이는 방식이라 추가 구축 비용 ≈ 0.
6) 기록      — explain-first 노트(§6) → docs/reviews/ + README_AIUSAGE.md 갱신.
```

**안티패턴 (연구 저득점 패턴과 1:1 대응 — 금지):**

* 완전 위임 "딸깍 merge" (이해도 40% 미만 코호트의 패턴)
* AI 반복 디버깅 의존 — 에러를 AI에 "해결"시키지 말고 "가설 검증 질문"만 할 것
* 리뷰 노트 읽기만 하고 끝내기 (재인은 인출이 아니다)
* 스스로 설명 못 하는 코드 merge (CLAUDE.md §0 위반이기도 함)

---

## 4. 시간 압축 실행 계획 (Production-First)

**원칙: 학습을 별도 트랙으로 만들지 않는다. 마일스톤 게이트에 인라인 삽입한다.**
예산: 마일스톤당 학습 오버헤드 ≤ 90분 (선요약 10분 + 드릴 ≤30분 + 퀴즈 ≤15분. 백지 재현은 레이어 전환점에만 별도 45분).

### 4.1 마일스톤 게이트

| 마일스톤 | 라우팅 | 게이트 (통과 조건) |
| --- | --- | --- |
| M1 스켈레톤 (완료) | [위임] 완료분 | 소급 1건만: 선요약 5줄 작성 (10분) |
| M2 Dockerfile/compose | **[소유] 구간** | Owner 손코딩 + ops-reviewer 리뷰 통과 + 드릴 #1 + **WB-1 백지 재현** |
| M3 모델/마이그레이션 | [위임]+운영은[소유] | drill-master 퀴즈 + 드릴 #2 |
| M4 API 구현 | [위임] | 퀴즈 + 드릴 #3 |
| M5 스모크/문서 | [읽기] | 드릴 #4 + **WB-2 (Phase 2 종합)** |
| Phase 3 진입 | **전부 [소유]** | Terraform/EKS는 소유 구역. WB-3, WB-4 + EKS 드릴 |

### 4.2 장애 드릴 카탈로그 — Phase 2 (compose 레벨, 각 15~30분)

| # | 시나리오 | 주입 | Owner가 해야 하는 것 |
| --- | --- | --- | --- |
| 1 | DB 다운 | `docker compose stop db` | 앱 증상 관찰 → 로그로 원인 특정 → 복구 → `/healthz`의 한계 설명 |
| 2 | 마이그레이션 실패 | 충돌 마이그레이션 시나리오 (chaos-coach가 안전 범위 안내) | `showmigrations` 판독 → 롤백 절차 수행 |
| 3 | 잘못된 env | DB 비밀번호 오타 후 재기동 | 부팅 로그에서 인증 실패 식별 → 환경변수 주입 경로 추적 |
| 4 | 볼륨 소실 | `docker compose down -v` (사전 동의 필수) | 데이터 초기화 재구성 절차 + "백업이 있었다면?"의 답 |
| 5 | 포트 충돌 | 호스트 8000 선점 후 `up` | 에러 메시지 판독 → 포트 매핑 개념 설명 |
| 6 | healthcheck 실패 | healthcheck 명령 고의 오타(복사본에서) | `depends_on` 대기 관찰 → started ≠ ready 체화 |

### 4.3 장애 드릴 — Phase 3 (EKS, 면접 단골)

CrashLoopBackOff(잘못된 CMD) / ImagePullBackOff(태그 오타) / OOMKilled(낮은 limits) / readiness 실패(경로 오타) / IAM 거부(IRSA 누락) — 각각 `kubectl describe`/`logs`/`events`로 진단.

### 4.4 백지 재현(WB) — 면접 화이트보드에 나올 것만, 총 4회

규칙: 프로젝트 문서·과거 코드 열람 금지. **공식 레퍼런스 문법 조회는 허용** (면접도 문법 암기가 아니라 구조·이유를 본다).

| # | 시점 | 과제 | 제한 |
| --- | --- | --- | --- |
| WB-1 | M2 직후 | 빈 폴더에서 Dockerfile + compose + settings 분할 재현 | 45분 |
| WB-2 | Phase 2 종료 | 요청→컨테이너→DB 흐름도 그리기 + 장애점 3개 구두 설명 | 15분 |
| WB-3 | Phase 3 초 | VPC/서브넷/ALB→EKS 트래픽 흐름도 | 20분 |
| WB-4 | Phase 3 중 | Deployment+Service+Ingress 매니페스트 백지 작성 | 30분 |

채점: `drill-master`에게 결과물 경로를 주고 기준 산출물과 diff 채점 요청.

---

## 5. 세션 프롬프트 템플릿 (Claude Code CLI 복붙용)

**[위임 세션] — 앱 보일러플레이트:**

```
이번 세션은 [위임] 세션이다. docs/learning/02 §2 소유권 맵을 따른다.
<모듈명>의 모델/serializer/viewset/router/admin을 생성하라.
단: (1) Dockerfile, docker-compose.yml, .env* 는 절대 건드리지 마라 — Owner 소유 구역이다.
(2) 각 파일에 "무엇을/왜" 설명을 함께 제공하라 (코드+설명 동시).
(3) 마지막에 내가 답해야 할 이해 확인 질문 3개를 제시하고, 내 답을 받아 채점하라.
```

**[소유 세션] — 인프라 손코딩:**

```
이번 세션은 [소유] 세션이다. 나는 <Dockerfile|docker-compose.yml|...>를 직접 작성한다.
너는 코치다: 코드를 제안·생성하지 말고, (1) 시작 전 요구사항 체크리스트(CLAUDE.md §10·§11, ADR-001,
docs/learning/01 §B.5 근거)만 제시하고, (2) 내가 막혔다고 말할 때만 단계적 힌트(위치→현상→원인 순)를 줘라.
작성이 끝나면 ops-reviewer 서브에이전트로 리뷰하라.
```

**[드릴 세션]:**

```
chaos-coach 서브에이전트로 현재 마일스톤에 맞는 드릴 1개를 진행하자.
docs/learning/02 §4.2 카탈로그에서 선택. 진단·복구는 내가 한다. 30분 제한.
```

**[채점 세션]:**

```
drill-master 서브에이전트로 방금 끝낸 작업에 대해 퀴즈 5문을 내라.
(개념 1, 매커니즘 2, 장애 시나리오 2.) 내 답을 받기 전에 정답을 말하지 마라.
끝나면 학습 부채 목록을 갱신해서 보여줘라.
```

---

## 6. explain-first 노트 규칙 (압축판)

§14 리뷰 노트는 유지하되, **AI가 노트를 쓰기 전에** Owner가 아래 5줄을 먼저 쓴다(10분). AI 노트 최상단에 그대로 보존한다.

```markdown
## Owner 선요약 (AI 노트 읽기 전, 기억만으로)
1. 오늘 바뀐 것:
2. 왜 이 방식인가:
3. 요청이 흐르는 경로:
4. 가장 부서지기 쉬운 지점:
5. 아직 설명 못 하는 것:   ← 학습 부채로 등록
```

AI는 선요약과 실제 구현의 차이(diff)를 노트 본문에서 짚는다 — 이것이 "생성 후 이해 질문" 고득점 패턴의 문서화 버전이다.

---

## 7. 에이전트 3종 사용법

| 에이전트 | 역할 | 호출 예 |
| --- | --- | --- |
| `drill-master` | 퀴즈 출제·채점, 백지 재현 채점, 학습 부채 관리. 정답 선공개 금지 | "drill-master로 오늘 작업 퀴즈 내줘" |
| `chaos-coach` | 장애 주입 드릴 진행. 힌트 3단계, 직접 수리 금지, 5줄 포스트모템 수취 | "chaos-coach로 드릴 1번 하자" |
| `ops-reviewer` | Owner 손코딩 인프라 파일 전용 리뷰. 재작성 금지, 코멘트+근거 조항만 | "ops-reviewer로 내 Dockerfile 리뷰해줘" |

파일 위치: `.claude/agents/*.md` — Claude Code CLI가 자동 인식한다(다음 세션부터).

---

## 8. 다음 단계

1. M2(Docker 레이어)부터 본 전략 적용 — 첫 [소유 세션] 실행.
2. (선택) 본 프로토콜의 ADR 승격 — 미래 세션 구속력 확보. Owner 결정.
3. 학습 부채 목록은 drill-master가 세션마다 갱신 — Phase 2 종료 시 부채 0이 목표가 아니라, **WB-2 통과**가 목표.
