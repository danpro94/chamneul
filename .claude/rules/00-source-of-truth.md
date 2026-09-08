# chamneul — 세션 시작 규칙

> 이 파일은 SessionStart 훅이 매 세션 자동 주입한다. 정본은 `docs/adr/ADR-005-ai-native-spec-driven-migration.md`.

## 읽기 순서

1. `CLAUDE.md` — 헌법. **단 §2·§3·§17은 ADR-005로 대체됨** (아래 참조)
2. `README.md` — 프로젝트 지도
3. `docs/00-project/STATUS.md` — 지금 어디까지 왔는가
4. 활성 SPEC의 `spec.md` + `acceptance.md`
5. 필요한 ADR / `docs/api.md` / `docs/model.md`의 **해당 절만**

거대 프롬프트를 붙여넣지 않는다. 저장소가 컨텍스트 시스템이다.

## CLAUDE.md 조항 상태 (ADR-005)

| 조항 | 상태 |
| --- | --- |
| §2 Source of Truth Order | ⚠️ **대체됨** — 아래 순서를 쓴다. **Notion은 은퇴했다** |
| §3 Current Known Project Tree | ⚠️ **대체됨** — `README.md`를 본다 (앱 5개 생기기 전 트리라 사실과 다름) |
| §17 First Recommended Workflow | ⚠️ **대체됨** — step 6 "Notion export 대기"는 무시한다. 기다릴 대상이 없다 |
| §13 Documentation Rules | ➕ 확장됨. 기존 유지 대상은 전부 유효 |
| §16 Approval Gates | ✅ **유효.** 대체되지 않았다 |
| **§6 도메인 규칙 전체** | ✅ **유효 — 무손실.** taxonomy 11종·상태 enum·소프트 삭제·버저닝 |
| §0·§1·§4·§5·§7~§12·§14·§15 | ✅ 유효 |

### 새 Source of Truth 순서

```
1. CLAUDE.md              헌법 (동결. ADR로만 개정)
2. docs/adr/              같은 조항은 높은 번호가 이긴다
3. docs/00-project/STATUS.md
4. specs/SPEC-NNN/        진행 중 작업 (자기 범위 안에서만)
5. docs/api.md            43 엔드포인트 계약 (정본)
6. docs/model.md
7. docs/2 mvp-scope_v1.md · docs/1 서비스기획_v1.md
8. code
```

**은퇴**: Notion export. `docs/api.md` §7의 동기화 계획도 은퇴했다.

## 절대 규칙

1. **`CLAUDE.md`를 직접 수정하지 않는다** (§16 헌법 락). 이견이 있으면 ADR을 제안한다.
2. **소유 구역을 수정하지 않는다** — `Dockerfile`, `docker-compose*.yml`, `.env*`. 제안과 리뷰만 한다 (`docs/learning/02` §2.1).
3. **새 서드파티 패키지를 도입하지 않는다** (§16 게이트). DRF + Django 기본 test runner만 쓴다. pytest·factory_boy·coverage 전부 미도입 (Owner 결정 G5).
4. **마이그레이션 적용은 Owner가 한다.** `makemigrations`는 하되 `migrate`는 실행하지 않는다.
5. **"완료했습니다"는 증거가 아니다.** 증거는 통과한 테스트·실측 출력이다. 실행하지 않은 명령은 "권장 명령"으로 표기한다 (§12).
6. **파일을 삭제하지 않는다** (§16 게이트). 이동은 `git mv`로 한다.

## 자주 틀리는 것

* **401 vs 403**: 인증 없음 = 401. 인증됨 + 권한 없음 = 403. ADVISOR 역할을 **보유**했어도 `active_role`이 `USER`면 조언가 리소스는 **403**이다. (학습 부채 ④ — M4 차단)
* **소프트 삭제**: `deleted_at` timestamp를 쓴다. `is_deleted` boolean이 아니다. 소프트 삭제 모델의 유니크 제약은 반드시 **부분 유니크 인덱스**여야 한다.
* **`intended_lane`**: 공개 응답에 절대 넣지 않는다. 권한 키로 쓰지 않는다.
* **테스트 실행**: `--settings=config.settings.test`를 **매번** 붙인다. 기본값은 `local`이다.

## 슬래시 명령

`/onboard` 세션 시작 보고 · `/verify` 검증 배터리 · `/spec-new` SPEC 생성 · `/handoff` 세션 종료 기록
