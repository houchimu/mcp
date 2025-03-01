from mcp.server.fastmcp import FastMCP
import os
import asyncio
import sys
import logging
import io
import builtins
import json
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, Browser

# サーバー起動前の準備
# -------------------------------

# デバッグ用ファイルロガーの設定
debug_log_file = "browser_use_debug.log"
def debug_log(message):
    """デバッグ情報をファイルに記録"""
    with open(debug_log_file, "a", encoding="utf-8") as f:
        f.write(f"{message}\n")

# 起動時の初期メッセージを記録
debug_log(f"サーバー起動開始: {sys.argv}")

# 元のprint関数を保存
original_print = builtins.print

# ファイルに出力するprint関数
def file_print(*args, **kwargs):
    """プリント出力をファイルに記録"""
    message = " ".join(str(arg) for arg in args)
    debug_log(f"PRINT: {message}")

# printを置き換え
builtins.print = file_print

# すべてのloggerを無効化
logging.basicConfig(level=logging.CRITICAL)

# すべての既存ロガーを無効化
for name in logging.root.manager.loggerDict:
    logger = logging.getLogger(name)
    logger.handlers = []
    logger.propagate = False
    logger.disabled = True
    logger.setLevel(logging.CRITICAL)

# ルートロガーからすべてのハンドラを削除
logging.root.handlers = []

# 特に重要なロガーを明示的に無効化
critical_loggers = [
    "uvicorn", 
    "uvicorn.error", 
    "uvicorn.access", 
    "uvicorn.asgi",
    "starlette", 
    "starlette.routing",
    "mcp",
    "mcp.server",
    "playwright",
    "fastapi",
    "asyncio",
    "multiprocessing"
]

for logger_name in critical_loggers:
    logger = logging.getLogger(logger_name)
    logger.handlers = []
    logger.propagate = False
    logger.disabled = True
    logger.setLevel(logging.CRITICAL)

# NullIO - 出力を完全に捨てるためのIO
class NullIO(io.IOBase):
    def __init__(self):
        super().__init__()
        # bufferプロパティを追加（自己参照）
        self.buffer = self

    def write(self, *args, **kwargs):
        return 0
    
    def read(self, *args, **kwargs):
        return ''
    
    def flush(self, *args, **kwargs):
        pass
    
    # バッファ操作のためのメソッドを追加
    def readable(self):
        return False
        
    def writable(self):
        return True
    
    def seekable(self):
        return False
    
    def fileno(self):
        raise OSError("NullIO has no file descriptor")
    
    def isatty(self):
        return False
    
    def truncate(self, size=None):
        return 0
        
    def readline(self, size=-1):
        return ''
        
    def readlines(self, hint=-1):
        return []
        
    def writelines(self, lines):
        return 0

# 標準出力をリダイレクト（NullIOを使用）
try:
    sys.stdout = NullIO()
    sys.stderr = NullIO()
    debug_log("標準出力と標準エラー出力をリダイレクトしました")
except Exception as e:
    debug_log(f"標準出力のリダイレクトに失敗: {str(e)}")

# asyncioのデバッグを無効化し、高速化設定を追加
try:
    # asyncio設定をオーバーライド（UVloopは使用しない）
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy() if sys.platform == 'win32' else asyncio.DefaultEventLoopPolicy())
    
    # プールサイズを調整して処理を高速化
    loop = asyncio.new_event_loop()
    loop.set_debug(False)  # デバッグモードを無効化
    
    # イベントループを設定
    asyncio.set_event_loop(loop)
    debug_log("asyncioイベントループを最適化設定で構成しました")
except Exception as e:
    debug_log(f"asyncioイベントループの設定に失敗: {str(e)}")

# 環境変数をロード
try:
    load_dotenv()
    debug_log("環境変数をロードしました")
except Exception as e:
    debug_log(f"環境変数のロードに失敗: {str(e)}")

# サーバー設定
# -------------------------------

# FastMCPのカスタムレスポンスハンドラー
def on_initialize(request):
    debug_log(f"初期化リクエストを受信: {request}")
    # 早期レスポンスを返す
    return {"message": "初期化が成功しました"}

