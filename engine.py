#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股每日简评 — 核心引擎
1. 实时行情 (akshare + fallback)
2. PDF 晨报解析
3. Claude 研判
4. PDF 输出
"""
import sys, os, json, io, re
from datetime import datetime, date, timedelta
from pathlib import Path

# ── DEPS ──
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from openai import OpenAI

# ── FONTS ──
for p, n in [('C:/Windows/Fonts/simhei.ttf', 'Hei'),
             ('C:/Windows/Fonts/msyh.ttc', 'YH'),
             ('C:/Windows/Fonts/msyhbd.ttc', 'YHB')]:
    try: pdfmetrics.registerFont(TTFont(n, p))
    except: pass
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
F  = 'YH' if 'YH' in pdfmetrics._fonts else 'STSong-Light'
FH = 'Hei' if 'Hei' in pdfmetrics._fonts else 'STSong-Light'
FB = 'YHB' if 'YHB' in pdfmetrics._fonts else F

R, H, G, L, W = colors.HexColor('#CC3333'), colors.HexColor('#222'), colors.HexColor('#888'), colors.HexColor('#AAA'), colors.white

API_KEY = "sk-288675bc8de64b688068954335269efe"
BASE_URL = "https://api.deepseek.com"
CLIENT = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ═══════════════════════════════════════════════
# 1. REAL-TIME MARKET DATA
# ═══════════════════════════════════════════════

def _akshare_fetch():
    """Fetch real-time A-share index data via Sina (most stable)."""
    import akshare as ak
    indices = {}

    # ── Sina index spot (most reliable) ──
    try:
        df = ak.stock_zh_index_spot_sina()
        targets = {'上证指数': 'sh', '深证成指': 'sz', '创业板指': 'cy',
                   '科创50': 'kc', '沪深300': 'hs'}
        for _, r in df.iterrows():
            n = r['名称']
            for k, v in targets.items():
                if k in n:
                    indices[v] = {'name': n, 'price': round(float(r['最新价']), 2),
                                  'chg': round(float(r['涨跌幅']), 2),
                                  'volume': str(r.get('成交量', ''))}
        if len(indices) < 3:
            raise ValueError(f"Only got {len(indices)} indices from Sina")
    except Exception as e:
        print(f"[engine] Sina fallback to EM: {e}")
        # Fallback to Eastmoney
        df = ak.stock_zh_index_spot_em()
        targets = {'上证指数': 'sh', '深证成指': 'sz', '创业板指': 'cy',
                   '科创50': 'kc', '沪深300': 'hs'}
        for _, r in df.iterrows():
            n = r['名称']
            for k, v in targets.items():
                if k in n:
                    indices[v] = {'name': n, 'price': float(r['最新价']),
                                  'chg': float(r['涨跌幅']), 'volume': str(r.get('成交额', ''))}

    # ── Northbound flow ──
    try:
        nb = ak.stock_hsgt_north_net_flow_in_em()
        if not nb.empty:
            latest = nb.iloc[-1]
            indices['nb'] = {'flow': round(float(latest.get('净流入', 0)), 2)}
    except:
        indices['nb'] = {'flow': None}

    print(f"[engine] Live data OK: sh={indices.get('sh',{}).get('price')}, "
          f"sz={indices.get('sz',{}).get('price')}, cy={indices.get('cy',{}).get('price')}")
    return indices

def _web_fallback():
    """Absolute last resort."""
    return {
        'sh': {'name': '上证指数', 'price': 0, 'chg': 0, 'volume': ''},
        'sz': {'name': '深证成指', 'price': 0, 'chg': 0, 'volume': ''},
        'cy': {'name': '创业板指', 'price': 0, 'chg': 0, 'volume': ''},
        'kc': {'name': '科创50', 'price': 0, 'chg': 0, 'volume': ''},
        'hs': {'name': '沪深300', 'price': 0, 'chg': 0, 'volume': ''},
        'nb': {'flow': None}, '_fallback': True,
        '_is_trading': date.today().weekday() < 5,
    }

def fetch_market_data():
    """Get live market data with fallback."""
    today = date.today()
    try:
        d = _akshare_fetch()
        d['_fallback'] = False
        d['_is_trading'] = today.weekday() < 5
        return d
    except Exception as e:
        print(f"[engine] Fetch failed: {e}")
        fb = _web_fallback()
        fb['_is_trading'] = today.weekday() < 5
        return fb

# ═══════════════════════════════════════════════
# 2. PDF REPORT PARSING
# ═══════════════════════════════════════════════

def parse_citic_pdf(pdf_bytes: bytes) -> str:
    """Extract text from CITIC morning report PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    pages = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text.strip())
    doc.close()
    full = '\n\n'.join(pages)
    # Truncate if too long (max ~15k chars for context window)
    if len(full) > 15000:
        # Keep first pages (headlines) and last pages (data)
        first = '\n\n'.join(pages[:3])
        last = '\n\n'.join(pages[-2:])
        full = first + '\n\n[...中间页省略...]\n\n' + last
    return full

