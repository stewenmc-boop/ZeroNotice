"""Build the ZeroNotice hackathon deck (Korean, 16:9, editable)."""

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

OUT = r"D:\KUN_lswes\ZeroNotice_발표자료.pptx"
IMG = r"D:\KUN_lswes\.tmp\deckimg"

INK = RGBColor(0x0B, 0x0B, 0x0F)
MUTED = RGBColor(0x6F, 0x6F, 0x78)
FAINT = RGBColor(0xA1, 0xA1, 0xAA)
LINE = RGBColor(0xE6, 0xE6, 0xEA)
SOFT = RGBColor(0xF7, 0xF7, 0xF8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
EMERALD = RGBColor(0x10, 0xB9, 0x81)
AMBER = RGBColor(0xD9, 0x77, 0x06)
FONT = "Malgun Gothic"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

MARGIN = Inches(0.75)
CONTENT_W = prs.slide_width - MARGIN * 2


def txbox(slide, x, y, w, h, text="", size=14, bold=False, color=INK,
          align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.0, font=FONT):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = font
    return box


def rect(slide, x, y, w, h, fill=None, line=None, radius=None, shadow=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, x, y, w, h)
    if radius:
        shape.adjustments[0] = radius
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(1)
    shape.shadow.inherit = False
    style = shape._element.find(qn("p:style"))
    if style is not None:
        shape._element.remove(style)
    return shape


def header(slide, kicker, title, sub=None):
    txbox(slide, MARGIN, Inches(0.52), CONTENT_W, Inches(0.24),
          kicker.upper(), size=10, bold=True, color=FAINT)
    txbox(slide, MARGIN, Inches(0.82), CONTENT_W, Inches(0.62),
          title, size=28, bold=True, color=INK)
    y = Inches(1.52)
    if sub:
        txbox(slide, MARGIN, Inches(1.46), CONTENT_W, Inches(0.36), sub, size=13, color=MUTED)
        y = Inches(1.95)
    rect(slide, MARGIN, y, CONTENT_W, Emu(9525), fill=LINE)
    return y


def footer(slide, idx, note=None):
    rect(slide, 0, prs.slide_height - Inches(0.42), prs.slide_width, Emu(9525), fill=LINE)
    txbox(slide, MARGIN, prs.slide_height - Inches(0.34), Inches(8), Inches(0.24),
          "ZeroNotice · 2026 KNU AI Hackathon · Zero to One", size=9, color=FAINT)
    txbox(slide, prs.slide_width - MARGIN - Inches(0.8), prs.slide_height - Inches(0.34),
          Inches(0.8), Inches(0.24), f"{idx:02d}", size=9, color=FAINT, align=PP_ALIGN.RIGHT)
    if note:
        slide.notes_slide.notes_text_frame.text = note


def kpi(slide, x, y, w, h, value, label, sub="", accent=INK):
    rect(slide, x, y, w, h, fill=SOFT, radius=0.08)
    txbox(slide, x + Inches(0.22), y + Inches(0.18), w - Inches(0.44), Inches(0.5),
          value, size=26, bold=True, color=accent)
    txbox(slide, x + Inches(0.22), y + Inches(0.72), w - Inches(0.44), Inches(0.28),
          label, size=11, bold=True, color=INK)
    if sub:
        txbox(slide, x + Inches(0.22), y + Inches(0.98), w - Inches(0.44), Inches(0.5),
              sub, size=9.5, color=MUTED, spacing=1.15)


def picture(slide, name, x, y, w=None, h=None):
    path = os.path.join(IMG, name)
    if w and h:
        return slide.shapes.add_picture(path, x, y, w, h)
    if w:
        return slide.shapes.add_picture(path, x, y, width=w)
    return slide.shapes.add_picture(path, x, y, height=h)


# ---------------------------------------------------------------- 01 cover
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, prs.slide_width, prs.slide_height, fill=WHITE)
rect(s, 0, 0, Inches(0.14), prs.slide_height, fill=INK)

txbox(s, MARGIN, Inches(0.9), Inches(7), Inches(0.3),
      "2026 KNU AI HACKATHON · ZERO TO ONE", size=10, bold=True, color=FAINT)
