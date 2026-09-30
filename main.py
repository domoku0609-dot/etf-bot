"""
台灣 ETF 智慧投資通知工具
每日早上 06:00 自動執行，分析台灣熱門 ETF，透過電子郵件發送分析結果。

執行流程：
  Step 1: 抓國際新聞 → 地緣政治風險評估
  Step 2: PTT 爬蟲 → 找出討論前5名 ETF
  Step 3: 抓國際市場數據
  Step 4: 逐檔情緒分析 + 投資分析
  Step 5: 發送 Email 通知
"""

import sys
import traceback
from datetime import datetime

from config import SENTIMENT_THRESHOLD

# 爬蟲
from scrapers.news_scraper import fetch_news, assess_geopolitical_risk, format_news_for_prompt
from scrapers.ptt_scraper import scrape_ptt, get_top_etfs, get_comments_for_etf

# 數據抓取
from fetchers.etf_fetcher import fetch_etf_data
from fetchers.market_fetcher import fetch_market_data

# 分析
from analyzers.sentiment_analyzer import analyze_sentiment
from analyzers.investment_analyzer import analyze_investment

# 通知
from notifiers.email_notifier import (
    send_recommendation,
    send_geo_risk_warning,
    send_no_recommendation,
    send_error_alert,
)


def log(msg: str) -> None:
    """帶時間戳的 log 輸出"""
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")


def main() -> None:
    log("========== ETF 分析工具啟動 ==========")
    start_time = datetime.now()

    # ----------------------------------------
    # Step 1: 抓國際新聞，評估地緣政治風險
    # ----------------------------------------
    log("Step 1｜抓取國際新聞...")
    try:
        news_data = fetch_news()
        geo_risk  = assess_geopolitical_risk(news_data)
        log(f"地緣政治風險：{geo_risk['level']}｜{geo_risk['reason']}")
    except Exception as e:
        log(f"新聞抓取失敗：{e}")
        send_error_alert(f"新聞抓取失敗：{e}")
        sys.exit(1)

    # 高風險直接停止，發送警示
    if geo_risk["level"] == "高":
        log("地緣政治風險過高，停止分析，發送警示通知")
        send_geo_risk_warning(geo_risk)
        log("========== 執行結束（風險中止）==========")
        return

    # ----------------------------------------
    # Step 2: PTT 爬蟲，找出討論前5名 ETF
    # ----------------------------------------
    log("Step 2｜爬取 PTT Stock 板...")
    try:
        ptt_data  = scrape_ptt()
        top_etfs  = get_top_etfs(ptt_data)
    except Exception as e:
        log(f"PTT 爬蟲失敗：{e}")
        send_error_alert(f"PTT 爬蟲失敗：{e}")
        sys.exit(1)

    if not top_etfs:
        log("PTT 今日無符合門檻的 ETF，發送無推薦通知")
        send_no_recommendation()
        log("========== 執行結束（無符合ETF）==========")
        return

    log(f"討論前 {len(top_etfs)} 名：{', '.join(top_etfs)}")

    # ----------------------------------------
    # Step 3: 抓國際市場數據
    # ----------------------------------------
    log("Step 3｜抓取國際市場數據...")
    try:
        market_data = fetch_market_data()
        if not market_data:
            raise ValueError("market_data 回傳空值")
        log("國際市場數據抓取完成")
    except Exception as e:
        log(f"國際市場數據抓取失敗：{e}")
        send_error_alert(f"國際市場數據抓取失敗：{e}")
        sys.exit(1)

    # ----------------------------------------
    # Step 4: 逐檔分析
    # ----------------------------------------
    log("Step 4｜開始逐檔分析...")
    recommendations = []

    for i, etf_code in enumerate(top_etfs):
        log(f"  [{i+1}/{len(top_etfs)}] 分析 {etf_code}...")

        # --- 4a. PTT 情緒分析 ---
        try:
            comments  = get_comments_for_etf(ptt_data, etf_code)
            sentiment = analyze_sentiment(etf_code, comments)
        except Exception as e:
            log(f"  {etf_code} 情緒分析失敗：{e}")
            continue

        # 情緒未達門檻 → 跳過（analyze_sentiment 已內部處理，回傳 None）
        if sentiment is None:
            log(f"  {etf_code} 情緒未達門檻，跳過")
            continue

        # --- 4b. 抓 ETF 詳細數據 ---
        try:
            etf_data = fetch_etf_data(etf_code)
        except Exception as e:
            log(f"  {etf_code} ETF數據抓取失敗：{e}")
            continue

        if etf_data is None:
            log(f"  {etf_code} 無法取得 ETF 數據，跳過")
            continue

        # --- 4c. Gemini 投資分析 ---
        try:
            result = analyze_investment(
                etf_data,
                market_data,
                sentiment,
                news_data,
            )
        except Exception as e:
            log(f"  {etf_code} 投資分析失敗：{e}")
            continue

        # 信心指數未達門檻 → 跳過（analyze_investment 已內部處理，回傳 None）
        if result is None:
            log(f"  {etf_code} 信心指數未達門檻，跳過")
            continue

        log(
            f"  {etf_code} ✅ 通過篩選｜"
            f"建議：{result['recommendation']}｜"
            f"信心：{result['confidence']}/10"
        )
        recommendations.append(result)

    log(f"逐檔分析完成，共 {len(recommendations)} 檔通過篩選")

    # ----------------------------------------
    # Step 5: 發送 Email 通知
    # ----------------------------------------
    log("Step 5｜發送 Email 通知...")
    try:
        if recommendations:
            send_recommendation(recommendations)
            log(f"推薦通知發送完成（{len(recommendations)} 檔）")
        else:
            send_no_recommendation()
            log("無推薦，發送觀望通知")
    except Exception as e:
        log(f"Email 通知發送失敗：{e}")
        send_error_alert(f"Email 通知發送失敗：{e}")

    # ----------------------------------------
    # 完成
    # ----------------------------------------
    elapsed = (datetime.now() - start_time).seconds
    log(f"========== 執行完成，耗時 {elapsed} 秒 ==========")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"[FATAL] 未預期錯誤：\n{error_msg}")
        try:
            send_error_alert(f"未預期錯誤：{str(e)}")
        except Exception:
            pass
        sys.exit(1)
