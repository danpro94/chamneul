---
description: 새 SPEC 디렉터리를 템플릿에서 만든다. 이전 SPEC이 안 닫혔으면 거부한다
argument-hint: <SPEC 번호> <슬러그>  예) 002 google-oauth
---

새 SPEC을 만든다: `$ARGUMENTS`

## 1단계 — 선행 조건 확인 (건너뛰지 마라)

`docs/00-project/STATUS.md`에서 활성 SPEC을 찾고, 그 `acceptance.md`에 **미체크 항목이 있는지** 확인하라.

미체크가 남아 있으면 **새 SPEC을 만들지 말고** 다음을 보고하고 멈춰라.

* 남은 미체크 항목 목록
* "이전 SPEC이 닫히지 않았습니다. 그래도 새 SPEC을 시작할까요?"

작은 루프를 겹치면 둘 다 안 닫힌다. Owner가 명시적으로 승인하면 진행한다.

## 2단계 — 범위 확인

`docs/00-project/STATUS.md` §5 SPEC 로드맵에서 이 SPEC이 맡을 **api.md 엔드포인트 번호**를 확인하라. 로드맵에 없는 번호를 임의로 넣지 마라.

`docs/00-project/DECISION_INDEX.md` §4·§5에서 **이 SPEC이 처리하기로 되어 있는 미결 항목**을 찾아 `spec.md`의 Open Questions에 옮겨라.

## 3단계 — 생성

`specs/_TEMPLATE/`을 `specs/SPEC-<번호>-<슬러그>/`로 복사하고 채운다.

```
spec.md         front-matter(routing 태그 필수) + Intent + GIVEN/WHEN/THEN + AC + Non-Goals
plan.md         변경 컴포넌트 / 데이터 흐름 / DB 변경 유무 / ADR 충돌 검토
tasks.md        TASK별 [소유]/[위임]/[읽기] 태그 + 검증 파일 경로
acceptance.md   AC 체크박스 (각 항목에 테스트 경로를 적을 자리를 비워 둔다)
handoff.md      라우팅 + 소유 구역 불가침 + 학습 게이트
evidence/       .gitkeep
```

`spec.md` front-matter는 반드시 채운다:

```yaml
spec: SPEC-NNN
title:
prd: docs/2 mvp-scope_v1.md
endpoints: [ ]        # api.md §3 번호
routing: 위임          # 소유 | 위임 | 읽기 — learning/02 §2.0
adr: [ ]
status: draft
```

## 4단계 — 규칙

* **아직 코드를 쓰지 마라.** 이 명령은 명세 단계다.
* AC는 **자동 테스트로 판정 가능한 형태**로 쓴다. "잘 동작한다"는 AC가 아니다. GIVEN/WHEN/THEN으로 쓴다.
* Non-Goals를 반드시 채운다. 무엇을 안 하는지가 범위를 지킨다.
* 기존 계약을 재작성하지 말고 **인용**하라 — `api.md #N`, `ADR-002 §N`, `model.md §N`.
* 확실하지 않은 것은 추측하지 말고 Open Questions에 남겨 Owner에게 물어라.

## 5단계 — 마무리

`docs/00-project/STATUS.md`의 활성 SPEC 줄을 갱신하는 수정안을 보여주고, Owner 확인 후 반영한다.
