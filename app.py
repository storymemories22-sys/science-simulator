import streamlit as st
import plotly.graph_objects as go
import json
from google import genai
from google.genai import types

st.set_page_config(
    page_title="과학과제연구 가상 실험 시뮬레이터",
    page_icon="🧪",
    layout="wide"
)

# 세션 상태 초기화 (브라우저 탭별 독립 세션)
if "history" not in st.session_state:
    st.session_state.history = []
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- 사이드바: 개인 계정 API 키 연동 ---
with st.sidebar:
    st.header("🔑 연구원 계정 인증")
    user_key = st.text_input(
        "Gemini API Key", 
        value=st.session_state.api_key, 
        type="password",
        placeholder="AI Studio 키를 붙여넣으세요",
        help="본인 구글 계정으로 발급받은 키입니다. 창을 닫으면 자동 초기화됩니다."
    )
    if user_key != st.session_state.api_key:
        st.session_state.api_key = user_key

    st.markdown("---")
    st.link_button("👉 구글 AI Studio 무료 키 발급", "https://aistudio.google.com/apikey")
    st.caption("1. 구글 로그인 후 [Create API key] 생성")
    st.caption("2. 발급받은 키를 위 입력창에 붙여넣기")
    st.markdown("---")
    st.caption("💡 **가상 드라이런(Dry-run) 시뮬레이션이란?**")
    st.caption("실제 실험 전, 과학적 메커니즘과 단계별 절차의 인과적 결함을 AI로 사전 검증하고 도출될 데이터를 예측하는 시스템입니다.")

# --- 메인 화면 ---
st.title("🧪 고교 과학과제연구 프로토콜 검증 & 가상 실험 시뮬레이터")
st.caption("실험 절차의 물리·화학·생물학적 결함을 추적하고, 실제 수행 시 도출될 결과 데이터와 가설 입증 확률을 예측합니다.")

col_input, col_sim = st.columns([1, 1])

# [좌측] 연구 설계 및 상세 프로토콜 입력
with col_input:
    st.subheader("📝 연구 설계 및 상세 프로토콜")
    
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        field = st.selectbox("연구 분야", ["화학", "생명과학", "물리", "지구·환경과학", "융합공학"])
    with col_f2:
        topic = st.text_input("연구 주제", value="감귤 껍질 플라보노이드 추출물의 항균 활성 검증")

    hypothesis = st.text_area(
        "연구 가설 (조작변인과 종속변인의 인과관계 명시)",
        value="감귤 껍질의 에탄올 추출물 농도가 5%, 10%, 20%로 증가할수록 대장균 배양 배지의 생장 억제환(Clear zone) 직경이 비례하여 확장될 것이다.",
        height=80
    )

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        indep_var = st.text_input("조작변인 및 측정 구간", value="추출물 농도 (대조군 0%, 5%, 10%, 20%)")
        control_group = st.text_area("대조군 (Control 설정)", value="음성 대조군: 70% 에탄올 용매만 처리한 디스크\n양성 대조군: 시판 항생제 디스크", height=70)
    with col_v2:
        dep_var = st.text_input("종속변인 (측정 단위 필수)", value="생장 억제환 직경 (mm, 버니어 캘리퍼스)")
        ctrl_var = st.text_area("통제변인 (고정 조건)", value="배양 온도 37°C, 배양 시간 24시간, 균 도말량 100μL", height=70)

    st.markdown("##### 🔬 단계별 상세 실험 절차 (Protocol)")
    st.caption("시료 처리, 농도 조절, 반응 시간, 측정 방식을 구체적으로 기술하세요.")
    protocol = st.text_area(
        "수행 과정 입력",
        value="[Step 1. 시료 추출]\n건조된 감귤 껍질 분말 10g에 70% 에탄올 100mL를 넣고 상온에서 24시간 침출 후 여과한다.\n\n"
              "[Step 2. 농도 희석]\n감압 농축기로 용매를 완전히 증발시킨 후 멸균 증류수로 5%, 10%, 20% 농도로 단계 희석한다.\n\n"
              "[Step 3. 접종 및 시료 처리]\nLB 고체 배지에 대장균 배양액 100μL를 도말하고, 농도별 추출액 20μL를 흡수시킨 6mm 페이퍼 디스크를 올린다.\n\n"
              "[Step 4. 배양 및 정량 측정]\n37°C 항온기에서 24시간 배양 후 캘리퍼스로 디스크 주변의 투명환 직경을 N=3 반복 측정한다.",
        height=200
    )

    run_btn = st.button("⚡ AI 가상 실험(Dry-Run) 실행", type="primary")

