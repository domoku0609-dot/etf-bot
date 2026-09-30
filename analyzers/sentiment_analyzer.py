import json
import re
from config import SENTIMENT_THRESHOLD
from gemini_client import call_gemini
from ptt_scraper import format_comments_for_prompt

# 情緒分析的 System Prompt
SENTIMENT_SYSTEM_PROMPT = """
你是一位專業的台灣股市社群情緒分析師。
你擅長分析 PTT 股版的留言語氣，包含反諷、鄉民用語、股市俚語。
請只回傳 JSON，不要有任何其他文字或 markdown 格式。
""".strip()


def analyze_sentiment(etf_code: str, comments: list[str]) -> dict | None:
    """
    將 PTT 留言丟給 Gemini 分析情緒分佈

    Args:
        etf_code: ETF 代碼，例如 "0050"
        comments: PTT 留言列表

    Returns:
        dict: 情緒分析結果，正面情緒未達門檻時回傳 None
        {
            "positive_pct":  60,
            "negative_pct":  20,
            "neutral_pct":   20,
            "keywords":      ["外資買", "分批", "接刀"],
            "sarcasm_detected": True,
            "overall_trend": "偏樂觀但有疑慮",
            "7d_trend":      "持續上升"
        }
    """
    if not comments:
        print(f"[Sentiment] {etf_code} 無留言可分析")
        return None

    comments_text = format_comments_for_prompt(comments, max_comments=30)

    prompt = f"""
以下是 PTT 股版今日提到「{etf_code}」的留言：

{comments_text}

請分析這些留言的整體情緒，以 JSON 格式回覆（只回傳 JSON，不要其他文字）：
{{
  "positive_pct": 正面情緒佔比（整數，0-100）,
  "negative_pct": 負面情緒佔比（整數，0-100）,
  "neutral_pct": 中立情緒佔比（整數，0-100）,
  "keywords": ["最多5個熱門關鍵字"],
  "sarcasm_detected": 是否偵測到大量反諷語氣（true/false）,
  "overall_trend": "整體情緒一句話總結（20字內）",
  "7d_trend": "若能判斷趨勢方向請填寫，否則填「資料不足」"
}}

注意：
- 台灣股市常見反諷用語如「嗨」「噴」「好棒棒」「穩」可能帶有諷刺意味，請仔細判斷上下文
- positive + negative + neutral 加總應等於 100
""".strip()

    try:
        raw = call_gemini([
            {"role": "user",  "parts": [SENTIMENT_SYSTEM_PROMPT]},
            {"role": "model", "parts": ["了解，我會只回傳 JSON 格式的情緒分析結果。"]},
            {"role": "user",  "parts": [prompt]},
        ])

        if raw is None:
            print(f"[Sentiment] {etf_code} Gemini 無回應（已達重試上限）")
            return None

        result = parse_json_response(raw)
        if result is None:
            print(f"[Sentiment] {etf_code} JSON 解析失敗")
            return None

        # 驗證必要欄位
        required_keys = ["positive_pct", "negative_pct", "neutral_pct", "keywords",
                         "sarcasm_detected", "overall_trend", "7d_trend"]
        for key in required_keys:
            if key not in result:
                print(f"[Sentiment] {etf_code} 缺少欄位：{key}")
                return None

        # 正面情緒門檻檢查
        positive_pct = result.get("positive_pct", 0)
        if positive_pct < SENTIMENT_THRESHOLD:
            print(
                f"[Sentiment] {etf_code} 正面情緒 {positive_pct}% "
                f"未達門檻 {SENTIMENT_THRESHOLD}%，跳過"
            )
            return None

        print(
            f"[Sentiment] {etf_code} 分析完成｜"
            f"正面 {result['positive_pct']}%｜"
            f"負面 {result['negative_pct']}%｜"
            f"反諷：{result['sarcasm_detected']}"
        )
        return result

    except Exception as e:
        print(f"[Sentiment] {etf_code} Gemini 呼叫失敗：{e}")
        return None


def format_sentiment_for_prompt(etf_code: str, sentiment: dict) -> str:
    """
    將情緒分析結果格式化為投資分析 Prompt 用的文字

    Args:
        etf_code:  ETF 代碼
        sentiment: analyze_sentiment() 的回傳值

    Returns:
        str: 格式化後的文字
    """
    sarcasm_note = "（注意：偵測到反諷語氣，正面數據可能虛高）" if sentiment.get("sarcasm_detected") else ""
    keywords_str = "、".join(sentiment.get("keywords", []))

    text = f"""
【PTT 市場情緒】
正面：{sentiment['positive_pct']}%｜負面：{sentiment['negative_pct']}%｜中立：{sentiment['neutral_pct']}%{sarcasm_note}
整體趨勢：{sentiment['overall_trend']}
近期情緒走向：{sentiment['7d_trend']}
熱門關鍵字：{keywords_str if keywords_str else '無'}
""".strip()

    return text


def parse_json_response(text: str) -> dict | None:
    """
    從 Gemini 回覆中解析 JSON
    處理可能含有 markdown 代碼塊的情況

    Args:
        text: Gemini 回覆的原始文字

    Returns:
        dict: 解析後的 JSON，失敗回傳 None
    """
    try:
        # 先嘗試直接解析
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 嘗試從 markdown 代碼塊中提取 JSON
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 嘗試找第一個 { 到最後一個 } 之間的內容
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    return None


if __name__ == "__main__":
    # 測試用假資料
    test_comments = [
        "0050 這個價位可以開始分批了吧",
        "外資一直買，散戶跟不跟？",
        "又在噴了，小心接刀",
        "量這麼大，感覺要走了",
        "長期持有不用管這些",
        "嗨嗨嗨，好棒棒",
        "這波是真的假的，不太確定",
        "外資連三買，訊號蠻強的",
        "等拉回再買比較穩",
        "今天爆量，明天看看能不能守住",
    ]

    print("測試情緒分析...")
    result = analyze_sentiment("0050", test_comments)

    if result:
        print("\n=== 分析結果 ===")
        print(f"正面：{result['positive_pct']}%")
        print(f"負面：{result['negative_pct']}%")
        print(f"中立：{result['neutral_pct']}%")
        print(f"反諷：{result['sarcasm_detected']}")
        print(f"趨勢：{result['overall_trend']}")
        print(f"關鍵字：{result['keywords']}")

        print("\n=== Prompt 格式預覽 ===")
        print(format_sentiment_for_prompt("0050", result))
    else:
        print("分析失敗或未達情緒門檻")
