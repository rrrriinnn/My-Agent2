# My-Agent2 - 환율 조회 챗봇

## 실행 방법 (PowerShell)

이 폴더에서 터미널을 열고 실행합니다.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

이미 설치된 원본 프로젝트의 가상환경으로 실행할 수도 있습니다.

```powershell
& "C:\Users\Administrator\Desktop\my-agent\.venv\Scripts\python.exe" -m streamlit run "C:\Users\Administrator\Desktop\frankfurter-chatbot\app.py"
```

브라우저에서 `http://localhost:8501`을 엽니다. 다른 Streamlit 앱이 실행 중이면 터미널에 표시된 주소를 사용하세요.

챗봇 사용 전 `.env`의 `OPENAI_API_KEY`에 본인의 키가 있는지 확인하세요.
`OPENAI_MODEL` 기본값은 원본 코드와 같은 `gpt-5.4-mini`입니다.
Frankfurter에는 별도 키가 필요 없으며 `TAVILY_API_KEY`도 필요 없습니다.
`.env`는 공유하거나 Git에 올리지 마세요.

## 질문 예시

- "100달러는 원화로 얼마야?"
- "그럼 200달러는?"
- "10000엔은 원화로 얼마야?"

## 데이터

[Frankfurter 공식 문서](https://frankfurter.dev/)의 v2 API를 사용합니다.

- 통화 목록: `GET https://api.frankfurter.dev/v2/currencies`
- 환율 조회: `GET https://api.frankfurter.dev/v2/rate/USD/KRW`
- 과거 조회: 같은 URL에 `?date=2025-01-02` 추가

환율은 일별 데이터이며 화면과 답변에 실제 데이터 기준일을 표시합니다.
요청일과 API 반환일이 다르면 두 날짜를 모두 안내합니다.