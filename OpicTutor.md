# OpicTutor

[참고](https://app.notion.com/p/41084879d81e800ebc08eedd33244ac6?pvs=21)

# OpicTutor — 원하는 기능과 기술 스택

> 프로젝트 구조를 설계하기 전에 생각을 정리하는 문서입니다.
정해진 내용만 적고, 고민 중인 항목은 `미정`으로 남겨 두세요.
표 대신 각 항목 아래에 자유롭게 적어도 됩니다.
> 

## 1. 만들고 싶은 서비스

- **한 줄 소개:** : Opic 시험을 준비하는 수험생을 위해 AI를 활용해서 자신의 수준을 파악하고 AI와 피드백을 진행하면서 최종적으로 수험생이 원하는 오픽 점수를 받을 수 있도록 도와주는 교육 플랫폼
- **이 서비스를 만들려는 이유:** : Opic시험이 말하기 시험으로 나오기 때문에 나올 수 있는 평가 방식의 애매모호함과 자신의 대답에 대한 객관적인 피드백을 언제 어디서나 할 수 없다는 점을 해결하기 위함
- **주로 사용할 사람:** Opic 시험과 토스 영어 시험등을 준비하려는 수험생
- **사용자가 해결하고 싶은 문제:** : 자신의 답변이 어느정도 수준인지 AI를 통해 진단하고 자신의 답변을 Elevate할 수 있도록 만들어 수험생이 원하는 점수를 얻을 수 있도록 도움
- **가장 중요하게 생각하는 경험:** : AI를 활용해 자신의 답변의 객관적인 수준과 이를 해결할 수 있도록 Chat interaction을 통한 피드백 과정을 진행

## 2. 사용 환경

- **제공 형태:** <!-- 웹 / 모바일 웹 / 모바일 앱 / 데스크톱 앱 등 --> : 웹
- **주로 사용할 기기:** : 노트북, 컴퓨터등 데스크탑 환경
- **사용 규모:** <!-- 나 혼자 / 지인 몇 명 / 일반 사용자에게 공개 등 --> : 일반 사용자에게 공개(MVP 수준)
- **로그인 필요 여부:** : YES
- **지원할 언어:** : Ko

## 3. 원하는 기능

우선순위는 `필수`, `있으면 좋음`, `나중에`로 구분해 주세요.
기능 설명에는 사용자가 무엇을 입력하거나 누르고, 어떤 결과를 받는지 적으면 좋습니다.

| 기능 | 사용자가 하는 일과 기대하는 결과 | 우선순위 | 비고 또는 고민 |
| --- | --- | --- | --- |
| 자신의 답변 평가 | 사용자가 문제에 대한 답변을 stt로 변환하면 그 답변을 범주화 해서 AH부터 IM까지로 변환한다. | 높음 | 정확한 평가 기준은 online에 있지 않기 때문에 RAG를 활용해서 [https://www.opic.co.kr/senior/img/com_2/ACTFL_Proficiency_Guidelines_2024.pdf](https://www.opic.co.kr/senior/img/com_2/ACTFL_Proficiency_Guidelines_2024.pdf)
여기에 있는 기준을 parsing해서 vector DB에 저장해야 함 |
| 가상 진행자 | *OPIc에서 '대화 상대'로 나오는 캐릭터 Eva와 같이 opic test를 진행할 수 있는 캐릭터* | 중간 | TTS 서비스를 고민해야 할수도 있음.  azure tts 가 생각보다 영어목소리가 괜찮았었음 사전 조사에서
나중에 확장으로 AI 온도를 적용해서 말투를 부드럽게에서, 띠껍게 까지 조정 가능 |
| AI 멘토링 | 가상 진행자와 대화한 기록을 저장하고 이를 AI를 통해 멘토링을 진행, 자신의 답변의 문제점을 파악하고 조금 더 발전할 수 있는 방향을 모색한다. | 높음 | 어떤 AI 모델을 사용할지, 대화 내용 전체를 embedding 해야 할지 모르겠음. |
| 회원 정보 관리 | 자신의 답변 내용을 저장하고 피드백 과정을 요약해서 한장의 md 파일로 저장 | 낮음 | 솔찍히 필요 없음. MVP에서는 그냥 UI공간과 계발중으로 표시 |
| 가상 진행자 애니메이션 | tts의 소리를 기반으로 실제로 가상 진행자가 목소리를 내는거 처럼 만들어야 함 | 보통 | TTS에 텍스트 전달

"안녕하세요! 반갑습니다!"

음성 생성 및 재생

Web Speech API / ElevenLabs / Azure TTS

Web Audio API로 음량 분석

소리가 커지면 큰 움직임, 작아지면 작은 움직임

캐릭터 애니메이션

위아래로 통통 + 좌우 회전 |
|  |  |  |  |

### 자세히 설명하고 싶은 기능

아래 틀을 복사해서 필요한 만큼 추가해 주세요.

#### 기능명: 수험생 답변 범주화(수험생 답변 평가)

- **이 기능이 필요한 이유: 이 서비스의 알파이자 오메가 수험생에게 예제 문제를 제공하고 수험생의 답변을 기반으로 최대한 객관적인 평가 기준 기반으로**
- **사용자가 입력하거나 선택하는 것: 사용자는 자신의 답변을 목소리를 통해 전송**
- **동작 방식: 음성 파일 → stt → db(should save both problem and user’s answer) → success call → user sees that server successfully recived user’s respond → server generate(fetching) new problem → server give user new Problem → repeat again until user answer every exams problem(not every problem, every exam problem (around 9 to 12))**
- **화면에 보여 줄 결과: 서버에서 새로운 문제를 제공**
- **저장할 내용: problem + stt processed text**
- **예외 상황에서 원하는 동작:** <!-- 입력이 없거나, 요청이 실패하는 경우 등 --> make user to say again (pardon me? // excuse me?)
- **참고 서비스 또는 링크:**

#### 기능명:

- **이 기능이 필요한 이유: 가상 진행자가 오픽 테스트를 진행, 가상 진행자가 사용자에게 피드백을 제공**
- **사용자가 입력하거나 선택하는 것:    부가기능: 진행자의 온도(말투, 태도)를 선택하여 진행**
- **동작 방식: 1.OPIC 테스트를 진행 2. 테스트 결과(앞서 설명한 기능)를 바탕으로 피드백을 진행**
- **화면에 보여 줄 결과: 실제 OPIC 시험의 EVA처럼 동작**
- **저장할 내용: 캐릭터 DATA(html,css, js file),**
- **예외 상황에서 원하는 동작:** <!-- 입력이 없거나, 요청이 실패하는 경우 등 --> if No input then Default Pose, Request user input after a set time limit expires  | if Request Failed then Please try again
- **참고 서비스 또는 링크:**

#### 기능명: AI 멘토링

- **이 기능이 필요한 이유: 수험생이 자신의 답변을 AI를 통해 피드백 하는 매우 중요한 과정**
- **사용자가 입력하거나 선택하는 것: None (서버가 user의 문제와 답변을 알아서 fetching 해야함)**
- **동작 방식: server fetches every user’s problem and responds after the exam finishes → AI generates 2 things FIRST AND FOREMOST: THE EXPECTED GRADE. IT SHOULD ALWAYS PRODUCE CURRENT USER’S EXPACTED OPIC GRADE BASED ON THEIR RESPONDS and the card that contains every mistake and stuffs that can elevate user’s grade dramatically → then display grade and feedback card to User → User should be able to interact with AI Agent(It it not necessary to make in MVP)**
- **화면에 보여 줄 결과: the Colored Grade that motivates user(silver, gold, plat, diamonds) and news Card that feedback responds**
- **저장할 내용: 만약 로그인을 구현한다면 이걸 만들어야 겠지 근데 글쎄 시간 보고**
- **예외 상황에서 원하는 동작:** <!-- 입력이 없거나, 요청이 실패하는 경우 등 --> IT SHOULD NOT FAIL
- **참고 서비스 또는 링크:**

## 4. 대표적인 사용 흐름

사용자가 서비스를 켠 뒤 목적을 달성할 때까지의 흐름을 적어 주세요.

1. 웹사이트 설명 및 서비스 사용 시작 버튼
2. 모의 시험 설정(선택 과제를 설정하고 마이크 테스트)
3. TTS 질문 
4. 마이크 버튼을 클릭해 자신의 답변을 녹음 한 이후 다시 마이크 버튼을 클릭해 녹음을 서버에 전송
5. 서버는 이를 STT를 사용해 DB에 저장 및 다음 질문을 제공
6. 시험 종료 후 DB에 저장했었던 질문과 답변을 그대로 AI에게 전달
7. AI에게서 받아야 하는 정보는 2가지, 1: 위 답변토대로 ACTFL을 근거한 사용자의 수준을 판정, 2. 사용자가 어떤 실수르 했었는지 및 위 질문을 어떤 식으로 답변해야 사용자의 수준이 높아 보일 수 있는지 멘토링
8. 이후 AI 체팅을 통해 위 내용을 가지고 내가 어떤 식으로 해야 할지 공부 방향을 제공

## 5. 사용할 기술 스택

사용하고 싶은 기술이 있는 항목만 작성해 주세요.
아직 선택하지 못했다면 `추천 필요`, 서비스에 필요 없다면 `사용 안 함`으로 적어 주세요.

| 영역 | 사용할 기술 또는 서비스 | 선택 이유 / 원하는 조건 | 확정 여부 |
| --- | --- | --- | --- |
| 개발 언어 | python, JS | rag, AI서비스, fastapi등 MVP를 build하기에 너무 좋은 도구 | Python은 확정 |
| 프론트엔드 / UI | Undefined(Probably React? IDK) | 이거는 알아서 하기 하지만
npx skills add [https://github.com/vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) --skill web-design-guidelines

vercel web guildline을 지킬것
npx skills add [https://github.com/anthropics/skills](https://github.com/anthropics/skills) --skill frontend-design
anthropic의 generic ai 디자인 버리기를 사용할것? 암튼 이런거 사용할듯 |  |
| 스타일링 / UI 라이브러리 | Undefined(Meterial Based?) |  |  |
| 백엔드 | FastAPI, Langchain | easy choice | yes |
| 데이터베이스 | progresql with vectorDB | easy choice | y |
| 로그인 / 인증 | jwt | idk so AI should handle this | n |
| AI 모델 / API | Pickle(it is Openai with diffecent provider), OpenAI | easy choice | y |
| 음성 인식 (필요한 경우) | Whisper(python Openai library) | best for local stt service | y |
| 음성 합성 (필요한 경우) | Azure TTS or [https://github.com/k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice) | It produced decent english tts but i dont know about korean | n |
| 파일 / 음성 저장소 | SUPERBASE(if necessary) | A backend platform built on PostgreSQL |  |
| 배포 / 호스팅 | None | It will not hosted at least so [Localhost](http://Localhost)  |  |
| 테스트 도구 | None | No, we will not QA in this MVP product | y |
| 기타 외부 서비스 | WebAudioAPI | to make Interview more engaging | y |
- **직접 써 보고 싶거나 익숙한 기술: fastAPI**
- **사용하고 싶지 않은 기술: none**
- **기술 선택 시 가장 중요한 기준:** <!-- 학습 목적, 개발 속도, 비용, 유지보수 등 --> 학습 목적 및 vibe코드로 rag기반 ai 웹 서비스 구현

## 6. 범위와 제약

- **첫 버전에서 꼭 완성하고 싶은 것: 답변 평가, 인텨뷰 환경, ai 멘토링**
- **첫 버전에는 넣지 않을 것: 회원 정보 관리**
- **목표 일정: 2026-11-06 ~ 11-07**
- **월 운영비 / API 비용 예산: 10달러 정도 있고 별로 하루 하고 끝**
- **개인정보·녹음 데이터의 저장 및 삭제에 대한 요구: 로컬에서 돌릴거기 때문에 의미 없음**
- **그 밖에 반드시 지켜야 할 조건: 사용자 음성 등 개인 정보 유출 금지 보안 신경**

## 7. 자유 메모와 논의할 점

- **아직 결정하지 못한 내용:**
- **구조를 설계할 때 함께 검토하고 싶은 내용:**
- **참고 자료 / 화면 아이디어:**
- **기타 메모:**