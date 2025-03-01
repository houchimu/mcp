from mcp.server.fastmcp import FastMCP

import logging
from contextlib import redirect_stdout, redirect_stderr
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Sync APIのインポートを削除
# from playwright.sync_api import sync_playwright


async def perform_console_error_check(url):
    async with async_playwright() as p:
        # ブラウザを起動
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # コンソールメッセージをキャプチャするためのリスナーを設定
        page = await context.new_page()
        console_errors = []

        # コンソールメッセージのハンドラー
        def handle_console(msg):
            if msg.type == "error":
                console_errors.append(f"Console Error: {msg.text}")
                logging.error(f"Console Error: {msg.text}")

        page.on("console", handle_console)

        try:
            # ページにアクセス
            await page.goto(url)

            # より完全なページ読み込みを待機
            await page.wait_for_load_state("load")  # DOMContentLoadedイベントを待機
            await page.wait_for_load_state("domcontentloaded")  # DOM構造の読み込み完了を待機
            await page.wait_for_load_state("networkidle")  # ネットワークリクエストの完了を待機

            # さらに追加の待機時間を設定（必要に応じて調整可能）
            await page.wait_for_timeout(3000)  # 3秒待機

            # エラーの確認と結果を返す
            if console_errors:
                return "\n".join(console_errors)
            else:
                return "コンソールエラーは検出されませんでした"

        except Exception as e:
            return f"エラーが発生しました: {str(e)}"
        finally:
            # ブラウザを閉じる
            await browser.close()

# シンプルなFastMCPインスタンス作成
mcp = FastMCP("Browser Use Server")


@mcp.tool()
async def check_console_errors(url: str) -> str:
    """
    指定されたURLにアクセスして、コンソールエラーをチェックします。

    Args:
        url: チェックしたいWebページのURL

    Returns:
        コンソールエラーの情報または正常終了メッセージ
    """
    return await perform_console_error_check(url)


# メイン関数
if __name__ == "__main__":
    mcp.run()
