import streamlit as st
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI 

# 1. 웹페이지 기본 설정
st.set_page_config(page_title="영진전문대 맛집 에이전트", page_icon="🍚", layout="wide")

st.title("🤖 나만의 AI 맛집 에이전트 챗봇")
st.write("안녕하세요! 대구 복현동/영진전문대 맛집 전문 AI 비서입니다. 준비된 맛집 데이터를 기반으로 추천해 드립니다!")

# 📂 [Pandas 연동] 준비하신 restaurant.csv 파일 읽어오기
# 파일이 없어도 에러가 나지 않도록 try-except로 안전하게 감쌌습니다.
try:
    df = pd.read_csv("restaurants.csv")
    # 챗봇이 참고할 수 있도록 데이터프레임의 내용을 텍스트(문자열)로 변환해 둡니다.
    restaurant_info = df.to_string(index=False)
except Exception as e:
    df = None
    restaurant_info = "현재 등록된 맛집 CSV 데이터를 불러올 수 없습니다."

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
if user_input := st.chat_input("맛집에 대해 물어보세요! (예: 정문 근처 가성비 좋은 식당 추천해줘)"):
    
    # 1. 사용자 질문을 화면에 띄우고 저장
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 2. AI에게 넘겨줄 질문 구성 (우리가 불러온 CSV 맛집 데이터를 주입합니다)
    # AI가 외부 지식이 아니라, 사용자가 만든 csv 정보를 바탕으로 답변하게 만드는 프롬프트 기법입니다.
    system_prompt = f"""
    너는 대구 복현동 영진전문대학교 맛집 추천 전문 AI 비서야.
    아래에 제공되는 우리의 공식 맛집 데이터 파일(CSV 내용)을 반드시 참고해서 사용자의 질문에 친절하게 답변해줘.
    만약 데이터에 없는 식당을 물어보면 제공된 데이터 내에서 최대한 비슷한 곳을 추천해주거나 정중히 모른다고 해줘.

    [우리 대학교 맛집 데이터 리스트]
    {restaurant_info}
    
    사용자 질문: {user_input}
    """
    
    # 3. AI 답변 생성 (실시간 스트리밍 적용 및 리스트 결합 오류 수정)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # 주입된 데이터를 포함한 system_prompt를 모델에 던집니다.
            for chunk in llm.stream(system_prompt):
                # 💡 핵심 수정: chunk.content가 리스트이거나 비어있을 때를 대비해 확실하게 str 타입만 걸러서 더합니다.
                if chunk.content and isinstance(chunk.content, str):
                    full_response += chunk.content
                    message_placeholder.markdown(full_response + "▌")
            
            # 최종 완성본 출력
            message_placeholder.markdown(full_response)
            
            # 4. AI 답변을 대화 기록에 저장
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"⚠️ 답변을 생성하는 도중 오류가 발생했습니다: {e}")


