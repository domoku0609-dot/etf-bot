"""
Gemini API 穩健呼叫模組
整合三個機制：
  1. API Key 輪轉 — 多組 Key 分散負載
  2. Retry 重試   — 指數退避，失敗自動重試
  3. Timeout 超時 — 單次呼叫最長等待時間
"""

import time
import itertools
import google.generativeai as genai
from config import (
    GEMINI_API_KEYS,
    GEMINI_MODEL,
    GEMINI_MAX_TOKENS,
    GEMINI_TEMPERATURE,
    GEMINI_TIMEOUT,
    GEMINI_MAX_RETRIES,
    GEMINI_RETRY_BASE_DELAY,
)


class GeminiClient:
    """
    Gemini API 穩健呼叫客戶端
    支援多 Key 輪轉、指數退避重試、超時保護
    """

    def __init__(self):
        # 過濾掉空白 Key
        valid_keys = [k for k in GEMINI_API_KEYS if k.strip()]
        if not valid_keys:
            raise ValueError("[GeminiClient] 沒有有效的 GEMINI_API_KEY，請檢查環境變數")

        self._keys      = valid_keys
        self._key_cycle = itertools.cycle(valid_keys)
        self._current_key_index = 0

        print(f"[GeminiClient] 初始化完成，共 {len(valid_keys)} 組 API Key")
        self._init_model(next(self._key_cycle))

    def _init_model(self, api_key: str) -> None:
        """用指定 Key 初始化 Gemini model"""
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config=genai.GenerationConfig(
                max_output_tokens=GEMINI_MAX_TOKENS,
                temperature=GEMINI_TEMPERATURE,
            ),
        )

    def _rotate_key(self) -> None:
        """切換到下一組 API Key"""
        next_key = next(self._key_cycle)
        self._current_key_index = (self._current_key_index + 1) % len(self._keys)
        print(f"[GeminiClient] 切換至 Key #{self._current_key_index + 1}")
        self._init_model(next_key)

    def generate(self, messages: list[dict]) -> str | None:
        """
        呼叫 Gemini API，內建重試與輪轉邏輯

        Args:
            messages: 對話訊息列表
                      格式：[{"role": "user", "parts": ["..."]}, ...]

        Returns:
            str: Gemini 回覆文字，所有重試失敗後回傳 None
        """
        last_error = None

        for attempt in range(1, GEMINI_MAX_RETRIES + 1):
            try:
                print(f"[GeminiClient] 呼叫 Gemini（第 {attempt}/{GEMINI_MAX_RETRIES} 次）...")

                # 設定超時（透過執行緒計時）
                response = self._call_with_timeout(messages, GEMINI_TIMEOUT)

                if response is None:
                    raise TimeoutError(f"Gemini 回應超過 {GEMINI_TIMEOUT} 秒")

                text = response.text.strip()
                print(f"[GeminiClient] 呼叫成功（{len(text)} 字元）")
                return text

            except TimeoutError as e:
                last_error = e
                print(f"[GeminiClient] 超時：{e}")
                self._rotate_key()

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # 判斷錯誤類型決定處理方式
                if any(keyword in error_str for keyword in [
                    "429", "quota", "rate limit", "resource exhausted"
                ]):
                    print(f"[GeminiClient] Rate Limit，切換 Key 並等待...")
                    self._rotate_key()

                elif any(keyword in error_str for keyword in [
                    "500", "503", "502", "unavailable", "internal"
                ]):
                    print(f"[GeminiClient] 伺服器錯誤：{e}")

                else:
                    print(f"[GeminiClient] 未知錯誤：{e}")

            # 指數退避等待（2, 4, 8 秒...）
            if attempt < GEMINI_MAX_RETRIES:
                wait = GEMINI_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                print(f"[GeminiClient] 等待 {wait} 秒後重試...")
                time.sleep(wait)

        print(f"[GeminiClient] 所有重試失敗，最後錯誤：{last_error}")
        return None

    def _call_with_timeout(self, messages: list[dict], timeout: int):
        """
        帶超時的 Gemini 呼叫
        使用 threading 實作超時保護

        Args:
            messages: 對話訊息列表
            timeout:  最長等待秒數

        Returns:
            Gemini response 物件，超時回傳 None
        """
        import threading

        result_container = [None]
        error_container  = [None]

        def _call():
            try:
                result_container[0] = self._model.generate_content(messages)
            except Exception as e:
                error_container[0] = e

        thread = threading.Thread(target=_call, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # 超時，執行緒仍在跑但我們不等了
            return None

        if error_container[0]:
            raise error_container[0]

        return result_container[0]


# ===========================
# 全域單例，所有模組共用同一個客戶端
# ===========================
_client: GeminiClient | None = None


def get_client() -> GeminiClient:
    """
    取得全域 GeminiClient 單例
    第一次呼叫時初始化，之後直接回傳同一個實例
    """
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client


def call_gemini(messages: list[dict]) -> str | None:
    """
    便利函式：直接呼叫 Gemini，不需要手動取得 client

    Args:
        messages: 對話訊息列表

    Returns:
        str: Gemini 回覆文字，失敗回傳 None
    """
    return get_client().generate(messages)


if __name__ == "__main__":
    print("測試 GeminiClient...")

    test_messages = [
        {
            "role":  "user",
            "parts": ["請用一句話介紹台灣ETF投資，只回傳這一句話。"],
        }
    ]

    response = call_gemini(test_messages)
    if response:
        print(f"回覆：{response}")
    else:
        print("呼叫失敗")
