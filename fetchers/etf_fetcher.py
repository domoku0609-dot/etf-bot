import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
from ta.trend import SMAIndicator
import requests
from bs4 import BeautifulSoup
import time

# ETF 中文名稱對照表
ETF_NAME_MAP = {
    "0050":   "元大台灣50",
    "0056":   "元大高股息",
    "00878":  "國泰永續高股息",
    "00929":  "復華台灣科技優息",
    "00919":  "群益台灣精選高息",
    "006208": "富邦台灣50",
    "00713":  "元大台灣高息低波",
    "00692":  "富邦公司治理",
    "00757":  "統一FANG+",
    "00850":  "元大臺灣ESG永續",
    "00881":  "國泰台灣5G+",
    "00896":  "中信綠能及電動車",
    "00900":  "富邦特選高股息30",
    "00905":  "FT臺灣Smart",
    "00915":  "凱基優選高股息30",
    "00918":  "大華優利高填息30",
    "00922":  "國泰台灣領袖50",
    "00934":  "中信成長高股息",
    "00939":  "統一台灣高息動能",
    "00940":  "元大台灣價值高息",
}


def fetch_etf_data(etf_code: str) -> dict | None:
    """
    抓取單一 ETF 的完整數據
    包含價格、技術指標、成交量、ETF專屬指標

    Args:
        etf_code: ETF 代碼，例如 "0050"

    Returns:
        dict: ETF 完整數據，失敗時回傳 None
    """
    try:
        ticker_code = f"{etf_code}.TW"
        ticker = yf.Ticker(ticker_code)

        # 抓取近一年歷史數據（計算技術指標需要足夠的歷史資料）
        hist = ticker.history(period="1y")

        if hist.empty:
            print(f"[ETF Fetcher] 無法取得 {etf_code} 的歷史數據")
            return None

        # ===========================
        # 價格數據
        # ===========================
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest

        close_today = round(float(latest["Close"]), 2)
        close_prev = round(float(prev["Close"]), 2)
        change_1d = round((close_today - close_prev) / close_prev * 100, 2)

        # 7日、30日漲跌幅
        close_7d_ago = round(float(hist.iloc[-7]["Close"]), 2) if len(hist) >= 7 else close_today
        close_30d_ago = round(float(hist.iloc[-30]["Close"]), 2) if len(hist) >= 30 else close_today
        close_1y_ago = round(float(hist.iloc[0]["Close"]), 2)

        change_7d = round((close_today - close_7d_ago) / close_7d_ago * 100, 2)
        change_30d = round((close_today - close_30d_ago) / close_30d_ago * 100, 2)
        change_1y = round((close_today - close_1y_ago) / close_1y_ago * 100, 2)

        # 52週高低點
        week52_high = round(float(hist["High"].max()), 2)
        week52_low = round(float(hist["Low"].min()), 2)
        dist_from_high = round((close_today - week52_high) / week52_high * 100, 2)
        dist_from_low = round((close_today - week52_low) / week52_low * 100, 2)

        # ===========================
        # 技術指標
        # ===========================
        closes = hist["Close"]

        # 均線
        ma20 = round(float(SMAIndicator(closes, window=20).sma_indicator().iloc[-1]), 2)
        ma60 = round(float(SMAIndicator(closes, window=60).sma_indicator().iloc[-1]), 2)

        # RSI
        rsi = round(float(RSIIndicator(closes, window=14).rsi().iloc[-1]), 2)

        # KD (Stochastic)
        stoch = StochasticOscillator(
            hist["High"], hist["Low"], closes, window=9, smooth_window=3
        )
        k_val = round(float(stoch.stoch().iloc[-1]), 2)
        d_val = round(float(stoch.stoch_signal().iloc[-1]), 2)

        # 布林通道
        bb = BollingerBands(closes, window=20, window_dev=2)
        bb_upper = float(bb.bollinger_hband().iloc[-1])
        bb_lower = float(bb.bollinger_lband().iloc[-1])
        bb_mid = float(bb.bollinger_mavg().iloc[-1])

        if close_today > bb_mid + (bb_upper - bb_mid) * 0.5:
            bollinger_position = "上軌附近"
        elif close_today > bb_mid:
            bollinger_position = "中軌偏上"
        elif close_today > bb_lower + (bb_mid - bb_lower) * 0.5:
            bollinger_position = "中軌偏下"
        else:
            bollinger_position = "下軌附近"

        # ===========================
        # 成交量
        # ===========================
        volumes = hist["Volume"]
        vol_today = int(latest["Volume"])
        avg_vol_5d = int(volumes.iloc[-5:].mean()) if len(volumes) >= 5 else vol_today
        avg_vol_30d = int(volumes.iloc[-30:].mean()) if len(volumes) >= 30 else vol_today
        vol_ratio_5d = round(vol_today / avg_vol_5d, 2) if avg_vol_5d > 0 else 1.0
        vol_ratio_30d = round(vol_today / avg_vol_30d, 2) if avg_vol_30d > 0 else 1.0

        # ===========================
        # ETF 專屬指標（證交所）
        # ===========================
        etf_specific = fetch_etf_specific(etf_code)

        # ===========================
        # 組合輸出
        # ===========================
        return {
            "code": etf_code,
            "name": ETF_NAME_MAP.get(etf_code, etf_code),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "price": {
                "open":       round(float(latest["Open"]), 2),
                "close":      close_today,
                "high":       round(float(latest["High"]), 2),
                "low":        round(float(latest["Low"]), 2),
                "change_1d":  change_1d,
                "change_7d":  change_7d,
                "change_30d": change_30d,
                "change_1y":  change_1y,
            },
            "technical": {
                "ma20":          ma20,
                "ma60":          ma60,
                "rsi":           rsi,
                "k":             k_val,
                "d":             d_val,
                "bollinger":     bollinger_position,
                "week52_high":   week52_high,
                "week52_low":    week52_low,
                "dist_from_high": dist_from_high,
                "dist_from_low":  dist_from_low,
            },
            "volume": {
                "today":     vol_today,
                "avg5d":     avg_vol_5d,
                "avg30d":    avg_vol_30d,
                "ratio5d":   vol_ratio_5d,
                "ratio30d":  vol_ratio_30d,
            },
            "etf_specific": etf_specific,
        }

    except Exception as e:
        print(f"[ETF Fetcher] 抓取 {etf_code} 失敗：{e}")
        return None


