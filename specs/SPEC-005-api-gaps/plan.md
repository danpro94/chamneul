# SPEC-005 — plan

## 1. 파일 계획

| 파일 | 작업 |
| --- | --- |
| `accounts/tests.py` (수정) | 회귀 8건 + 재설정 2건. 현재 55개 → 약 100개 |
| `accounts/services.py` (수정) | `request_password_reset` / `confirm_password_reset` 추가 |
| `accounts/serializers.py` (수정) | `PasswordResetRequestSerializer` / `PasswordResetConfirmSerializer` |
| `accounts/views.py` (수정) | `PasswordResetView` / `PasswordResetConfirmView` |
| `accounts/urls.py` (수정) | path 2개 |
| `accounts/emails.py` (**신규**) | 메일 본문 생성 — 계정 종류(로컬/Google)에 따라 분기 |
| `concerns/services.py` (수정) | `update_own_concern` 추가 |
| `concerns/serializers.py` (수정) | `ConcernUpdateSerializer` |
| `concerns/views.py` (수정) | `ConcernDetailView.patch` |
| `concerns/tests.py` (수정) | #47 테스트 |
| `config/settings/base.py` (수정) | `PASSWORD_RESET_TIMEOUT` · `PASSWORD_RESET_URL` |
| `config/settings/{local,test}.py` (수정) | `EMAIL_BACKEND = console` |
| `.env.example` (수정) | `PASSWORD_RESET_URL` 키 |

**마이그레이션 없음.** 토큰은 저장하지 않고(Django가 계산으로 검증), 고민 수정은 기존 컬럼만 건드린다. `makemigrations --check`가 `No changes`여야 한다 — 아니라면 설계를 잘못한 것이다.

`accounts/urls.py`는 이미 `GrantableRoleConverter`를 담고 있으므로 파일 성격상 path 추가만 한다.

## 2. 서비스 레이어 설계

### `request_password_reset(email)` (#45)

```
user = User.objects.filter(email=email.lower()).first()
if user is not None:
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    send_reset_mail(user, uid, token)      # emails.py — 계정 종류로 본문 분기
# user가 None이어도 여기서 끝. 호출부는 결과를 구분하지 않는다.
return None
```

**반환값이 없다는 점이 설계다.** 서비스가 "찾았다/못 찾았다"를 돌려주면 뷰가 그걸 응답에 반영할 유혹이 생긴다. **구분할 정보를 애초에 주지 않는다.**

타이밍 공격은 Phase 2 범위 밖이나, 메일 발송이 비동기가 아니므로 가입/미가입 응답 시간이 다를 수 있다는 점은 §5 갭으로 기록한다.

### `confirm_password_reset(uidb64, token, new_password)` (#46)

```
with transaction.atomic():
    user = _decode_uid(uidb64)                 # 실패 → Conflict 아님, ValidationError(400)
    if user is None or not default_token_generator.check_token(user, token):
        raise ValidationError(...)             # 만료·위조·재사용을 구분하지 않는다
    validate_password(new_password, user=user) # 검증기 4종 (400)

    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])

    # 비밀번호를 되찾는 상황 = 계정이 탈취됐을 수 있는 상황.
    # 남의 세션을 살려두면 비밀번호만 바뀌고 침입자는 그대로 남는다.
    _purge_sessions_of(user)
```

**토큰 재사용이 자동으로 막히는 이유**: Django의 토큰은 `user.password` 해시와 `last_login`을 입력으로 계산된다. 비밀번호가 바뀌면 같은 토큰의 검증이 실패한다. **저장·폐기 로직이 필요 없다.**

세션 무효화는 `django.contrib.sessions` 백엔드가 DB이므로 `Session` 테이블을 훑어 해당 `_auth_user_id`를 지운다. 세션 수가 적은 Phase 2에서는 전수 조회가 허용 범위다 — 규모가 커지면 `Session`에 사용자 인덱스를 붙이는 것이 다음 수순이며 §5에 기록한다.

### `update_own_concern(user, concern_id, validated_data)` (#47)