txbox(s, MARGIN, Inches(1.35), Inches(7.4), Inches(2.1),
      "공지의 숨은 비용을\n0으로 만드는 AI 비서", size=40, bold=True, color=INK, spacing=1.15)
txbox(s, MARGIN, Inches(3.55), Inches(7.2), Inches(1.0),
      "ZeroNotice (제로노티스)\n강원대 공지 탐색 · HWP·PDF·XLSX 판독 · 자격 판정 · 신청 링크 추출 · 마감 알림",
      size=14, color=MUTED, spacing=1.4)
rect(s, MARGIN, Inches(4.95), Inches(1.2), Emu(19050), fill=EMERALD)
txbox(s, MARGIN, Inches(5.15), Inches(7), Inches(0.9),
      "류위신 · 2026.11.06\n첨단AI공학부", size=12, color=INK, spacing=1.35)

picture(s, "detail.png", Inches(8.35), Inches(0.85), h=Inches(5.8))
rect(s, Inches(8.35), Inches(0.85), Inches(4.2), Inches(5.8), line=LINE)
footer(s, 1, "표지. 3분 발표 기준: 문제(30초) → 데모(90초) → 증명(45초) → 확장(15초).")

# ---------------------------------------------------------------- 02 problem
s = prs.slides.add_slide(BLANK)
y = header(s, "01 · 문제 정의", "한 문장으로: 누가, 언제, 무엇 때문에, 얼마를 내고 있나",
           "평가 기준 20점 — 문제 정의·현장성")
rect(s, MARGIN, y + Inches(0.22), CONTENT_W, Inches(1.28), fill=SOFT, radius=0.06)
txbox(s, MARGIN + Inches(0.3), y + Inches(0.36), CONTENT_W - Inches(0.6), Inches(1.0),
      "강원대 재학생이 매주 장학·학사 공지를 찾을 때, 본문이 비어 있고 자격요건이 HWP 첨부 안에 숨어 있어\n"
      "확인만 하다 시간을 쓰고, 신청 링크를 놓쳐 마감을 넘긴다.",
      size=15, color=INK, spacing=1.35)

cards = [
    ("6.1분", "공지 1건 확인", "탐색 3.5 + 첨부 열람 1.5 + 자격 대조 1.1분"),
    ("주 5건", "실제 확인 빈도", "장학·학사·공모·행사 공지 합산"),
    ("6.8시간", "학기당 소모", "15주 기준 · 시급 1만원 가정 시 68,000원"),
    ("D-3", "평균 발견 시점", "마감 직전에야 알게 되는 경우"),
]
w = (CONTENT_W - Inches(0.45)) / 4
for i, (v, l, sub) in enumerate(cards):
    kpi(s, MARGIN + i * (w + Inches(0.15)), y + Inches(1.75), w, Inches(1.65), v, l, sub)

txbox(s, MARGIN, y + Inches(3.65), CONTENT_W, Inches(0.9),
      "핵심은 ‘검색이 안 된다’가 아니라 ‘확인·판단·신청 준비’가 전부 사람 손이라는 점입니다.\n"
      "공지는 이미 공개되어 있지만, 내 조건과 대조되고 신청까지 이어지는 경로가 없습니다.",
      size=13, color=MUTED, spacing=1.4)
footer(s, 2, "수치는 자체 추정 공식(공지 1건 6.1분)과 파일럿 측정 계획으로 산출. 뒤 슬라이드에서 공식을 공개합니다.")

# ---------------------------------------------------------------- 03 why broken
s = prs.slides.add_slide(BLANK)
y = header(s, "02 · 왜 지금도 안 되는가", "공지 3중 구조: 빈 본문 · 첨부 안의 조건 · 흩어진 신청 경로")

