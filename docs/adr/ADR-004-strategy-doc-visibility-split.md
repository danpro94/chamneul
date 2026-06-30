# ADR-004. 전략 문서 공개 범위 분할 (Public 요약본 / Private 상세본)

## Status

Accepted

## Date

2026-06-30

## Context

chamneul 저장소를 독립 git 저장소로 초기화하면서 **Public 공개**를 결정했다. 이 프로젝트는 DevOps/Cloud/Platform 포트폴리오인 동시에 실제 서비스를 지향한다.

비밀정보 교차검증 결과, 자격증명(`.env` 등)은 git에 추적된 적이 없고 `.gitignore`로 적절히 제외되어 있음을 확인했다 (CLAUDE.md §10).

그러나 `docs/1 서비스기획_v1.md` 원본에는 자격증명과는 다른 범주의 민감 자산, 즉 **전략 IP**가 포함되어 있었다.

* 신뢰 비즈니스 모델 흐름 (생성 → 검증 → 전이 → 보증)
* ELO 기반 신뢰 점수 설계 (Layer1 Identity ~ Layer4 Accountability)
* 조언자(전문가·시니어) 평가 모델 (전문성·구체성·경험밀도·실패경험·반성·의사소통)
* 조언자 승인 의사결정 트리

이는 CLAUDE.md §5에서 Phase 3+로 미룬 **핵심 차별 역량(신뢰 점수 알고리즘, 매칭 로직)**의 설계 원형에 해당한다.

### 판단 근거 (Data-Driven)

* 초기 스타트업에서 **코드 자체는 해자가 아니다.** 다수의 공개-소스 기업(GitLab, Sentry, PostHog, Supabase, Cal.com 등)이 소스를 공개하고도 성장했으며, 해자는 실행력·데이터·네트워크·브랜드·유통에 있다. → MVP 수준 코드/기술 문서 공개는 경쟁 손실이 거의 없고 포트폴리오 이득이 크다.
* 반면 **사업 전략·평가 알고리즘 설계를 public repo에 통째로 커밋하는 것**은 경쟁자에게 제품 동작뿐 아니라 *설계 의도(reasoning)*까지 넘기는 별개 범주의 리스크다. 업계 표준 관행은 "코드는 public이어도 전략·스코어링 설계는 private(Notion/사내 위키/private repo)"이다.

---

## Decision

전략 문서를 **공개 요약본 / 비공개 상세본**으로 분할 발행한다 (옵션 B).

### 1. 3단계 분류 기준

| 등급 | 처리 | 대상 |
| --- | --- | --- |
| Tier 1 — 절대 비밀 | 커밋 금지 (기존 처리) | `.env`, OAuth/DB 자격증명, 사용자 PII, DB 덤프 |
| Tier 2 — 비공개 (전략 IP) | `docs/_private/` (git-ignored) | 신뢰 점수 설계, 조언자 평가 모델, 승인 트리, 추후 GTM/수익모델/재무/투자 자료 |
| Tier 3 — 공개 안전 (포트폴리오 자산) | public | 코드, `api.md`, `model.md`, ADR, `mvp-scope`, `README*`, Dockerfile/compose, ERD, 컨셉추얼 아키텍처, 서비스 기획 **요약본** |

### 2. 파일 배치

| 경로 | 공개 여부 | 성격 |
| --- | --- | --- |
| `docs/1 서비스기획_v1.md` | Public | 가공 요약본 (비전·문제·해결·차별점·시장정의). **파생물.** |
| `docs/_private/1 서비스기획_v1_full.md` | Private (git-ignored) | 원본 전체. 전략 IP의 **권위 있는 원본(source of truth).** |

* `docs/_private/`는 `.gitignore`에 등록한다.
* 공개 요약본 상단에는 분할 사실과 본 ADR 참조를 명시한다.

### 3. CLAUDE.md 정합성

* CLAUDE.md §2(Source of Truth)와 §3(프로젝트 트리)는 `docs/1 서비스기획_v1.md` 경로를 그대로 참조한다. 본 ADR은 **경로를 바꾸지 않으므로** 해당 참조는 유효하다.
* 다만 의미가 바뀐다: §2의 4순위 문서(`docs/1 서비스기획_v1.md`)는 이제 **공개 요약본**이며, 전략 세부의 권위 있는 원본은 `docs/_private/1 서비스기획_v1_full.md`다. 두 문서가 충돌하면 비공개 원본이 우선한다.
* CLAUDE.md는 constitutional lock 상태이므로 직접 수정하지 않는다. 본 ADR이 위 의미 해석을 보충한다.

---

## Rationale (Why)

* **분할 발행(B)은 포트폴리오 서사와 IP 보호를 동시에 만족한다.** 공개 요약본으로 "무엇을·왜" 만드는지 보여주고, "어떻게 점수화/평가/승인하는지"라는 해자는 비공개로 지킨다.
* **`docs/_private/` git-ignore는 단순하고 실수 방지가 명확하다.** 별도 private repo 운영 부담 없이, 같은 워크스페이스에서 작업하되 추적만 제외한다.
* **원본을 먼저 보존한 뒤 요약했다.** 정보 손실이 없다.

## Trade-offs

* `docs/_private/`는 git으로 백업/버전관리되지 않는다. → 별도 백업(예: private Notion, 암호화 백업)이 권장된다. 실서비스 진입 시 private repo 또는 비밀관리 체계로 승격을 재검토한다.
* 같은 저장소 안에 비추적 디렉터리가 존재하므로, 신규 협업자가 `git status`에서 보지 못한다. 온보딩 문서에 존재를 명시해야 한다.

## Consequences

* `.gitignore`에 `docs/_private/` 추가됨.
* `docs/1 서비스기획_v1.md`는 요약본으로 교체됨.
* `docs/_private/1 서비스기획_v1_full.md` 원본 보존됨 (비추적).
* 향후 모든 Tier 2 전략 문서(수익모델/GTM/재무/투자)는 동일 규칙으로 `docs/_private/`에 둔다.

## Validation

* `git status` 및 `git check-ignore docs/_private/` → 비공개 디렉터리가 추적 대상에서 제외됨을 확인.
* `git ls-files docs/` 초기화 후 → `_private/` 하위 파일이 포함되지 않음을 확인.
* 공개 요약본에 ELO 점수 설계·평가 항목·승인 트리가 포함되지 않았는지 육안 확인.

## Review Triggers

* 실서비스 트래픽/투자 단계 진입 시 → 비밀관리 체계(private repo, vault) 승격 재검토.
* 신뢰 점수 알고리즘이 Phase 3에서 코드로 구현될 때 → 코드 공개 범위 별도 결정 ADR.
* 협업자가 추가되어 비공개 문서 공유가 필요할 때 → private 공유 채널 결정.
