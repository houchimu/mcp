from mcp.server.fastmcp import FastMCP
import os
import asyncio
import sys
import logging
import io
import builtins
import json
import traceback
import threading
import time
from contextlib import redirect_stdout, redirect_stderr
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, Browser

# サーバー設定
# -------------------------------
debug_log_file = "browser_use_debug.log"
error_log_file = "browser_use_error.log"

# ファイルロガーの設定
def debug_log(message):
    """デバッグ情報をファイルに記録"""
    with open(debug_log_file, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {message}\n")

def error_log(message):
    """エラー情報をファイルに記録"""
    with open(error_log_file, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {message}\n")

# 起動時の初期メッセージを記録
debug_log(f"サーバー起動プロセス開始: {sys.argv}")

# 標準出力リダイレクト用クラス
class NullIO(io.IOBase):
    def __init__(self):
        super().__init__()
        self.buffer = self  # バッファープロパティを追加

    def write(self, *args, **kwargs):
        return 0
    
    def read(self, *args, **kwargs):
        return ''
    
    def flush(self, *args, **kwargs):
        pass
    
    def readable(self):
        return False
    
    def writable(self):
        return True
    
    def seekable(self):
        return False
        
    def readline(self, size=-1):
        return ''
        
    def readlines(self, hint=-1):
        return []

# 標準出力をリダイレクト
sys.stdout = NullIO()
sys.stderr = NullIO()

# ロギングシステムを無効化
logging.basicConfig(level=logging.CRITICAL)
for name in logging.root.manager.loggerDict:
    logger = logging.getLogger(name)
    logger.handlers = []
    logger.propagate = False
    logger.disabled = True
    logger.setLevel(logging.CRITICAL)

# 重要なロガーを無効化
critical_loggers = ["uvicorn", "uvicorn.error", "fastapi", "starlette", "mcp", "playwright", "asyncio"]
for name in critical_loggers:
    logger = logging.getLogger(name)
    logger.handlers = []
    logger.propagate = False
    logger.disabled = True
    logger.setLevel(logging.CRITICAL)

# グローバル変数
playwright = None
browser = None
page = None
context = None
current_url = ""
BROWSER_INITIALIZED = False
BROWSER_INIT_LOCK = threading.Lock()

# ブラウザ初期化のための関数
async def _initialize_browser_async():
    global playwright, browser, page, context, BROWSER_INITIALIZED
    
    try:
        debug_log("ブラウザ非同期初期化開始")
        # 既存のインスタンスをクローズ
        await _close_browser_async()
            
        # Playwrightを起動
        playwright = await async_playwright().start()
        debug_log("Playwright起動完了")
        
        # ブラウザオプション設定
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        debug_log("ブラウザ起動完了")
        
        # ブラウザコンテキスト作成
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True
        )
        debug_log("ブラウザコンテキスト作成完了")
        
        # 新しいページを開く
        page = await context.new_page()
        debug_log("ページ作成完了")
        
        BROWSER_INITIALIZED = True
        debug_log("ブラウザ初期化完了")
        return True
    except Exception as e:
        error_msg = f"ブラウザ初期化エラー: {str(e)}\n{traceback.format_exc()}"
        error_log(error_msg)
        debug_log(error_msg)
        return False

# ブラウザをクローズする関数
async def _close_browser_async():
    global playwright, browser, page, context, BROWSER_INITIALIZED
    
    try:
        if page:
            await page.close()
            page = None
        
        if context:
            await context.close()
            context = None
            
        if browser:
            await browser.close()
            browser = None
            
        if playwright:
            await playwright.stop()
            playwright = None
            
        BROWSER_INITIALIZED = False
        debug_log("ブラウザリソースをクローズしました")
        return True
    except Exception as e:
        error_log(f"ブラウザクローズ中にエラー: {str(e)}")
        return False

# MCPサーバー作成
try:
    # シンプルなFastMCPインスタンス作成
    mcp = FastMCP(
        "Browser Use Server",
        settings={
            "log_level": "critical",
            "debug": False
        }
    )
    debug_log("FastMCPサーバーを作成しました")
except Exception as e:
    error_msg = f"FastMCPサーバー作成エラー: {str(e)}"
    error_log(error_msg)
    debug_log(error_msg)
    sys.exit(1)

# ツール定義
@mcp.tool()
async def initialize_browser() -> str:
    """ブラウザを初期化します。他のツールを使用する前に必ずこれを呼び出してください。
    
    Returns:
        初期化結果のメッセージ
    """
    global BROWSER_INITIALIZED, BROWSER_INIT_LOCK
    
    # 初期化が既に完了している場合は早期リターン
    if BROWSER_INITIALIZED:
        return "ブラウザは既に初期化されています"
    
    # 同時実行を防ぐためのロック
    if not BROWSER_INIT_LOCK.acquire(blocking=False):
        return "ブラウザ初期化プロセスは既に進行中です。しばらくお待ちください..."
    
    try:
        debug_log("initialize_browser ツールが呼び出されました")
        success = await _initialize_browser_async()
        
        if success:
            return "ブラウザが正常に初期化されました"
        else:
            return "ブラウザの初期化に失敗しました。詳細はログを確認してください。"
    except Exception as e:
        error_msg = f"ブラウザ初期化中に例外が発生: {str(e)}"
        error_log(error_msg)
        debug_log(error_msg)
        return f"エラー: {error_msg}"
    finally:
        BROWSER_INIT_LOCK.release()

@mcp.tool()
async def browse(url: str) -> str:
    """指定されたURLにアクセスします。
    
    Args:
        url: アクセスしたいWebページのURL
    
    Returns:
        アクセス結果のメッセージ
    """
    global page, current_url, BROWSER_INITIALIZED
    
    # ブラウザが初期化されていない場合は初期化
    if not BROWSER_INITIALIZED or not page:
        init_message = await initialize_browser()
        if not BROWSER_INITIALIZED:
            return f"ブラウザが初期化されていません: {init_message}"
    
    try:
        debug_log(f"URLアクセス開始: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        current_url = url
        
        title = await page.title()
        debug_log(f"URLアクセス完了: {url}, タイトル: {title}")
        
        return f"URLにアクセスしました: {url}\nタイトル: {title}"
    except Exception as e:
        error_msg = f"URLアクセス失敗: {str(e)}"
        error_log(error_msg)
        debug_log(error_msg)
        return f"エラー: {error_msg}"

@mcp.tool()
async def get_page_info() -> str:
    """現在開いているページの情報を取得します。
    
    Returns:
        ページの情報、またはエラーメッセージ
    """
    global page, current_url, BROWSER_INITIALIZED
    
    if not BROWSER_INITIALIZED or not page:
        return "ブラウザが初期化されていません。initialize_browser()を先に実行してください。"
    
    if not current_url:
        return "ページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        debug_log("ページ情報取得開始")
        title = await page.title()
        url = page.url
        
        result = f"ページ情報:\nタイトル: {title}\nURL: {url}"
        debug_log("ページ情報取得完了")
        
        return result
    except Exception as e:
        error_msg = f"ページ情報取得失敗: {str(e)}"
        debug_log(error_msg)
        return f"エラー: {error_msg}"

@mcp.tool()
async def click_element(selector: str) -> str:
    """指定されたセレクタに一致する要素をクリックします。
    
    Args:
        selector: クリックする要素のCSSセレクタまたはテキスト
    
    Returns:
        クリック操作の結果、またはエラーメッセージ
    """
    global page, BROWSER_INITIALIZED
    
    if not BROWSER_INITIALIZED or not page:
        return "ブラウザが初期化されていません。initialize_browser()を先に実行してください。"
    
    try:
        debug_log(f"要素クリック操作: {selector}")
        await page.click(selector)
        
        title = await page.title()
        debug_log(f"要素クリック完了: {selector}")
        
        return f"要素 '{selector}' をクリックしました\n新しいページ: {title}"
    except Exception as e:
        error_msg = f"要素クリック失敗: {str(e)}"
        debug_log(error_msg)
        return f"エラー: {error_msg}"

@mcp.tool()
async def take_screenshot() -> str:
    """現在のページのスクリーンショットを撮影します。
    
    Returns:
        スクリーンショットの結果、またはエラーメッセージ
    """
    global page, BROWSER_INITIALIZED
    
    if not BROWSER_INITIALIZED or not page:
        return "ブラウザが初期化されていません。initialize_browser()を先に実行してください。"
    
    try:
        debug_log("スクリーンショット撮影開始")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # ディレクトリ作成
        os.makedirs("screenshots", exist_ok=True)
        filename = f"screenshots/screenshot_{timestamp}.png"
        
        # スクリーンショット撮影
        await page.screenshot(path=filename)
        debug_log(f"スクリーンショット撮影完了: {filename}")
        
        return f"スクリーンショット撮影成功: {filename}"
    except Exception as e:
        error_msg = f"スクリーンショット撮影失敗: {str(e)}"
        debug_log(error_msg)
        return f"エラー: {error_msg}"

# シャットダウン時の処理
def shutdown_handler():
    debug_log("シャットダウンハンドラ実行")
    # asyncioのランタイムが利用可能かを確認
    try:
        if playwright or browser or context or page:
            asyncio.run(_close_browser_async())
    except Exception as e:
        error_log(f"シャットダウン処理エラー: {str(e)}")

# サーバー起動関数
def start_server():
    debug_log("サーバー起動処理開始")
    
    # シャットダウンハンドラ登録
    import atexit
    atexit.register(shutdown_handler)
    
    try:
        # 標準出力をリダイレクト
        with redirect_stdout(NullIO()), redirect_stderr(NullIO()):
            debug_log("FastMCPサーバー実行開始")
            mcp.run()
            debug_log("FastMCPサーバー実行終了")
    except Exception as e:
        error_msg = f"サーバー実行中に重大なエラーが発生: {str(e)}\n{traceback.format_exc()}"
        error_log(error_msg)
        debug_log(error_msg)
        sys.exit(1)

# メイン関数
if __name__ == "__main__":
    debug_log("メイン関数開始")
    start_server()