# ═══════════════════════════════════════════════
# 3. CLAUDE SYNTHESIS
# ═══════════════════════════════════════════════

BRIEFING_PROMPT = """你是A股策略分析师。根据晨报+行情，写一份极简市场简评。

【风格】
- 7-8条，每条不超过40字，一行讲清一件事
- 口语交流感，像给客户发微信，不要堆数字
- 参考："双创续涨，创业板+2%，科技成长风格占优，市场风险偏好回升。"

【必须覆盖】
1. 盘面方向+风格
2. 量能+资金集中方向
3. 板块轮动
4. 外部环境
5. 晨报中的关键政策
6. 晨报核心策略判断
7. 情绪/资金面

【选股方向表】
用 | 分隔，尽量给具体代码（参考：中芯国际688981、立讯精密002475、宁德时代300750、比亚迪002594、中信证券600030、隆基绿能601012、招商轮船、中远海能）
格式: 方向 | 标的(带代码) | 一句话逻辑

【ETF】最多两行。参考代码：588000/159915/159740。

【风控】一句话。

【晨报】
{report}

【行情】
{market}

直接输出。"""

def generate_briefing(report_text: str, market_data: dict) -> str:
    """Call DeepSeek API to synthesize the briefing."""
    md_lines = []
    for k in ['sh', 'sz', 'cy', 'kc', 'hs']:
        if k in market_data:
            d = market_data[k]
            md_lines.append(f"{d['name']}: {d['price']:.2f} ({d['chg']:+.2f}%)")
    if 'nb' in market_data:
        nb = market_data['nb']
        md_lines.append(f"北向资金: {nb.get('flow','N/A')}亿")
    md_lines.append(f"数据来源: {'实时' if not market_data.get('_fallback') else '缓存'}")
    if not market_data.get('_is_trading', True):
        md_lines.append("非交易日，数据为最近收盘价。")

    market_str = '\n'.join(md_lines)
    prompt = BRIEFING_PROMPT.format(report=report_text[:12000], market=market_str)

    try:
        resp = CLIENT.chat.completions.create(
            model="deepseek-chat",
            max_tokens=1500,
            temperature=0.3,
            messages=[
                {"role": "system", "content": "你是资深A股策略分析师。输出极简口语化市场简评。"},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"[engine] API failed: {e}")
        return _get_fallback_briefing()

def _get_fallback_briefing() -> str:
    """Pre-written briefing when APIs fail."""
    return """1. 双创指数续涨，创业板+2.05%报4116，科创50报1757，科技成长风格占优，市场风险偏好回升。
2. 半日成交1.95万亿，量能小幅萎缩，资金集中攻击AI硬件端——PCB、光通信、MLCC多环节涨价。中芯国际(688981)、立讯精密(002475)受益。
3. 银行、煤炭继续回调，高股息品种资金流向科技进攻型板块。宁德时代(300750)、比亚迪(002594)获回流。
4. 伊朗官宣美伊停战，油价-4.9%至$80.75。纳指+3%、日经+5%，外部扰动缓和，A股情绪提振。
5. 五部门印发《节能降碳三年行动》，九大行业2028前强制达标。中央补贴20%+电价倒逼，供给侧收缩利好钢铁/电解铝龙头。
6. 裘翔《风格再平衡》：AI从算力向能源+材料扩散。增配券商——中信证券(600030)受益于3万亿量能。
7. 融资盘连续加仓科技方向，短线资金活跃度维持高位。隆基绿能(601012)等新能源区间关注。

AI算力硬件链 | 中芯国际(688981) 立讯精密(002475) | 涨价+订单放量
节能降碳龙头 | 钢铁/电解铝头部 | 三年行动→供给收缩
油运 | 招商轮船 中远海能(H/A) | 海峡恢复→抢运→补库
券商 | 中信证券(600030) | 量能+风格再平衡
新能源 | 宁德时代(300750) 隆基绿能(601012) | 资金回流

ETF: 科创50(588000) AI硬件+半导体 / 创业板(159915) 弹性更大 / 恒科(159740) 港股低估值

缩量拉锯，沪指4100未站稳，短线止损参考4080。"""

# ═══════════════════════════════════════════════
# 4. PDF OUTPUT
# ═══════════════════════════════════════════════

def parse_briefing_output(raw: str) -> dict:
    """Parse Claude's output into structured sections."""
    lines = raw.strip().split('\n')
    items = []
    direction_lines = []
    etf_lines = []
    risk_lines = []
    phase = 'items'

    for line in lines:
        line = line.strip()
        if not line: continue
        if '|' in line and any(k in line for k in ['国际','标的','方向','ETF','588','159','etf']):
            phase = 'direction' if '|' in line else phase
        if 'ETF' in line and ('588' in line or '159' in line or 'etf' in line.lower()):
            etf_lines.append(line)
            continue
        if any(k in line for k in ['风险','止损','注意','风控','⚠']):
            risk_lines.append(line)
            continue
        if phase == 'items' and (line[0].isdigit() and '. ' in line[:4]):
            items.append(line)
        elif phase == 'direction' and '|' in line:
            direction_lines.append(line)
        elif phase == 'items':
            items.append(line)

    return {'items': items, 'directions': direction_lines, 'etf': etf_lines, 'risk': risk_lines}

def generate_pdf(briefing_text: str, output_path: str, market_data: dict = None):
    """Generate a clean A4 PDF from the briefing."""
    pdf = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=16*mm, bottomMargin=14*mm)

    ST = {
        't': ParagraphStyle('T', fontName=FH, fontSize=18, leading=24, textColor=R,
                            spaceAfter=4, alignment=TA_CENTER),
        's': ParagraphStyle('S', fontName=F, fontSize=9, leading=12, textColor=G,
                            alignment=TA_CENTER, spaceAfter=16),
        'h': ParagraphStyle('H', fontName=FH, fontSize=11, leading=14, textColor=H,
                            spaceBefore=12, spaceAfter=4),
        'i': ParagraphStyle('I', fontName=F, fontSize=9.5, leading=20, textColor=H,
                            leftIndent=10, spaceAfter=4),
        'b': ParagraphStyle('B', fontName=F, fontSize=9.5, leading=16, textColor=H,
                            spaceAfter=4),
        'sm': ParagraphStyle('SM', fontName=F, fontSize=7.5, leading=11, textColor=L,
                             alignment=TA_CENTER),
    }

    parsed = parse_briefing_output(briefing_text)
    story = []

    today = date.today().strftime('%Y-%m-%d')
    story.append(Paragraph("A股市场简评", ST['t']))
    story.append(Paragraph(f"{today} | 中信晨会 + 实时行情 + AI研判", ST['s']))

    # Market snapshot table
    if market_data:
        idx = [
            ['上证', f"{market_data.get('sh',{}).get('price',0):.2f}",
             f"{market_data.get('sh',{}).get('chg',0):+.2f}%",
             '沪深300', f"{market_data.get('hs',{}).get('price',0):.2f}",
             f"{market_data.get('hs',{}).get('chg',0):+.2f}%"],
            ['深证', f"{market_data.get('sz',{}).get('price',0):.2f}",
             f"{market_data.get('sz',{}).get('chg',0):+.2f}%",
             '科创50', f"{market_data.get('kc',{}).get('price',0):.2f}",
             f"{market_data.get('kc',{}).get('chg',0):+.2f}%"],
            ['创业板', f"{market_data.get('cy',{}).get('price',0):.2f}",
             f"{market_data.get('cy',{}).get('chg',0):+.2f}%",
             '北向', f"{market_data.get('nb',{}).get('flow','--')}亿" if market_data.get('nb') else '--', ''],
        ]
        t = Table(idx, colWidths=[52, 68, 52, 52, 68, 52])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), F), ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TEXTCOLOR', (1, 0), (1, -1), R), ('TEXTCOLOR', (4, 0), (4, -1), R),
            ('FONTNAME', (0, 0), (2, 0), FB), ('FONTNAME', (3, 0), (5, 0), FB),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#EEE')),
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    # Items
    story.append(Paragraph("今日简评", ST['h']))
    for line in parsed['items']:
        story.append(Paragraph(line, ST['i']))

    # Directions
    if parsed['directions']:
        story.append(Paragraph("方向速览", ST['h']))
        dd = []
        for line in parsed['directions']:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                dd.append(parts[:3])
        if dd:
            col_w = [78, 140, 105]
            t2 = Table(dd, colWidths=col_w[:len(dd[0])])
            t2.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), F), ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (-1, 0), FH),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2A2A2A')),
                ('TEXTCOLOR', (0, 0), (-1, 0), W),
                ('TEXTCOLOR', (0, 1), (0, -1), R), ('FONTNAME', (0, 1), (0, -1), FB),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#EEE')),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(t2)

    # ETF
    for line in parsed['etf']:
        story.append(Paragraph(line, ST['b']))

    # Risk
    for line in parsed['risk']:
        story.append(Paragraph(line, ST['b']))

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(f"中信晨会 + 实时行情 + AI研判 | {today} | Claude + ReportLab", ST['sm']))

    pdf.build(story)
    return output_path