# 제미나이 가상 시뮬레이션 연동 로직
if run_btn:
    active_key = st.session_state.api_key.strip()
    if not active_key:
        st.error("⚠️ 좌측 사이드바에 Gemini API Key를 먼저 입력해주세요.")
    elif not protocol.strip() or not hypothesis.strip():
        st.warning("⚠️ 연구 가설과 상세 프로토콜을 모두 작성해야 합니다.")
    else:
        with st.spinner("AI가 실험 프로토콜의 인과 메커니즘을 추적하며 가상 실험을 구동 중입니다..."):
            try:
                client = genai.Client(api_key=active_key)
                
                system_prompt = f"""
당신은 첨단 과학 연구소의 수석 연구원이자 고교 과학과제연구 심사위원장입니다.
제공된 연구 설계와 단계별 실험 절차(Protocol)를 바탕으로 '가상 실험(Dry-run)'을 수행하고 인과적 분석 결과를 순수 JSON 규격으로 응답하세요.

[시뮬레이션 및 데이터 생성 기준]
1. 가상 도출 데이터 (simulated_data):
   - 학생의 조작변인 구간(최소 4개 지점)에 맞춰 실제로 실험을 수행했을 때 도출될 현실적인 측정값(expected_y)과 표준오차(error_margin)를 과학 이론에 기반해 수치로 산출할 것.
   - x축 라벨과 y축 라벨(단위 포함)을 정확히 지정할 것.
2. 단계별 프로토콜 추적 (step_evaluations):
   - 학생이 작성한 각 Step을 개별 분석하여 상태("정상", "주의", "치명적 결함")를 매길 것.
   - 화학 반응 오차, 용매 잔류, 열 변성, 오염 위험 등 현장에서 겪을 인과적 병목을 구체적으로 지적할 것.
3. 가설 입증 확률 (success_probability):
   - 현재 프로토콜 설계대로 수행했을 때 가설이 유의미하게 검증될 확률 (0~100 정수).

[반환 JSON 포맷]
{{
  "success_probability": (0~100 정수),
  "verdict_summary": "시뮬레이션 총평 요약 (1~2문장)",
  "simulated_data": {{
    "x_axis_title": "조작변인 축 이름 (단위)",
    "y_axis_title": "종속변인 축 이름 (단위)",
    "data_points": [
      {{"x_val": "0 (대조군)", "expected_y": 6.0, "error_margin": 0.2}},
      {{"x_val": "5%", "expected_y": 8.5, "error_margin": 0.7}},
      {{"x_val": "10%", "expected_y": 12.0, "error_margin": 1.0}},
      {{"x_val": "20%", "expected_y": 14.5, "error_margin": 1.3}}
    ]
  }},
  "step_evaluations": [
    {{
      "step_name": "단계 명칭",
      "status": "정상" / "주의" / "치명적 결함",
      "analysis": "단계별 과학적 메커니즘 검증 및 결함 분석"
    }}
  ],
  "critical_failure_points": [
    "실제 실험 시 실패를 유발할 수 있는 결정적 요인 1",
    "결정적 요인 2"
  ],
  "protocol_optimization": [
    "절차 수정을 위한 구체적 최적화 제안 1",
    "측정 정밀도를 높이기 위한 대안 2"
  ],
  "expected_log": "실험 진행 시 현장에서 목격될 실제 육안 관찰 현상 묘사"
}}
"""

                user_prompt = f"""
[연구 설계]
분야: {field}
주제: {topic}
가설: {hypothesis}
조작변인: {indep_var}
종속변인: {dep_var}
대조군: {control_group}
통제변인: {ctrl_var}

[실험 상세 절차]
{protocol}
"""

                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )

                sim_result = json.loads(response.text)
                st.session_state.history.append(sim_result)

            except Exception as e:
                st.error(f"가상 시뮬레이션 중 오류 발생: {str(e)}")

