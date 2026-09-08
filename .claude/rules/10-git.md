# Git 규칙

## 브랜치

* 하나의 SPEC = 하나의 feature branch가 기본이다.
* 이름: `feat/SPEC-001-local-session-auth` 또는 `claude/<주제>-<식별자>`
* `main` 직접 push 금지.
* 테스트가 실패하는 상태로 merge하지 않는다.

## 커밋 메시지

Conventional Commits + 한국어 본문. 기존 이력의 형식을 그대로 따른다.

```
<type>: <한 줄 요약 — 무엇이 바뀌었는지>

<본문 — 왜 이렇게 했는지. 무엇을 했는지가 아니라.>
- 근거 조항(CLAUDE.md §N, ADR-NNN, api.md #N)을 함께 적는다
- 판단이 갈렸던 지점은 선택 이유를 남긴다

Spec: SPEC-001
Task: SPEC-001/T-01,T-02
Co-Authored-By: ...
```

**type**: `feat` `fix` `docs` `test` `chore` `refactor`

## 추적성 트레일러

`Spec:` / `Task:` 두 줄이 추적 사슬의 중간 고리다. 이것만 있으면 몇 달 뒤에 복원할 수 있다.

```bash
git log --grep "SPEC-004"          # 이 SPEC의 전체 이력
git log --grep "SPEC-004/T-02"     # 특정 태스크
```

사슬: `PRD → SPEC-NNN → ADR-NNN → TASK → Commit → PR`

## 커밋 단위

**검증 가능한 최소 단위로 자른다.** 큰 기능 전체를 한 커밋에 담지 않는다 (CLAUDE.md §9).

```
TASK-001 → 코드 → 테스트 → 커밋
TASK-002 → 코드 → 테스트 → 커밋
```

앱 단위 / 계층 단위로 나누는 것도 좋다 (M3가 4개 앱을 4커밋으로 나눈 선례).

## 하지 않는 것

* **파일 삭제** — §16 승인 게이트. 이동은 `git mv`(이력 보존).
* **`git push --force`** — 남의 브랜치 이력을 다시 쓰지 않는다.
* **`CLAUDE.md` 수정** — §16 헌법 락.
* **실패하는 테스트를 지우고 커밋** — 원인을 고친다.

## PR

Owner가 요청할 때만 만든다. 제목에 SPEC ID를 넣는다.