# カスタムハンドラーを追加したFastMCP サーバーの作成
try:
    mcp = FastMCP(
        "Browser Use Server",
        settings={
            "log_level": "critical",
            "debug": False,
            "timeout": 120,  # タイムアウトを120秒に拡張
            "host": "127.0.0.1",  # ローカルホストに限定
            "ready_timeout": 10,  # 準備完了タイムアウトを短く設定
            "shutdown_timeout": 10  # シャットダウンタイムアウトを短く設定
        }
    )
    debug_log("FastMCPサーバーを作成しました")
except Exception as e:
    debug_log(f"FastMCPサーバーの作成に失敗: {str(e)}")
    # 致命的なエラーの場合は終了
    sys.exit(1)

# Playwrightセッション管理
playwright = None
browser = None
page = None
context = None
current_url = ""

# 遅延初期化によるPlaywrightの起動エラー回避
BROWSER_INITIALIZED = False
INITIALIZATION_IN_PROGRESS = False  # 初期化進行中フラグ

# サーバーツール定義 
# -------------------------------

@mcp.tool()
async def initialize_browser() -> str:
    """ブラウザを初期化します。他のツールを使用する前に必ずこれを呼び出してください。
    
    Returns:
        初期化結果のメッセージ
    """
    global playwright, browser, page, context, BROWSER_INITIALIZED, INITIALIZATION_IN_PROGRESS
    
    # 既に初期化中の場合は待機中のメッセージを返す
    if INITIALIZATION_IN_PROGRESS:
        return "ブラウザの初期化が既に進行中です。しばらくお待ちください..."
    
    # 既に初期化済みの場合は成功メッセージを返す
    if BROWSER_INITIALIZED and browser and page:
        return "ブラウザは既に初期化されています"
    
    # 初期化フラグを設定
    INITIALIZATION_IN_PROGRESS = True
    
    try:
        debug_log("ブラウザ初期化を開始します")
        
        # 既存のインスタンスをクローズ
        await close_browser()
            
        # Playwrightを起動（高速化オプション追加）
        debug_log("Playwrightを起動します")
        playwright = await async_playwright().start()
        debug_log("Playwrightが起動しました")
        
        # ブラウザオプションを設定（高速化設定追加）
        browser_options = {
            "headless": True,
            "args": [
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--no-zygote",
                "--disable-extensions",
                "--disable-software-rasterizer",
                "--disable-features=site-per-process",
                "--disable-web-security",
                "--js-flags=--max_old_space_size=128"  # メモリ使用量を制限
            ]
        }
        
        # Chromiumブラウザを起動
        debug_log("ブラウザを起動します")
        browser = await playwright.chromium.launch(**browser_options)
        debug_log("ブラウザが起動しました")
        
        # ブラウザコンテキストオプションを設定
        context_options = {
            "viewport": {"width": 1280, "height": 800},
            "ignore_https_errors": True,
            "java_script_enabled": True,  # JavaScriptを有効化
            "bypass_csp": True,  # CSP制約を回避
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36"  # 一般的なUAを設定
        }
        
        # ブラウザコンテキストを作成
        debug_log("ブラウザコンテキストを作成します")
        context = await browser.new_context(**context_options)
        debug_log("ブラウザコンテキストが作成されました")
        
        # 新しいページを開く
        debug_log("新しいページを開きます")
        page = await context.new_page()
        debug_log("新しいページが開かれました")
        
        BROWSER_INITIALIZED = True
        debug_log("ブラウザの初期化が完了しました")
        
        return "ブラウザが正常に初期化されました"
    except Exception as e:
        error_msg = f"ブラウザの初期化に失敗しました: {str(e)}"
        stack_trace = traceback.format_exc()
        debug_log(f"{error_msg}\n{stack_trace}")
        return error_msg
    finally:
        # 初期化フラグをリセット
        INITIALIZATION_IN_PROGRESS = False

