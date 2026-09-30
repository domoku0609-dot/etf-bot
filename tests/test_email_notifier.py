import unittest
from unittest.mock import MagicMock, patch

from notifiers import email_notifier


class EmailNotifierTests(unittest.TestCase):
    def setUp(self):
        self.config = patch.multiple(
            email_notifier,
            SMTP_HOST="smtp.example.test",
            SMTP_PORT="587",
            SMTP_USERNAME="account",
            SMTP_PASSWORD="test-password",
            SMTP_FROM="sender@example.test",
            SMTP_TO="one@example.test, two@example.test",
            SMTP_USE_SSL=False,
            SMTP_USE_TLS=True,
        )
        self.config.start()
        self.addCleanup(self.config.stop)

    @patch("notifiers.email_notifier.smtplib.SMTP")
    def test_send_email_uses_starttls_and_configured_recipients(self, smtp_class):
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        smtp.send_message.return_value = {}
        smtp_class.return_value = smtp

        self.assertTrue(email_notifier._send_email("Subject", "Body"))

        smtp_class.assert_called_once_with("smtp.example.test", 587, timeout=10)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("account", "test-password")
        message = smtp.send_message.call_args.args[0]
        self.assertEqual(message["From"], "sender@example.test")
        self.assertEqual(message["To"], "one@example.test, two@example.test")
        self.assertEqual(message["Subject"], "Subject")
        self.assertEqual(message.get_content(), "Body\n")

    @patch("notifiers.email_notifier.smtplib.SMTP_SSL")
    def test_send_email_supports_ssl(self, smtp_ssl_class):
        email_notifier.SMTP_USE_SSL = True
        email_notifier.SMTP_USE_TLS = False
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        smtp.send_message.return_value = {}
        smtp_ssl_class.return_value = smtp

        self.assertTrue(email_notifier._send_email("Subject", "Body"))

        self.assertEqual(smtp_ssl_class.call_args.args[:2], ("smtp.example.test", 587))
        smtp.starttls.assert_not_called()

    @patch("notifiers.email_notifier.smtplib.SMTP")
    def test_missing_configuration_fails_without_connecting(self, smtp_class):
        email_notifier.SMTP_HOST = ""

        self.assertFalse(email_notifier._send_email("Subject", "Body"))

        smtp_class.assert_not_called()

    @patch("notifiers.email_notifier.smtplib.SMTP")
    def test_requires_encrypted_smtp(self, smtp_class):
        email_notifier.SMTP_USE_TLS = False

        self.assertFalse(email_notifier._send_email("Subject", "Body"))

        smtp_class.assert_not_called()

    @patch("notifiers.email_notifier.smtplib.SMTP")
    def test_refused_recipient_is_reported_as_failure(self, smtp_class):
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        smtp.send_message.return_value = {"one@example.test": (550, b"refused")}
        smtp_class.return_value = smtp

        self.assertFalse(email_notifier._send_email("Subject", "Body"))

    @patch("notifiers.email_notifier._send_email")
    def test_recommendation_body_keeps_report_content(self, send_email):
        recommendation = {
            "name": "元大台灣50",
            "code": "0050",
            "price": 201.3,
            "change_1d": 1.41,
            "market_cycle": "中性",
            "valuation": "合理",
            "confidence": 8,
            "reason": "技術面與籌碼面同步偏多。",
            "geopolitical_risk": "低",
            "geopolitical_reason": "國際局勢平穩",
        }

        email_notifier.send_recommendation([recommendation])

        subject, body = send_email.call_args.args
        self.assertTrue(subject.startswith("ETF 分析報告 "))
        self.assertIn("分析時間：06:00｜建議於今日開盤評估", body)
        self.assertIn("✅ 建議關注（1 檔）", body)
        self.assertIn("元大台灣50（0050）", body)
        self.assertIn("信心指數：8/10", body)
        self.assertIn("技術面與籌碼面同步偏多。", body)
        self.assertIn("🌏 地緣政治風險：🟢 低", body)

    @patch("notifiers.email_notifier._send_email")
    def test_other_notification_bodies_are_preserved(self, send_email):
        email_notifier.send_no_recommendation()
        no_recommendation_body = send_email.call_args.args[1]
        self.assertIn("今日無符合條件的 ETF", no_recommendation_body)
        self.assertIn("建議繼續觀望 🕐", no_recommendation_body)

        email_notifier.send_geo_risk_warning({"reason": "市場風險升高"})
        risk_body = send_email.call_args.args[1]
        self.assertIn("今日地緣政治風險偏高", risk_body)
        self.assertIn("市場風險升高", risk_body)

        email_notifier.send_error_alert("資料抓取失敗")
        error_body = send_email.call_args.args[1]
        self.assertIn("今日分析執行失敗，請手動檢查", error_body)
        self.assertIn("資料抓取失敗", error_body)


if __name__ == "__main__":
    unittest.main()
