import streamlit as str
import pandas as pd
from g4f.client import Client

# 1. 웹페이지 기본 설정
str.set_page_config(page_title="영진전문대 맛집 에이전트", page_icon="🍚", layout="wide")

str.title("🤖 나만의 AI 맛집 에이전트 챗봇")
str.write("안녕하세요! 대구 복현동/영진전문대 맛집 전문 AI 비서입니다. 아무 말이나 편하게 걸어주세요!")

# 🔮 g4f 클라이언트를 캐싱하여 로드 (API 키 불필요)
@str.cache_resource
def load_llm():
    try:
        return Client()
    except Exception:
        return None

client = load_llm()

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
    
    if client is None:
        str.error("🚨 AI 클라이언트를 초기화하지 못했습니다. 패키지 설치 상태를 확인해 주세요.")
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
            # 🔄 g4f 문법에 맞게 invoke 대신 client.chat.completions.create 사용
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": routing_prompt}]
            )
            user_intent = response.choices[0].message.content.strip()
            
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
                
                tag_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": tag_prompt}]
                )
                ai_extracted_tag = tag_response.choices[0].message.content.strip()
                
                try:
                    df = pd.read_csv("restaurants.csv")
                    filtered_df = df[df['tags'].str.contains(ai_extracted_tag, na=False)].copy()
                    
                    if filtered_df.empty:
                        fail_prompt = f"너는 다정한 매니저야. '{ai_extracted_tag}'에 맞는 맛집이 없어. 정중히 양해를 구하는 멘트를 2문장 이내로 써줘."
                        fail_response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "user", "content": fail_prompt}]
                        )
                        ai_reply = fail_response.choices[0].message.content
                        str.chat_message("assistant").write(ai_reply)
                        str.session_state["chat_history"].append({"role": "assistant", "content": ai_reply})
                    else:
                        filtered_df['score'] = (filtered_df['rating'] * 10) + (filtered_df['review_count'] * 0.01)
                        final_result = filtered_df.sort_values(by='score', ascending=False).head(5)
                        
                        top_restaurant_name = final_result.iloc[0]['name']
                        
                        story_prompt = f"너는 다정한 맛집 매니저야. 과거 대화 맥락({history_text})과 현재 답변({user_input})을 조합해서, 왜 1등으로 뽑힌 '{top_restaurant_name}'이 어울리는지 2문장 이내로 설명해줘."
                        story_response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "user", "content": story_prompt}]
                        )
                        ai_serving_ment = story_response.choices[0].message.content
                        
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
                chat_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": chat_guide_prompt}]
                )
                ai_chat_response = chat_response.choices[0].message.content
                str.chat_message("assistant").write(ai_chat_response)
                str.session_state["chat_history"].append({"role": "assistant", "content": ai_chat_response})
        
        except Exception as api_err:
            str.error(f"🚨 AI 서비스 통신 에러 발생: {api_err}\n\n무료 서버 우회 공급망의 일시적인 혼잡일 수 있습니다. 잠시 후 다시 시도해 주세요.")

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

