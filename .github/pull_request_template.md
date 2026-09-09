<!--
PR 작성 규칙 (Owner 결정 2026-09-09, M2 리뷰 리스크 #5 해소)
- 하나의 SPEC = 하나의 브랜치 = 하나의 PR 을 기본으로 한다.
- 제목에 SPEC ID 또는 마일스톤 모듈 번호를 포함한다.  예) feat(SPEC-001): concerns API #16~25
- 검증 체크박스는 "실제 실행한 것"만 체크한다. 미실행은 체크 해제로 남겨 추적 대상으로 둔다.
- 이 PR 본문이 리뷰 노트 역할을 겸한다(CLAUDE.md §14).
-->

## 요약

<!-- 무엇을, 왜. 2~4줄. -->

## 범위

| 항목 | api.md / SPEC | 커밋 |
| --- | --- | --- |
|  |  |  |

**비범위(다음 PR)**:

## 검증

<!-- 실제 실행한 명령의 출력을 근거로만 체크한다. "완료했습니다"는 증거가 아니다. -->

- [ ] `manage.py check` 0 issues
- [ ] `manage.py makemigrations --check` No changes
- [ ] `ruff check .` 통과
- [ ] `manage.py test` 통과 (D-7 확정 — 신규 기능은 test-first)
- [ ] Acceptance Criteria 실측 (해당 SPEC의 acceptance.md)
- [ ] 서브에이전트 리뷰 (해당 시: `security-reviewer` / `api-architect` / `data-modeler` / `ops-reviewer`)

실행 출력:

```text

```

## 보안 / 접근 제어 확인

- [ ] 객체 수준 접근 제어 적용 (타인 자원 404/403)
- [ ] 응답 필드 의도적 선별 (CLAUDE.md §8 — 민감 필드 미노출)
- [ ] 시크릿 미포함 (`.env` 계열 변경 없음 또는 키 이름만)

## 문서 갱신

- [ ] `docs/00-project/STATUS.md` 갱신 (구현 커밋에는 필수)
- [ ] `README_AIUSAGE.md` 1항목 추가 (CLAUDE.md §13)
- [ ] `docs/api.md` / `docs/model.md` 정합 (변경 시)
- [ ] ADR 추가·갱신 (아키텍처 결정 변경 시)

## 알려진 부채 / 후속

<!-- 이 PR에서 의도적으로 남긴 것. 이월이면 어디에 기록했는지까지. -->

## 관련 문서

<!-- SPEC / ADR / api.md 절 / 마일스톤 정의 문서 링크 -->
