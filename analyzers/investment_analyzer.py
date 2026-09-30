import json
import time
from config import CONFIDENCE_THRESHOLD
from gemini_client import call_gemini
from etf_fetcher import format_etf_for_prompt
from market_fetcher import format_market_for_prompt
from sentiment_analyzer import format_sentiment_for_prompt, parse_json_response
from news_scraper import format_news_for_prompt

# 投資分析 System Prompt
INVESTMENT_SYSTEM_PROMPT = """
你是一位經驗豐富的台灣 ETF 投資顧問，融合以下兩位大師的投資哲學：

1. 巴菲特（Warren Buffett）：
   - 長期持有優質資產
   - 在別人恐慌時貪婪，在別人貪婪時恐慌
   - 重視內在價值與安全邊際

2. 霍華馬克斯（Howard Marks）：
   - 重視市場週期位置
   - 風險意識優先於報酬追求
   - 在週期低點積極布局，高點保守應對

分析時請同時考量：
- 技術面：均線、RSI、KD、布林通道
- 基本面：折溢價率、外資動向、殖利率
- 總體面：國際市場、地緣政治、市場情緒

請只回傳 JSON，不要有任何其他文字或 markdown 格式。
""".strip()


def analyze_investment(
    etf_data: dict,
    market_data: dict,
    sentiment: dict,
    news_data: dict,
) -> dict | None:
    """
    整合所有數據，讓 Gemini 給出 ETF 投資建議

    Args:
        etf_data:    fetch_etf_data() 的回傳值
        market_data: fetch_market_data() 的回傳值
        sentiment:   analyze_sentiment() 的回傳值
        news_data:   fetch_news() 的回傳值

    Returns:
        dict: 投資分析結果，信心指數未達門檻時回傳 None
        {
            "code":               "0050",
            "name":               "元大台灣50",
            "geopolitical_risk":  "低",
            "geopolitical_reason":"...",
            "market_cycle":       "中性",
            "valuation":          "合理",
            "recommendation":     "買入",
            "reason":             "...",
            "confidence":         8,
            "price":              201.3,
            "change_1d":          1.41,
        }
    """
    etf_code = etf_data["code"]
    etf_name = etf_data["name"]

    # 組裝 Prompt 各區塊
    news_text      = format_news_for_prompt(news_data)
    market_text    = format_market_for_prompt(market_data)
    etf_text       = format_etf_for_prompt(etf_data)
    sentiment_text = format_sentiment_for_prompt(etf_code, sentiment)

    prompt = f"""
請分析以下台灣 ETF 數據，給出今日投資建議。

===== {etf_name}（{etf_code}）=====

【國際新聞摘要】
{news_text}

{market_text}

{etf_text}

{sentiment_text}

===== 回覆格式（只回傳 JSON，不要其他文字）=====
{{
  "geopolitical_risk":   "低/中/高",
  "geopolitical_reason": "地緣政治風險判斷理由（30字內）",
  "market_cycle":        "恐慌/中性/貪婪",
  "valuation":           "低估/合理/高估",
  "recommendation":      "買入/觀望/不買",
  "reason":              "投資建議理由（100字內，需提及關鍵指標）",
  "confidence":          評估信心指數（整數 1-10）
}}

評分標準：
- 信心 8-10：多項指標強烈共振，強力推薦
- 信心 7：指標偏正面，值得關注
- 信心 5-6：訊號混雜，建議觀望
- 信心 1-4：指標偏負面，不建議進場
""".strip()

    try:
        raw = call_gemini([
            {"role": "user",  "parts": [INVESTMENT_SYSTEM_PROMPT]},
            {"role": "model", "parts": ["了解，我會以巴菲特與霍華馬克斯的投資哲學分析，只回傳 JSON 格式結果。"]},
            {"role": "user",  "parts": [prompt]},
        ])

        if raw is None:
            print(f"[Investment] {etf_code} Gemini 無回應（已達重試上限）")
            return None

        result = parse_json_response(raw)
        if result is None:
            print(f"[Investment] {etf_code} JSON 解析失敗")
            return None

        # 驗證必要欄位
        required_keys = [
            "geopolitical_risk", "geopolitical_reason",
            "market_cycle", "valuation",
            "recommendation", "reason", "confidence",
        ]
        for key in required_keys:
            if key not in result:
                print(f"[Investment] {etf_code} 缺少欄位：{key}")
                return None

        confidence = int(result.get("confidence", 0))

        # 信心指數門檻檢查
        if confidence < CONFIDENCE_THRESHOLD:
            print(
                f"[Investment] {etf_code} 信心指數 {confidence} "
                f"未達門檻 {CONFIDENCE_THRESHOLD}，跳過"
            )
            return None

        # 補充 ETF 基本資訊，方便後續通知使用
        result["code"]      = etf_code
        result["name"]      = etf_name
        result["price"]     = etf_data["price"]["close"]
        result["change_1d"] = etf_data["price"]["change_1d"]
        result["confidence"] = confidence

        print(
            f"[Investment] {etf_code} 分析完成｜"
            f"建議：{result['recommendation']}｜"
            f"信心：{confidence}/10"
        )
        return result

    except Exception as e:
        print(f"[Investment] {etf_code} Gemini 呼叫失敗：{e}")
        return None


