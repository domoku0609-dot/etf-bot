import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime
from config import (
    PTT_BASE_URL,
    PTT_BOARD,
    PTT_MAX_PAGES,
    PTT_REQUEST_DELAY,
    TAIWAN_ETF_LIST,
    TOP_ETF_COUNT,
    MIN_PTT_MENTIONS,
)

# PTT 需要帶入 cookie 才能進入18禁版（Stock板不需要，但保留以防萬一）
PTT_COOKIES = {"over18": "1"}
HEADERS = {"User-Agent": "Mozilla/5.0"}


# ===========================
# 主要爬蟲函式
# ===========================

def scrape_ptt() -> dict:
    """
    爬取 PTT Stock 板當日文章標題與留言
    統計每檔 ETF 的提及次數與相關留言

    Returns:
        dict: {
            "0050": {
                "mention_count": 45,
                "comments": ["留言1", "留言2", ...]
            },
            ...
        }
        只回傳提及次數達 MIN_PTT_MENTIONS 的 ETF
    """
    print(f"[PTT Scraper] 開始爬取 PTT {PTT_BOARD} 板...")

    # 取得文章列表
    articles = fetch_article_list()
    print(f"[PTT Scraper] 共取得 {len(articles)} 篇文章連結")

    # 統計每檔 ETF 的提及次數與留言
    etf_data = {code: {"mention_count": 0, "comments": []} for code in TAIWAN_ETF_LIST}

    for i, article_url in enumerate(articles):
        try:
            title, comments = fetch_article_content(article_url)

            # 合併標題 + 留言一起比對
            all_text = [title] + comments

            for text in all_text:
                for etf_code in TAIWAN_ETF_LIST:
                    if etf_code in text:
                        etf_data[etf_code]["mention_count"] += 1
                        # 留言才加入 comments（標題不算留言）
                        if text != title and text not in etf_data[etf_code]["comments"]:
                            etf_data[etf_code]["comments"].append(text)

            time.sleep(PTT_REQUEST_DELAY)

        except Exception as e:
            print(f"[PTT Scraper] 文章解析失敗 {article_url}：{e}")
            continue

    # 過濾掉提及次數不足的 ETF
    filtered = {
        code: data
        for code, data in etf_data.items()
        if data["mention_count"] >= MIN_PTT_MENTIONS
    }

    print(f"[PTT Scraper] 共找到 {len(filtered)} 檔達門檻的 ETF")
    return filtered


def fetch_article_list() -> list[str]:
    """
    爬取 PTT Stock 板的文章列表（最新幾頁）

    Returns:
        list[str]: 文章的完整 URL 列表
    """
    article_urls = []
    board_url = f"{PTT_BASE_URL}/bbs/{PTT_BOARD}/index.html"

    for page in range(PTT_MAX_PAGES):
        try:
            resp = requests.get(
                board_url,
                cookies=PTT_COOKIES,
                headers=HEADERS,
                timeout=10,
            )
            soup = BeautifulSoup(resp.text, "html.parser")

            # 抓文章連結
            links = soup.select("div.r-ent div.title a")
            for link in links:
                href = link.get("href", "")
                if href:
                    article_urls.append(PTT_BASE_URL + href)

            # 找「上一頁」按鈕取得前一頁 URL
            prev_btn = soup.select_one("a.btn.wide:nth-of-type(2)")
            if prev_btn and prev_btn.get("href"):
                board_url = PTT_BASE_URL + prev_btn["href"]
            else:
                break

            time.sleep(PTT_REQUEST_DELAY)

        except Exception as e:
            print(f"[PTT Scraper] 爬取文章列表第 {page+1} 頁失敗：{e}")
            break

    return article_urls


def fetch_article_content(url: str) -> tuple[str, list[str]]:
    """
    爬取單篇 PTT 文章的標題與留言

    Args:
        url: 文章完整 URL

    Returns:
        tuple: (標題字串, 留言列表)
    """
    resp = requests.get(
        url,
        cookies=PTT_COOKIES,
        headers=HEADERS,
        timeout=10,
    )
    soup = BeautifulSoup(resp.text, "html.parser")

    # 標題
    title_tag = soup.select_one("span.article-meta-value:last-of-type")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # 留言（推文）
    comments = []
    for push in soup.select("div.push"):
        content_tag = push.select_one("span.push-content")
        if content_tag:
            comment = content_tag.get_text(strip=True).lstrip(": ")
            if comment:
                comments.append(comment)

    return title, comments


# ===========================
# 排序與篩選
# ===========================

def get_top_etfs(etf_data: dict) -> list[str]:
    """
    從爬蟲結果中取出討論度前 TOP_ETF_COUNT 名的 ETF 代碼

    Args:
        etf_data: scrape_ptt() 的回傳值

    Returns:
        list[str]: ETF 代碼列表，依討論度降序排列
    """
    sorted_etfs = sorted(
        etf_data.keys(),
        key=lambda code: etf_data[code]["mention_count"],
        reverse=True,
    )
    top = sorted_etfs[:TOP_ETF_COUNT]

    print(f"[PTT Scraper] 討論度前 {TOP_ETF_COUNT} 名：")
    for code in top:
        print(f"  {code}：{etf_data[code]['mention_count']} 次提及")

    return top


def get_comments_for_etf(etf_data: dict, etf_code: str) -> list[str]:
    """
    取得特定 ETF 的留言列表

    Args:
        etf_data: scrape_ptt() 的回傳值
        etf_code: ETF 代碼

    Returns:
        list[str]: 留言列表
    """
    return etf_data.get(etf_code, {}).get("comments", [])


def format_comments_for_prompt(comments: list[str], max_comments: int = 30) -> str:
    """
    將留言列表格式化為 Gemini Prompt 用的文字

    Args:
        comments:     留言列表
        max_comments: 最多傳入幾則留言（避免 token 過多）

    Returns:
        str: 格式化後的文字
    """
    if not comments:
        return "（今日無相關留言）"

    # 只取前 max_comments 則，避免 token 爆炸
    selected = comments[:max_comments]
    lines = [f"{i+1}. {c}" for i, c in enumerate(selected)]
    return "\n".join(lines)


# ===========================
# 測試
# ===========================

if __name__ == "__main__":
    print(f"測試爬取 PTT {PTT_BOARD} 板...")
    data = scrape_ptt()

    if data:
        top5 = get_top_etfs(data)
        print(f"\n前 {TOP_ETF_COUNT} 名 ETF：{top5}")

        # 預覽第一名的留言
        if top5:
            first = top5[0]
            comments = get_comments_for_etf(data, first)
            print(f"\n{first} 相關留言（共 {len(comments)} 則）：")
            print(format_comments_for_prompt(comments, max_comments=5))
    else:
        print("未找到符合條件的 ETF")