@mcp.tool()
async def browse(url: str) -> str:
    """指定されたURLにアクセスします。
    
    Args:
        url: アクセスしたいWebページのURL
    
    Returns:
        アクセス結果のメッセージ
    """
    global page, current_url, BROWSER_INITIALIZED
    
    if not BROWSER_INITIALIZED or not page:
        debug_log("ブラウザが初期化されていないため、初期化を実行します")
        init_result = await initialize_browser()
        if not BROWSER_INITIALIZED:
            return f"ブラウザの初期化に失敗しました。initialize_browser()を先に実行してください。詳細: {init_result}"
    
    try:
        debug_log(f"URLにアクセスします: {url}")
        # URLに移動（タイムアウトを30秒に設定）
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        current_url = url
        debug_log(f"URLへのアクセスが完了しました: {url}")
        
        # ページタイトルを取得
        title = await page.title()
        debug_log(f"ページタイトル: {title}")
        
        # ページの基本情報のみを返す（コンテンツは重いため省略）
        return f"URLにアクセスしました: {url}\nタイトル: {title}"
    except Exception as e:
        error_msg = f"URLアクセスに失敗しました: {str(e)}"
        stack_trace = traceback.format_exc()
        debug_log(f"{error_msg}\n{stack_trace}")
        return error_msg

@mcp.tool()
async def get_page_info() -> str:
    """現在開いているページの情報を取得します。
    
    Returns:
        ページの情報、またはエラーメッセージ
    """
    global page, current_url, BROWSER_INITIALIZED
    
    if not BROWSER_INITIALIZED or not page:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    if not current_url:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        debug_log("ページ情報を取得します")
        # ページタイトルを取得
        title = await page.title()
        
        # 現在のURL
        url = page.url
        
        # メタディスクリプションを取得
        description = await page.evaluate("() => { const meta = document.querySelector('meta[name=\"description\"]'); return meta ? meta.getAttribute('content') : ''; }")
        
        # 結果をフォーマット
        result = f"ページ情報:\n"
        result += f"タイトル: {title}\n"
        result += f"URL: {url}\n"
        result += f"説明: {description}\n"
        
        debug_log("ページ情報の取得が完了しました")
        return result
    except Exception as e:
        error_msg = f"ページ情報の取得に失敗しました: {str(e)}"
        debug_log(error_msg)
        return error_msg

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
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        debug_log(f"要素をクリックします: {selector}")
        # セレクタが「text=」で始まっていない場合は追加
        if not selector.startswith("text=") and not any(char in selector for char in "[]#.:>+"):
            selector = f"text={selector}"
        
        # 要素が見つかるまで待機してからクリック
        await page.wait_for_selector(selector, timeout=5000)
        await page.click(selector)
        
        # クリック後のページタイトルを取得
        title = await page.title()
        debug_log(f"要素のクリックが完了しました: {selector}")
        
        return f"要素 '{selector}' をクリックしました\n新しいページ: {title}"
    except Exception as e:
        error_msg = f"クリックに失敗しました: {str(e)}"
        debug_log(error_msg)
        return error_msg

@mcp.tool()
async def fill_form(selector: str, text: str) -> str:
    """指定されたセレクタに一致するフォーム要素にテキストを入力します。
    
    Args:
        selector: 入力フィールドのCSSセレクタまたはラベルテキスト
        text: 入力するテキスト
    
    Returns:
        フォーム入力の結果、またはエラーメッセージ
    """
    global page, BROWSER_INITIALIZED
    
    if not BROWSER_INITIALIZED or not page:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        debug_log(f"フォームに入力します: {selector}")
        # セレクタをテキストベースに変換（必要な場合）
        if not any(char in selector for char in "[]#.:>+"):
            selector = f"input[placeholder*='{selector}'], textarea[placeholder*='{selector}'], [aria-label*='{selector}']"
        
        # 要素を待機して入力
        await page.wait_for_selector(selector, timeout=5000)
        await page.fill(selector, text)
        debug_log(f"フォーム入力が完了しました: {selector}")
        
        return f"'{selector}' に「{text}」を入力しました"
    except Exception as e:
        error_msg = f"フォーム入力に失敗しました: {str(e)}"
        debug_log(error_msg)
        return error_msg

