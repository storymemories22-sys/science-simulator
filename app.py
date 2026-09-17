import streamlit as st
import plotly.graph_objects as go
import json
import urllib.parse
from google import genai
from google.genai import types

st.set_page_config(
    page_title="고교 과학과제연구 가상 실험 시뮬레이터",
    page_icon="🧪",
    layout="wide"
)

# --- 기본 예시 데이터 명세 ---
DEFAULT_DATA = {
    "field": "화학",
    "topic": "감귤 껍질 플라보노이드 추출물의 항균 활성 검증",
    "hypothesis": "감귤 껍질의 에탄올 추출물 농도가 5%, 10%, 20%로 증가할수록 대장균 배양 배지의 생장 억제환(Clear zone) 직경이 비례하여 확장될 것이다.",
    "indep_var": "추출물 농도 (대조군 0%, 5%, 10%, 20%)",
    "dep_var": "생장 억제환 직경 (mm, 버니어 캘리퍼스)",
    "control_group": "음성 대조군: 70% 에탄올 용매만 처리한 디스크\n양성 대조군: 시판 항생제 디스크",
    "ctrl_var": "배양 온도 37°C, 배양 시간 24시간, 균 도말량 100μL",
    "protocol": "[Step 1. 시료 추출]\n건조된 감귤 껍질 분말 10g에 70% 에탄올 100mL를 넣고 상온에서 24시간 침출 후 여과한다.\n\n[Step 2. 농도 희석]\n감압 농축기로 용매를 완전히 증발시킨 후 멸균 증류수로 5%, 10%, 20% 농도로 단계 희석한다.\n\n[Step 3. 접종 및 시료 처리]\nLB 고체 배지에 대장균 배양액 100μL를 도말하고, 농도별 추출액 20μL를 흡수시킨 6mm 페이퍼 디스크를 올린다.\n\n[Step 4. 배양 및 정량 측정]\n37°C 항온기에서 24시간 배양 후 캘리퍼스로 디스크 주변의 투명환 직경을 N=3 반복 측정한다."
}

# 세션 상태 초기화
for k, v in DEFAULT_DATA.items():
    if k not in st.session_state:
        st.session_state[k] = v

if "history" not in st.session_state:
    st.session_state.history = []
if "custom_key" not in st.session_state:
    st.session_state.custom_key = ""

# --- API 키 자동 감지 (서버 시크릿 우선 적용) ---
server_api_key = ""
if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
    server_api_key = st.secrets["GEMINI_API_KEY"]

