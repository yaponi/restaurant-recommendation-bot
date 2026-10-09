import streamlit as st
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI 

# 1. 웹페이지 기본 설정 (str -> st로 안전하게 변경)
st.set_page_config(page_title="영진전문대 맛집 에이전트", page_icon="🍚", layout="wide")

st.title("🤖 나만의 AI 맛집 에이전트 챗봇")
st.write("안녕하세요! 대구 복현동/영진전문대 맛집 전문 AI 비서입니다. 아무 말이나 편하게 걸어주세요!")

# 🔮 구글 API 로드 로직 최적화 및 방어 코드 구축
@st.cache_resource
def load_llm():
    api_key = None
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        
    if not api_key:
        st.error("🚨 Streamlit Cloud 설정의 'Secrets' 금고에 GEMINI_API_KEY가 등록되지 않았습니다! 관리자 화면에서 키를 주입해 주세요.")
        return None
        
    try:
        # 최신 모델 설정 및 연결 안정화
        return ChatGoogleGenerativeAI(model="gemini-3.8-flash", google_api_key=api_key)
    except Exception as init_err:
        st.error(f"🚨 모델 초기화 중 오류가 발생했습니다: {init_err}")
        return None

llm = load_llm()

# 💬 대화 기록 저장을 위한 Streamlit Session State 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 이전 대화 내용들을 화면에 다시 그려주기
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ⌨️ 사용자의 질문 입력창
if user_input := st.chat_input("맛집에 대해 물어보세요! (예: 영진전문대 정문 근처 가성비 맛집 추천해줘)"):
    
    # 1. 사용자 질문을 화면에 띄우고 저장
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 2. AI 답변 생성 (실시간 스트리밍 적용)
    with st.chat_message("assistant"):
        # 답변이 실시간으로 찍힐 빈 칸 생성
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # 💡 실시간으로 쪼개져 들어오는 글자 조각들을 결합하여 실시간 화면 갱신
            for chunk in llm.stream(user_input):
                if chunk.content:  # 빈 콘텐츠 방어 코드
                    full_response += chunk.content
                    message_placeholder.markdown(full_response + "▌")
            
            # 최종 완성본 출력
            message_placeholder.markdown(full_response)
            
            # 3. AI 답변을 대화 기록에 저장
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"⚠️ 답변을 생성하는 도중 오류가 발생했습니다: {e}")


