# OWNER-ACTIONS-GUIDE — Owner만 할 수 있는 일 (클릭 단위 안내)

> 작성일 2026-10-22 · 대상: macOS + Chrome · 기준 브랜치 `feat/spec-005-api-gaps`
> 이 문서에는 **AI가 대신 할 수 없는 일**만 모았다. 계정 만들기, 결제, 법적 판단, 콘솔 클릭, 인프라 손코딩이 여기에 해당한다. 인프라 파일(.env.example, Dockerfile, compose, Terraform, k8s, CI)은 정책상 **Owner가 직접 손으로** 쓴다. 그래서 이 문서는 "어디서 무엇을 누르는지"와 "나중에 무엇을 손코딩하게 되는지"만 알려준다.
> 콘솔 화면은 자주 바뀐다. 메뉴가 안 보이면 각 콘솔 상단 **검색창**에 괄호 안 키워드를 입력하라. 직접 확인하지 못한 라벨에는 "(메뉴명이 다를 수 있음)"을 붙였다.

---

## 0. 한 화면 체크리스트

| 순서 | 작업 | 소요 | 마감 권장 | 상태 |
| --- | --- | --- | --- | --- |
| A-1 | `.env.example`에 `PASSWORD_RESET_URL` 줄 추가 | 5분 | 오늘 | □ |
| A-2 | Google OAuth client secret 회전 | 20분 | 오늘 | □ |
| A-3 | SPEC-005 PR 리뷰·머지 (GitHub 웹) | 30분 | 이번 주 | □ |
| A-4 | "붙여넣기 금지" 출력 2종 숙지 | 2분 | 오늘 | □ |
| A-5 | Google 로그인 계정 연결 변화(F-5) 숙지 | 5분 | 베타 전 | □ |
| B-1 | GitHub 계정 2FA + 저장소 보호 설정 | 30분 | 이번 주 | □ |
| B-2 | AWS 계정 생성 + 루트 MFA | 40분 | Phase 3 시작 전 | □ |
| B-3 | IAM Identity Center 관리자 사용자 | 30분 | B-2 직후 | □ |
| B-4 | 결제 알림 (AWS Budgets) | 15분 | B-2 직후 (**필수**) | □ |
| B-5 | Route 53 호스팅 영역 + Namecheap 네임서버 위임 | 30분 (+전파 최대 48시간) | 배포 2주 전 | □ |
| B-6 | ACM 인증서 (DNS 검증) | 15분 | B-5 직후 | □ |
| B-7 | Amazon SES 도메인 인증 (DKIM·SPF·DMARC) | 40분 | 배포 2주 전 | □ |
| B-8 | SES 프로덕션 액세스(샌드박스 해제) 요청 | 20분 (+심사 1일~수일) | B-7 직후 | □ |
| C-1 | 개인정보 처리방침 초안 | 반나절 | 베타 공개 전 | □ |
| C-2 | 이용약관 초안 | 반나절 | 베타 공개 전 | □ |
| C-3 | 민감정보·14세 미만 정책 결정 | 1시간 | 베타 공개 전 | □ |
| C-4 | 사업자등록·통신판매업 필요 여부 판단 | 1시간 | 유료화 전 | □ |
| C-5 | 도메인 WHOIS 보호·자동갱신 확인 | 5분 | 이번 주 | □ |
| D | 나중에 내릴 결정 목록 | — | Phase 3 계획 시 | □ |

> **C(법률·사업) 부분은 법률 자문이 아니다. 확정 전에 변호사·개인정보 전문가·세무사 검토를 권장한다.**

---

## A. 지금 바로 (개발 마무리)

### A-1. `.env.example`에 `PASSWORD_RESET_URL` 추가

- **목적**: 비밀번호 재설정 링크가 가리킬 주소 키를 "이 프로젝트가 쓰는 환경변수 목록"에 올린다. SPEC-005 spec §10에서 §16 승인 대기로 남은 항목이다.
- **소요·비용**: 5분 · 무료
- **사전 준비**: 편집기(VS Code 또는 텍스트 편집기)
- **단계**
  1. `⌘+Space` → `Terminal` 입력 → Enter.
  2. `cd ~/projects/personal/chamneul && open -e .env.example` (VS Code가 있으면 `code .env.example`).
  3. `GOOGLE_OAUTH_SUCCESS_REDIRECT` 줄 바로 아래(Google 블록 끝)에 다음 3줄을 **손으로** 입력한다.
     ```dotenv
     # 비밀번호 재설정 메일 속 링크의 앞부분 (api.md #45). 프론트 화면 주소.
     # 실제 링크는 {이 값}#uid=...&token=... 형태다. prod에서는 반드시 https:// (빠뜨리면 localhost로 나간다 — S-6).
     PASSWORD_RESET_URL=http://localhost:3000/reset-password
     ```
     값은 `config/settings/base.py`의 기본값과 같다. 비밀이 아닌 주소라서 예시 값을 그대로 적어도 된다.
  4. `⌘+S`로 저장.
