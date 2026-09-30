import feedparser
import time
from datetime import datetime, timedelta, timezone
from config import NEWS_KEYWORDS, NEWS_MAX_PER_KEYWORD


def fetch_news() -> dict:
    """
    從 Google News RSS 抓取過去24小時的國際重要新聞標題
    涵蓋地緣政治、Fed動態、半導體產業

    Returns:
        dict: {
            "geopolitical": ["標題1", "標題2", ...],
            "fed":          ["標題1", ...],
            "semiconductor":["標題1", ...],
        }
    """
    result = {category: [] for category in NEWS_KEYWORDS}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    for category, keywords in NEWS_KEYWORDS.items():
        seen_titles = set()

        for keyword in keywords:
            try:
                headlines = fetch_rss(keyword, cutoff)
                for title in headlines:
                    # 去重複
                    if title not in seen_titles:
                        seen_titles.add(title)
                        result[category].append(title)
                        if len(result[category]) >= NEWS_MAX_PER_KEYWORD * len(keywords):
                            break

                time.sleep(0.5)

            except Exception as e:
                print(f"[News Scraper] 關鍵字「{keyword}」抓取失敗：{e}")
                continue

        print(f"[News Scraper] {category}：共 {len(result[category])} 則新聞")

    return result


def fetch_rss(keyword: str, cutoff: datetime) -> list[str]:
    """
    抓取單一關鍵字的 Google News RSS 結果

    Args:
        keyword: 搜尋關鍵字
        cutoff:  時間截止點（只取此時間之後的新聞）

    Returns:
        list[str]: 新聞標題列表
    """
    encoded = keyword.replace(" ", "+")
    url = (
        f"https://news.google.com/rss/search"
        f"?q={encoded}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    )

    feed = feedparser.parse(url)
    titles = []

    for entry in feed.entries[:NEWS_MAX_PER_KEYWORD * 2]:
        # 解析發布時間
        published = entry.get("published_parsed")
        if published:
            pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
            if pub_dt < cutoff:
                continue  # 超過24小時的跳過

        title = entry.get("title", "").strip()

        # 清理 Google News 標題格式（通常是「標題 - 媒體名稱」）
        if " - " in title:
            title = title.rsplit(" - ", 1)[0].strip()

        if title:
            titles.append(title)

    return titles[:NEWS_MAX_PER_KEYWORD]


def format_news_for_prompt(news_data: dict) -> str:
    """
    將新聞數據格式化為 Gemini Prompt 用的純文字

    Args:
        news_data: fetch_news() 的回傳值

    Returns:
        str: 格式化後的文字
    """
    sections = []

    label_map = {
        "geopolitical": "地緣政治",
        "fed":          "Fed / 貨幣政策",
        "semiconductor": "半導體 / 科技",
    }

    for category, label in label_map.items():
        headlines = news_data.get(category, [])
        if headlines:
            lines = "\n".join(f"・{h}" for h in headlines)
            sections.append(f"[{label}]\n{lines}")
        else:
            sections.append(f"[{label}]\n・今日無重要新聞")

    return "\n\n".join(sections)


def assess_geopolitical_risk(news_data: dict) -> dict:
    """
    根據新聞標題初步評估地緣政治風險等級
    高風險關鍵字出現時直接標記，交由 Gemini 最終裁定

    Args:
        news_data: fetch_news() 的回傳值

    Returns:
        dict: {
            "level":  "低" / "中" / "高",
            "reason": "觸發原因說明"
        }
    """
    # 高風險觸發詞
    high_risk_keywords = [
        "戰爭", "開戰", "軍事衝突", "飛彈攻擊", "空襲",
        "台海封鎖", "台灣海峽衝突", "核武", "nuclear",
        "invasion", "military strike", "war declared",
        "全面制裁", "金融制裁", "SWIFT",
    ]

    # 中風險觸發詞
    mid_risk_keywords = [
        "軍演", "緊張升溫", "警告", "制裁",
        "tensions", "warning", "sanctions",
        "試射", "missile test", "провокация",
        "貿易戰", "trade war", "關稅",
    ]

    all_headlines = []
    for headlines in news_data.values():
        all_headlines.extend(headlines)

    combined = " ".join(all_headlines).lower()

    # 逐一檢查高風險詞
    for kw in high_risk_keywords:
        if kw.lower() in combined:
            return {
                "level":  "高",
                "reason": f"偵測到高風險關鍵字：「{kw}」",
            }

    # 逐一檢查中風險詞
    triggered_mid = []
    for kw in mid_risk_keywords:
        if kw.lower() in combined:
            triggered_mid.append(kw)

    if len(triggered_mid) >= 2:
        return {
            "level":  "中",
            "reason": f"偵測到多個中風險關鍵字：{', '.join(triggered_mid[:3])}",
        }
    elif len(triggered_mid) == 1:
        return {
            "level":  "中",
            "reason": f"偵測到中風險關鍵字：「{triggered_mid[0]}」",
        }

    return {
        "level":  "低",
        "reason": "今日無重大地緣政治風險訊號",
    }


if __name__ == "__main__":
    print("測試抓取 Google News RSS...")
    news = fetch_news()

    print("\n=== 各類新聞數量 ===")
    for category, headlines in news.items():
        print(f"{category}：{len(headlines)} 則")
        for h in headlines:
            print(f"  - {h}")

    print("\n=== 地緣政治風險評估 ===")
    risk = assess_geopolitical_risk(news)
    print(f"風險等級：{risk['level']}")
    print(f"原因：{risk['reason']}")

    print("\n=== Prompt 格式預覽 ===")
    print(format_news_for_prompt(news))
