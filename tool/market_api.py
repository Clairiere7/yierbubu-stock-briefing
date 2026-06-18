#!/usr/bin/env python3
"""
akshare 行情 FastAPI 微服务
启动: uvicorn tool.market_api:app --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import akshare as ak

app = FastAPI(title="A股行情 API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/market")
def market():
    """拉取A股五大指数 + 北向资金"""

    result = {"indices": {}, "northbound": None, "status": "ok"}

    # ── Sina 指数现货 ──
    try:
        df = ak.stock_zh_index_spot_sina()
        targets = {
            "上证指数": "sh", "深证成指": "sz", "创业板指": "cy",
            "科创50": "kc", "沪深300": "hs",
        }
        for _, r in df.iterrows():
            n = r["名称"]
            for k, v in targets.items():
                if k in n:
                    result["indices"][v] = {
                        "name": n,
                        "price": round(float(r["最新价"]), 2),
                        "chg_pct": round(float(r["涨跌幅"]), 2),
                        "volume": r.get("成交量", ""),
                    }
    except Exception as e:
        # fallback: 东方财富
        try:
            df = ak.stock_zh_index_spot_em()
            targets = {
                "上证指数": "sh", "深证成指": "sz", "创业板指": "cy",
                "科创50": "kc", "沪深300": "hs",
            }
            for _, r in df.iterrows():
                n = r["名称"]
                for k, v in targets.items():
                    if k in n:
                        result["indices"][v] = {
                            "name": n,
                            "price": float(r["最新价"]),
                            "chg_pct": float(r["涨跌幅"]),
                            "volume": str(r.get("成交额", "")),
                        }
        except Exception as e2:
            result["status"] = "fallback_failed"
            result["error"] = str(e2)

    # ── 北向资金 ──
    try:
        nb = ak.stock_hsgt_north_net_flow_in_em()
        if not nb.empty:
            latest = nb.iloc[-1]
            result["northbound"] = round(float(latest.get("净流入", 0)), 2)
    except:
        result["northbound"] = None

    return result


@app.get("/market/text")
def market_text():
    """返回纯文本格式，直接塞进 LLM prompt"""
    data = market()
    if data["status"] != "ok":
        return "⚠️ 行情数据获取失败"

    lines = []
    for k in ["sh", "sz", "cy", "kc", "hs"]:
        if k in data["indices"]:
            d = data["indices"][k]
            lines.append(f"{d['name']}: {d['price']} ({d['chg_pct']:+.2f}%)")

    nb = data.get("northbound")
    if nb is not None:
        lines.append(f"北向资金净流入: {nb}亿")

    return "\n".join(lines)


@app.get("/health")
def health():
    return {"status": "ok", "service": "akshare-market-api"}
