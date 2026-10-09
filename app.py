import streamlit as str
import pandas as pd
# 🔮 Ollama 대신 Google Gemini 도구로 변경
from langchain_google_genai import ChatGoogleGenerativeAI 

# 1. 웹페이지 기본 설정
str.set_page_config(page_title="영진전문대 맛집 에이전트", page_icon="🍚", layout="wide")

str.title("🤖 나만의 AI 맛집 에이전트 챗봇")
str.write("안녕하세요! 대구 복현동/영진전문대 맛집 전문 AI 비서입니다. 아무 말이나 편하게 걸어주세요!")

# 🔮 내 컴퓨터의 Ollama 대신, 인터넷 주소로 작동하는 Google Gemini 연결
@str.cache_resource
def load_llm():
    try:
        # 스트림릿 서버에 숨겨놓은 안전한 비밀키(Secrets)를 자동으로 가져옵니다.
        api_key = str.secrets["GEMINI_API_KEY"]
        # 가장 빠르고 가성비 좋은 구글의 gemini-1.5-flash 모델을 장착합니다.
        return ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
    except Exception as e:
        # 내 컴퓨터에서 로컬로 테스트할 때는 .env나 시스템 환경변수의 키를 찾습니다.
        try:
            return ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        except:
            return None

llm = load_llm()

# 비로그인 유저의 과거 대화 기록을 기억하는 메모리 장치 세팅
if "chat_history" not in str.session_state:
    str.session_state["chat_history"] = []

# 📱 웹 화면에 과거에 나눴던 대화 목록들을 차례대로 그려두기
for chat in str.session_state["chat_history"]:
    str.chat_message(chat["role"]).write(chat["content"])
    if "results" in chat:
        for index, row in chat["results"].iterrows():
            with str.expander(f"👑 {row['name']} ({row['category']}) - 점수: {row['score']:.1f}점"):
                str.write(f"⭐️ **대중 평점:** {row['rating']}점 / 💬 **리뷰 수:** {row['review_count']}개")
                str.write(f"🏷️ **이 식당의 특징:** {row['tags']}")
                if pd.notna(row['image_url']):
                    str.image(row['image_url'], caption=f"{row['name']} 전경/음식 이미지", width=350)

# 2. 대화 입력창 만들기
user_input = str.chat_input("예: 오늘 동기들이랑 회식하기 좋은 삼겹살집 추천해줘!")

