# 部署說明書

以下以 GitHub Actions 自動每日執行為例。照步驟設定後，工具會在台灣時間每天早上 6 點分析 ETF，並寄出電子郵件通知。

## 你需要先準備

- GitHub 帳號，以及已放上這個專案的 GitHub repository。
- Gemini API 金鑰（至少一組）。
- 可使用 SMTP 寄信的電子郵件帳號，以及郵件服務商提供的 SMTP 連線資料。
- 一個用來接收通知的電子郵件地址。

本專案不限定郵件服務商。SMTP 主機、連接埠、帳號、密碼及加密方式，請以你所選服務商提供的資料為準；不要猜主機或連接埠。

## 設定 GitHub Actions

1. 到 GitHub 開啟專案 repository。
2. 選擇 **Settings → Secrets and variables → Actions**。
3. 在 **Secrets** 區塊選 **New repository secret**，建立以下項目：

   | 名稱 | 填入內容 |
   | --- | --- |
   | `GEMINI_API_KEY_1` | Gemini API 金鑰（必填） |
   | `GEMINI_API_KEY_2` | 第二組 Gemini API 金鑰（選填） |
   | `GEMINI_API_KEY_3` | 第三組 Gemini API 金鑰（選填） |
   | `SMTP_HOST` | 郵件服務商提供的 SMTP 主機名稱 |
   | `SMTP_PORT` | 郵件服務商提供的 SMTP 連接埠 |
   | `SMTP_USERNAME` | SMTP 登入帳號 |
   | `SMTP_PASSWORD` | SMTP 密碼或服務商要求的應用程式密碼 |
   | `SMTP_FROM` | 寄件者郵件地址 |
   | `SMTP_TO` | 通知收件者地址；多個地址以逗號分隔 |

   每個值都要單獨建立一筆 Secret，名稱須完全一致。此工具不會自動讀取 `.env` 檔案。

4. 在同一頁的 **Variables** 區塊，依照郵件服務商的加密方式建立以下其中一個變數：

   - 使用 **STARTTLS**：建立 `SMTP_USE_TLS`，值為 `true`；`SMTP_USE_SSL` 可不設定（預設為 `false`）。
   - 使用 **SSL/TLS**：建立 `SMTP_USE_SSL`，值為 `true`；建立 `SMTP_USE_TLS`，值為 `false`。

   必須且只能啟用其中一種加密方式。請使用服務商指示的連接埠；常見值不保證適用於你的帳號。若 Variables 沒設定，工作流程會使用 STARTTLS。

5. 確認 repository 的 **Actions** 頁面允許執行工作流程，且專案包含 `.github/workflows/daily_run.yml`。

## 手動測試寄送

完成設定後，到 repository 的 **Actions → Daily ETF Analysis → Run workflow → Run workflow** 手動執行一次。

這會執行完整分析，而不只是寄送測試郵件；分析完成後可能寄出推薦或無推薦通知。如果分析中途失敗，則會嘗試寄出錯誤通知。查看該次 workflow 的執行紀錄，確認 **Run ETF analysis** 步驟成功，並檢查收件匣和垃圾郵件匣。

## 自動執行時間

工作流程排程為每日 UTC 22:00，也就是台灣時間隔日早上 06:00。GitHub Actions 排程偶爾可能延遲；也可以使用前述 **Run workflow** 手動執行。

## 常見問題

- **沒有收到信**：先確認 workflow 是否成功，再檢查垃圾郵件匣、收件地址、寄件地址和 SMTP 服務商的寄信限制。
- **SMTP 認證失敗**：確認 `SMTP_USERNAME` 與 `SMTP_PASSWORD`；部分服務商要求使用應用程式密碼，而不是平常登入網站的密碼。
- **連線或 TLS 錯誤**：向服務商確認 `SMTP_HOST`、`SMTP_PORT` 及應使用 STARTTLS 或 SSL/TLS，並確認只啟用一種模式。
- **SMTP 設定不完整**：逐一確認六項必要設定均已建立：`SMTP_HOST`、`SMTP_PORT`、`SMTP_USERNAME`、`SMTP_PASSWORD`、`SMTP_FROM`、`SMTP_TO`。Secrets 名稱需要完全相符。
- **郵件收到但 workflow 顯示其他錯誤**：到該次執行的 Actions log 查看失敗步驟；資料抓取或分析服務出錯也可能導致 workflow 失敗。

## 安全提醒

- 不要把 API 金鑰、SMTP 密碼或真實帳號寫進程式、提交到 Git，或貼在公開 issue/log。
- GitHub Actions 的帳密應存放在 **Secrets**，而不是 Variables。
- `.env.example` 只有空白範例，不含可直接使用的郵件主機或憑證。
