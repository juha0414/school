# pages/1_달력별_급식.py — 나이스 급식 API로 그날 식단을 카드로 보여 주는 페이지
import datetime
import re

import requests
import streamlit as st

st.title("🍚 우리 학교 급식")

# 날짜와 알레르기 스위치를 나란히 놓는다
left, right = st.columns([2, 1])
picked = left.date_input("날짜를 고르세요", value=(datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date())  # 한국 시간 기준 오늘
show_allergy = right.toggle("알레르기 정보 보기", value=True)
ymd = picked.strftime("%Y%m%d")

# 나이스 급식 API — 인증키 없이 호출한다 (조회 기간은 하루)
url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
params = {
    "Type": "json",                # 응답을 JSON으로
    "ATPT_OFCDC_SC_CODE": "J10",   # 경기도교육청
    "SD_SCHUL_CODE": "7530480",    # 송탄고등학교
    "MMEAL_SC_CODE": "2",          # 중식
    "MLSV_FROM_YMD": ymd,
    "MLSV_TO_YMD": ymd,
}
data = requests.get(url, params=params, timeout=10).json()

weekday = "월화수목금토일"[picked.weekday()]
st.subheader(picked.strftime("%Y년 %m월 %d일") + f" ({weekday}) 중식")

if "mealServiceDietInfo" not in data:
    result = data.get("RESULT", {})
    if result.get("CODE") == "INFO-200":
        st.info("조회한 날짜의 급식 정보가 없습니다.")
    else:
        st.error("급식 조회에 실패했습니다. " + result.get("MESSAGE", "요청 조건을 확인해 주세요."))
else:
    row = data["mealServiceDietInfo"][1]["row"][0]
    # 메뉴 전체가 한 덩어리 글자로 온다 — <br/>로 잘라 낱개 메뉴로
    dishes = [d.strip() for d in row["DDISH_NM"].split("<br/>") if d.strip()]
    if not show_allergy:
        # 괄호 속 알레르기 번호 떼기
        dishes = [re.sub(r"\s*\([0-9.]+\)", "", d) for d in dishes]

    # 큰 숫자 카드 — 메뉴 가짓수와 칼로리
    m1, m2 = st.columns(2)
    m1.metric("메뉴", f"{len(dishes)}가지")
    m2.metric("칼로리", row["CAL_INFO"])

    # 메뉴를 카드 세 칸씩 나란히
    cols = st.columns(3)
    for i, dish in enumerate(dishes):
        with cols[i % 3].container(border=True):
            st.write(dish)