if user_input:
    str.chat_message("user").write(user_input)
    str.session_state["chat_history"].append({"role": "user", "content": user_input})
    
    if llm is None:
        str.error("🚨 구글 AI API 키 설정이 올바르지 않거나 켜지지 않았습니다! secrets 설정을 확인해 주세요.")
    else:
        history_text = "\n".join([f"{c['role']}: {c['content']}" for c in str.session_state["chat_history"][:-1]])
        
        routing_prompt = f"""
        너는 사용자의 현재 의도를 분류하는 판단관이야. 과거 대화 내용의 맥락을 고려해서 현재 질문을 분석해야 해.
        사용자가 대형 맛집 리스트 추천을 원하는 상황이거나, 과거에 맛집을 찾던 대화의 연장선상이라면 '추천'을 출력해줘.
        만약 단순한 인사나 맛집과 상관없는 진짜 일상 대화라면 '잡담'을 출력해줘.
        설명 없이 오직 '추천' 또는 '잡담' 둘 중 하나의 단어만 출력해.

        [과거 대화 기록]:
        {history_text}
        
        [현재 사용자 질문]: {user_input}
        [분류 결과]:"""
        
        # 🔮 랭체인 Chat 모델의 출력 형식을 문자열로 정제 (.content 추가)
        user_intent = llm.invoke(routing_prompt).content.strip()
        
        # 🎯 시나리오 A: 맛집 추천 실행
        if "추천" in user_intent:
            tag_prompt = f"""
            너는 사용자의 질문과 과거 대화 맥락을 분석해서 맛집 검색용 키워드 태그를 딱 하나만 뽑아내는 천재 에이전트야.
            유저의 이전 대화와 현재 답변을 종합해서 아래 목록 중 하나만 골라야 해.
            설명 없이 오직 단어 '한 개'만 출력해.

            [선택 가능한 엑셀 태그 목록]: 상견례, 데이트, 회식, 카페, 혼밥, 가족식사, 가성비
            [과거 대화 기록]:
            {history_text}
            
            [현재 사용자 질문]: {user_input}
            [AI 에이전트의 선택 단어]:"""
            
            ai_extracted_tag = llm.invoke(tag_prompt).content.strip()
            
            try:
                df = pd.read_csv("restaurants.csv")
                filtered_df = df[df['tags'].str.contains(ai_extracted_tag, na=False)].copy()
                
                if filtered_df.empty:
                    fail_prompt = f"너는 다정한 매니저야. '{ai_extracted_tag}'에 맞는 맛집이 없어. 정중히 양해를 구하는 멘트를 2문장 이내로 써줘."
                    ai_reply = llm.invoke(fail_prompt).content
                    str.chat_message("assistant").write(ai_reply)
                    str.session_state["chat_history"].append({"role": "assistant", "content": ai_reply})
                else:
                    filtered_df['score'] = (filtered_df['rating'] * 10) + (filtered_df['review_count'] * 0.01)
                    final_result = filtered_df.sort_values(by='score', ascending=False).head(5)
                    
                    top_restaurant_name = final_result.iloc[0]['name']
                    
                    story_prompt = f"너는 다정한 맛집 매니저야. 과거 대화 맥락({history_text})과 현재 답변({user_input})을 조합해서, 왜 1등으로 뽑힌 '{top_restaurant_name}'이 어울리는지 2문장 이내로 설명해줘."
                    ai_serving_ment = llm.invoke(story_prompt).content
                    
                    str.chat_message("assistant").write(f"🧠 **AI 에이전트 연속 문맥 분석:** 과거 대화를 바탕으로 '[{ai_extracted_tag}]' 상황에 어울리는 최적의 맛집 랭킹을 가져왔습니다.")
                    str.chat_message("assistant").write(ai_serving_ment)
                    
                    for index, row in final_result.iterrows():
                        with str.expander(f"👑 {row['name']} ({row['category']}) - 점수: {row['score']:.1f}점"):
                            str.write(f"⭐️ **대중 평점:** {row['rating']}점 / 💬 **리뷰 수:** {row['review_count']}개")
                            str.write(f"🏷️ **이 식당의 특징:** {row['tags']}")
                            if pd.notna(row['image_url']):
                                str.image(row['image_url'], caption=f"{row['name']} 전경/음식 이미지", width=350)
                                
                    str.session_state["chat_history"].append({
                        "role": "assistant", 
                        "content": f"🧠 AI 분석 완료: [{ai_extracted_tag}] 상황 추천\n" + ai_serving_ment,
                        "results": final_result
                    })
            except FileNotFoundError:
                str.error("restaurants.csv 파일이 없습니다.")
                
        # 🎯 시나리오 B: 일상 대화 및 유도
        else:
            chat_guide_prompt = f"""
            너는 대구 복현동/영진전문대 맛집 웹의 AI 마스코트야. 이전 대화 기록을 참고해서 유저의 말에 대답해야 해.
            [과거 기록]: {history_text}
            [현재 유저의 말]: "{user_input}"
            
            대화를 친절하게 받아주면서, 자연스럽게 복현동 맛집 추천(데이트, 회식, 혼밥 등)으로 유도하는 대답을 3문장 이내로 해줘.
            """
            ai_chat_response = llm.invoke(chat_guide_prompt).content
            str.chat_message("assistant").write(ai_chat_response)
            str.session_state["chat_history"].append({"role": "assistant", "content": ai_chat_response})

# 3. 🐱 우측 하단 가쪽에 고화질 냥캣 캐릭터 이미지 고정
character_image_url = "https://tse4.mm.bing.net/th/id/OIP.95620q0SRD92J15XFWne5QHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3" 
str.markdown(
    f"""
    <style>
    .floating-character {{
        position: fixed; 
        bottom: 20px; 
        right: 20px; 
        z-index: 999; 
        width: 220px; 
        height: auto; 
        mix-blend-mode: multiply; 
        border: none; 
    }}
    </style>
    <img src="{character_image_url}" class="floating-character">
    """, 
    unsafe_allow_html=True
)
