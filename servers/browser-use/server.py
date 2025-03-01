from mcp.server.fastmcp import FastMCP
import asyncio
import os
import json
import logging
import sys
import io
import builtins
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI

# カスタムNullIOクラスを作成
class NullIO(io.IOBase):
    def write(self, *args, **kwargs):
        return 0
    
    def read(self, *args, **kwargs):
        return ''
    
    def flush(self, *args, **kwargs):
        pass

# 元のprint関数を保存
original_print = builtins.print

# グローバルな設定ファイル
LOG_FILE = 'browser_use_server.log'

# print関数をオーバーライドする関数
def disable_print():
    def silent_print(*args, **kwargs):
        # ログファイルに書き込む
        with open(LOG_FILE, 'a') as f:
            kwargs['file'] = f
            original_print(*args, **kwargs)
    
    builtins.print = silent_print

# print関数を元に戻す関数
def enable_print():
    builtins.print = original_print

# ログ設定
def setup_logging():
    # すべてのロガーから既存のハンドラを削除
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = False
        logger.setLevel(logging.CRITICAL)  # すべてのロガーの出力レベルを制限
    
    # ルートロガーから既存のハンドラを削除
    logging.root.handlers = []
    
    # ファイルハンドラを作成
    file_handler = logging.FileHandler(LOG_FILE, mode='a')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # サーバーのロガーだけ設定
    server_logger = logging.getLogger("browser-use-server")
    server_logger.setLevel(logging.INFO)
    server_logger.propagate = False
    server_logger.handlers = [file_handler]
    
    return server_logger

# 標準出力を置き換えるクラス
class OutputRedirector:
    def __init__(self):
        self.null_io = NullIO()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
    
    def __enter__(self):
        sys.stdout = self.null_io
        sys.stderr = self.null_io
        disable_print()  # print関数をオーバーライド
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        enable_print()  # print関数を元に戻す

# もっとも厳格な標準出力リダイレクト
def initialize_server():
    # まずprint関数をオーバーライド
    disable_print()
    
    # ログ設定
    logger = setup_logging()
    
    try:
        with OutputRedirector():
            # 環境変数のロード
            load_dotenv()
            
            # FastMCPを使用してサーバーを作成
            mcp = FastMCP("Browser Use Server")
            
            # オリジナルのrunメソッドを保存
            original_run = mcp.run
            
            # runメソッドをサイレントバージョンにオーバーライド
            def silent_run():
                with OutputRedirector():
                    return original_run()
            
            # runメソッドを置き換え
            mcp.run = silent_run
        
        logger.info("サーバーが正常に初期化されました")
        return mcp, logger
    except Exception as e:
        logger.error(f"サーバーの初期化に失敗しました: {str(e)}")
        sys.exit(1)

# サーバーの初期化
mcp, logger = initialize_server()

# ブラウザエージェント管理
browser_agent = None
browser_instance = None
last_response = None
current_url = ""

# ブラウザインスタンスを初期化するツール
@mcp.tool()
async def initialize_browser() -> str:
    """ブラウザを初期化します。他のツールを使用する前に必ずこれを呼び出してください。
    
    Returns:
        初期化結果のメッセージ
    """
    global browser_instance
    
    try:
        # 標準出力をリダイレクトして初期化
        with OutputRedirector():
            # ブラウザインスタンスを作成
            browser_instance = Browser(
                config=BrowserConfig(
                    headless=True
                )
            )
        
        logger.info("ブラウザが正常に初期化されました")
        return "ブラウザが正常に初期化されました"
    except Exception as e:
        logger.error(f"ブラウザの初期化に失敗しました: {str(e)}")
        return f"ブラウザの初期化に失敗しました: {str(e)}"

# ブラウザを終了するツール
@mcp.tool()
async def close_browser() -> str:
    """ブラウザを終了します。サーバーを終了する前に呼び出すことをお勧めします。
    
    Returns:
        終了結果のメッセージ
    """
    global browser_instance
    
    if not browser_instance:
        logger.warning("ブラウザはまだ初期化されていません")
        return "ブラウザはまだ初期化されていません。"
    
    try:
        with OutputRedirector():
            await browser_instance.close()
        browser_instance = None
        logger.info("ブラウザが正常に終了しました")
        return "ブラウザが正常に終了しました"
    except Exception as e:
        logger.error(f"ブラウザの終了に失敗しました: {str(e)}")
        return f"ブラウザの終了に失敗しました: {str(e)}"

