import streamlit as str
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI 

# 1. 웹페이지 기본 설정
str.set_page_config(page_title="영진전문대 맛집 에이전트", page_icon="🍚", layout="wide")

str.title("🤖 나만의 AI 맛집 에이전트 챗봇")
str.write("안녕하세요! 대구 복현동/영진전문대 맛집 전문 AI 비서입니다. 아무 말이나 편하게 걸어주세요!")

# 안전한 LLM 로드 세팅
if "llm" not in str.session_state:
    try:
        api_key = str.secrets.get("GEMINI_API_KEY", None)
        if api_key:
            str.session_state["llm"] = ChatGoogleGenerativeAI(
                model="gemini-3.8-flash", 
                google_api_key=api_key,
                timeout=15.0
            )
        else:
            str.session_state["llm"] = ChatGoogleGenerativeAI(model="gemini-3.8-flash", timeout=15.0)
    except Exception as e:
        str.session_state["llm"] = None

llm = str.session_state["llm"]

# 과거 대화 기록 저장을 위한 세션 메모리 설정
if "chat_history" not in str.session_state:
    str.session_state["chat_history"] = []

# 📱 웹 화면에 과거 대화 렌더링
for chat in str.session_state["chat_history"]:
    str.chat_message(chat["role"]).write(chat["content"])
    if "results" in chat:
        for index, row in chat["results"].iterrows():
            with str.expander(f"👑 {row['name']} ({row['category']}) - 점수: {row['score']:.1f}점"):
                str.write(f"⭐️ **대중 평점:** {row['rating']}점 / 💬 **리뷰 수:** {row['review_count']}개")
                str.write(f"🏷️ **이 식당의 특징:** {row['tags']}")
                if pd.notna(row['image_url']):
                    str.image(row['image_url'], caption=f"{row['name']} 전경/음식 이미지", width=350)

# 2. 대화 입력창 생성
user_input = str.chat_input("예: 오늘 동기들이랑 회식하기 좋은 삼겹살집 추천해줘!")

if user_input:
    str.chat_message("user").write(user_input)
    str.session_state["chat_history"].append({"role": "user", "content": user_input})
    
    if llm is None:
        str.error("🚨 구글 AI API 키 설정이 올바르지 않습니다! Streamlit Cloud의 Secrets 설정을 확인해 주세요.")
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
        
        # 🛠️ 수정한 예외 처리: 내장 함수 str()을 쓰지 않고 포맷팅하여 AttributeError 근절
        try:
            with str.spinner("사용자 의도 분석 중..."):
                user_intent = llm.invoke(routing_prompt).content.strip()
        except Exception as api_err:
            str.error(f"🚨 Google Gemini API 통신 실패: API 키가 누락되었거나 비정상적입니다. 에러 종류: {api_err}")
            user_intent = "잡담" 
        
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
            
            try:
                with str.spinner("추천 카테고리 분석 중..."):
                    ai_extracted_tag = llm.invoke(tag_prompt).content.strip()
            except Exception:
                ai_extracted_tag = "가성비" 
            
            try:
                df = pd.read_csv("restaurants.csv")
                filtered_df = df[df['tags'].str.contains(ai_extracted_tag, na=False)].copy()
                
                if filtered_df.empty:
                    str.chat_message("assistant").write(f"죄송합니다. 현재 복현동 주변에 '{ai_extracted_tag}'에 딱 맞는 추천 맛집 데이터를 찾지 못했습니다.")
                else:
                    filtered_df['score'] = (filtered_df['rating'] * 10) + (filtered_df['review_count'] * 0.01)
                    final_result = filtered_df.sort_values(by='score', ascending=False).head(5)
                    
                    # 🛠️ 판다스 인덱싱 에러 완벽 해결: .iloc[0]을 명시하여 첫 번째 행의 'name' 컬럼값 안전 추출
                    top_restaurant_name = final_result.iloc[0]['name']
                    
                    story_prompt = f"너는 다정한 맛집 매니저야. 과거 대화 맥락({history_text})과 현재 답변({user_input})을 조합해서, 왜 1등으로 뽑힌 '{top_restaurant_name}'이 어울리는지 2문장 이내로 설명해줘."
                    
                    try:
                        with str.spinner("맞춤형 설명 문장 작성 중..."):
                            ai_serving_ment = llm.invoke(story_prompt).content
                    except Exception:
                        ai_serving_ment = f"점수 기준으로 1등인 {top_restaurant_name}을(를) 추천해 드립니다!"
                    
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
            try:
                with str.spinner("답변 생각 중..."):
                    ai_chat_response = llm.invoke(chat_guide_prompt).content
            except Exception:
                ai_chat_response = "안녕하세요! 대구 복현동 맛집 에이전트입니다. 삼겹살, 회식, 혼밥 등 원하시는 맛집 스타일을 말씀해주시면 딱 맞게 골라드릴게요!"
                
            str.chat_message("assistant").write(ai_chat_response)
            str.session_state["chat_history"].append({"role": "assistant", "content": ai_chat_response})

# 3. 우측 하단 고정 UI 캐릭터 디자인
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