def run_batch_analysis(
    top_etfs: list[str],
    etf_data_map: dict,
    market_data: dict,
    sentiment_map: dict,
    news_data: dict,
    delay: float = 2.0,
) -> list[dict]:
    """
    批次分析多檔 ETF，每次間隔 delay 秒避免 API 頻率限制

    Args:
        top_etfs:     ETF 代碼列表（PTT 討論前5名）
        etf_data_map: {etf_code: etf_data} 的字典
        market_data:  國際市場數據
        sentiment_map:{etf_code: sentiment} 的字典
        news_data:    新聞數據
        delay:        每次 API 呼叫間隔秒數

    Returns:
        list[dict]: 通過信心門檻的推薦清單
    """
    recommendations = []

    for i, etf_code in enumerate(top_etfs):
        print(f"\n[Investment] 分析第 {i+1}/{len(top_etfs)} 檔：{etf_code}")

        etf_data  = etf_data_map.get(etf_code)
        sentiment = sentiment_map.get(etf_code)

        if not etf_data:
            print(f"[Investment] {etf_code} 無 ETF 數據，跳過")
            continue

        if not sentiment:
            print(f"[Investment] {etf_code} 無情緒數據，跳過")
            continue

        result = analyze_investment(etf_data, market_data, sentiment, news_data)

        if result:
            recommendations.append(result)

        # API 呼叫間隔
        if i < len(top_etfs) - 1:
            time.sleep(delay)

    print(f"\n[Investment] 批次分析完成，共 {len(recommendations)} 檔通過篩選")
    return recommendations


if __name__ == "__main__":
    # 測試用假數據
    from etf_fetcher import fetch_etf_data
    from market_fetcher import fetch_market_data
    from news_scraper import fetch_news

    test_sentiment = {
        "positive_pct":    60,
        "negative_pct":    20,
        "neutral_pct":     20,
        "keywords":        ["外資買", "分批", "量增"],
        "sarcasm_detected": False,
        "overall_trend":   "偏樂觀",
        "7d_trend":        "持續上升",
    }

    print("測試投資分析（抓取真實數據）...")
    etf_data    = fetch_etf_data("0050")
    market_data = fetch_market_data()
    news_data   = fetch_news()

    if etf_data and market_data and news_data:
        result = analyze_investment(etf_data, market_data, test_sentiment, news_data)
        if result:
            print("\n=== 分析結果 ===")
            print(f"建議：{result['recommendation']}")
            print(f"信心：{result['confidence']}/10")
            print(f"理由：{result['reason']}")
            print(f"市場週期：{result['market_cycle']}")
            print(f"估值：{result['valuation']}")
        else:
            print("未通過信心門檻")