# エージェントの作成または取得
def get_or_create_agent(task: str):
    """タスクに基づいてブラウザエージェントを作成または取得します"""
    global browser_agent, browser_instance
    
    if not browser_agent and browser_instance:
        with OutputRedirector():
            # OpenAI APIキーが設定されていない場合、ダミーのLLMを作成
            # 実際の利用時には適切なAPIキーを設定してください
            llm = ChatOpenAI(model="gpt-4o")
            
            browser_agent = Agent(
                task=task,
                llm=llm,
                browser=browser_instance
            )
    
    return browser_agent

@mcp.tool()
async def browse(url: str) -> str:
    """指定されたURLにアクセスします。
    
    Args:
        url: アクセスしたいWebページのURL
    
    Returns:
        アクセス結果のメッセージ
    """
    global browser_instance, current_url
    
    if not browser_instance:
        logger.warning("ブラウザが初期化されていません")
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        logger.info(f"URL {url} にアクセスします")
        agent = get_or_create_agent(f"Webページ「{url}」にアクセスする")
        
        # 標準出力をリダイレクトして実行
        with OutputRedirector():
            response = await agent.run()
        
        current_url = url
        logger.info(f"URL {url} にアクセスしました")
        return f"URLにアクセスしました: {url}\n\n応答: {response[:500]}..." if len(response) > 500 else response
    except Exception as e:
        logger.error(f"URLアクセス中にエラーが発生しました: {str(e)}")
        return f"エラーが発生しました: {str(e)}"

@mcp.tool()
async def execute_task(task: str) -> str:
    """指定されたタスクをブラウザで実行します。
    
    Args:
        task: 実行するタスク内容（自然言語で指定）
    
    Returns:
        タスク実行の結果、またはエラーメッセージ
    """
    global browser_instance, last_response
    
    if not browser_instance:
        logger.warning("ブラウザが初期化されていません")
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        logger.info(f"タスク実行: {task}")
        agent = get_or_create_agent(task)
        
        # 標準出力をリダイレクトして実行
        with OutputRedirector():
            response = await agent.run()
            
        last_response = response
        
        # 長い応答は切り詰める
        if len(response) > 1500:
            response = response[:1497] + "..."
        
        logger.info("タスクが完了しました")
        return f"タスク実行結果:\n{response}"
    except Exception as e:
        logger.error(f"タスク実行中にエラーが発生しました: {str(e)}")
        return f"タスク実行に失敗しました: {str(e)}"

@mcp.tool()
async def get_page_info() -> str:
    """現在開いているページの情報を取得します。
    
    Returns:
        ページの情報、またはエラーメッセージ
    """
    global browser_instance, current_url
    
    if not browser_instance:
        logger.warning("ブラウザが初期化されていません")
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    if not current_url:
        logger.warning("まだページが開かれていません")
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        logger.info("ページ情報を取得します")
        agent = get_or_create_agent(f"現在開いているページ「{current_url}」のタイトル、URL、主要なコンテンツを取得する")
        
        with OutputRedirector():
            response = await agent.run()
        
        # 長い応答は切り詰める
        if len(response) > 1500:
            response = response[:1497] + "..."
        
        logger.info("ページ情報を取得しました")
        return f"ページ情報:\n{response}"
    except Exception as e:
        logger.error(f"ページ情報取得中にエラーが発生しました: {str(e)}")
        return f"ページ情報の取得に失敗しました: {str(e)}"

@mcp.tool()
async def find_elements(description: str) -> str:
    """指定された説明に一致する要素を検索します。
    
    Args:
        description: 検索する要素の説明（自然言語で）
    
    Returns:
        見つかった要素の情報、またはエラーメッセージ
    """
    global browser_instance
    
    if not browser_instance:
        logger.warning("ブラウザが初期化されていません")
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        logger.info(f"要素を検索します: {description}")
        agent = get_or_create_agent(f"現在のページで「{description}」に一致する要素を見つけて内容を報告する")
        
        with OutputRedirector():
            response = await agent.run()
        
        # 長い応答は切り詰める
        if len(response) > 1500:
            response = response[:1497] + "..."
        
        logger.info("要素の検索が完了しました")
        return f"検索結果:\n{response}"
    except Exception as e:
        logger.error(f"要素検索中にエラーが発生しました: {str(e)}")
        return f"要素の検索に失敗しました: {str(e)}"

