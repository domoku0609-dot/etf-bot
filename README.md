# 台灣 ETF 智慧投資通知工具

工具每日執行 ETF 分析，並以 SMTP 電子郵件寄送推薦、無推薦、地緣政治高風險或執行錯誤通知。通知觸發時機與原有通知內容維持不變。

初次部署請參閱 [`DEPLOYMENT.md`](DEPLOYMENT.md)。

## 設定

請設定下列環境變數；`.env.example` 僅供參考，程式不會自動載入 `.env`。GitHub Actions 請將主機、連接埠、帳密及郵件地址設定在 Repository **Settings → Secrets and variables → Actions → Secrets**，並在工作流程執行時注入；加密模式則設定在同頁的 **Variables**：

| 變數 | 說明 |
| --- | --- |
| `GEMINI_API_KEY_1` | 必填，Gemini API 金鑰；`GEMINI_API_KEY_2`、`GEMINI_API_KEY_3` 可選 |
| `SMTP_HOST` | SMTP 主機名稱 |
| `SMTP_PORT` | SMTP 連接埠 |
| `SMTP_USERNAME` | SMTP 登入帳號 |
| `SMTP_PASSWORD` | SMTP 登入密碼或郵件服務商提供的應用程式密碼 |
| `SMTP_FROM` | 寄件者郵件地址 |
| `SMTP_TO` | 收件者郵件地址；多位收件者以逗號分隔 |
| `SMTP_USE_SSL` | 使用 SMTP implicit TLS 時設為 `true`（通常搭配服務商指定的 SSL 連接埠） |
| `SMTP_USE_TLS` | 使用 STARTTLS 時設為 `true`（通常搭配服務商指定的 STARTTLS 連接埠）；預設為 `true` |

`SMTP_USE_SSL` 與 `SMTP_USE_TLS` 必須且只能有一個設為 `true`，避免以明文傳送登入憑證。請依郵件服務商提供的主機、連接埠與加密方式設定；本工具不限定特定郵件供應商，也不提供主機或憑證預設值。請勿將真實帳密提交至版本控制。

## 執行與測試

```powershell
python -m pip install -r requirements.txt
python main.py
python -m unittest discover -s tests -v
```

GitHub Actions 每日於台灣時間 06:00 執行，也支援手動觸發。