items = [
    ("본문 0자 + HWP 첨부", "실제 공지 25건 중 다수가 본문이 비어 있고 모집요강은 .hwp 로만 제공.\n한글 오피스 없이는 열리지 않습니다."),
    ("자격요건이 문서 안에", "GPA·소득분위·캠퍼스·재학상태 조건이 첨부 3~4p에 흩어져 있음.\n사람은 3개 사이트를 오가며 대조합니다."),
    ("신청 경로가 제각각", "어떤 공지는 이메일, 어떤 공지는 구글폼, 어떤 공지는 포스터 이미지 안의 QR.\n링크가 본문에 없는 경우도 있습니다."),
]
w = (CONTENT_W - Inches(0.4)) / 3
for i, (t, d) in enumerate(items):
    x = MARGIN + i * (w + Inches(0.2))
    rect(s, x, y + Inches(0.25), w, Inches(2.45), fill=WHITE, line=LINE, radius=0.05)
    txbox(s, x + Inches(0.25), y + Inches(0.45), w - Inches(0.5), Inches(0.5),
          f"0{i+1}", size=11, bold=True, color=EMERALD)
    txbox(s, x + Inches(0.25), y + Inches(0.78), w - Inches(0.5), Inches(0.6),
          t, size=15, bold=True, color=INK)
    txbox(s, x + Inches(0.25), y + Inches(1.45), w - Inches(0.5), Inches(1.1),
          d, size=10.5, color=MUTED, spacing=1.35)

txbox(s, MARGIN, y + Inches(2.95), CONTENT_W, Inches(0.4),
      "→ 그래서 우리는 ‘공지를 보여주는 앱’이 아니라, 공지를 읽고 판단해서 신청 직전까지 데려다주는 비서를 만들었습니다.",
      size=13, bold=True, color=INK)

rect(s, MARGIN, y + Inches(3.5), CONTENT_W, Inches(1.15), fill=SOFT, radius=0.04)
txbox(s, MARGIN + Inches(0.28), y + Inches(3.62), Inches(11.4), Inches(0.9),
      "실제 공지 본문(캡처): “강원대학교 KNU창업혁신원은 … 창업장학금을 지원하고자 합니다. …\n"
      "1-2. 전체 학기 성적 평점 평균이 3.5점(4.5만점 기준) 이상 …”",
      size=10.5, color=MUTED, spacing=1.35)
txbox(s, MARGIN + Inches(0.28), y + Inches(4.24), Inches(11.4), Inches(0.3),
      "첨부 3개가 전부 .hwp — 한글 오피스 없이는 열리지 않고, 자격 기준은 2페이지 안에 있습니다.",
      size=9.5, color=FAINT)
footer(s, 3, "실제 수집 데이터: 25건 / 첨부 45개(HWP 10·PDF 11·XLSX 8·HWPX 4·PNG 5).")

# ---------------------------------------------------------------- 04 solution
s = prs.slides.add_slide(BLANK)
y = header(s, "03 · 해결", "공지 한 건이 ‘확인’에서 ‘신청 완료’까지 이어지도록")