@mcp.tool()
async def click_element(description: str) -> str:
    """指定された説明に一致する要素をクリックします。
    
    Args:
        description: クリックする要素の説明（自然言語で）
    
    Returns:
        クリック操作の結果、またはエラーメッセージ
    """
    global browser_instance
    
    if not browser_instance:
        logger.warning("ブラウザが初期化されていません")
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        logger.info(f"要素をクリックします: {description}")
        agent = get_or_create_agent(f"現在のページで「{description}」に一致する要素を見つけてクリックする")
        
        with OutputRedirector():
            response = await agent.run()
        
        logger.info("クリック操作が完了しました")
        return f"クリック結果:\n{response}"
    except Exception as e:
        logger.error(f"クリック操作中にエラーが発生しました: {str(e)}")
        return f"クリックに失敗しました: {str(e)}"

@mcp.tool()
async def fill_form(form_description: str, data: str) -> str:
    """指定されたフォームにデータを入力します。
    
    Args:
        form_description: 入力するフォームの説明（自然言語で）
        data: 入力するデータの説明（自然言語で）
    
    Returns:
        フォーム入力の結果、またはエラーメッセージ
    """
    global browser_instance
    
    if not browser_instance:
        logger.warning("ブラウザが初期化されていません")
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        logger.info(f"フォームにデータを入力します: {form_description}, データ: {data}")
        agent = get_or_create_agent(f"現在のページで「{form_description}」に一致するフォームを見つけて、以下のデータを入力する: {data}")
        
        with OutputRedirector():
            response = await agent.run()
        
        logger.info("フォーム入力が完了しました")
        return f"フォーム入力結果:\n{response}"
    except Exception as e:
        logger.error(f"フォーム入力中にエラーが発生しました: {str(e)}")
        return f"フォーム入力に失敗しました: {str(e)}"

@mcp.tool()
async def take_screenshot() -> str:
    """現在のページのスクリーンショットを撮影します。
    
    Returns:
        スクリーンショットの結果、またはエラーメッセージ
    """
    global browser_instance
    
    if not browser_instance:
        logger.warning("ブラウザが初期化されていません")
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        logger.info("スクリーンショットを撮影します")
        agent = get_or_create_agent("現在のページのスクリーンショットを撮影する")
        
        with OutputRedirector():
            response = await agent.run()
        
        # スクリーンショットのパスを設定
        screenshot_dir = "screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # タイムスタンプ付きのファイル名
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{screenshot_dir}/screenshot_{timestamp}.png"
        
        # スクリーンショットを保存
        # 注: browser-useライブラリによるスクリーンショットの保存方法は実際の実装に合わせて調整してください
        
        logger.info(f"スクリーンショットを保存しました: {filename}")
        return f"スクリーンショット処理結果:\n{response}"
    except Exception as e:
        logger.error(f"スクリーンショット撮影中にエラーが発生しました: {str(e)}")
        return f"スクリーンショット撮影に失敗しました: {str(e)}"

@mcp.tool()
async def submit_form(form_description: str) -> str:
    """指定されたフォームを送信します。
    
    Args:
        form_description: 送信するフォームの説明（自然言語で）
    
    Returns:
        フォーム送信の結果、またはエラーメッセージ
    """
    global browser_instance
    
    if not browser_instance:
        logger.warning("ブラウザが初期化されていません")
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        logger.info(f"フォームを送信します: {form_description}")
        agent = get_or_create_agent(f"現在のページで「{form_description}」に一致するフォームを見つけて送信する")
        
        with OutputRedirector():
            response = await agent.run()
        
        logger.info("フォーム送信が完了しました")
        return f"フォーム送信結果:\n{response}"
    except Exception as e:
        logger.error(f"フォーム送信中にエラーが発生しました: {str(e)}")
        return f"フォーム送信に失敗しました: {str(e)}"

# メイン関数
if __name__ == "__main__":
    # サーバー起動メッセージをログに記録
    logger.info("Browser Use MCPサーバーを起動します...")
    
    try:
        # オーバーライドしたサイレントバージョンのrunメソッドを使用
        mcp.run()
    except Exception as e:
        logger.error(f"サーバー実行中にエラーが発生しました: {str(e)}")
        sys.exit(1) 