- **완료 확인**: 터미널에서 `grep PASSWORD_RESET_URL .env.example` → 한 줄이 나온다. `git diff .env.example`에 3줄만 추가돼 있다.
- **흔한 실수**
  - 진짜 파일 `.env`에만 쓰고 `.env.example`은 안 고친다.
  - 반대로 `.env.example`에 실제 시크릿을 적는다.
  - 키 이름 오타(`PASSWORD_RESET_URI`).
  - 값 끝에 `#`나 `?token=`을 붙인다. 링크 뒷부분은 서버가 붙이므로 **주소까지만** 적는다.

### A-2. Google OAuth client secret 회전

- **목적**: 과거 세션 로그에 평문으로 찍힌 secret을 새 것으로 바꾼다(리뷰 노트 07 §3-5-1).
- **소요·비용**: 20분 · 무료
- **사전 준비**: 로컬 스택이 `docker compose up -d`로 떠 있어야 한다. 참늘 프로젝트를 만든 Google 계정으로 로그인한다.
- **원리**: secret은 "앱 전용 비밀번호"다. Google은 클라이언트 하나에 **secret 두 개를 동시에** 둘 수 있게 해 준다. 그래서 새 것을 먼저 만들고, 바꿔 끼우고, 잘 되면 옛 것을 끈다. 순서를 바꾸면 그 순간 로그인이 끊긴다.
- **단계**
  1. Chrome에서 https://console.cloud.google.com/auth/clients 로 간다. 예전 주소 `.../apis/credentials`도 같은 곳으로 이어진다. 상단 프로젝트 선택기에서 참늘 프로젝트를 고른다.
  2. 왼쪽 메뉴 **Google Auth Platform → Clients(클라이언트)** 에서 참늘의 웹 클라이언트 이름을 클릭한다.
  3. 오른쪽 **Client secrets** 영역에서 **Add secret(보안 비밀 추가)** 을 누른다. (메뉴명이 다를 수 있음 — 페이지에서 `⌘+F` → "secret")
  4. 새 secret은 **딱 한 번만** 전체가 보인다. 복사 버튼을 누르고 바로 다음 단계로 간다. 메모장이나 메신저에 붙이지 않는다.
  5. 터미널에서 `open -e ~/projects/personal/chamneul/.env`를 실행한다. `GOOGLE_OAUTH_CLIENT_SECRET=` 뒤 값을 새 값으로 바꾸고 `⌘+S`로 저장한다. 그다음 아무 단어나 하나 `⌘+C` 해서 클립보드를 덮어쓴다.
  6. `docker compose up -d`를 실행한다. env_file은 컨테이너를 다시 만들 때 새로 읽힌다. `docker compose ps`에서 app이 `healthy`인지 확인한다.
  7. Chrome에서 `http://localhost:8000/api/v1/auth/google/authorize`로 간다. Google 로그인 후 성공 리다이렉트까지 한 번 끝까지 확인한다.
  8. 콘솔로 돌아가 **옛 secret** 행에서 **Disable(사용 중지)** 을 누른다. 로그인을 한 번 더 해 보고, 문제가 없으면 **Delete(삭제)** 를 누른다.
- **완료 확인**: secret 목록에 활성 secret이 1개(새 것)만 남고, 로그인이 성공한다.
- **흔한 실수**
  - 옛 secret을 먼저 지운다.
  - `docker compose restart`만 하면 컨테이너가 새로 만들어지지 않아 새 값이 안 들어간다. `up -d`를 쓴다.
  - 새 secret을 복사하지 못하고 창을 닫는다. 이때는 하나 더 추가하고, 못 쓰게 된 것은 지우면 된다.
- **참고**: Google은 6개월 동안 쓰지 않은 OAuth 클라이언트를 자동 삭제한다(30일 안에는 복구 가능). 오래 쉬었다면 Google에서 온 알림 메일을 확인하라.

### A-3. SPEC-005 PR 승인·머지 (GitHub 웹)

- **목적**: `feat/spec-005-api-gaps`를 `main`에 합친다. 이 PR에는 **TASK-003~006**이 들어 있다.
  - #45 비밀번호 재설정 요청, #46 재설정 확정
  - #47 고민 수정(`SUBMITTED` 상태에서만 가능)
  - 보안 리뷰 후속 수정. 재설정 링크가 프래그먼트 형식(`#uid=...&token=...`)으로 바뀌었고, Google 계정 연결 시 로컬 비밀번호를 무효화한다(F-5, A-5 참고).
