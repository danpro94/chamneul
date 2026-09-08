# PROJECT_CONTEXT — 변하지 않는 배경

> 마일스톤과 무관하게 유지되는 맥락이다. 자주 바뀌는 것은 `STATUS.md`에 있다.
> 이 문서는 **AI가 이 프로젝트에서 무엇을 최적화해야 하는지**를 알려준다.

---

## 1. 이 프로젝트는 두 가지다

| | 목적 | 결과 |
| --- | --- | --- |
| 제품 | 신뢰할 수 있는 인생 의사결정 가이드 서비스 | 동작하는 MVP 백엔드 |
| 포트폴리오 | DevOps / Cloud / Platform 역량 증명 | **Owner가 설명할 수 있는** 시스템 |

두 번째가 제약을 만든다. **Owner가 이해하고 설명하지 못하는 코드는 완성이 아니다** (CLAUDE.md §0). 영리한 코드보다 지루하고 설명 가능한 코드가 낫다.

## 2. Owner

* 백엔드 전문 개발자가 **아니다.** DevOps / Cloud 커리어 전환 중이다.
* 최종 목표는 AWS·EKS 운영 설명 가능성이다 — `docs/00-project/AWS_ASSIGNMENT_BRIEF.md` 참조.
* 팀 규모 1인. 리뷰어가 없으므로 **테스트와 증거가 리뷰를 대신한다.**
* 작업 언어는 한국어. 코드·식별자는 영어, 문서·커밋 본문은 한국어 중심.

## 3. AI가 최적화해야 하는 것

우선순위 순이다 (CLAUDE.md §0).

1. **정확성** — 동작하지 않는 코드는 논외
2. **유지보수성** — 6개월 뒤에 읽어도 이해되는가
3. **명시적 추론** — 왜 이렇게 했는지가 코드나 주석이나 문서에 남는가
4. **운영 설명 가능성** — 요청이 어디를 거치는지, 어디가 부서지는지 Owner가 말할 수 있는가
5. **보안**
6. **깨끗한 로컬 컨테이너 실행**
7. **유용한 문서**
8. **최소한이지만 의미 있는 MVP 범위**

## 4. 역할 분담 — `[소유]` / `[위임]` / `[읽기]`

`docs/learning/02-ai-collaboration-and-ownership-strategy.md` §2가 정본이다. 판정은 한 줄이다.

```
이 산출물이 DevOps 면접 화이트보드에 나오는가?
  Yes → [소유]  Owner 손코딩. AI는 코치·리뷰어·출제자만.
  No  → 시스템 흐름 설명에 필요한가?
          Yes → [읽기]  AI 생성 + Owner가 설명 가능할 때까지 질문.
          No  → [위임]  AI 생성 + Owner 검수.
```

### AI 수정 금지 구역 (`[소유]`)

```
Dockerfile
docker-compose.yml
docker-compose.override.yml
.env / .env.example
```

마이그레이션은 **작성은 `[위임]`, 적용·판독·롤백은 `[소유]`**다. AI가 `makemigrations`는 하되 `migrate`는 Owner가 실행한다.

### `[위임]` — AI 생성, Owner 검수

Django/DRF 앱 코드(모델·serializer·viewset·router·admin), 테스트 코드 대량 작성(**무엇을 테스트할지는 Owner가 지정**), SQL 최적화, 유틸 함수, 문서 초안.

> `[위임]` = 몰라도 됨이 **아니다.** 위임한 코드도 흐름을 설명할 수 있어야 한다. 포기하는 것은 백지 작성 숙련뿐이다.

### `[읽기]` — 작성은 안 해도 설명은 해야 함

Django 요청 수명주기(WSGI → 미들웨어 → view → ORM, 커넥션이 어디서 열리고 닫히는지), N+1·슬로우쿼리·커넥션 고갈이 인프라 장애로 전이되는 경로, HTTP 시맨틱·상태 코드·세션·쿠키·CSRF, 트랜잭션/락/인덱스의 운영 영향.

## 5. 지켜야 하는 제약

| 제약 | 근거 |
| --- | --- |
| **PostgreSQL 전용.** 전 단계에서 SQLite 미사용 | CLAUDE.md §4 — `ArrayField`·JSONB·부분 유니크를 1일차부터 쓴다 |
| **Session 인증 단일 전략.** JWT·DRF Token·Knox 미도입 | ADR-002 |
| **새 서드파티 패키지는 Owner 승인 게이트** | CLAUDE.md §16 |
| **pytest 미도입.** Django 기본 test runner + DRF `APITestCase` | Owner 결정 G5 |
| **CLAUDE.md 직접 수정 금지.** 이견은 ADR로 제안 | CLAUDE.md §16 헌법 락 |
| **파일 삭제는 Owner 승인** | CLAUDE.md §16 |
| **소프트 삭제는 `deleted_at` + 부분 유니크 인덱스.** 소프트 삭제 모델에 평범한 `unique=True` 금지 | CLAUDE.md §6.6 — 탈퇴 사용자 이메일이 신규 가입을 막는 실패 모드 |
| **taxonomy 11종 고정.** 임의 추가 금지 | CLAUDE.md §6.5 |

## 6. 반복하면 안 되는 안티패턴

`docs/learning/02` §3이 연구 저득점 패턴과 1:1로 대응시킨 것들이다.

* 완전 위임 후 "딸깍 merge" — 이해도 40% 미만 코호트의 패턴
* 에러를 AI에게 "해결시키기" — 대신 **가설 검증 질문**만 던진다
* 리뷰 노트를 읽기만 하고 끝내기 — 재인(recognition)은 인출(recall)이 아니다
* 스스로 설명 못 하는 코드 merge
* **AI의 "완료했습니다"를 증거로 수용하기** — 증거는 테스트 통과·스모크 통과·기대 응답 실측뿐이다

## 7. 왜 Notion을 떠났는가

Notion DB는 v0(41 엔드포인트)에서 멈췄고, v1(43)이 `docs/api.md`로 확정된 뒤 한 번도 동기화되지 않았다. `docs/api.md` §7에 동기화 계획이 있었으나 실행된 적이 없다.

수기 동기화는 (1) 실효가 없었고 (2) 같은 정보를 두 곳에서 관리하게 만들었으며 (3) 현업 수준에 미치지 못한다. 2026-09-08 Owner 결정으로 폐지했다 (ADR-005).

**대체물은 `DECISION_INDEX.md`다** — 내용을 복사하지 않고 이미 존재하는 문서를 가리키기만 한다. 관리 비용이 0에 수렴한다.

## 8. 참조

* 제품 배경: `docs/1 서비스기획_v1.md` (공개 요약본) · `docs/2 mvp-scope_v1.md`
* 아키텍처 결정: `docs/adr/`
* 운영 모델 정본: `docs/learning/02-ai-collaboration-and-ownership-strategy.md`
* Phase 3 목표: `docs/00-project/AWS_ASSIGNMENT_BRIEF.md`
