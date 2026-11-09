#!/usr/bin/env bash
# 스모크 여정 — docs/smoke-test.md §3 (사용자 여정 15단계)
#
# 사용법:
#   SMOKE_ADMIN_PASSWORD='<createsuperuser로 만든 비밀번호>' bash scripts/smoke-journey.sh
#
# 전제: 컨테이너가 떠 있고 migrate + createcachetable + createsuperuser가 끝나 있을 것 (§2).
# 매 실행마다 새 계정을 만들므로 반복 실행해도 409가 나지 않는다.
# 단, 요청 횟수 제한(api.md §1.10)은 실행 사이에도 남는다. 로컬은 모든 요청이 같은 IP다.
#   - 로그인 IP 한도 20회/분, 실행당 14회 → 1분 안에 다시 돌리면 15단계가 일찍 429를 받는다
#   - 가입 IP 한도 10회/시간, 실행당 3회 → 한 시간에 네 번째 실행이 막힌다
# 다시 돌리기 전에 1분 이상 기다리거나 카운터를 비운다(smoke-test §6).
# 관리자 비밀번호는 환경변수로 받는다 — 자격증명을 저장소에 커밋하지 않는다.
# 13단계는 local의 콘솔 메일에서 재설정 링크를 읽는다(docker compose logs) — 토큰은
# 살아 있는 링크라 화면에 찍지 않는다(§5 갭 10).
set -uo pipefail
cd "$(dirname "$0")/.."   # 13단계의 docker compose logs가 compose 파일을 찾도록
B=http://localhost:8000/api/v1
RUN=${RUN:-$(date +%H%M%S)}   # 재실행 가능하도록 계정을 매번 새로 만든다
# 쿠키 항아리에는 관리자 세션이 들어 있다 — 나만 읽는 임시 폴더에 두고, 끝나면 지운다.
umask 077
J=$(mktemp -d "${TMPDIR:-/tmp}/chamneul-smoke.XXXXXX")
trap 'rm -rf "$J"' EXIT

