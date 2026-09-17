#!/usr/bin/env bash
# 스모크 여정 — docs/smoke-test.md §3 (사용자 여정 12단계)
#
# 사용법:
#   SMOKE_ADMIN_PASSWORD='<createsuperuser로 만든 비밀번호>' bash scripts/smoke-journey.sh
#
# 전제: 컨테이너가 떠 있고 migrate + createsuperuser가 끝나 있을 것 (§2).
# 매 실행마다 새 계정을 만들므로 반복 실행해도 409가 나지 않는다.
# 관리자 비밀번호는 환경변수로 받는다 — 자격증명을 저장소에 커밋하지 않는다.
set -uo pipefail
B=http://localhost:8000/api/v1
RUN=${RUN:-$(date +%H%M%S)}   # 재실행 가능하도록 계정을 매번 새로 만든다
J=/tmp/smoke; rm -rf $J; mkdir -p $J

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

for a in user advisor admin; do boot $J/$a.jar; done

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