- **소요·비용**: 30분 · 무료
- **사전 준비**: 브랜치가 push돼 있고 PR이 열려 있어야 한다. 없으면 `gh pr create --base main`으로 만들거나 AI에게 요청한다.
- **단계**
  1. https://github.com/ 에 로그인 → 저장소 `chamneul` → 상단 **Pull requests** 탭 → SPEC-005 PR을 클릭한다.
  2. **Files changed** 탭에서 파일을 하나씩 훑고, 이해한 파일은 오른쪽 **Viewed**에 체크한다. 이때 `.env*`, Dockerfile, compose 파일이 **바뀌지 않았는지** 꼭 본다. 바뀌었다면 정책 위반이니 멈추고 질문한다. A-1에서 직접 고친 `.env.example`은 별도 커밋으로 올린다.
  3. **Conversation** 탭 아래쪽에서 체크(테스트) 상태를 본다. CI가 아직 없으니 로컬 터미널에서 아래를 돌리고, 결과의 마지막 두 줄(`Ran N tests`, `OK`)만 PR 코멘트로 남긴다. db 컨테이너가 떠 있어야 한다(`docker compose up -d db`).
     ```bash
     cd ~/projects/personal/chamneul && uv run python manage.py test --settings=config.settings.test
     ```
     *컨테이너 안(`docker compose exec app …`)이 아니라 호스트에서 테스트 설정(`config.settings.test`)으로 돌리는 것이 이 프로젝트의 정해진 방법이다.*
  4. 오른쪽 위 **Review changes**를 누른다. 자기 PR은 **Approve**할 수 없으니 **Comment**로 "리뷰 완료"를 남기고 **Submit review**를 누른다.
  5. **Merge pull request** 옆 ▼에서 이전 PR #3~#11과 같은 방식을 고르고 **Confirm**을 누른다.
  6. **Delete branch**를 누른다. 로컬에서는 `git switch main && git pull`을 실행한다.
- **완료 확인**: PR 상단에 보라색 **Merged**가 보인다. `git log main --oneline -5`에 SPEC-005 커밋들이 있다.
- **흔한 실수**: 머지하고 로컬 `main`을 안 당겨 와서, 다음 작업을 옛 코드 위에서 시작한다.

### A-4. 절대 어디에도 붙여넣지 말 것 (2종)

| 명령 출력 | 왜 위험한가 | 대신 쓸 것 |
| --- | --- | --- |
| `docker compose logs app` | 로컬은 메일을 보내는 대신 콘솔에 찍는다. 그래서 로그에 **아직 쓸 수 있는 비밀번호 재설정 링크**(`#uid=...&token=...`)가 그대로 보인다. 그 링크를 가진 사람은 누구나 그 계정의 비밀번호를 바꿀 수 있다(S-3). | 필요한 부분만 눈으로 보고 말로 설명한다. 꼭 붙여야 하면 토큰을 가린 출력만 쓴다: `docker compose logs app --since 10m \| sed -E 's/token=[0-9a-z]+-[0-9a-f]+/token=<가림>/'` (smoke-test §6) |
| `docker compose config` | `.env`의 secret을 **평문**으로 펼쳐서 보여 준다. | `docker compose config --services` 또는 `--quiet` |

"어디에도"에는 AI 채팅창, Slack, GitHub 이슈·PR 코멘트, 스크린샷이 모두 들어간다.

### A-5. Google 로그인 계정 연결 변화 (TASK-006, F-5) — 베타 사용자 문의 대비