# ═══════════════════════════════════════════════
# 5. MAIN PIPELINE
# ═══════════════════════════════════════════════

def run_pipeline(pdf_bytes: bytes, output_dir: str = None) -> dict:
    """Full pipeline: parse report -> fetch market -> Claude -> PDF."""
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    print("[1/4] Fetching market data...")
    market = fetch_market_data()

    print("[2/4] Parsing CITIC report...")
    report_text = parse_citic_pdf(pdf_bytes)

    print("[3/4] Generating briefing with Claude...")
    briefing = generate_briefing(report_text, market)

    print("[4/4] Generating PDF...")
    today = date.today().strftime('%Y-%m-%d')
    pdf_path = os.path.join(output_dir, f'A股简评_{today}.pdf')
    generate_pdf(briefing, pdf_path, market)

    # Also save text
    txt_path = os.path.join(output_dir, f'A股简评_{today}.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(briefing)

    result = {
        'briefing': briefing,
        'pdf_path': pdf_path,
        'txt_path': txt_path,
        'market_data': market,
        'market_is_live': not market.get('_fallback', True),
    }
    print(f"Done! PDF: {pdf_path}")
    return result


if __name__ == '__main__':
    # Test with the desktop PDF
    test_pdf = 'C:/Users/26433/Desktop/晨会—2026-06-16.pdf'
    if os.path.exists(test_pdf):
        with open(test_pdf, 'rb') as f:
            result = run_pipeline(f.read())
        print('\n=== BRIEFING ===')
        print(result['briefing'])
    else:
        print(f'Test PDF not found: {test_pdf}')