rows = [
    ("공지 통합", "5개 게시판(장학·학사·공모·일반·행사)을 한 화면에. Supabase 공유 DB로 모든 사용자가 같은 데이터를 봅니다."),
    ("첨부 5종 판독", "HWP · HWPX · PDF · XLSX · DOCX 를 서버에서 직접 파싱. 한글 오피스 없이 조건을 읽습니다."),
    ("자격 자동 판정", "캠퍼스·신분·GPA·소득분위를 규칙 엔진으로 대조해 ‘지원 가능 / 조건 확인 / 대상 아님’을 즉시 표시."),
    ("신청 정보 추출", "AI가 본문·첨부·포스터에서 신청 링크, 접수 방법, 제출 서류, 문의처를 뽑고 출처·신뢰도를 함께 표기."),
    ("마감 알림", "관심 등록하면 마감 24시간 전에 메일 + .ics 캘린더. 한 번 보내면 중복 발송하지 않습니다."),
]
yy = y + Inches(0.28)
for i, (t, d) in enumerate(rows):
    rect(s, MARGIN, yy, Inches(0.42), Inches(0.42), fill=INK, radius=0.5)
    txbox(s, MARGIN, yy + Inches(0.07), Inches(0.42), Inches(0.3),
          str(i + 1), size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txbox(s, MARGIN + Inches(0.62), yy - Inches(0.02), Inches(2.5), Inches(0.32),
          t, size=14, bold=True, color=INK)
    txbox(s, MARGIN + Inches(3.15), yy - Inches(0.02), CONTENT_W - Inches(3.2), Inches(0.55),
          d, size=11, color=MUTED)
    yy += Inches(0.86)
footer(s, 4, "5개 기능은 모두 같은 데이터(공지 JSON + 추출 캐시)를 공유합니다. 화면만 다를 뿐 판정 근거는 하나입니다.")

# ---------------------------------------------------------------- 05 demo 1
s = prs.slides.add_slide(BLANK)
y = header(s, "04 · 데모 ①", "목록에서 3초 만에 ‘내가 지원 가능한 공지’만")
picture(s, "detail.png", MARGIN, y + Inches(0.25), h=Inches(4.55))
bx = MARGIN + Inches(4.95)
txbox(s, bx, y + Inches(0.3), Inches(7), Inches(0.4), "무엇을 보여주나", size=11, bold=True, color=EMERALD)
txbox(s, bx, y + Inches(0.7), Inches(6.9), Inches(1.4),
      "• 좌측: 캠퍼스·신분·GPA·소득분위를 입력하면 그 자리에서 판정\n"
      "• 목록: ‘지원 가능 / 조건 확인 / 대상 아님’ + D-day\n"
      "• 상단: ‘신청 링크만’ 필터로 바로 신청 가능한 공지만 추려보기",
      size=12, color=INK, spacing=1.5)
txbox(s, bx, y + Inches(2.35), Inches(7), Inches(0.4), "심사 포인트", size=11, bold=True, color=EMERALD)
txbox(s, bx, y + Inches(2.75), Inches(6.9), Inches(1.6),
      "판정은 LLM이 아니라 규칙 엔진이 합니다(agent.evaluate_real_notice).\n"
      "LLM은 요약·작문만 담당하므로 ‘GPA 3.5 미만인데 지원 가능’ 같은 오판이 구조적으로 불가능합니다.",
      size=12, color=MUTED, spacing=1.5)
footer(s, 5, "데모: 왼쪽에서 GPA를 2.0으로 낮추면 즉시 ‘대상 아님’으로 바뀌는 장면을 보여주면 효과적.")

# ---------------------------------------------------------------- 06 demo 2
s = prs.slides.add_slide(BLANK)
y = header(s, "05 · 데모 ②", "공지 안의 ‘신청 링크’와 ‘문의 메일’을 AI가 꺼내옵니다")
picture(s, "apply.png", MARGIN, y + Inches(0.25), w=Inches(6.0))
txbox(s, MARGIN, y + Inches(2.9), Inches(6.2), Inches(0.3),
      "신청 정보 카드 — 링크·접수 방법·서류·문의처 + 출처/신뢰도", size=9.5, color=FAINT)

txbox(s, MARGIN, y + Inches(3.35), Inches(6.0), Inches(0.35),
      "왜 이게 중요한가", size=10, bold=True, color=EMERALD)
txbox(s, MARGIN, y + Inches(3.7), Inches(6.0), Inches(1.4),
      "공지 25건 중 신청 링크가 본문에 있는 건 7건뿐.\n"
      "1건은 포스터 이미지 안에만 링크가 있었고, OCR + HTTP 검증으로 찾아냈습니다.\n"
      "나머지는 ‘이메일 제출’이라 링크가 없는 게 정상 — 그래서 메일 초안 기능이 필요합니다.",
      size=10.5, color=MUTED, spacing=1.4)
picture(s, "assistant.png", MARGIN + Inches(6.55), y + Inches(0.25), h=Inches(4.05))
txbox(s, MARGIN + Inches(6.55), y + Inches(4.42), Inches(4.1), Inches(0.6),
      "플로팅 AI 비서 — “이번 주 마감 공지”, “이 공지 구독해줘”\n처럼 말하면 도구를 호출해 실제로 처리", size=9.5, color=FAINT)
footer(s, 6, "7건은 본문/첨부에서, 1건은 포스터 OCR에서 링크를 찾았습니다. OCR 링크는 HTTP 200 검증을 통과한 것만 노출.")

# ---------------------------------------------------------------- 07 demo 3
s = prs.slides.add_slide(BLANK)
y = header(s, "06 · 데모 ③", "잊지 않도록: 관심 등록 → 마감 24시간 전 메일 + 캘린더")
picture(s, "sub.png", MARGIN, y + Inches(0.3), w=Inches(6.4))
picture(s, "gallery.png", MARGIN, y + Inches(2.35), w=Inches(6.4))
bx = MARGIN + Inches(6.75)
txbox(s, bx, y + Inches(0.35), Inches(5.6), Inches(0.4), "동작 방식", size=11, bold=True, color=EMERALD)
txbox(s, bx, y + Inches(0.75), Inches(5.5), Inches(2.3),
      "1. 공지에서 🔔 클릭 → 구독 저장(사용자별)\n"
      "2. 서버가 5분마다 점검(서버리스는 Cron 1일 1회)\n"
      "3. 마감 24시간 전, 프로필 이메일로 발송\n"
      "4. .ics 첨부 → 열면 캘린더 자동 등록\n"
      "5. reminded_at 기록으로 중복 발송 차단",
      size=12, color=INK, spacing=1.55)
txbox(s, bx, y + Inches(3.15), Inches(5.6), Inches(0.4), "실측", size=11, bold=True, color=EMERALD)
txbox(s, bx, y + Inches(3.55), Inches(5.5), Inches(1.0),
      "QQ SMTP 실제 발송 성공(465/SSL, 587/STARTTLS 모두 확인)\n"
      "메일 1건 + 다이제스트 3건 발송 테스트 완료",
      size=11, color=MUTED, spacing=1.4)
footer(s, 7, "심사위원 앞에서 실제 메일함을 열어 .ics 첨부를 보여주는 것이 가장 강한 증거입니다.")

# ---------------------------------------------------------------- 08 architecture
s = prs.slides.add_slide(BLANK)
y = header(s, "07 · 구조", "규칙은 코드, 언어는 LLM, 실행은 에이전트")

boxes = [
    ("데이터", "강원대 5개 게시판\nHWP·PDF·XLSX·DOCX 파싱\n포스터 OCR + 링크 검증", MARGIN, y + Inches(0.35)),
    ("판정", "규칙 엔진\n캠퍼스·신분·GPA·소득\n(LLM 사용 안 함)", MARGIN + Inches(4.0), y + Inches(0.35)),
    ("생성", "LLM(DeepSeek)\n요약·문의메일·지원서\nJSON 구조화 추출", MARGIN + Inches(8.0), y + Inches(0.35)),
]
bw, bh = Inches(3.5), Inches(1.9)
for t, d, x, yy2 in boxes:
    rect(s, x, yy2, bw, bh, fill=SOFT, radius=0.06)
    txbox(s, x + Inches(0.22), yy2 + Inches(0.18), bw - Inches(0.44), Inches(0.3),
          t, size=11, bold=True, color=EMERALD)
    txbox(s, x + Inches(0.22), yy2 + Inches(0.55), bw - Inches(0.44), Inches(1.2),
          d, size=10.5, color=INK, spacing=1.35)

rect(s, MARGIN, y + Inches(2.55), CONTENT_W, Inches(1.25), fill=WHITE, line=LINE, radius=0.04)
txbox(s, MARGIN + Inches(0.3), y + Inches(2.72), CONTENT_W - Inches(0.6), Inches(0.35),
      "AI 비서(도구 호출 에이전트)", size=12, bold=True, color=INK)
txbox(s, MARGIN + Inches(0.3), y + Inches(3.08), CONTENT_W - Inches(0.6), Inches(0.9),
      "search_notices · get_notice · list_upcoming · subscribe_notice · list_subscriptions · "
      "draft_inquiry_email · send_inquiry_email · get_my_profile",
      size=9.5, color=MUTED, spacing=1.4)

txbox(s, MARGIN, y + Inches(4.0), CONTENT_W, Inches(1.0),
      "• 모든 사실은 도구 결과에서만 나옵니다. 도구가 실패하면 “확인 못 했다”고 말합니다.\n"
      "• 쓰기 동작(구독·메일 발송)은 사용자가 그 의도를 말했을 때만 실행합니다.",
      size=11, color=MUTED, spacing=1.4)
footer(s, 8, "질문 대비: 왜 RAG가 아니라 도구 호출인가? → 공지 데이터가 정형(JSON)이라 검색보다 정확한 조회가 필요.")

# ---------------------------------------------------------------- 09 data trust
s = prs.slides.add_slide(BLANK)
y = header(s, "08 · 데이터 신뢰성", "‘AI가 그럴듯하게 쓴 것’과 ‘원문에서 확인한 것’을 구분합니다")

kpis = [("25건", "공지 수집", "원문 제목 22/22 일치 확인"),
        ("45개", "첨부 업로드", "Supabase Storage · 최대 9.4MB"),
        ("23건", "AI 신청정보 추출", "링크 7 · 문의메일 6"),
        ("403", "RLS 차단", "타 사용자 행 쓰기 시도 실측")]
w = (CONTENT_W - Inches(0.45)) / 4
for i, (v, l, sub) in enumerate(kpis):
    kpi(s, MARGIN + i * (w + Inches(0.15)), y + Inches(0.25), w, Inches(1.2), v, l, sub)

rules = [
    "없는 정보는 만들지 않습니다. 이메일·링크가 없으면 버튼 자체를 만들지 않고 ‘공고에 없음’으로 표시합니다.",
    "OCR로 읽은 링크는 실제 HTTP 요청으로 살아있는지 확인한 뒤에만 노출합니다(죽은 링크 5건은 rejected 처리).",
    "개인정보(이름·학번·연락처)는 사용자가 입력한 값만 사용합니다. 비어 있으면 (미입력)으로 표기합니다.",
    "30일이 지난 공지는 자동 삭제(purge_expired_notices). 첨부·추출 캐시도 함께 정리됩니다.",
]
yy = y + Inches(1.75)
for r in rules:
    rect(s, MARGIN + Inches(0.02), yy + Inches(0.08), Inches(0.14), Inches(0.14), fill=EMERALD, radius=0.5)
    txbox(s, MARGIN + Inches(0.32), yy, CONTENT_W - Inches(0.4), Inches(0.5), r, size=11.5, color=INK)
    yy += Inches(0.62)
footer(s, 9, "Supabase RLS 실측: A가 쓴 profile을 B가 읽으면 [], B가 A의 user_id로 쓰면 403.")

# ---------------------------------------------------------------- 10 cost
s = prs.slides.add_slide(BLANK)
y = header(s, "09 · 비용 증명", "줄었다고 말하지 않고, 계산식을 공개합니다")

headers = ["항목", "기존(수동)", "ZeroNotice", "절감"]
data = [
    ("공지 1건 확인", "6.1분", "0.7분", "-5.4분"),
    ("주 5건", "30.5분", "3.5분", "-27분"),
    ("학기(15주)", "7.6시간", "0.9시간", "-6.7시간"),
    ("금액(시급 1만원)", "76,000원", "9,000원", "-67,000원"),
]
col_w = [Inches(3.4), Inches(2.6), Inches(2.6), Inches(2.2)]
x = MARGIN
for i, h in enumerate(headers):
    txbox(s, x, y + Inches(0.3), col_w[i], Inches(0.3), h, size=10, bold=True, color=FAINT)
    x += col_w[i]
yy = y + Inches(0.65)
for row in data:
    x = MARGIN
    rect(s, MARGIN, yy - Inches(0.06), CONTENT_W, Inches(0.42), fill=SOFT if data.index(row) % 2 == 0 else WHITE)
    for i, cell in enumerate(row):
        color = EMERALD if i == 3 else INK
        txbox(s, x + Inches(0.12), yy, col_w[i], Inches(0.3), cell,
              size=11, bold=(i == 3), color=color)
        x += col_w[i]
    yy += Inches(0.46)

txbox(s, MARGIN, y + Inches(2.55), CONTENT_W, Inches(0.34),
      "계산식(공개): 수동 6.1분 = 탐색 3.5 + 첨부 열람 1.5 + 자격 대조 1.1 / 도구 0.7분 = 검색 0.2 + 판정 0.2 + 알림 등록 0.3",
      size=10, color=MUTED)
txbox(s, MARGIN, y + Inches(2.95), CONTENT_W, Inches(1.3),
      "• 위 수치는 ‘추정 공식’이며, 발표 전 3명 파일럿(같은 과제, 15분 상한, 정답 대조)으로 대체 예정입니다.\n"
      "• 시스템 실측: 공지 25건 + 첨부 45개 파싱, AI 추출 23건, 메일 발송 성공까지 실제 동작 확인.\n"
      "• 측정 방법과 원자료는 저장소 docs/measurement-protocol.md 에 공개되어 재현 가능합니다.",
      size=11, color=INK, spacing=1.45)
footer(s, 10, "정직성 포인트: 추정치와 실측치를 섞지 않는다고 먼저 말하면 오히려 신뢰가 올라갑니다.")

# ---------------------------------------------------------------- 11 deploy
s = prs.slides.add_slide(BLANK)
y = header(s, "10 · 배포와 확장", "웹에서 끝나지 않고, 설치형 앱과 공유 DB로 확장")

cols = [
    ("웹 (Vercel)", "zero-notice.vercel.app\n서버리스 + Cron으로 마감 알림\n누구나 링크로 접속"),
    ("데스크톱 (.exe/.dmg)", "Python + 웹 UI 패키징\n로컬에서도 동작(오프라인 폴백)\n개인 데이터는 기기별 분리"),
    ("공유 데이터 (Supabase)", "공지·첨부는 모두 공유\n프로필·구독·AI 키는 사용자별(RLS)\n30일 보관 정책"),
]
w = (CONTENT_W - Inches(0.4)) / 3
for i, (t, d) in enumerate(cols):
    x = MARGIN + i * (w + Inches(0.2))
    rect(s, x, y + Inches(0.3), w, Inches(2.2), fill=WHITE, line=LINE, radius=0.05)
    txbox(s, x + Inches(0.24), y + Inches(0.5), w - Inches(0.48), Inches(0.4), t, size=14, bold=True, color=INK)
    txbox(s, x + Inches(0.24), y + Inches(1.0), w - Inches(0.48), Inches(1.2), d, size=10.5, color=MUTED, spacing=1.4)

txbox(s, MARGIN, y + Inches(2.75), CONTENT_W, Inches(0.4),
      "다음 단계", size=11, bold=True, color=EMERALD)
txbox(s, MARGIN, y + Inches(3.1), CONTENT_W, Inches(1.4),
      "• 카카오 로그인으로 신원 연결 → 학과·학번 자동 매칭\n"
      "• 공지 크롤러를 타 대학으로 확장(현재 강원대 5개 게시판)\n"
      "• 신청서 자동 작성 → 제출까지(현재는 초안 + 메일 발송)",
      size=11.5, color=INK, spacing=1.45)
footer(s, 11, "확장성 15점 대응: 같은 파이프라인에 게시판 URL만 추가하면 다른 대학에도 적용됩니다.")

# ---------------------------------------------------------------- 12 close
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, prs.slide_width, prs.slide_height, fill=INK)
txbox(s, MARGIN, Inches(1.5), Inches(10), Inches(0.4), "THANK YOU", size=11, bold=True,
      color=RGBColor(0x6E, 0x6E, 0x76))