# 각 배우는 자기 쿠키 항아리를 갖는다 (세션 3개 동시 유지).
csrf() { grep csrftoken "$1" | awk '{print $7}'; }
boot() { curl -s -c "$1" -o /dev/null "$B/csrf"; }
req()  { # req <jar> <method> <path> [json]
  local jar=$1 m=$2 p=$3 body=${4:-}
  local t; t=$(csrf "$jar")
  if [ -n "$body" ]; then
    curl -s -c "$jar" -b "$jar" -X "$m" -H 'Content-Type: application/json' \
         -H "X-CSRFToken: $t" -d "$body" -w $'\n%{http_code}' "$B$p"
  else
    curl -s -c "$jar" -b "$jar" -X "$m" -H "X-CSRFToken: $t" -w $'\n%{http_code}' "$B$p"
  fi
}
code() { tail -1 <<<"$1"; }
body() { sed '$d' <<<"$1"; }
# jq_ <response> <key> [key...]  — 중첩 키는 공백으로 이어서 넘긴다.
jq_() { local r=$1; shift; body "$r" | python3 -c '
import sys, json
d = json.load(sys.stdin)
for k in sys.argv[1:]:
    d = d[int(k)] if k.lstrip("-").isdigit() else d[k]
print(d)' "$@" 2>/dev/null; }
step() { printf '\n── %s\n' "$*"; }

for a in user advisor admin advisor2 ratelimit; do boot $J/$a.jar; done

step "1. 회원가입 (#2) — 고민 작성자"
R=$(req $J/user.jar POST /auth/signup "{\"email\":\"smoke.user+$RUN@example.com\",\"nickname\":\"user$RUN\",\"password\":\"SmokePw12345!\"}")
echo "HTTP $(code "$R")  $(body "$R" | head -c 120)"
grep -q sessionid $J/user.jar && echo "sessionid 쿠키 발급됨 (가입 즉시 로그인)"

step "1b. 회원가입 (#2) — 조언가"
R=$(req $J/advisor.jar POST /auth/signup "{\"email\":\"smoke.advisor+$RUN@example.com\",\"nickname\":\"adv$RUN\",\"password\":\"SmokePw12345!\"}")
echo "HTTP $(code "$R")"
ADVISOR_ID=$(jq_ "$R" user_id)
echo "advisor_id=$ADVISOR_ID"

step "2. 로그인 (#3) — 관리자(superuser)"
ADMIN_EMAIL=${SMOKE_ADMIN_EMAIL:-root@chamneul.local}
ADMIN_PW=${SMOKE_ADMIN_PASSWORD:?SMOKE_ADMIN_PASSWORD를 설정하세요 (createsuperuser로 만든 관리자 비밀번호)}
R=$(req $J/admin.jar POST /auth/login "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PW\"}")
echo "HTTP $(code "$R")  $(body "$R" | head -c 120)"

step "3. 고민 작성 (#16)"
R=$(req $J/user.jar POST /users/me/concerns '{"concern_summary":"3년차인데 이직을 할지 남을지 결정해야 합니다","concern_type":"job_change","decision_context":"제안 2건, 연봉은 비슷하고 직무가 다릅니다."}')
echo "HTTP $(code "$R")"
CONCERN=$(jq_ "$R" concern_id); echo "concern_id=$CONCERN"

step "3b. 내 고민 목록 (#17)"
R=$(req $J/user.jar GET /users/me/concerns)
echo "HTTP $(code "$R")  total=$(jq_ "$R" page_info total)"

step "4. 관리자 고민 목록 (#22)"
R=$(req $J/admin.jar GET /admin/concerns)
echo "HTTP $(code "$R")  total=$(jq_ "$R" page_info total)"

step "4b. 조언가 역할 부여 (#42) — 정상 경로는 신청·승인이나 스모크는 직접 부여"
R=$(req $J/admin.jar POST "/admin/users/$ADVISOR_ID/roles" '{"role":"ADVISOR","reason":"smoke test"}')
echo "HTTP $(code "$R")  roles=$(jq_ "$R" roles)"

step "4c. 배정 (#24)"
R=$(req $J/admin.jar POST "/admin/concerns/$CONCERN/assignments" "{\"advisor_user_id\":\"$ADVISOR_ID\",\"triage_decision\":\"suitable\",\"priority\":\"normal\"}")
echo "HTTP $(code "$R")  $(body "$R" | head -c 160)"

step "5. 조언가 역할 전환 (#10)"
R=$(req $J/advisor.jar PATCH /users/me/active-role '{"active_role":"ADVISOR"}')
echo "HTTP $(code "$R")  $(body "$R" | head -c 120)"

step "5b. 배정 고민 목록 (#20) · 상세 (#21)"
R=$(req $J/advisor.jar GET /users/me/assigned-concerns)
echo "#20 HTTP $(code "$R")  total=$(jq_ "$R" page_info total)"
R=$(req $J/advisor.jar GET "/users/me/assigned-concerns/$CONCERN")
echo "#21 HTTP $(code "$R")"

step "6. 조언 작성 (#28)"
R=$(req $J/advisor.jar POST "/concerns/$CONCERN/advices" '{"directional_guidance":"두 선택지의 5년 후 모습을 각각 적어보세요. 지금 비교하는 축이 그때도 중요한지 확인하는 방법입니다.","reflective_questions":"무엇이 가장 두려운가요? / 3년 뒤 후회할 선택은 어느 쪽인가요?","considerations":"연봉 외 요소(성장·동료·통근)를 같은 저울에 올려보세요.","submit":true}')
echo "HTTP $(code "$R")"
ADVICE=$(jq_ "$R" advice_id); echo "advice_id=$ADVICE  status=$(jq_ "$R" status)  version=$(jq_ "$R" version)"

step "7. 관리자 리뷰 목록 (#32) · 승인 (#33)"
R=$(req $J/admin.jar GET /admin/advices)
echo "#32 HTTP $(code "$R")  total=$(jq_ "$R" page_info total)"
R=$(req $J/admin.jar PATCH "/admin/advices/$ADVICE/review" '{"decision":"approved","expected_version":1}')
echo "#33 HTTP $(code "$R")  $(body "$R" | head -c 200)"

step "7b. concern 상태 전이 확인 (ASSIGNED -> ANSWERED)"
R=$(req $J/user.jar GET "/users/me/concerns/$CONCERN")
echo "HTTP $(code "$R")  status=$(jq_ "$R" status)"

step "8. 사용자: 받은 조언 (#26) · 상세 (#27)"
R=$(req $J/user.jar GET /users/me/advices)
echo "#26 HTTP $(code "$R")  total=$(jq_ "$R" page_info total)"
R=$(req $J/user.jar GET "/advices/$ADVICE")
echo "#27 HTTP $(code "$R")  reject_reason 노출여부=$(body "$R" | grep -c reject_reason)"

step "9. 피드백 작성 (#34)"
R=$(req $J/user.jar POST "/advices/$ADVICE/feedbacks" '{"score":5,"is_helpful":true,"comment":"질문 두 개가 특히 도움이 됐습니다."}')
echo "HTTP $(code "$R")  $(body "$R" | head -c 160)"

step "10. 알림 (#39 목록 · #41 읽음 · target_url 이동)"
R=$(req $J/user.jar GET /notifications)
echo "#39 HTTP $(code "$R")  unread_count=$(jq_ "$R" unread_count)  총 $(jq_ "$R" page_info total)건"
NOTI=$(jq_ "$R" items 0 notification_id)
TURL=$(jq_ "$R" items 0 target_url)
echo "첫 알림 type=$(jq_ "$R" items 0 type)  target_url=$TURL"
R=$(req $J/user.jar PATCH "/notifications/$NOTI/read")
echo "#41 HTTP $(code "$R")  $(body "$R" | head -c 140)"
R=$(req $J/user.jar GET /notifications)
echo "읽음 후 unread_count=$(jq_ "$R" unread_count)"
R=$(curl -s -b $J/user.jar -w $'\n%{http_code}' "http://localhost:8000$TURL")
echo "target_url 이동 -> HTTP $(code "$R")"

step "10b. 조언가 알림함 (배정 알림 본문이 고민 요약 사본을 담지 않는지)"
R=$(req $J/advisor.jar GET /notifications)
echo "HTTP $(code "$R")  총 $(jq_ "$R" page_info total)건"
echo "message: $(jq_ "$R" items 0 message)"

step "11. 역할 회수 (#43) 직후 조언가 활동 차단"
R=$(req $J/admin.jar DELETE "/admin/users/$ADVISOR_ID/roles/ADVISOR?reason=smoke")
echo "#43 HTTP $(code "$R")"
R=$(req $J/advisor.jar GET /users/me/assigned-concerns)
echo "회수 후 #20 -> HTTP $(code "$R")  $(body "$R" | head -c 100)"
R=$(req $J/advisor.jar GET /users/me/roles)
echo "회수 후 내 역할: $(body "$R")"

step "12. 로그아웃 (#4)"
R=$(req $J/user.jar POST /auth/logout)
echo "HTTP $(code "$R")"
R=$(req $J/user.jar GET /users/me)
echo "로그아웃 후 /users/me -> HTTP $(code "$R")  (401이면 서버 세션 삭제됨)"

step "13. 비밀번호 재설정 (#45 요청 → 콘솔 메일의 링크 → #46 확정 → 새 비밀번호로 로그인)"
R=$(req $J/user.jar POST /auth/password-reset "{\"email\":\"smoke.user+$RUN@example.com\"}")
echo "#45 HTTP $(code "$R")"
LINK=""
for _ in 1 2 3 4 5; do   # 메일은 요청 안에서 보내지만, 로그 수집이 조금 늦을 수 있다
  LINK=$(docker compose logs app --since 1m 2>/dev/null \
         | grep -oE 'uid=[A-Za-z0-9_-]+&token=[0-9a-z]+-[0-9a-f]+' | tail -1)
  [ -n "$LINK" ] && break; sleep 1
done
RESET_UID=${LINK#uid=}; RESET_UID=${RESET_UID%%&*}; RESET_TOKEN=${LINK##*token=}
if [ -n "$LINK" ]; then echo "콘솔 메일에서 링크 찾음 (uid=${RESET_UID:0:6}…, token=<가림>)"
else echo "콘솔 메일에서 링크를 찾지 못함"; fi
CONFIRM="{\"uid\":\"$RESET_UID\",\"token\":\"$RESET_TOKEN\",\"new_password\":\"SmokeNewPw67890!\"}"
R=$(req $J/user.jar POST /auth/password-reset/confirm "$CONFIRM")
echo "#46 HTTP $(code "$R")"
R=$(req $J/user.jar POST /auth/password-reset/confirm "$CONFIRM")
echo "같은 링크 다시 → HTTP $(code "$R")  (400이면 한 번만 쓸 수 있다)"
unset LINK RESET_TOKEN CONFIRM
R=$(req $J/user.jar POST /auth/login "{\"email\":\"smoke.user+$RUN@example.com\",\"password\":\"SmokePw12345!\"}")
echo "옛 비밀번호 로그인 → HTTP $(code "$R")"
R=$(req $J/user.jar POST /auth/login "{\"email\":\"smoke.user+$RUN@example.com\",\"password\":\"SmokeNewPw67890!\"}")
echo "새 비밀번호 로그인 → HTTP $(code "$R")"

step "14. 고민 수정 (#47) — 배정 전 200, 배정 후 409"
R=$(req $J/user.jar POST /users/me/concerns '{"concern_summary":"번아웃인지 일시적인 피로인지 모르겠습니다","concern_type":"burnout","decision_context":"석 달째 쉬어도 회복되지 않습니다."}')
CONCERN2=$(jq_ "$R" concern_id); echo "#16 HTTP $(code "$R")  concern_id=$CONCERN2"
R=$(req $J/user.jar PATCH "/users/me/concerns/$CONCERN2" '{"decision_context":"석 달째 쉬어도 회복되지 않고, 주 3회 이상 야근합니다."}')
echo "배정 전 #47 HTTP $(code "$R")  decision_context=$(jq_ "$R" decision_context)"
# 11단계에서 첫 조언가의 역할을 회수했으므로 조언가를 새로 세운다.
R=$(req $J/advisor2.jar POST /auth/signup "{\"email\":\"smoke.advisor2+$RUN@example.com\",\"nickname\":\"adv2$RUN\",\"password\":\"SmokePw12345!\"}")
ADVISOR2_ID=$(jq_ "$R" user_id)
R=$(req $J/admin.jar POST "/admin/users/$ADVISOR2_ID/roles" '{"role":"ADVISOR","reason":"smoke test"}')
echo "조언가2 역할 부여 #42 HTTP $(code "$R")"
R=$(req $J/admin.jar POST "/admin/concerns/$CONCERN2/assignments" "{\"advisor_user_id\":\"$ADVISOR2_ID\",\"triage_decision\":\"suitable\"}")
echo "배정 #24 HTTP $(code "$R")"
R=$(req $J/user.jar PATCH "/users/me/concerns/$CONCERN2" '{"decision_context":"배정 뒤에 고치려는 시도"}')
echo "배정 후 #47 HTTP $(code "$R")  reason=$(jq_ "$R" error details reason)"

step "15. 로그인 요청 횟수 제한 (#3) — 같은 주소로 한도(10회/시간)를 넘기면 429"
RL='{"email":"smoke.ratelimit+'$RUN'@example.com","password":"wrong-password"}'
CODES=""
for _ in $(seq 1 10); do R=$(req $J/ratelimit.jar POST /auth/login "$RL"); CODES="$CODES $(code "$R")"; done
echo "1~10번째:$CODES"
T=$(csrf $J/ratelimit.jar)
C=$(curl -s -D $J/rl.headers -o $J/rl.body -c $J/ratelimit.jar -b $J/ratelimit.jar -X POST \
     -H 'Content-Type: application/json' -H "X-CSRFToken: $T" -d "$RL" -w '%{http_code}' "$B/auth/login")
echo "11번째 → HTTP $C  $(grep -i '^retry-after' $J/rl.headers | tr -d '\r')  code=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["error"]["code"])' $J/rl.body 2>/dev/null)"

step "정리 — 관리자 로그아웃"
R=$(req $J/admin.jar POST /auth/logout)
echo "관리자 #4 HTTP $(code "$R")  (세션을 남기지 않는다 — 쿠키 폴더도 종료 때 지워진다)"
