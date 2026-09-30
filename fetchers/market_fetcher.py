import yfinance as yf
from config import MARKET_TICKERS


def fetch_market_data() -> dict | None:
    """
    抓取國際市場數據
    包含美股、半導體、美元、VIX、原油、上證

    Returns:
        dict: 國際市場數據，失敗時回傳 None
    """
    try:
        result = {}

        for key, ticker_code in MARKET_TICKERS.items():
            try:
                ticker = yf.Ticker(ticker_code)
                hist = ticker.history(period="2d")

                if hist.empty or len(hist) < 2:
                    print(f"[Market Fetcher] {ticker_code} 數據不足")
                    result[key] = None
                    continue

                # 取最後兩天計算漲跌幅
                close_today = float(hist["Close"].iloc[-1])
                close_prev  = float(hist["Close"].iloc[-2])
                change_pct  = round((close_today - close_prev) / close_prev * 100, 2)

                result[key] = {
                    "price":  round(close_today, 2),
                    "change": change_pct,
                }

            except Exception as e:
                print(f"[Market Fetcher] 抓取 {ticker_code} 失敗：{e}")
                result[key] = None

        return result

    except Exception as e:
        print(f"[Market Fetcher] 整體執行失敗：{e}")
        return None


def get_vix_status(vix_value: float) -> str:
    """
    將 VIX 數值轉換為人類可讀的狀態描述

    Args:
        vix_value: VIX 指數數值

    Returns:
        str: 狀態描述
    """
    if vix_value >= 30:
        return "極度恐慌"
    elif vix_value >= 20:
        return "市場緊張"
    elif vix_value >= 15:
        return "略有波動"
    else:
        return "市場平穩"


def get_dxy_trend(dxy_change: float) -> str:
    """
    將美元指數變動轉換為趨勢描述

    Args:
        dxy_change: 美元指數漲跌幅（%）

    Returns:
        str: 趨勢描述
    """
    if dxy_change >= 0.5:
        return "明顯走強（外資撤出壓力）"
    elif dxy_change >= 0.1:
        return "小幅走強"
    elif dxy_change <= -0.5:
        return "明顯走弱（有利外資流入）"
    elif dxy_change <= -0.1:
        return "小幅走弱"
    else:
        return "持平"


def format_market_for_prompt(market_data: dict) -> str:
    """
    將國際市場數據格式化為 Gemini Prompt 用的純文字

    Args:
        market_data: fetch_market_data() 的回傳值

    Returns:
        str: 格式化後的文字
    """
    def fmt(key, label, unit="%"):
        item = market_data.get(key)
        if item is None:
            return f"{label}：資料不足"
        change = item["change"]
        price  = item["price"]
        sign   = "+" if change >= 0 else ""
        if unit == "%":
            return f"{label}：{sign}{change}%"
        else:
            return f"{label}：{price}（{sign}{change}%）"

    # VIX 狀態
    vix_item = market_data.get("vix")
    vix_str = "資料不足"
    if vix_item:
        vix_val = vix_item["price"]
        vix_str = f"{vix_val}（{get_vix_status(vix_val)}）"

    # 美元指數趨勢
    dxy_item = market_data.get("dxy")
    dxy_str = "資料不足"
    if dxy_item:
        dxy_str = f"{dxy_item['price']}（{get_dxy_trend(dxy_item['change'])}）"

    # 原油
    oil_item = market_data.get("oil")
    oil_str = "資料不足"
    if oil_item:
        sign = "+" if oil_item["change"] >= 0 else ""
        oil_str = f"{oil_item['price']} 美元（{sign}{oil_item['change']}%）"

    # 上證
    sh_item = market_data.get("shanghai")
    sh_str = "資料不足"
    if sh_item:
        sign = "+" if sh_item["change"] >= 0 else ""
        sh_str = f"{sign}{sh_item['change']}%"

    text = f"""
【國際市場（昨夜收盤）】
{fmt('spy',  '標普500 SPY')}｜{fmt('qqq', '納斯達克 QQQ')}｜{fmt('soxx', '費城半導體 SOXX')}
VIX 恐慌指數：{vix_str}
美元指數 DXY：{dxy_str}
WTI 原油：{oil_str}
上證指數：{sh_str}
""".strip()

    return text


if __name__ == "__main__":
    print("測試抓取國際市場數據...")
    data = fetch_market_data()
    if data:
        for key, val in data.items():
            print(f"{key}: {val}")
        print("\n=== Prompt 格式預覽 ===")
        print(format_market_for_prompt(data))