# [우측] 가상 드라이런 결과 대시보드
with col_sim:
    st.subheader("📊 가상 실험(Dry-Run) 결과 대시보드")

    if not st.session_state.history:
        st.info("좌측 사이드바에 API 키를 입력하고 **[⚡ AI 가상 실험 실행]** 버튼을 누르면 AI 드라이런 결과가 도출됩니다.")
    else:
        latest = st.session_state.history[-1]
        
        # 1. 성공 확률 및 판정 메트릭
        prob = latest["success_probability"]
        m1, m2 = st.columns([1, 2])
        with m1:
            st.metric("가설 검증 성공 확률", f"{prob}%")
        with m2:
            if prob >= 75:
                st.success(f"🟢 **[수행 권장]** {latest['verdict_summary']}")
            elif prob >= 50:
                st.warning(f"🟡 **[조건부 보완]** {latest['verdict_summary']}")
            else:
                st.error(f"🔴 **[설계 재검토]** {latest['verdict_summary']}")

        st.markdown("---")

        # 2. 가상 측정 데이터 추세선 및 오차 막대 차트
        st.markdown("##### 📈 가상 도출 데이터 추세선 (Simulated Outcome)")
        sim_data = latest.get("simulated_data", {})
        points = sim_data.get("data_points", [])

        if points:
            x_vals = [p["x_val"] for p in points]
            y_vals = [p["expected_y"] for p in points]
            errors = [p.get("error_margin", 0) for p in points]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                error_y=dict(type='data', array=errors, visible=True),
                mode='lines+markers',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8, color='#0d47a1'),
                name="예상 측정값 (평균±오차)"
            ))

            fig.update_layout(
                xaxis_title=sim_data.get("x_axis_title", "조작변인"),
                yaxis_title=sim_data.get("y_axis_title", "종속변인"),
                margin=dict(l=40, r=30, t=20, b=40),
                height=320
            )
            st.plotly_chart(fig, use_container_width=True)

        # 3. 단계별 프로토콜 메커니즘 진단 로그
        st.markdown("##### 🔍 단계별 프로토콜 정밀 진단 (Step-by-step Dry Run)")
        for step in latest.get("step_evaluations", []):
            status = step.get("status", "주의")
            icon = "✅" if status == "정상" else ("⚠️" if status == "주의" else "🚫")
            with st.expander(f"{icon} **{step.get('step_name', '단계')}** - [{status}]", expanded=(status != "정상")):
                st.write(step.get("analysis", ""))

        # 4. 현장 실패 요인 및 프로토콜 최적화 처방
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("##### ⚠️ 현장 실패 유발 요인")
            for fail in latest.get("critical_failure_points", []):
                st.error(f"• {fail}")

        with col_c2:
            st.markdown("##### 💡 프로토콜 최적화 가이드")
            for opt in latest.get("protocol_optimization", []):
                st.info(f"• {opt}")

        # 5. 가상 현장 관찰 일지 프리뷰
        if "expected_log" in latest:
            st.markdown("##### 📋 가상 실험 관찰 일지 (현장 현상 프리뷰)")
            st.text_area("예상되는 시각적·물리적 변화", value=latest["expected_log"], height=90, disabled=True)

        if st.button("🔄 기록 초기화"):
            st.session_state.history = []
            st.rerun()