from mcp.server.fastmcp import FastMCP
import os
import asyncio
import sys
import logging
import io
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI

# ------ ロギング関連の設定 -------
# すべてのロガーを無効化
logging.basicConfig(level=logging.CRITICAL)

# すべての既存ロガーを無効化
for name in logging.root.manager.loggerDict:
    logger = logging.getLogger(name)
    logger.handlers = []
    logger.propagate = False
    logger.setLevel(logging.CRITICAL)

# ルートロガーからすべてのハンドラを削除
logging.root.handlers = []

# FastMCPに関連するモジュールのロガーを明示的に無効化
critical_loggers = [
    "uvicorn", 
    "uvicorn.error", 
    "uvicorn.access", 
    "uvicorn.asgi",
    "starlette", 
    "starlette.routing",
    "mcp",
    "mcp.server",
    "browser_use",
    "playwright",
    "fastapi"
]

for logger_name in critical_loggers:
    logger = logging.getLogger(logger_name)
    logger.handlers = []
    logger.propagate = False
    logger.disabled = True
    logger.setLevel(logging.CRITICAL)

# NullIO - 出力を完全に捨てるためのIO
class NullIO(io.IOBase):
    def write(self, *args, **kwargs):
        return 0
    
    def read(self, *args, **kwargs):
        return ''
    
    def flush(self, *args, **kwargs):
        pass

# 標準出力をリダイレクト
sys.stdout = NullIO()
sys.stderr = NullIO()

# 環境変数をロード
load_dotenv()

# FastMCP サーバーの作成 - デバッグモードを無効にし、ログレベルを CRITICAL に設定
# CRITICAL は最も高いロギングレベルで、ほとんどのメッセージを抑制します
mcp = FastMCP(
    "Browser Use Server",
    settings={
        "debug": False,
        "log_level": "critical"  # UvicornとStarletteのログレベルを最も制限
    }
)

# ブラウザエージェント管理
browser_agent = None
browser_instance = None
current_url = ""

# エージェントの作成または取得
def get_or_create_agent(task: str):
    """タスクに基づいてブラウザエージェントを作成または取得します"""
    global browser_agent, browser_instance
    
    if not browser_agent and browser_instance:
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
async def initialize_browser() -> str:
    """ブラウザを初期化します。他のツールを使用する前に必ずこれを呼び出してください。
    
    Returns:
        初期化結果のメッセージ
    """
    global browser_instance
    
    try:
        # ブラウザインスタンスを作成
        browser_instance = Browser(
            config=BrowserConfig(
                headless=True
            )
        )
        
        return "ブラウザが正常に初期化されました"
    except Exception as e:
        return f"ブラウザの初期化に失敗しました: {str(e)}"

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
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        agent = get_or_create_agent(f"Webページ「{url}」にアクセスする")
        response = await agent.run()
        
        current_url = url
        return f"URLにアクセスしました: {url}\n\n応答: {response[:500]}..." if len(response) > 500 else response
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

@mcp.tool()
async def execute_task(task: str) -> str:
    """指定されたタスクをブラウザで実行します。
    
    Args:
        task: 実行するタスク内容（自然言語で指定）
    
    Returns:
        タスク実行の結果、またはエラーメッセージ
    """
    global browser_instance
    
    if not browser_instance:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        agent = get_or_create_agent(task)
        response = await agent.run()
        
        # 長い応答は切り詰める
        if len(response) > 1500:
            response = response[:1497] + "..."
        
        return f"タスク実行結果:\n{response}"
    except Exception as e:
        return f"タスク実行に失敗しました: {str(e)}"

@mcp.tool()
async def get_page_info() -> str:
    """現在開いているページの情報を取得します。
    
    Returns:
        ページの情報、またはエラーメッセージ
    """
    global browser_instance, current_url
    
    if not browser_instance:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    if not current_url:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        agent = get_or_create_agent(f"現在開いているページ「{current_url}」のタイトル、URL、主要なコンテンツを取得する")
        response = await agent.run()
        
        # 長い応答は切り詰める
        if len(response) > 1500:
            response = response[:1497] + "..."
        
        return f"ページ情報:\n{response}"
    except Exception as e:
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
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        agent = get_or_create_agent(f"現在のページで「{description}」に一致する要素を見つけて内容を報告する")
        response = await agent.run()
        
        # 長い応答は切り詰める
        if len(response) > 1500:
            response = response[:1497] + "..."
        
        return f"検索結果:\n{response}"
    except Exception as e:
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
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        agent = get_or_create_agent(f"現在のページで「{description}」に一致する要素を見つけてクリックする")
        response = await agent.run()
        
        return f"クリック結果:\n{response}"
    except Exception as e:
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
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        agent = get_or_create_agent(f"現在のページで「{form_description}」に一致するフォームを見つけて、以下のデータを入力する: {data}")
        response = await agent.run()
        
        return f"フォーム入力結果:\n{response}"
    except Exception as e:
        return f"フォーム入力に失敗しました: {str(e)}"

@mcp.tool()
async def take_screenshot() -> str:
    """現在のページのスクリーンショットを撮影します。
    
    Returns:
        スクリーンショットの結果、またはエラーメッセージ
    """
    global browser_instance
    
    if not browser_instance:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        agent = get_or_create_agent("現在のページのスクリーンショットを撮影する")
        response = await agent.run()
        
        # スクリーンショットのパスを設定
        screenshot_dir = "screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # タイムスタンプ付きのファイル名
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{screenshot_dir}/screenshot_{timestamp}.png"
        
        return f"スクリーンショット処理結果:\n{response}"
    except Exception as e:
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
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        agent = get_or_create_agent(f"現在のページで「{form_description}」に一致するフォームを見つけて送信する")
        response = await agent.run()
        
        return f"フォーム送信結果:\n{response}"
    except Exception as e:
        return f"フォーム送信に失敗しました: {str(e)}"

# メイン関数
if __name__ == "__main__":
    try:
        # シンプルな実行
        mcp.run()
    except Exception as e:
        # 例外情報をファイルに記録（デバッグ用）
        with open("browser_use_error.log", "a") as f:
            f.write(f"{str(e)}\n")
        sys.exit(1) 