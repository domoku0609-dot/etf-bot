import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

from config import (
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_TO,
    SMTP_USERNAME,
    SMTP_USE_SSL,
    SMTP_USE_TLS,
)

# 數字序號 emoji
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]


def _send_email(subject: str, text: str) -> bool:
    """透過 SMTP 發送純文字郵件。"""
    recipients = [address.strip() for address in SMTP_TO.split(",") if address.strip()]
    if not all((SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM)) or not recipients:
        print("[Email] 設定不完整，請檢查 SMTP_HOST、SMTP_PORT、SMTP_USERNAME、SMTP_PASSWORD、SMTP_FROM 與 SMTP_TO")
        return False

    try:
        port = int(SMTP_PORT)
        if not 1 <= port <= 65535:
            raise ValueError("SMTP_PORT 必須介於 1 到 65535")
        if SMTP_USE_SSL == SMTP_USE_TLS:
            raise ValueError("SMTP_USE_SSL 與 SMTP_USE_TLS 必須且只能啟用一種")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = SMTP_FROM
        message["To"] = ", ".join(recipients)
        message.set_content(text)

        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(
                SMTP_HOST, port, timeout=10, context=ssl.create_default_context()
            ) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                refused = server.send_message(message)
        else:
            with smtplib.SMTP(SMTP_HOST, port, timeout=10) as server:
                if SMTP_USE_TLS:
                    server.starttls(context=ssl.create_default_context())
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                refused = server.send_message(message)

        if refused:
            print(f"[Email] 部分或全部收件者遭拒：{', '.join(refused)}")
            return False

        print("[Email] 郵件發送成功")
        return True
    except (OSError, ValueError, smtplib.SMTPException) as e:
        print(f"[Email] 發送失敗：{e}")
        return False


def send_recommendation(recommendations: list[dict]) -> bool:
    """發送有推薦標的的每日報告。"""
    today = datetime.now().strftime("%Y/%m/%d")
    count = len(recommendations)
    lines = [
        f"📊 ETF 分析報告 {today}",
        "分析時間：06:00｜建議於今日開盤評估",
        "",
        f"✅ 建議關注（{count} 檔）",
    ]

    for i, rec in enumerate(recommendations):
        emoji = NUMBER_EMOJIS[i] if i < len(NUMBER_EMOJIS) else f"{i+1}."
        sign = "+" if rec["change_1d"] >= 0 else ""
        change = f"{sign}{rec['change_1d']}%"
        cycle_emoji = {
            "恐慌": "😱",
            "中性": "😐",
            "貪婪": "🤑",
        }.get(rec.get("market_cycle", ""), "")
        valuation_note = {
            "低估": "（低估區）",
            "合理": "（合理區）",
            "高估": "（高估區）",
        }.get(rec.get("valuation", ""), "")
        lines += [
            "",
            f"{emoji} {rec['name']}（{rec['code']}）",
            f"   收盤：{rec['price']} 元（{change}）{valuation_note}",
            f"   市場週期：{rec.get('market_cycle', 'N/A')} {cycle_emoji}",
            f"   信心指數：{rec['confidence']}/10",
            f"   理由：{rec['reason']}",
        ]

    if recommendations:
        geo_risk = recommendations[0].get("geopolitical_risk", "低")
        geo_reason = recommendations[0].get("geopolitical_reason", "")
        geo_emoji = {"低": "🟢", "中": "🟡", "高": "🔴"}.get(geo_risk, "⚪")
        lines += [
            "",
            f"🌏 地緣政治風險：{geo_emoji} {geo_risk}",
            f"   {geo_reason}",
        ]

    lines += ["", "⚠️ AI 分析僅供參考，請自行評估風險後操作"]
    return _send_email(f"ETF 分析報告 {today}", "\n".join(lines))


def send_geo_risk_warning(risk: dict) -> bool:
    """發送地緣政治高風險警示通知。"""
    today = datetime.now().strftime("%Y/%m/%d")
    text = "\n".join([
        f"🔴 ETF 分析報告 {today}",
        "",
        "⚠️ 今日地緣政治風險偏高",
        "",
        f"偵測到：{risk.get('reason', '重大地緣政治事件')}",
        "",
        "今日暫不建議操作",
        "請觀望至情勢明朗後再評估進場",
        "",
        "⚠️ AI 分析僅供參考，請自行評估風險",
    ])
    return _send_email(f"ETF 分析報告｜地緣政治高風險 {today}", text)


def send_no_recommendation() -> bool:
    """發送今日無推薦標的的通知。"""
    today = datetime.now().strftime("%Y/%m/%d")
    text = "\n".join([
        f"📊 ETF 分析報告 {today}",
        "",
        "今日無符合條件的 ETF",
        "",
        "可能原因：",
        "・PTT 討論熱度不足",
        "・市場情緒偏負面",
        "・Gemini 信心指數未達門檻",
        "",
        "建議繼續觀望 🕐",
    ])
    return _send_email(f"ETF 分析報告｜今日無推薦 {today}", text)


def send_error_alert(error_msg: str) -> bool:
    """發送程式執行錯誤的緊急通知。"""
    today = datetime.now().strftime("%Y/%m/%d")
    text = "\n".join([
        f"🚨 ETF 分析工具異常 {today}",
        "",
        "今日分析執行失敗，請手動檢查",
        "",
        "錯誤訊息：",
        error_msg[:200],
        "",
        "請至 GitHub Actions 查看詳細 log",
    ])
    return _send_email(f"ETF 分析工具異常 {today}", text)
