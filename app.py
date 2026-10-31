import streamlit as st
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from openai import (
    AuthenticationError, PermissionDeniedError, RateLimitError,
    NotFoundError, APITimeoutError, APIConnectionError, APIStatusError,
)

load_dotenv()

from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.tools import tool

from exchange_api import get_currencies, get_exchange_rate

@tool
def exchange_rate_tool(
    base_currency: str,
    target_currency: str,
    amount: float = 1.0,
    date: str = "latest",
) -> dict:
    """Frankfurter에서 환율과 환산 금액을 조회합니다.

    base_currency와 target_currency는 USD, KRW, JPY 같은 영문 통화 코드입니다.
    amount는 환산할 금액이며, date는 최신 조회 시 latest, 과거 조회 시 YYYY-MM-DD입니다.
    """
    try:
        return get_exchange_rate(base_currency, target_currency, amount, date)
    except ValueError as error:
        return {"error": str(error)}


@tool
def currency_list_tool() -> dict:
    """Frankfurter가 지원하는 통화 코드와 이름을 조회합니다."""
    try:
        return get_currencies()
    except ValueError as error:
        return {"error": str(error)}


st.set_page_config(
    page_title="모아 · 환율을 묻다",
    page_icon="💱",
    layout="centered",
    initial_sidebar_state="collapsed",
)
st.html(f"<style>{Path(__file__).with_name('styles.css').read_text(encoding='utf-8')}</style>")

if "messages" not in st.session_state:
    st.session_state.messages = []

api_key = os.getenv("OPENAI_API_KEY", "").strip()
today_kst = datetime.now(ZoneInfo("Asia/Seoul"))

brand, reset = st.columns([5, 1.2], vertical_alignment="center")
with brand:
    st.html('''<div class="brand"><span class="brand-icon" aria-hidden="true">↗</span>
        <span>모아<span class="brand-divider">/</span><span class="brand-description">환율을 묻다</span></span></div>''')
with reset:
    if st.button("＋ 새 대화", use_container_width=True, disabled=not st.session_state.messages):
        st.session_state.messages = []
        st.rerun()

st.html(f'''<section class="hero">
    <div class="hero-copy">
        <div class="eyebrow"><span class="status-dot"></span> YOUR EVERYDAY CURRENCY COMPANION</div>
        <h1>다른 나라 돈도,<br><span>우리 말로 가볍게.</span></h1>
        <p>여행 전에도, 해외 직구할 때도.<br>궁금한 환율을 물어보면 모아가 확인해 드려요.</p>
        <div class="hero-date">{today_kst:%Y.%m.%d} <span>· 한국 기준</span></div>
    </div>
    <div class="currency-art" aria-hidden="true">
        <div class="art-orbit"></div>
        <div class="currency-tile tile-dollar"><span class="tile-code">USD</span><strong>$</strong><span>미국 달러</span></div>
        <div class="exchange-symbol">⇄</div>
        <div class="currency-tile tile-won"><span class="tile-code">KRW</span><strong>₩</strong><span>대한민국 원</span></div>
        <div class="art-note">환율부터 환산까지, 한 번에.</div>
    </div>
</section>
<div class="feature-strip">
    <span><b>01</b> 말하듯 편하게</span><span><b>02</b> 과거 환율도 확인</span><span><b>03</b> 데이터 기준일 안내</span>
</div>''')

if not api_key:
    st.info("대화를 시작하려면 API 연결이 필요해요. 아래 연결 안내를 확인해 주세요.", icon="🔑")
    with st.expander("API 연결 안내"):
        st.markdown("프로젝트의 `.env` 파일에 `OPENAI_API_KEY`를 설정한 뒤 앱을 다시 실행해 주세요. 키는 화면에 표시되지 않습니다.")

prompt = None
if not st.session_state.messages:
    st.html('''<div class="section-heading"><h2>어떤 환율이 궁금하세요?</h2><span>질문을 골라 시작해 보세요 ↘</span></div>''')
    suggestions = [
        ("💵", "달러 환산", "100달러는 원화로 얼마야?"),
        ("🧳", "여행 준비", "일본 여행 갈 때 3만 엔은 원화로 얼마야?"),
        ("🗓️", "지난 환율", "2025년 1월 2일의 100유로는 원화로 얼마야?"),
    ]
    for column, (emoji, title, question) in zip(st.columns(3), suggestions):
        with column:
            with st.container(border=True, key=f"suggestion_{title}"):
                st.markdown(f"<div class='suggestion-icon'>{emoji}</div><h3>{title}</h3>", unsafe_allow_html=True)
                st.caption(question)
                if st.button("이 질문으로 시작 ↗", key=f"ask_{title}", disabled=not api_key, use_container_width=True):
                    prompt = question
else:
    st.html('<div class="section-heading"><h2>모아와 나눈 대화</h2><span>이어서 편하게 물어보세요</span></div>')