- **무엇이 바뀌었나**: 이메일·비밀번호로 가입한 사람이 **나중에 같은 주소로 Google 로그인**을 하면, 두 로그인이 한 계정으로 합쳐진다. 그 순간 **예전 비밀번호는 더 이상 쓸 수 없다.** 비밀번호로도 로그인하고 싶으면 **"비밀번호 찾기"(#45)** 로 새 비밀번호를 만들어야 한다.
- **왜**: 누군가 남의 이메일로 먼저 가입해 비밀번호를 정해 둘 수 있다. 진짜 주인이 나중에 Google로 들어오면 계정이 합쳐지는데, 이때 옛 비밀번호가 살아 있으면 가짜 가입자도 계속 들어올 수 있다. 이것이 "사전 계정 탈취"다. Google은 이메일 주인임을 확인해 주므로, 합쳐질 때 확인되지 않은 옛 비밀번호를 끊는다.
- **Owner가 할 일**: 코드 작업은 없다. 문의가 오면 아래처럼 답한다.
  > "Google로 로그인하시면서 계정이 하나로 합쳐졌고, 보안을 위해 이전 비밀번호는 해제됐어요. Google 로그인은 그대로 쓰시면 되고, 비밀번호 로그인도 원하시면 로그인 화면의 '비밀번호 찾기'로 새로 설정해 주세요."
- **완료 확인**: 이 안내 문구를 FAQ나 고객 응대 메모에 저장했다. 프론트를 만들 때 Google 로그인 버튼 근처에 한 줄 안내를 넣을지도 D 목록에서 정한다.
- **주의**: 실제 메일 발송은 B-7·B-8 이후에야 된다. 그전 베타에서는 "비밀번호 찾기" 메일이 사용자에게 도착하지 않는다.

---

## B. 계정·돈·인프라 기반

### B-1. GitHub 2FA + 저장소 보호

- **목적**: 계정 탈취, `main` 직접 push, 시크릿 커밋을 막는다.
- **소요·비용**: 30분 · 공개 저장소는 무료. 비공개 저장소에서는 일부 보안 기능(시크릿 스캔 등)이 유료 플랜일 수 있다.
- **단계 — 2FA**
  1. https://github.com/settings/security → **Two-factor authentication** → **Enable two-factor authentication**.
  2. 방법은 **Passkey**나 인증 앱(1Password, Google Authenticator 등)을 고른다. SMS는 권장하지 않는다.
  3. **Recovery codes**를 다운로드해서 비밀번호 관리자에 저장한다. 바탕화면에 두지 않는다.
- **단계 — 저장소 규칙(ruleset)**
  1. 저장소 → **Settings** → 왼쪽 **Rules → Rulesets** → **New ruleset → New branch ruleset**.
  2. 이름은 `protect-main`, Enforcement status는 **Active**. **Target branches → Add target → Include default branch**.
  3. 다음을 체크한다.
     - **Restrict deletions**
     - **Block force pushes**
     - **Require a pull request before merging**(혼자 개발하면 required approvals 0)
     - CI가 생긴 뒤에는 **Require status checks to pass**
  4. **Create**를 누른다.
- **단계 — 보안 스캔**
  1. Settings → **Advanced Security**로 간다. 예전 이름은 "Code security and analysis"다. (메뉴명이 다를 수 있음)
  2. **Dependabot alerts**와 **Dependabot security updates**를 **Enable**.
  3. **Secret scanning**(또는 Secret Protection)과 **Push protection**을 **Enable**.
- **완료 확인**: `git push origin main`을 직접 시도하면 거부된다. **Security** 탭에 Dependabot이 보인다.
- **흔한 실수**: recovery code를 보관하지 않는다. 그 상태에서 폰을 잃어버리면 계정이 영구히 잠길 수 있다.

### B-2. AWS 계정 생성 + 루트 MFA

- **목적**: Phase 3(EKS) 실습·운영용 계정을 안전하게 연다.
- **소요·비용**: 40분 · 가입 자체는 무료.
  - **2025-07-15 이후 신규 계정은 가입할 때 Free plan과 Paid plan 중 하나를 고른다.** 처음에 크레딧 $100을 받고, 온보딩 과제를 하면 최대 $100을 더 받는다(합계 최대 $200).
  - Free plan은 **6개월이 지나거나 크레딧을 다 쓰면**(먼저 오는 쪽) 끝난다. 계속 쓰려면 Paid로 바꿔야 한다.
  - 예전의 "12개월 t2.micro 750시간" 혜택은 신규 계정에 없다.
  - **EKS 컨트롤 플레인은 시간당 과금**이다. NAT Gateway와 로드밸런서도 켜 두는 동안 계속 과금되므로 크레딧이 빨리 준다. 실습이 끝나면 반드시 지운다(`terraform destroy`).
  - 최신 조건은 https://aws.amazon.com/free/ 에서 직접 확인한다. 위 내용은 2차 자료로 교차 확인했다.
- **사전 준비**: 이 용도 전용 이메일(별칭도 됨), 해외결제가 되는 카드, 휴대폰.
- **단계**
  1. https://signin.aws.amazon.com/signup?request_type=register 에 들어가 루트 이메일과 계정 이름(예: `chamneul`)을 넣고 이메일 인증 코드를 입력한다.
  2. 루트 비밀번호는 비밀번호 관리자로 20자 이상 생성한다.
  3. 연락처 유형은 **Personal**(사업자가 없으면)을 고르고, 카드 입력과 전화 인증을 마친다. 플랜은 학습 단계라면 **Free plan**을 권장한다. 실수로 큰 요금이 나가는 것을 막아 준다.
  4. 로그인 후 오른쪽 위 계정 이름 → **Security credentials** → **Assign MFA device**. **Passkey or security key**(Mac의 Touch ID·iCloud 키체인)나 **Authenticator app**을 고른다. 가능하면 두 개를 등록해 백업으로 둔다.
  5. 같은 화면에서 루트 **Access keys**가 0개인지 확인한다. 만들지 않는다.
- **완료 확인**: 로그아웃했다가 다시 로그인하면 MFA를 요구한다.
- **흔한 실수**
  - 보안이 약한 개인 메일로 루트를 만든다.
  - 루트 계정으로 일상 작업을 한다.
  - 루트 액세스 키를 만든다.

### B-3. IAM Identity Center 관리자 사용자

- **목적**: 루트 대신 매일 쓸 관리자 로그인을 만든다. 나중에 CLI의 `aws sso login`도 이것으로 한다.
- **소요·비용**: 30분 · 무료
- **단계**
  1. 콘솔 오른쪽 위 리전을 **Asia Pacific (Seoul) ap-northeast-2**로 바꾼다.
  2. 상단 검색창에 `IAM Identity Center` → **Enable**. 조직 단위로 켤지 묻는 화면이 나오면 **AWS Organizations와 함께 활성화**를 권장한다. (메뉴명이 다를 수 있음)
  3. 왼쪽 **Users → Add user**에서 사용자 이름(`dan-admin` 등)과 본인 이메일을 넣고 **Next → Add user**. 초대 메일에서 비밀번호를 정하고 MFA를 등록한다.
  4. 왼쪽 **Permission sets → Create permission set → Predefined permission set → AdministratorAccess**를 고르고, 세션 시간은 기본값으로 만든다.
  5. 왼쪽 **AWS accounts**에서 계정을 체크하고 **Assign users or groups** → `dan-admin` → `AdministratorAccess` → **Submit**.
  6. **Dashboard**(또는 Settings)에 있는 **AWS access portal URL**을 북마크한다(`⌘+D`).
- **완료 확인**: 포털 URL로 로그인 → 계정 → AdministratorAccess를 눌러 콘솔에 들어간다. CLI는 `brew install awscli` → `aws configure sso` → `aws sts get-caller-identity`가 성공하면 된다.
- **흔한 실수**: IAM의 "Users"(오래 쓰는 액세스 키 방식)와 헷갈린다. 이 프로젝트는 Identity Center를 쓴다.

### B-4. 결제 알림 (AWS Budgets) — 필수

- **목적**: 크레딧이 줄어들거나 요금이 생기면 바로 메일로 안다.
- **소요·비용**: 15분 · 일반 알림 예산은 보통 무료 범위다. 자동 조치(Action)가 붙은 예산은 일정 개수를 넘으면 소액이 붙을 수 있으니 요금 페이지를 확인한다.
- **단계**
  1. 검색창에 `Billing and Cost Management` → 왼쪽 **Budgets → Create budget**.
  2. **Use a template → Zero spend budget**을 고른다. 크레딧을 빼고 실제 청구가 $0.01만 넘어도 알림이 온다. 이메일을 넣고 만든다.
  3. 한 번 더 **Create budget → Monthly cost budget**을 고르고 금액(예: `$20`)과 이메일을 넣어 만든다.
  4. 왼쪽 **Billing preferences**(또는 Preferences)에서 **Free Tier usage alerts**와 **청구서 이메일 수신**을 켠다. (메뉴명이 다를 수 있음)
  5. 남은 크레딧과 만료일은 **Credits** 메뉴에서 확인한다. 주 1회 들어가는 습관을 들인다.
- **완료 확인**: Budgets 목록에 2개가 있고 상태가 OK다.
- **흔한 실수**: 알림만 믿고 리소스를 방치한다. 비용 데이터는 하루에 몇 번만 갱신되므로 알림이 늦게 온다. 실습이 끝나면 바로 지운다.

### B-5. Route 53 호스팅 영역 + Namecheap 네임서버 위임

- **목적**: `chamneul.com`의 DNS를 AWS에서 관리한다. 그러면 ACM·SES·로드밸런서를 연결하기 쉬워진다.
- **소요·비용**: 30분 + 전파에 최대 48시간 · 호스팅 영역 월 $0.50 + 조회량에 따른 소액
- **단계**
  1. AWS 검색창에 `Route 53` → **Hosted zones → Create hosted zone** → Domain name `chamneul.com`, **Public hosted zone** → Create.
     - Phase 3에서 이걸 Terraform `aws_route53_zone`으로 **직접 손코딩**할 계획이라면 콘솔로는 만들지 않는다. 같은 도메인 영역은 하나만 둔다.
  2. 만들어진 영역의 **NS 레코드 값 4개**(`ns-123.awsdns-xx.com` 형태)를 적어 둔다.
  3. https://ap.www.namecheap.com/domains/list/ → `chamneul.com` 옆 **MANAGE** → **Domain** 탭 → **NAMESERVERS** 드롭다운에서 **Custom DNS**를 고른다. 값 4개를 넣고(끝의 점 `.`은 빼고) 초록 체크로 저장한다.
  4. Namecheap **Advanced DNS** 탭에 기존 레코드가 있었다면, 위임하기 **전에** Route 53에 같은 레코드를 먼저 만들어 둔다.
  5. ⚠️ Namecheap의 무료 **메일 포워딩**(예: `support@chamneul.com` → 개인 메일)은 Namecheap 네임서버를 쓸 때만 동작한다. **Custom DNS로 바꾸는 순간 멈춘다.** 받는 주소가 필요하면 위임 전에 대안(메일 호스팅 서비스의 MX 레코드를 Route 53에 등록 등)을 정해 둔다. (메뉴명이 다를 수 있음 — Namecheap 검색창에 `email forwarding`)
- **완료 확인**: 터미널에서 `dig NS chamneul.com +short` → awsdns 4개가 나온다.
- **흔한 실수**: 호스팅 영역을 지웠다가 다시 만든다. 그러면 **NS 값이 바뀌어서** Namecheap도 다시 고쳐야 한다.

### B-6. ACM 인증서 (DNS 검증)

- **목적**: `https://`에 쓸 인증서를 받는다.
- **소요·비용**: 15분 · 로드밸런서 등 AWS 서비스에 붙여 쓰는 공인 인증서는 무료
- **단계**
  1. 리전이 **ap-northeast-2**인지 확인한다. ALB용은 같은 리전에서 받는다. CloudFront를 쓰게 되면 us-east-1에서 따로 받는다.
  2. 검색창에 `Certificate Manager` → **Request → Request a public certificate**.
  3. 도메인에 `chamneul.com`과 `*.chamneul.com`을 넣고 **DNS validation**을 고른 뒤 Request.
  4. 인증서 상세에서 **Create records in Route 53** → Create.
- **완료 확인**: Status가 **Issued**가 된다. 보통 몇 분에서 30분쯤 걸린다.
- **흔한 실수**: 리전을 착각한다. 발급은 됐는데 ALB 화면에서 안 보인다.

### B-7. Amazon SES 도메인 인증 (DKIM·SPF·DMARC)

- **목적**: 비밀번호 재설정 메일이 스팸함이 아니라 받은편지함에 도착하게 한다. "이 메일은 정말 chamneul.com이 보냈다"를 증명하는 단계다.
- **소요·비용**: 40분 · 보내는 양만큼 소액(1,000통당 약 $0.10 수준이니 최신 요금을 확인)
- **단계**
  1. 리전 ap-northeast-2 → 검색창에 `Amazon SES` → **Configuration → Identities → Create identity** → **Domain** → `chamneul.com`.
  2. **Use a custom MAIL FROM domain**을 체크하고 `mail.chamneul.com`을 넣는다. MX 실패 시 동작은 기본값으로 둔다.
  3. **Easy DKIM**, **RSA_2048_BIT**, **Publish DNS records to Route 53**을 체크하고 Create identity. DKIM용 CNAME 3개와 MAIL FROM용 MX·SPF TXT가 자동으로 만들어진다.
  4. SPF를 확인한다. Route 53에 `mail.chamneul.com TXT "v=spf1 include:amazonses.com ~all"`이 있으면 된다.
  5. DMARC를 추가한다. Route 53 → 영역 → **Create record** → 이름 `_dmarc`, 유형 TXT.
     - 받는 메일함(`dmarc@chamneul.com`)이 **있으면**: `"v=DMARC1; p=none; rua=mailto:dmarc@chamneul.com"`
     - **없으면**(지금 상태): `"v=DMARC1; p=none"`으로 시작한다. 보고서만 못 받을 뿐 인증 자체는 동작한다.
     - 몇 주 지켜본 뒤 `p=quarantine`으로 강화한다.
  6. `rua`를 **다른 도메인 주소**(예: Gmail)로 적으면 대부분 보고서가 오지 않는다. 받는 쪽 도메인이 "chamneul.com의 보고서를 받겠다"는 허가 레코드를 내야 하기 때문이다. 보고서를 받으려면 chamneul.com 주소의 메일함을 만들거나 DMARC 보고서 수집 서비스를 쓴다. Namecheap 포워딩은 B-5 위임 뒤에는 동작하지 않는다.
- **완료 확인**: Identity 상태가 **Verified**, DKIM이 **Successful**, MAIL FROM이 **Success**다.
- **흔한 실수**: 처음부터 DMARC를 `p=reject`로 둔다. 설정이 하나라도 틀리면 모든 메일이 막힌다.
- **나중에 손코딩할 것**: prod 설정의 `EMAIL_BACKEND`(SMTP), `DEFAULT_FROM_EMAIL=no-reply@chamneul.com`, SES SMTP 자격증명. 자격증명은 시크릿으로 관리하고, Owner가 k8s Secret이나 Terraform으로 직접 연결한다. prod는 반드시 `config.settings.prod`로 띄워야 한다. 아니면 메일이 콘솔 로그로 새어 나간다(S-3).

### B-8. SES 프로덕션 액세스(샌드박스 해제) 요청

- **목적**: 샌드박스에서는 인증된 주소로만, 하루 200통·초당 1통까지만 보낼 수 있다. 실제 사용자에게 보내려면 리전마다 해제 신청을 해야 한다.
- **소요·비용**: 20분 + 심사(보통 하루 안팎이지만 보장되지 않음) · 무료
- **사전 준비**: B-7을 끝낸다. 최소한의 웹사이트(랜딩 페이지와 개인정보 처리방침)가 열려 있으면 승인될 확률이 올라간다.
- **단계**
  1. SES → **Account dashboard** → **Request production access**(또는 Get set up 페이지의 같은 버튼).
  2. Mail type은 **Transactional**, Website URL은 `https://chamneul.com`, 언어는 Korean/English로 한다.
  3. Use case description 예시다(영문 권장). 실제 상황에 맞게 고쳐 쓴다.
     ```text
     chamneul.com is an early-stage advice platform for Korean users. We send only
     transactional emails triggered by the user's own action: password reset links
     and account notifications. No marketing emails and no purchased lists. Recipients
     are registered users who signed up on our site. Expected volume: under 100
     emails/day during beta. Bounces and complaints are handled via SES event
     notifications (SNS); addresses that hard-bounce or complain are suppressed with
     the SES account-level suppression list. The domain is verified with DKIM, a
     custom MAIL FROM domain (SPF) and DMARC.
     ```
  4. AWS 이용 정책(AUP) 동의에 체크하고 Submit. 결과는 AWS Support 케이스와 메일로 온다.
- **완료 확인**: Account dashboard에 프로덕션 액세스가 표시되고 일일 발송 한도가 늘어난다.
- **흔한 실수**
  - "나중에 뉴스레터도…"처럼 마케팅 계획을 언급해서 거절된다.
  - 바운스 처리 계획을 빼먹어서 거절된다.
  - 거절 메일에는 사유가 없다. 내용을 보완해서 다시 신청한다.

---

## C. 한국 법·사업 (법률 자문 아님 — 확정 전 전문가 검토 권장)

### C-1. 개인정보 처리방침

- **목적**: 개인정보 보호법 제30조에 따라 **공개해야 하는** 문서다. 가입 화면과 사이트 하단에 링크를 둔다.
- **소요·비용**: 반나절 · 무료(전문가 검토는 유료)
- **단계**
  1. https://www.privacy.go.kr (개인정보 포털)의 검색창에 `처리방침 작성지침` → **개인정보 처리방침 작성지침(2025.4 개정)** 을 내려받는다. 같은 포털의 처리방침 만들기(생성기) 메뉴도 활용할 수 있다. (메뉴명이 다를 수 있음)
  2. https://www.pipc.go.kr (개인정보보호위원회)에서 `작성지침`을 검색해 원문 공지를 확인한다.
  3. 지침의 **법정 필수 기재 사항**을 표로 채운다. 처리 목적, 처리 항목, 보유기간, 제3자 제공·위탁, 파기, 정보주체 권리, 안전성 확보조치, 개인정보 보호책임자 연락처가 여기에 들어간다. 항목은 `docs/model.md`의 실제 컬럼을 기준으로 적는다.
  4. **위탁·국외 이전**을 정리한다. AWS(호스팅), Amazon SES(메일), Google(로그인)이 대상이다. 서버가 서울 리전이라도 Google 로그인 같은 부분은 국외 이전 고지 대상일 수 있으니 전문가에게 확인한다.
- **완료 확인**: 지침 체크리스트의 모든 항목에 답이 있고 시행일자가 적혀 있다.
- **흔한 실수**: 다른 서비스의 방침을 그대로 복사한다. 실제 처리와 다르면 그 자체로 위반 소지가 있다.

### C-2. 이용약관

- **목적**: 서비스 규칙과 책임 범위를 밝힌다. 특히 다음을 넣는다.
  - "조언은 참고용이며 의료·법률·재무 전문 자문이 아니다"
  - 조언 승인·반려 권한, 조언가 신청 심사
  - 게시물 권리
  - 탈퇴·삭제 정책
- **단계**: 공정거래위원회 표준약관(https://www.ftc.go.kr 에서 `표준약관` 검색)으로 시작한다. 그다음 참늘 도메인 규칙(CLAUDE.md §6: 승인된 조언만 공개, 조언가 신청 심사)을 반영한다.
- **흔한 실수**: 위기 상황 대응 문구를 빼먹는다. 고민 글에 자해나 자살을 암시하는 내용이 있을 수 있으니, 상담전화 안내(자살예방상담전화 109)를 약관과 화면에 두는 것을 검토한다.

### C-3. 민감정보 · 14세 미만

- **민감정보**: 법 제23조의 민감정보(건강, 성생활 등)는 **별도 동의**를 받아야 처리할 수 있다. 2025.4 작성지침은 "계약 이행에 필요한 정보는 동의 없이 처리할 수 있지만, 민감정보는 계약 관계여도 동의가 필요하다"고 정리한다. 참늘의 고민 본문(번아웃, 관계 등)에는 사용자가 건강이나 정신건강 정보를 **스스로 적어 넣을 수 있다.** 다음 중 하나를 전문가와 상의해 정한다.
  - (a) "민감정보를 적지 말라"고 안내하고 별도 동의 없이 운영한다.
  - (b) 고민을 쓸 때 **민감정보 처리 별도 동의** 체크박스를 둔다.
  - 어느 쪽이든 조언가에게 무엇이 보이는지 처리방침에 적는다.
- **14세 미만**: 법 제22조의2에 따라 만 14세 미만의 개인정보를 처리하려면 **법정대리인 동의를 받고 그 동의를 확인해야** 한다. 참늘의 대상은 20~30대이므로, **가입할 때 "만 14세 이상입니다"를 확인하고 미만은 가입을 막는 방식**이 가장 단순하다. 백엔드에 반영하려면 별도 SPEC이 필요하다(D 목록).

### C-4. 사업자등록 · 통신판매업 신고

- **지금(무료, 수익 없음)**: 영리 목적으로 계속·반복해서 파는 것이 없으니, 신고 의무가 생기는 전형적인 상황은 아니다. 다만 광고 수익 같은 **수익이 생기는 순간** 사업자등록 대상이 될 수 있다.
- **유료화할 때**: 온라인으로 돈을 받으면 통신판매에 해당한다. 원칙적으로 **통신판매업 신고**를 해야 한다(정부24 https://www.gov.kr 에서 `통신판매업 신고` 검색).
  - 면제 기준(거래 횟수, 간이과세자 등)은 2차 자료마다 다르게 적혀 있다. **공정위 고시 원문으로 확인해야** 한다.
  - PG사(결제대행사)에 가입할 때 신고번호를 요구하는 경우가 많다.
- **사업자등록**: 홈택스 https://www.hometax.go.kr → 신청/제출 → 사업자등록 신청(개인). 업종은 정보통신업(소프트웨어·플랫폼) 계열이 될 것이다. 세무사 확인을 권장한다.
- 사업자를 내면 처리방침·약관·사이트 하단에 상호, 대표자, 사업자번호를 표시해야 할 수 있다.

### C-5. 도메인 WHOIS 보호

- **단계**: https://ap.www.namecheap.com/domains/list/ → `chamneul.com` **MANAGE** → **Domain** 탭 → **PRIVACY PROTECTION**(Withheld for Privacy)이 **ON**인지 확인한다. 같은 화면에서 **Auto-Renew**도 켠다.
- **완료 확인**: 터미널에서 `whois chamneul.com | grep -i registrant` → 실명 대신 "Withheld for Privacy"나 "Redacted"가 나온다.

---

## D. 나중에 Owner가 내릴 결정 (짧은 목록)

1. **프론트엔드 스택**(예: Next.js, SvelteKit, 모바일 우선 중 무엇). 재설정 화면은 링크의 `#uid=...&token=...`을 읽어 #46으로 보내야 한다(형식은 이미 정해짐). 프래그먼트를 분석 도구나 로그로 보내지 않는 것도 프론트 쪽 책임이다.
2. **레이트 리밋 숫자**: 로그인 시도(IP·계정별), 재설정 요청(주소별 시간당 몇 회).
3. **베타 범위**: 초대제 vs 공개, 조언가 수, 기간, 14세 미만 차단을 언제 구현할지.
4. **남은 보안 결정**(SPEC-005 spec §12 표에서 처리 상태 확인): prod 설정 모듈 강제(S-3), prod `PASSWORD_RESET_URL` 필수화·https 검사(S-6), Google 로그인 버튼 옆 안내 문구(A-5).
5. **민감정보 동의 방식**(C-3의 a 또는 b).
6. **AWS 비용 상한**: EKS를 계속 켜 둘지, 실습할 때만 만들지.

---

## 검증 출처 (접속일 2026-10-22)

- AWS Free Tier: https://aws.amazon.com/free/
  - 개편 해설: https://www.neowin.net/news/aws-free-tier-overhauled-new-users-get-200-in-credits-but-theres-a-catch/
  - https://tech-insider.org/what-changed-in-the-aws-free-tier-for-2026/
- AWS 가입: https://signin.aws.amazon.com/signup?request_type=register
- IAM Identity Center: https://docs.aws.amazon.com/singlesignon/latest/userguide/getting-started.html
- AWS Budgets: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-create.html
- Route 53 위임: https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-name-servers-glue-records.html
- ACM DNS 검증: https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html
- SES 도메인 인증·MAIL FROM·DMARC:
  - https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html
  - https://docs.aws.amazon.com/ses/latest/dg/mail-from.html
  - https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dmarc.html
- SES 샌드박스 해제:
  - https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html
  - https://repost.aws/knowledge-center/ses-production-access-request-faq
- Google OAuth 클라이언트·secret 회전:
  - https://support.google.com/cloud/answer/6158849
  - https://developers.googleblog.com/usability-and-safety-updates-to-google-auth-platform/
- GitHub:
  - https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa
  - https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets
  - https://docs.github.com/en/code-security/secret-scanning
- 개인정보 처리방침 작성지침(2025.4):
  - https://www.pipc.go.kr
  - https://www.privacy.go.kr
  - 해설: https://www.daeryunlaw.com/newsletter/news/151
- 개인정보 보호법(제22조의2·제23조·제30조): https://www.law.go.kr
  - 해설: https://www.nepla.ai/wiki/it-정보-방송통신/개인정보-위치정보-신용정보/아동의-개인정보-보호-g6w93voqnojp
- 통신판매업(2차 자료라서 고시 원문 확인 필요):
  - https://www.gov.kr
  - https://imweb.me/blog?idx=491
  - https://www.findsemusa.com/service/consult/consultView.do?qidx=36534
- 공정위 표준약관: https://www.ftc.go.kr

> **직접 확인하지 못한 것**: AWS, GitHub, SES, Google 콘솔의 일부 버튼 라벨. privacy.go.kr 생성기 메뉴명. AWS Budgets 세부 요금. 통신판매업 면제 수치. 화면이 다르면 각 콘솔 검색창을 쓰고, 법·세무 수치는 원문으로 확인한다.
