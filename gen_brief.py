#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A股简评 — 极简专业版"""
import sys,os
sys.stdout.reconfigure(encoding='utf-8')

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER,TA_LEFT
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

for p,n in [('C:/Windows/Fonts/simhei.ttf','Hei'),('C:/Windows/Fonts/msyh.ttc','YH'),('C:/Windows/Fonts/msyhbd.ttc','YHB')]:
    try:pdfmetrics.registerFont(TTFont(n,p))
    except:pass
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
F ='YH' if 'YH' in pdfmetrics._fonts else 'STSong-Light'
FH='Hei' if 'Hei' in pdfmetrics._fonts else 'STSong-Light'
FB='YHB' if 'YHB' in pdfmetrics._fonts else F

R,H,G,L,W=colors.HexColor('#CC3333'),colors.HexColor('#222'),colors.HexColor('#888'),colors.HexColor('#AAA'),colors.white
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'A股简评_2026-06-16.pdf')

pdf=SimpleDocTemplate(OUT,pagesize=A4,rightMargin=22*mm,leftMargin=22*mm,topMargin=16*mm,bottomMargin=14*mm)

ST={
    't':ParagraphStyle('T',fontName=FH,fontSize=18,leading=24,textColor=R,spaceAfter=4,alignment=TA_CENTER),
    's':ParagraphStyle('S',fontName=F,fontSize=9,leading=12,textColor=G,alignment=TA_CENTER,spaceAfter=16),
    'st':ParagraphStyle('ST',fontName=FH,fontSize=12,leading=16,textColor=R,spaceBefore=8,spaceAfter=6),
    'h':ParagraphStyle('H',fontName=FH,fontSize=11,leading=14,textColor=H,spaceBefore=12,spaceAfter=4),
    'i':ParagraphStyle('I',fontName=F,fontSize=9.5,leading=20,textColor=H,leftIndent=10,spaceAfter=4),
    'b':ParagraphStyle('B',fontName=F,fontSize=9.5,leading=16,textColor=H,spaceAfter=4),
    'sm':ParagraphStyle('SM',fontName=F,fontSize=7.5,leading=11,textColor=L,alignment=TA_CENTER),
}

story=[]

story.append(Paragraph("A股市场简评",ST['t']))
story.append(Paragraph("2026-06-16 周二 | 中信晨会 + 实时行情 + AI研判",ST['s']))

# ── 行情 ──
idx=[
    ['上证','4,098.85','+0.06%','沪深300','4,898.14','+0.13%'],
    ['深证','15,712.64','+1.17%','科创50','1,756.90','+0.49%'],
    ['创业板','4,116.36','+2.05%','昨成交额','3.03万亿','—'],
]
t=Table(idx,colWidths=[52,72,54,52,64,54])
t.setStyle(TableStyle([
    ('FONTNAME',(0,0),(-1,-1),F),('FONTSIZE',(0,0),(-1,-1),9),('ALIGN',(0,0),(-1,-1),'CENTER'),
    ('TEXTCOLOR',(1,0),(1,-1),R),('TEXTCOLOR',(4,0),(4,-1),R),
    ('FONTNAME',(0,0),(2,0),FB),('FONTNAME',(3,0),(5,0),FB),
    ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#EEE')),
    ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
]))
story.append(t)

# ── 简评 ──
story.append(Paragraph("今日简评",ST['h']))
items=[
    "1. 双创指数续涨，创业板+2.05%报4116，科创50报1757。科技成长风格占优，市场风险偏好回升。",
    "2. 半日成交1.95万亿，量能小幅萎缩。资金集中攻击AI硬件端——PCB、光通信、MLCC多环节涨价。中芯国际(688981)、立讯精密(002475)受益。",
    "3. 银行、煤炭继续回调，高股息品种资金流向科技进攻型板块。宁德时代(300750)、比亚迪(002594)获回流。",
    "4. 伊朗官宣美伊停战，油价-4.9%至$80.75。纳指+3%、日经+5%，外部扰动缓和，A股情绪提振。",
    "5. 五部门印发《节能降碳三年行动》，九大行业2028前强制达标。中央补贴20%+电价倒逼，供给侧收缩利好钢铁/电解铝龙头。",
    "6. 裘翔《风格再平衡》：AI从算力向能源+材料扩散。增配券商——中信证券(600030)受益于3万亿量能。",
    "7. 融资盘连续加仓科技方向，短线资金活跃度维持高位。隆基绿能(601012)等新能源区间关注。",
]
for t_i in items:
    story.append(Paragraph(t_i,ST['i']))

story.append(Spacer(1,4*mm))

# ── 速览 ──
story.append(Paragraph("方向与标的",ST['h']))
dd=[
    ['AI算力硬件链','中芯国际(688981) 立讯精密(002475)','涨价+订单放量'],
    ['节能降碳龙头','钢铁/电解铝头部','三年行动→供给收缩'],
    ['油运','招商轮船 中远海能(H/A)','海峡恢复→抢运→补库'],
    ['券商','中信证券(600030)','量能+风格再平衡'],
    ['新能源','宁德时代(300750) 隆基绿能(601012)','资金回流'],
]
t2=Table(dd,colWidths=[82,128,95])
t2.setStyle(TableStyle([
    ('FONTNAME',(0,0),(-1,-1),F),('FONTSIZE',(0,0),(-1,-1),9),
    ('FONTNAME',(0,0),(-1,0),FH),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#2A2A2A')),
    ('TEXTCOLOR',(0,0),(-1,0),W),('TEXTCOLOR',(0,1),(0,-1),R),
    ('FONTNAME',(0,1),(0,-1),FB),
    ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#EEE')),
    ('ALIGN',(0,0),(-1,0),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
    ('LEFTPADDING',(0,0),(-1,-1),6),
]))
story.append(t2)

story.append(Spacer(1,4*mm))
story.append(Paragraph("ETF：科创50(588000)、创业板(159915)、恒科(159740)。","以上AI研判交流，仅供参考。", ST['b']))
story.append(Spacer(1,8*mm))
story.append(Paragraph("中信晨会2026-06-16 | 东方财富 · 华尔街见闻 · 财联社 | Claude + ReportLab",ST['sm']))

pdf.build(story)
print('PDF: '+OUT)
