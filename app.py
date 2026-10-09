import streamlit as str
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI 

# 1. 웹페이지 기본 설정
str.set_page_config(page_title="영진전문대 맛집 에이전트", page_icon="🍚", layout="wide")

str.title("🤖 나만의 AI 맛집 에이전트 챗봇")
str.write("안녕하세요! 대구 복현동/영진전문대 맛집 전문 AI 비서입니다. 아무 말이나 편하게 걸어주세요!")

# 🔮 [버그 해결] 구글 API 로드 로직 최적화 및 방어 코드 구축
@str.cache_resource
def load_llm():
    # 1. Streamlit Secrets (금고) 또는 시스템 환경 변수에서 키 확인
    api_key = None
    if "GEMINI_API_KEY" in str.secrets:
        api_key = str.secrets["GEMINI_API_KEY"]
        
    # 2. API 키가 금고에 아예 안 들어있는 경우 가이드 에러 출력
    if not api_key:
        str.error("🚨 Streamlit Cloud 설정의 'Secrets' 금고에 GEMINI_API_KEY가 등록되지 않았습니다! 관리자 화면에서 키를 주입해 주세요.")
        return None
        
    # 3. 키가 있다면 안전하게 모델 생성
    try:
        # ⚠️ 중요: 단종된 2.5 대신 최신 지원 모델인 gemini-3.8-flash로 수정완료
        return ChatGoogleGenerativeAI(model="gemini-3.8-flash", google_api_key=api_key)
    except Exception as init_err:
        str.error(f"🚨 모델 초기화 중 오류가 발생했습니다: {init_err}")
        return None

# LLM 모델 로드
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
        str.error("🚨 구글 AI API 키 연동 실패로 인해 답변을 생성할 수 없습니다. 대시보드의 Secrets 설정을 다시 점검해 주세요.")
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
        
        try:
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
                        
                        # 🛠️ [iloc 버그 방지 고도화] 판다스 시리즈의 요소 접근법을 .iloc[0]['name'] 대신 가장 안정적인 대괄호 직렬 접근으로 유지 [1]
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
        
        except Exception as api_err:
            str.error(f"🚨 구글 API 통신 에러 발생: {api_err}\n\n배포 서버가 구글 서버와 통신하는 과정에서 거절되었습니다. API 키 자체에 오타가 있거나 무료 계정 한도를 일시 초과했을 수 있습니다.")

# 3. 🐱 우측 하단 가쪽에 고화질 냥캣 캐릭터 이미지 고정
character_image_url = "https://bing.net" 
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