def fetch_etf_specific(etf_code: str) -> dict:
    """
    從證交所抓取 ETF 專屬指標
    包含折溢價率、外資買賣超、股息殖利率、除息日

    Args:
        etf_code: ETF 代碼

    Returns:
        dict: ETF 專屬指標
    """
    result = {
        "premium_discount":   0.0,
        "foreign_net_5d":     [],
        "dividend_yield":     0.0,
        "days_to_exdividend": None,
    }

    try:
        # --- 折溢價率（從證交所 ETF 申購買回專區） ---
        twse_url = (
            "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
            f"?ex_ch=tse_{etf_code}.tw&json=1&delay=0"
        )
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(twse_url, headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            msg_array = data.get("msgArray", [])
            if msg_array:
                item = msg_array[0]
                nav = float(item.get("nav", 0) or 0)       # 每單位淨值
                price = float(item.get("z", 0) or 0)       # 成交價
                if nav > 0 and price > 0:
                    premium = round((price - nav) / nav * 100, 2)
                    result["premium_discount"] = premium

        time.sleep(0.5)

        # --- 外資近5日買賣超（從證交所三大法人） ---
        today = datetime.now()
        foreign_net = []

        for i in range(5):
            date = today - timedelta(days=i + 1)
            date_str = date.strftime("%Y%m%d")
            url = (
                f"https://www.twse.com.tw/fund/T86"
                f"?response=json&date={date_str}&selectType=ALLBUT0999"
            )
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                d = r.json()
                rows = d.get("data", [])
                for row in rows:
                    # row[0] 是股票代碼
                    if row[0].strip() == etf_code:
                        # row[4] 是外資買賣超張數
                        net_str = row[4].replace(",", "").replace("+", "")
                        try:
                            foreign_net.append(int(net_str))
                        except ValueError:
                            foreign_net.append(0)
                        break
            time.sleep(0.5)

        result["foreign_net_5d"] = foreign_net

        # --- 股息殖利率 & 除息日（yfinance） ---
        ticker = yf.Ticker(f"{etf_code}.TW")
        info = ticker.info

        # 殖利率
        dividend_yield = info.get("trailingAnnualDividendYield", 0) or 0
        result["dividend_yield"] = round(float(dividend_yield) * 100, 2)

        # 下次除息日（若有）
        ex_div = info.get("exDividendDate")
        if ex_div:
            ex_div_dt = datetime.fromtimestamp(ex_div)
            days_left = (ex_div_dt - datetime.now()).days
            result["days_to_exdividend"] = days_left if days_left >= 0 else None

    except Exception as e:
        print(f"[ETF Fetcher] 抓取 {etf_code} ETF專屬指標失敗：{e}")

    return result


def format_etf_for_prompt(etf_data: dict) -> str:
    """
    將 ETF 數據格式化為 Gemini Prompt 用的純文字

    Args:
        etf_data: fetch_etf_data() 的回傳值

    Returns:
        str: 格式化後的文字
    """
    p = etf_data["price"]
    t = etf_data["technical"]
    v = etf_data["volume"]
    e = etf_data["etf_specific"]

    # 量比狀態說明
    def vol_status(ratio):
        if ratio >= 1.5:
            return "大幅放量"
        elif ratio >= 1.2:
            return "放量"
        elif ratio >= 0.8:
            return "正常"
        else:
            return "縮量"

    # VIX 狀態
    foreign_str = (
        "/".join(str(x) for x in e["foreign_net_5d"])
        if e["foreign_net_5d"]
        else "資料不足"
    )

    ex_div_str = (
        f"{e['days_to_exdividend']}天後"
        if e["days_to_exdividend"] is not None
        else "無資料"
    )

    text = f"""
【價格數據】
收盤：{p['close']}元｜今日：{p['change_1d']:+.2f}%
7日：{p['change_7d']:+.2f}%｜30日：{p['change_30d']:+.2f}%｜一年：{p['change_1y']:+.2f}%

【技術指標】
MA20：{t['ma20']}｜MA60：{t['ma60']}
RSI：{t['rsi']}｜KD：{t['k']}/{t['d']}
布林通道：{t['bollinger']}
量比(5日)：{v['ratio5d']}（{vol_status(v['ratio5d'])}）｜量比(30日)：{v['ratio30d']}（{vol_status(v['ratio30d'])}）

【位置判斷】
52週高：{t['week52_high']}｜52週低：{t['week52_low']}
距高點：{t['dist_from_high']:+.2f}%｜距低點：{t['dist_from_low']:+.2f}%

【ETF指標】
折溢價率：{e['premium_discount']:+.2f}%
外資近5日買賣超（張）：{foreign_str}
股息殖利率：{e['dividend_yield']}%｜距下次除息：{ex_div_str}
""".strip()

    return text


if __name__ == "__main__":
    # 測試用
    print("測試抓取 0050...")
    data = fetch_etf_data("0050")
    if data:
        print(f"名稱：{data['name']}")
        print(f"收盤價：{data['price']['close']}")
        print(f"RSI：{data['technical']['rsi']}")
        print(f"折溢價率：{data['etf_specific']['premium_discount']}%")
        print("\n=== Prompt 格式預覽 ===")
        print(format_etf_for_prompt(data))