@mcp.tool()
async def take_screenshot() -> str:
    """現在のページのスクリーンショットを撮影します。
    
    Returns:
        スクリーンショットの結果、またはエラーメッセージ
    """
    global page, BROWSER_INITIALIZED
    
    if not BROWSER_INITIALIZED or not page:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        debug_log("スクリーンショットを撮影します")
        # スクリーンショットのパスを設定
        screenshot_dir = "screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # タイムスタンプ付きのファイル名
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{screenshot_dir}/screenshot_{timestamp}.png"
        
        # スクリーンショットを撮影
        await page.screenshot(path=filename)
        debug_log(f"スクリーンショットを保存しました: {filename}")
        
        return f"スクリーンショット撮影成功:\nファイル: {filename}"
    except Exception as e:
        error_msg = f"スクリーンショット撮影に失敗しました: {str(e)}"
        debug_log(error_msg)
        return error_msg

# ブラウザを確実にクローズするための関数
async def close_browser():
    global playwright, browser, page, context
    
    debug_log("ブラウザクローズ処理を開始します")
    try:
        if page:
            try:
                await page.close()
                debug_log("ページをクローズしました")
            except Exception as e:
                debug_log(f"ページクローズ中にエラー: {str(e)}")
            page = None
            
        if context:
            try:
                await context.close()
                debug_log("コンテキストをクローズしました")
            except Exception as e:
                debug_log(f"コンテキストクローズ中にエラー: {str(e)}")
            context = None
            
        if browser:
            try:
                await browser.close()
                debug_log("ブラウザをクローズしました")
            except Exception as e:
                debug_log(f"ブラウザクローズ中にエラー: {str(e)}")
            browser = None
            
        if playwright:
            try:
                await playwright.stop()
                debug_log("Playwrightをクローズしました")
            except Exception as e:
                debug_log(f"Playwright停止中にエラー: {str(e)}")
            playwright = None
            
    except Exception as e:
        debug_log(f"ブラウザクローズ中にエラーが発生: {str(e)}")

# シャットダウンハンドラの追加
def shutdown_handler():
    debug_log("シャットダウンハンドラが呼び出されました")
    asyncio.run(close_browser())

# サーバー起動関数
def start_server():
    debug_log("サーバーを起動します")
    try:
        # シャットダウンイベントを登録
        import atexit
        atexit.register(shutdown_handler)
        
        # サーバー起動前のヘルスチェック
        debug_log("ヘルスチェックを実行します")
        # OSやプロセスのリソース状況を確認
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        debug_log(f"メモリ使用量: {memory_info.rss / (1024*1024):.2f} MB")
        
        # サーバー起動（追加のエラー捕捉）
        debug_log("mcp.run()を呼び出します")
        
        # 標準出力のリダイレクトを保護
        with redirect_stdout(NullIO()), redirect_stderr(NullIO()):
            # サーバー起動のためのエラーハンドリング追加
            try:
                mcp.run()
            except Exception as server_error:
                error_msg = f"サーバー実行中にエラーが発生: {str(server_error)}"
                stack_trace = traceback.format_exc()
                debug_log(f"{error_msg}\n{stack_trace}")
                
                # 深刻なエラーをログファイルに記録
                with open("browser_use_fatal_error.log", "a", encoding="utf-8") as f:
                    f.write(f"{error_msg}\n{stack_trace}\n")
                
                # ブラウザを確実にクローズ
                asyncio.run(close_browser())
                
                # 例外を再スロー
                raise
            
    except ImportError:
        debug_log("psutilがインストールされていないため、リソースチェックをスキップします")
    except Exception as e:
        error_msg = f"サーバー起動中にエラーが発生: {str(e)}"
        stack_trace = traceback.format_exc()
        debug_log(f"{error_msg}\n{stack_trace}")
        
        # エラーログをファイルに記録
        with open("browser_use_error.log", "a", encoding="utf-8") as f:
            f.write(f"{error_msg}\n{stack_trace}\n")
        
        # 確実にブラウザをクローズ
        asyncio.run(close_browser())
        
        # 意図的にエラーメッセージを標準エラーに出力（デバッグ用）
        try:
            original_stderr = sys.__stderr__
            original_stderr.write(f"MCPサーバーエラー: {error_msg}\n")
        except:
            pass
        
        sys.exit(1)

# メイン関数
if __name__ == "__main__":
    debug_log("メイン関数が呼び出されました")
    start_server()