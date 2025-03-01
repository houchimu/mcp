from mcp.server.fastmcp import FastMCP
import asyncio
import os
import json
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI

# 環境変数のロード
load_dotenv()

# FastMCPを使用してサーバーを作成
mcp = FastMCP("Browser Use Server")

# ブラウザエージェント管理
browser_agent = None
browser_instance = None
last_response = None
current_url = ""

# サーバー初期化
@mcp.on_startup
async def startup():
    """サーバー起動時にブラウザを初期化します"""
    global browser_instance
    
    # ブラウザインスタンスを作成
    browser_instance = Browser(
        config=BrowserConfig(
            headless=True
        )
    )
    
    print("ブラウザが初期化されました")

# サーバー終了時の処理
@mcp.on_shutdown
async def shutdown():
    """サーバー終了時にブラウザを閉じます"""
    global browser_instance
    
    if browser_instance:
        await browser_instance.close()
        print("ブラウザが正常に終了しました")

# エージェントの作成または取得
def get_or_create_agent(task: str):
    """タスクに基づいてブラウザエージェントを作成または取得します"""
    global browser_agent, browser_instance
    
    if not browser_agent:
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
    global browser_instance, last_response
    
    if not browser_instance:
        return "まだブラウザが初期化されていません。"
    
    try:
        agent = get_or_create_agent(task)
        response = await agent.run()
        last_response = response
        
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
        return "まだブラウザが初期化されていません。"
    
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
        return "まだブラウザが初期化されていません。"
    
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
        return "まだブラウザが初期化されていません。"
    
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
        return "まだブラウザが初期化されていません。"
    
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
        return "まだブラウザが初期化されていません。"
    
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
        
        # スクリーンショットを保存
        # 注: browser-useライブラリによるスクリーンショットの保存方法は実際の実装に合わせて調整してください
        
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
        return "まだブラウザが初期化されていません。"
    
    try:
        agent = get_or_create_agent(f"現在のページで「{form_description}」に一致するフォームを見つけて送信する")
        response = await agent.run()
        
        return f"フォーム送信結果:\n{response}"
    except Exception as e:
        return f"フォーム送信に失敗しました: {str(e)}"

# メイン関数
if __name__ == "__main__":
    # サーバーを実行
    mcp.run() 