txbox(s, MARGIN, Inches(2.0), Inches(11), Inches(1.6),
      "공지를 찾는 시간을 0으로,\n신청까지의 거리를 0으로.", size=34, bold=True, color=WHITE, spacing=1.2)

stats = [("25", "공지"), ("45", "첨부"), ("23", "AI 추출"), ("24h", "마감 알림")]
x = MARGIN
for v, l in stats:
    txbox(s, x, Inches(4.05), Inches(2.2), Inches(0.6), v, size=26, bold=True, color=WHITE)
    txbox(s, x, Inches(4.62), Inches(2.2), Inches(0.3), l, size=10, color=RGBColor(0x9A, 0x9A, 0xA4))
    x += Inches(2.4)

txbox(s, MARGIN, Inches(5.35), Inches(11), Inches(0.9),
      "github.com/stewenmc-boop/ZeroNotice   ·   zero-notice.vercel.app\n"
      "류위신 · 첨단AI공학부 · 2026 KNU AI Hackathon",
      size=11.5, color=RGBColor(0xC9, 0xC9, 0xD0), spacing=1.5)
txbox(s, MARGIN, Inches(6.5), Inches(11), Inches(0.4),
      "감사합니다. 질문 받겠습니다.", size=12, color=RGBColor(0x9A, 0x9A, 0xA4))
txbox(s, prs.slide_width - MARGIN - Inches(0.8), prs.slide_height - Inches(0.34),
      Inches(0.8), Inches(0.24), "12", size=9, color=RGBColor(0x6E, 0x6E, 0x76), align=PP_ALIGN.RIGHT)

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides.__iter__.__self__._sldIdLst))