```
with transaction.atomic():
    concern = get_object_or_404(
        Concern.objects.select_for_update(of=("self",)).filter(author=user),
        pk=concern_id,
    )
    if concern.status != ConcernStatus.SUBMITTED:
        raise Conflict("배정된 뒤에는 고칠 수 없습니다.", reason="NOT_EDITABLE")
    for field, value in validated_data.items():
        setattr(concern, field, value)
    concern.save(update_fields=[*validated_data, "updated_at"])
    return concern
```

`.claude/rules/coding.md`의 상태 전이 3종 가드를 그대로 적용한다 — 상태를 **읽고 판단하는** 함수이므로 대상이다. 잠금이 없으면 "SUBMITTED를 확인한 직후 관리자가 배정"하는 창이 열리고, 조언가가 이미 읽기 시작한 글을 고치게 된다.

`update_fields`에 받은 필드만 넣는 것도 의도적이다 — 전체 컬럼을 쓰면 동시에 일어난 다른 변경(예: 배정에 의한 `status`)을 덮어쓴다.

접근 제어는 알림·#21과 같은 형태로 **쿼리셋 스코프**다. 타인의 고민은 로드되지 않아 404가 된다.

## 3. 메일 본문 설계 (`accounts/emails.py`)

| 계정 종류 | 판별 | 본문 |
| --- | --- | --- |
| 로컬 비밀번호 있음 | `user.has_usable_password()` | 재설정 링크 |
| Google 전용 | `not user.has_usable_password()` | "이 계정은 Google 로그인을 씁니다" + **재설정 링크도 함께**(§7 결정 2로 비밀번호 설정이 가능하므로) |

링크 형식: `{PASSWORD_RESET_URL}?uid={uidb64}&token={token}`

`PASSWORD_RESET_URL` 기본값은 `http://localhost:3000/reset-password`(프론트 자리표시자). 환경변수로 덮는다 — `GOOGLE_OAUTH_SUCCESS_REDIRECT`와 같은 패턴.

## 4. 회귀 테스트 전략 (TASK-001·002)

**구현을 바꾸지 않는다.** 지금 동작을 그대로 고정한다.

| 영역 | 확인할 것 |
| --- | --- |
| `#2` 가입 | 201 + `sessionid` 발급 + 응답 필드 집합 + 중복 이메일/닉네임 + 약한 비밀번호 400 |
| `#3` 로그인 | 성공 시 세션 발급 / 틀린 비밀번호·없는 계정 모두 **같은 오류**인지 |
| `#4` 로그아웃 | **서버 세션 레코드 삭제** + 쿠키 만료. 클라이언트 쿠키 삭제만으로 끝나지 않는지(§10) |
| `#5` authorize | 리다이렉트 URL에 `client_id`·`redirect_uri`·`state` 포함 |
| `#6` callback | 신규 생성 / 기존 이메일 연결 / **이미 다른 Google 계정과 연결됨 → 409** |
| `#7`/`#8` | 조회 필드 집합 + 부분 수정 + 닉네임 중복 409 |
| `#9` | `roles`·`active_role`·`advisor_status` |

### OAuth mock 경계

**우리 코드를 mock하지 않는다.** `accounts/oauth.py`의 함수를 통째로 mock하면 그 함수가 검증되지 않는다. `urllib`의 호출 지점을 mock해 **응답 바이트만 가짜로 주고, 파싱·분기는 실제 코드가 하게** 한다.

```python
with patch("accounts.oauth.urlopen") as m:   # ← 네트워크 경계
    m.return_value = _fake_json({"sub": "...", "email": "...", "aud": "..."})
```

`aud` 검증, 이메일 소문자화, 닉네임 충돌 해소(C-11)가 실제로 도는지 확인하는 것이 목적이다.

## 5. 검증

TASK마다 4종(`check` / `makemigrations --check` / `ruff` / `test`). TASK-003 이후에는 **콘솔에 출력된 재설정 링크를 실제로 복사해 #46에 넣어보는 왕복**을 수행한다 — SPEC-003에서 `target_url`이 "옳았지만 아무도 눌러본 적 없었던" 일을 반복하지 않기 위해서다.

Mock-Up UI는 이번에는 별도로 만들지 않는다. 프로토타입에 해당 화면(비밀번호 찾기·고민 고치기)이 이미 있고, 이 SPEC은 그 화면을 **실제로 동작하게** 만드는 일이다. 대신 콘솔 링크 왕복 출력을 첨부한다.