# --- [사이드바] 계정 인증 및 프로젝트 보관함 ---
with st.sidebar:
    st.header("🔑 AI 연구 인프라 인증")
    
    if server_api_key:
        st.success("🔒 학교 공용 연구 AI 엔진 활성화됨\n(학생 별도 로그인/키 입력 불필요)")
        active_key = server_api_key
    else:
        st.info("💡 서버 등록 키가 없습니다. 로컬 테스트용 키를 입력하세요.")
        user_key = st.text_input(
            "Gemini API Key", 
            value=st.session_state.custom_key, 
            type="password",
            placeholder="AI Studio 키를 입력하세요"
        )
        if user_key != st.session_state.custom_key:
            st.session_state.custom_key = user_key
        active_key = user_key

    st.markdown("---")
    st.header("📁 연구 프로젝트 보관함")
    st.caption("작성한 연구 계획과 AI 가상 실험 결과를 파일로 저장하거나 불러옵니다.")

    # 1. 파일 저장 (내보내기)
    export_payload = {
        "field": st.session_state.field,
        "topic": st.session_state.topic,
        "hypothesis": st.session_state.hypothesis,
        "indep_var": st.session_state.indep_var,
        "dep_var": st.session_state.dep_var,
        "control_group": st.session_state.control_group,
        "ctrl_var": st.session_state.ctrl_var,
        "protocol": st.session_state.protocol,
        "history": st.session_state.history
    }
    json_export_str = json.dumps(export_payload, ensure_ascii=False, indent=2)
    safe_topic = "".join([c for c in st.session_state.topic if c.isalnum() or c in (' ', '_')]).rstrip()
    filename = f"{safe_topic[:15] or '과학과제연구'}.json"

    st.download_button(
        label="💾 현재 연구 저장 (.json)",
        data=json_export_str,
        file_name=filename,
        mime="application/json",
        use_container_width=True
    )

    # 2. 파일 불러오기 (가져오기)
    uploaded_file = st.file_uploader("저장된 연구 파일 업로드", type=["json"])
    if uploaded_file is not None:
        if st.button("📥 불러온 데이터 적용하기", use_container_width=True):
            try:
                loaded_content = json.load(uploaded_file)
                for key in DEFAULT_DATA.keys():
                    if key in loaded_content:
                        st.session_state[key] = loaded_content[key]
                if "history" in loaded_content:
                    st.session_state.history = loaded_content["history"]
                st.success("데이터가 복원되었습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"파일을 읽는 중 오류가 발생했습니다: {str(e)}")

# --- [메인 화면] 연구 계획서 구조화 입력 폼 ---
st.title("🧪 고교 과학과제연구 가상 실험 & 학술 근거 시뮬레이터")
st.caption("프로토콜의 결함을 사전 검증하고, 예상 결과 데이터와 실시간 학술 논문 검색 근거를 도출합니다.")

col_input, col_sim = st.columns([1, 1])

with col_input:
    st.subheader("📝 연구 설계 및 상세 프로토콜")
    
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        field_list = ["화학", "생명과학", "물리", "지구·환경과학", "융합공학"]
        current_idx = field_list.index(st.session_state.field) if st.session_state.field in field_list else 0
        field = st.selectbox("연구 분야", field_list, index=current_idx, key="field")
    with col_f2:
        topic = st.text_input("연구 주제", key="topic")

    hypothesis = st.text_area("연구 가설 (조작변인과 종속변인의 인과관계 명시)", key="hypothesis", height=80)

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        indep_var = st.text_input("조작변인 및 측정 구간", key="indep_var")
        control_group = st.text_area("대조군 (Control 설정)", key="control_group", height=70)
    with col_v2:
        dep_var = st.text_input("종속변인 (측정 단위 필수)", key="dep_var")
        ctrl_var = st.text_area("통제변인 (고정 조건)", key="ctrl_var", height=70)

    st.markdown("##### 🔬 단계별 상세 실험 절차 (Protocol)")
    st.caption("시료 처리, 농도 조절, 반응 시간, 측정 방식을 구체적으로 기술하세요.")
    protocol = st.text_area("수행 과정 입력", key="protocol", height=200)

    run_btn = st.button("⚡ AI 가상 실험(Dry-Run) 및 학술 근거 탐색", type="primary")

# --- 제미나이 추론 엔진 ---
if run_btn:
    if not active_key:
        st.error("⚠️ AI 인증 키가 설정되지 않았습니다. 관리자에게 문의하거나 사이드바에 키를 입력하세요.")
    elif not protocol.strip() or not hypothesis.strip():
        st.warning("⚠️ 연구 가설과 상세 프로토콜을 모두 작성해야 합니다.")
    else:
        with st.spinner("AI가 프로토콜 메커니즘을 시뮬레이션하고 관련 학술 논문 근거를 분석 중입니다..."):
            try:
                client = genai.Client(api_key=active_key)
                
                system_prompt = f"""
당신은 첨단 과학 연구소의 수석 연구원이자 고교 과학과제연구 심사위원장입니다.
제공된 연구 설계와 단계별 실험 절차(Protocol)를 바탕으로 '가상 실험(Dry-run)'을 수행하고 인과적 분석 결과를 순수 JSON 규격으로 응답하세요.

[시뮬레이션 지침]
1. 가상 도출 데이터 (simulated_data):
   - 조작변인 구간에 맞춰 실제 수행 시 도출될 현실적 측정값(expected_y)과 오차 범위(error_margin)를 과학 이론치 기반으로 산출할 것.
2. 단계별 프로토콜 추적 (step_evaluations):
   - 각 Step을 개별 분석하여 상태("정상", "주의", "치명적 결함")를 매기고 현장 결함을 지적할 것.
3. 가설 입증 확률 (success_probability):
   - 현재 설계대로 진행 시 가설 지지 결과가 도출될 확률(0~100%).
4. 학술 근거 및 선행 연구 (references):
   - 가짜 URL을 절대 임의로 만들지 말 것.
   - theoretical_background: 이 연구의 핵심 과학적 배경 메커니즘 (2~3문장).
   - recommended_keywords_ko: 국내 학술 DB(ScienceON, RISS, DBpia) 검색에 최적화된 핵심 단어 조합 (공백 구분, 최대 3단어).
   - recommended_keywords_en: 해외 학술 DB(Google Scholar) 검색에 최적화된 영문 키워드 조합 (공백 구분, 최대 4단어).
   - suggested_topics: 학생들이 보고서 서론 작성 시 참고할 만한 선행 연구 논문/보고서 형태의 구체적 주제명 2가지.

[응답 JSON 스키마]
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
      "analysis": "단계별 메커니즘 타당성 및 결함 분석"
    }}
  ],
  "critical_failure_points": [
    "현장 실패 유발 결정 요인 1",
    "결정 요인 2"
  ],
  "protocol_optimization": [
    "절차 수정을 위한 구체적 솔루션 1",
    "측정 정밀도 개선안 2"
  ],
  "expected_log": "현장에서 실제 관찰될 현상 묘사 (색상 변화, 침전 등)",
  "references": {{
    "theoretical_background": "과학적 이론 및 메커니즘 설명",
    "recommended_keywords_ko": "국문 검색 키워드",
    "recommended_keywords_en": "영문 검색 키워드",
    "suggested_topics": [
      "추천 선행 연구 논문 주제 1",
      "추천 선행 연구 논문 주제 2"
    ]
  }}
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
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    st.error("⚠️ AI 호출 한도(분당 사용량)를 초과했습니다. 학생들의 동시 요청이 많을 수 있으니 약 30초~1분 후 다시 버튼을 눌러주세요.")
                else:
                    st.error(f"가상 시뮬레이션 중 오류 발생: {err_msg}")

# --- [우측] 결과 대시보드 ---
with col_sim:
    st.subheader("📊 가상 실험 결과 및 학술 근거")

    if not st.session_state.history:
        st.info("좌측 연구 절차를 작성하고 **[⚡ AI 가상 실험 실행]** 버튼을 누르면 시뮬레이션 결과와 학술 근거가 도출됩니다.")
    else:
        latest = st.session_state.history[-1]
        
        # 1. 성공 확률 및 판정
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

        # 2. 오차 막대 차트
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
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)

        # 3. 선행 연구 고찰 및 학술 검색 다이렉트 링크 (신규 추가)
        st.markdown("##### 📚 이론적 배경 & 학술 DB 다이렉트 검색")
        ref = latest.get("references", {})
        
        if ref:
            st.info(f"🧬 **핵심 이론 배경:** {ref.get('theoretical_background', '')}")
            
            topics = ref.get("suggested_topics", [])
            if topics:
                st.markdown("**📖 참고 권장 선행 연구 주제:**")
                for t in topics:
                    st.markdown(f"- {t}")

            # 학술 검색어 인코딩
            kw_ko = urllib.parse.quote(ref.get("recommended_keywords_ko", topic))
            kw_en = urllib.parse.quote(ref.get("recommended_keywords_en", topic))

            col_link1, col_link2 = st.columns(2)
            with col_link1:
                st.link_button(
                    "🌐 Google Scholar (글로벌 논문 검색)",
                    f"https://scholar.google.com/scholar?q={kw_en}",
                    use_container_width=True
                )
                st.link_button(
                    "🔬 ScienceON (KISTI 과학기술 논문)",
                    f"https://scienceon.kisti.re.kr/srch/selectPORSrchArticle.do?query={kw_ko}",
                    use_container_width=True
                )
            with col_link2:
                st.link_button(
                    "📑 DBpia (국내 학술지 검색)",
                    f"https://www.dbpia.co.kr/search/topSearch?searchOption=all&query={kw_ko}",
                    use_container_width=True
                )
                st.link_button(
                    "🎓 RISS (학위 및 학술 논문 검색)",
                    f"https://www.riss.kr/search/Search.do?query={kw_ko}",
                    use_container_width=True
                )

        st.markdown("---")

        # 4. 단계별 프로토콜 진단
        st.markdown("##### 🔍 단계별 프로토콜 정밀 진단 (Step-by-step Dry Run)")
        for step in latest.get("step_evaluations", []):
            status = step.get("status", "주의")
            icon = "✅" if status == "정상" else ("⚠️" if status == "주의" else "🚫")
            with st.expander(f"{icon} **{step.get('step_name', '단계')}** - [{status}]", expanded=(status != "정상")):
                st.write(step.get("analysis", ""))

        # 5. 실패 요인 및 개선안
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("##### ⚠️ 현장 실패 유발 요인")
            for fail in latest.get("critical_failure_points", []):
                st.error(f"• {fail}")

        with col_c2:
            st.markdown("##### 💡 프로토콜 최적화 가이드")
            for opt in latest.get("protocol_optimization", []):
                st.info(f"• {opt}")

        # 6. 가상 관찰 일지
        if "expected_log" in latest:
            st.markdown("##### 📋 가상 실험 관찰 일지 (현장 현상 프리뷰)")
            st.text_area("예상되는 시각적·물리적 변화", value=latest["expected_log"], height=80, disabled=True)

        if st.button("🔄 기록 초기화"):
            st.session_state.history = []
            st.rerun()