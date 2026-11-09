// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// 결과 PDF 첫 페이지에 넣는 "AI 연습 자료 요청문"과 PDF 기본 파일명.
// PDF만 다른 AI(ChatGPT·Claude·Gemini 등)에 첨부하면, 이 요청문을 따라 실제로 소리 내어 연습할 문장을 만들도록 한다.
// 요청문 첫 단락은 사용자가 정한 문장을 그대로 쓰고, 아래에 출력 구조만 덧붙인다.

export const TARGET_LEVEL = 'AL';

/** 사용자가 정한 요청문 원문(수정하지 않는다) */
export const USER_PROMPT = [
  '첨부한 영어 말하기 모의 인터뷰 진단 PDF를 바탕으로, OPIc AL을 목표로 하는 개인 맞춤형 말하기 연습 자료를 만들어 줘. 단순히 리포트를 요약하거나 공부법을 설명하는 것이 아니라, 내가 실제로 소리 내어 연습할 영어 문장을 생성하는 것이 핵심이야.',
  '설명은 한국어로, 연습 문장은 영어와 한국어를 함께 제공해.',
  '일반적인 조언보다 실제로 말할 문장에 가장 많은 분량을 사용해.',
];

export interface PromptContext {
  /** 화면에 보이는 예상 수준 문구(예: "IM2", "IM(세분화 보류)", "판단 근거 부족") */
  levelText: string;
  headline: string;
  nextLevelGap: string;
}

/** 출력 구조 지시. 사용자 원문 뒤에 붙는다. */
export function buildGuide(ctx: PromptContext): string[] {
  return [
    `[진단 요약] 이 PDF의 예상 수준: ${ctx.levelText} / 목표: OPIc ${TARGET_LEVEL}`,
    ctx.headline ? `한 줄 진단: ${ctx.headline}` : '',
    ctx.nextLevelGap ? `다음 단계까지의 차이: ${ctx.nextLevelGap}` : '',
    '',
    '[PDF 읽는 법] 이 페이지 다음부터가 진단 리포트야. "문항별 상세"의 "내 답변(전사)"이 내가 실제로 한 말이고, "고칠 점"과 "연습 카드"가 진단 결과야. 전사는 음성 인식 결과라 철자 오류가 있을 수 있어.',
    '',
    '[출력 구성] 아래 순서와 분량 비율을 지켜 줘.',
    '1. 핵심 약점 3가지 (전체의 10% 이하) — 리포트 근거(문항 번호, 내 실제 표현)를 짧게 인용하고 한국어로 한두 줄씩만 설명.',
    '2. 내 답변 AL 버전으로 고쳐 쓰기 (가장 큰 분량) — 채점된 문항마다: 내 원래 문장 → AL 수준 영어 문장 → 한국어 뜻. 내가 말한 내용·경험은 유지하고 표현·구조·연결만 끌어올려.',
    '3. 문항 유형별 AL 모범 답변 (큰 분량) — 묘사, 루틴/습관, 과거 경험, 비교/변화, 롤플레이(질문하기·문제 해결), 돌발 주제. 유형마다 1분 30초~2분 분량의 영어 답변 + 한국어 번역. 내 리포트에 나온 주제와 내 상황을 소재로 써.',
    '4. 바로 꺼내 쓸 문장 뱅크 — 도입, 시간 흐름, 이유·예시, 대조, 감정·의견, 마무리 표현을 각 5개 이상 영어+한국어로. 내가 리포트에서 반복한 단순 표현을 무엇으로 바꿀지 짝지어 보여 줘.',
    '5. 소리 내어 연습하는 순서 (짧게) — 위 문장으로 섀도잉 → 따라 말하기 → 내 말로 바꿔 말하기 순서를 3일 정도 분량으로.',
    '',
    '[형식] 영어 문장은 한 줄에 하나, 바로 아래 줄에 한국어 뜻. 일반적인 공부법·동기 부여 문구는 넣지 마. 모든 영어 문장은 실제 시험장에서 그대로 말할 수 있는 자연스러운 구어체로.',
  ].filter((l, i, a) => l !== '' || (i > 0 && a[i - 1] !== ''));
}

/** 복사용 전체 요청문(텍스트) */
export function buildPromptText(ctx: PromptContext): string {
  return [...USER_PROMPT, '', ...buildGuide(ctx)].join('\n');
}

/** PDF 저장 시 기본 파일명(= 인쇄 직전 document.title). 저장하는 시각 기준, 파일명에 쓸 수 없는 문자는 쓰지 않는다. */
export function pdfTitle(now = new Date()): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `OpicTutor_진단리포트_${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}_${p(now.getHours())}-${p(now.getMinutes())}`;
}
