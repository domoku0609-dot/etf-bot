import os

# ===========================
# API 金鑰（從環境變數讀取）
# ===========================

# Gemini 支援多組 Key 輪轉（至少填一組，最多可填無限組）
# 申請方式：每個 Google 帳號到 aistudio.google.com 各取一組免費 Key
GEMINI_API_KEYS = [
    os.environ.get("GEMINI_API_KEY_1", ""),
    os.environ.get("GEMINI_API_KEY_2", ""),
    os.environ.get("GEMINI_API_KEY_3", ""),
]

# SMTP 郵件通知設定（由環境變數提供，不在程式中保存憑證）
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = os.environ.get("SMTP_PORT", "")
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "")
SMTP_TO = os.environ.get("SMTP_TO", "")
SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

# ===========================
# 分析參數
# ===========================
CONFIDENCE_THRESHOLD = 7    # Gemini 信心指數門檻（>=7 才推薦）
SENTIMENT_THRESHOLD = 40    # PTT 正面情緒門檻（% ，低於此值跳過）
MIN_PTT_MENTIONS = 5        # PTT 最低提及次數（低於此值不算熱門）
TOP_ETF_COUNT = 5           # 取 PTT 討論前幾名

# ===========================
# 地緣政治風險設定
# ===========================
GEO_RISK_HIGH = "高"        # 高風險時停止分析
GEO_RISK_MID = "中"
GEO_RISK_LOW = "低"

# ===========================
# 台灣主要 ETF 清單
# 用於 PTT 爬蟲比對提及次數
# ===========================
TAIWAN_ETF_LIST = [
    "0050",   # 元大台灣50
    "0056",   # 元大高股息
    "00878",  # 國泰永續高股息
    "00929",  # 復華台灣科技優息
    "00919",  # 群益台灣精選高息
    "006208", # 富邦台灣50
    "00713",  # 元大台灣高息低波
    "00692",  # 富邦公司治理
    "00757",  # 統一FANG+
    "00850",  # 元大臺灣ESG永續
    "00881",  # 國泰台灣5G+
    "00896",  # 中信綠能及電動車
    "00900",  # 富邦特選高股息30
    "00905",  # FT臺灣Smart
    "00915",  # 凱基優選高股息30
    "00918",  # 大華優利高填息30
    "00922",  # 國泰台灣領袖50
    "00934",  # 中信成長高股息
    "00939",  # 統一台灣高息動能
    "00940",  # 元大台灣價值高息
]

# ===========================
# 國際市場標的（yfinance代碼）
# ===========================
MARKET_TICKERS = {
    "spy":      "SPY",        # 標普500 ETF
    "qqq":      "QQQ",        # 納斯達克 ETF
    "soxx":     "SOXX",       # 費城半導體 ETF
    "dxy":      "DX-Y.NYB",   # 美元指數
    "vix":      "^VIX",       # 恐慌指數
    "oil":      "CL=F",       # WTI 原油
    "shanghai": "000001.SS",  # 上證指數
}

# ===========================
# Google News RSS 關鍵字
# ===========================
NEWS_KEYWORDS = {
    "geopolitical": [
        "台海",
        "Taiwan Strait",
        "兩岸",
        "North Korea missile",
        "Ukraine war",
        "中東衝突",
        "Israel Gaza",
    ],
    "fed": [
        "Fed rate decision",
        "Federal Reserve",
        "聯準會",
        "Powell",
    ],
    "semiconductor": [
        "semiconductor Taiwan",
        "台積電",
        "TSMC",
        "Nvidia earnings",
        "晶片出口",
    ],
}

# 每個關鍵字最多抓幾則新聞標題
NEWS_MAX_PER_KEYWORD = 3

# ===========================
# PTT 設定
# ===========================
PTT_BOARD = "Stock"                              # PTT 看板名稱
PTT_BASE_URL = "https://www.ptt.cc"             # PTT 網址
PTT_MAX_PAGES = 5                               # 最多爬幾頁（避免太慢）
PTT_REQUEST_DELAY = 1.5                         # 每次請求間隔秒數（避免被封）

# ===========================
# Gemini 設定
# ===========================
GEMINI_MODEL       = "gemini-3.8-flash"   # 使用的模型
GEMINI_MAX_TOKENS  = 1000                 # 最大回覆 token 數
GEMINI_TEMPERATURE = 0.3                  # 低溫度確保回覆穩定

# 穩健呼叫參數
GEMINI_TIMEOUT          = 30    # 單次呼叫最長等待秒數
GEMINI_MAX_RETRIES      = 3     # 最多重試次數
GEMINI_RETRY_BASE_DELAY = 2     # 指數退避基礎秒數（2, 4, 8 秒）

# ===========================
# ===========================
# 執行時間（供本地測試用，GitHub Actions 用 cron 控制）
# ===========================
RUN_HOUR = 6    # 台灣時間早上6點