st.html('''<div class="data-note"><span aria-hidden="true">ⓘ</span> Frankfurter 일별 환율 기준 · 은행의 실제 환전 금액은 수수료에 따라 달라질 수 있어요.</div>''')


def render_message(message):
    is_assistant = message["role"] == "assistant"
    with st.chat_message(message["role"], avatar="✳️" if is_assistant else "👤"):
        st.caption("모아" if is_assistant else "나")
        if message.get("is_error"):
            st.error(message["content"], icon="⚠️")
        else:
            st.markdown(message["content"])


for message in st.session_state.messages:
    render_message(message)

typed_prompt = st.chat_input("예: 100달러는 원화로 얼마야?", disabled=not api_key)
prompt = typed_prompt or prompt
if prompt:
    render_message({"role": "user", "content": prompt})
    is_error = True
    with st.chat_message("assistant", avatar="✳️"):
        st.caption("모아")
        reply_placeholder = st.empty()
    try:
        # 기존 파일과 같은 모델 초기화 → 도구 연결 → agent.invoke 순서입니다.
        model = init_chat_model(
            os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
            model_provider="openai",
            api_key=api_key,
            timeout=45,
            max_retries=1,
        )
        today = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
        agent = create_agent(
            model,
            tools=[exchange_rate_tool, currency_list_tool],
            system_prompt=(
                f"당신은 한국어로 답변하는 환율 조회 도우미입니다. 오늘은 한국 기준 {today}입니다. "
                "환율과 환산 금액은 반드시 이번 질문에서 exchange_rate_tool을 호출해 확인하세요. "
                "이전 대화의 숫자나 기억으로 환율을 추측하지 마세요. 날짜 미지정 시 latest를 사용하세요. "
                "달러는 USD, 원화는 KRW, 엔화는 JPY, 유로는 EUR로 해석하세요. "
                "기준 또는 대상 통화가 빠지면 이전 대화를 참고하되 불명확하면 질문하세요. "
                "조회 결과의 기준 통화, 대상 통화, 1단위 환율, 환산 금액, 실제 데이터 기준일을 표시하세요. "
                "동일 통화 결과의 date가 null이면 환산 비율 1이며 조회가 불필요하다고 설명하세요. "
                "과거 조회에서 요청 날짜와 반환 날짜가 다르면 두 날짜를 모두 안내하세요. "
                "오류 결과는 원인을 안내하고, 성공한 환율처럼 답변하지 마세요. "
                "실시간 시세라고 표현하지 말고 은행의 실제 환전 금액은 수수료 등으로 다를 수 있다고 안내하세요. "
                "환율 관련 요청에 집중하고, 답변 끝에 출처 https://frankfurter.dev/ 를 표시하세요."
            ),
        )
        with reply_placeholder.container(), st.spinner("환율과 데이터 기준일을 확인하고 있어요..."):
            response = agent.invoke(
                {"messages": [
                    {"role": message["role"], "content": message["content"]}
                    for message in st.session_state.messages
                ] + [{"role": "user", "content": prompt}]},
                config={"recursion_limit": 12},
            )
        answer = response["messages"][-1].content
        if isinstance(answer, list):
            answer = "\n".join(block.get("text", "") for block in answer if isinstance(block, dict))
        if not answer:
            raise ValueError("답변이 비어 있습니다.")
        is_error = False
    except AuthenticationError:
        answer = "OpenAI 인증에 실패했습니다. .env의 OPENAI_API_KEY 값이 올바른지 확인해 주세요. (401)"
    except PermissionDeniedError:
        answer = "현재 OpenAI 프로젝트에서 이 모델을 사용할 권한이 없습니다. (403)"
    except NotFoundError:
        answer = "설정된 모델을 찾을 수 없습니다. .env의 OPENAI_MODEL과 모델 이용 권한을 확인해 주세요. (404)"
    except RateLimitError as error:
        if error.code == "insufficient_quota":
            answer = "OpenAI API 잔액 또는 사용 한도가 부족합니다. API 결제 및 프로젝트 사용 한도를 확인해 주세요. (429)"
        else:
            answer = "OpenAI 요청 한도를 초과했습니다. 잠시 후 다시 질문해 주세요. (429)"
    except APITimeoutError:
        answer = "OpenAI 응답 시간이 초과됐습니다. 잠시 후 다시 질문해 주세요."
    except APIConnectionError:
        answer = "OpenAI 서버에 연결하지 못했습니다. 인터넷 연결을 확인해 주세요."
    except APIStatusError as error:
        answer = f"OpenAI 서버 요청에 실패했습니다. HTTP 상태 코드: {error.status_code}"
    except Exception as error:
        # 비밀 값이 포함될 수 있는 오류 원문 대신 오류 종류만 표시합니다.
        answer = f"답변 처리 중 오류가 발생했습니다. 오류 종류: {type(error).__name__}"

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append({"role": "assistant", "content": answer, "is_error": is_error})
    st.rerun()
