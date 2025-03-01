from mcp.server.fastmcp import FastMCP
import asyncio
import os
import json
import re
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Page, Browser

# FastMCPを使用してサーバーを作成
mcp = FastMCP("Browser Use Server")

# ブラウザセッション管理
browser_instance = None
current_page = None

# サーバー初期化
@mcp.on_startup
async def startup():
    """サーバー起動時にブラウザを初期化します"""
    global browser_instance
    
    playwright = await async_playwright().start()
    browser_instance = await playwright.chromium.launch(headless=True)
    
    print("ブラウザが初期化されました")

# サーバー終了時の処理
@mcp.on_shutdown
async def shutdown():
    """サーバー終了時にブラウザを閉じます"""
    global browser_instance
    
    if browser_instance:
        await browser_instance.close()
        print("ブラウザが正常に終了しました")

# ページ取得または新規作成
async def get_or_create_page() -> Page:
    """現在のページを取得、または新しいページを作成します"""
    global browser_instance, current_page
    
    if not browser_instance:
        print("ブラウザを起動しています...")
        playwright = await async_playwright().start()
        browser_instance = await playwright.chromium.launch(headless=True)
    
    if not current_page:
        print("新しいページを作成しています...")
        current_page = await browser_instance.new_page()
    
    return current_page

@mcp.tool()
async def browse(url: str) -> str:
    """指定されたURLにアクセスします。
    
    Args:
        url: アクセスしたいWebページのURL
    
    Returns:
        アクセス結果のメッセージ
    """
    global current_page
    
    try:
        page = await get_or_create_page()
        await page.goto(url, wait_until="domcontentloaded")
        return f"URLにアクセスしました: {url}"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

@mcp.tool()
async def get_page_title() -> str:
    """現在開いているページのタイトルを取得します。
    
    Returns:
        ページのタイトル、またはエラーメッセージ
    """
    global current_page
    
    if not current_page:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        title = await current_page.title()
        return f"ページタイトル: {title}"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

@mcp.tool()
async def get_page_content() -> str:
    """現在開いているページのテキスト内容を取得します。
    
    Returns:
        ページのテキスト内容、またはエラーメッセージ
    """
    global current_page
    
    if not current_page:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        # ページ上のテキストコンテンツを取得
        content = await current_page.evaluate('() => document.body.innerText')
        
        # 長いコンテンツは切り詰める
        if len(content) > 1500:
            content = content[:1497] + "..."
        
        return f"ページ内容:\n{content}"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

@mcp.tool()
async def find_elements(selector: str) -> str:
    """現在のページから指定されたCSSセレクタに一致する要素を検索します。
    
    Args:
        selector: 検索するCSSセレクタ
    
    Returns:
        見つかった要素のテキスト、またはエラーメッセージ
    """
    global current_page
    
    if not current_page:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        # セレクタに一致する要素を取得
        elements = await current_page.query_selector_all(selector)
        
        if not elements:
            return f"セレクタ '{selector}' に一致する要素は見つかりませんでした。"
        
        # 最大5つの要素を表示
        result = []
        for i, element in enumerate(elements[:5]):
            text = await element.text_content()
            text = text.strip()
            if text:
                result.append(f"{i+1}. {text[:100]}..." if len(text) > 100 else f"{i+1}. {text}")
        
        total = len(elements)
        more_info = f"\n\n合計 {total} 個の要素が見つかりました。" if total > 5 else ""
        
        return f"セレクタ '{selector}' の検索結果:\n" + "\n".join(result) + more_info
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

@mcp.tool()
async def get_current_url() -> str:
    """現在開いているページのURLを取得します。
    
    Returns:
        現在のURL、またはエラーメッセージ
    """
    global current_page
    
    if not current_page:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        url = current_page.url
        return f"現在のURL: {url}"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

@mcp.tool()
async def click(selector: str) -> str:
    """指定されたセレクタに一致する要素をクリックします。
    
    Args:
        selector: クリックする要素のCSSセレクタ
    
    Returns:
        クリック操作の結果、またはエラーメッセージ
    """
    global current_page
    
    if not current_page:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        await current_page.click(selector)
        return f"セレクタ '{selector}' の要素をクリックしました。"
    except Exception as e:
        return f"クリックに失敗しました: {str(e)}"

@mcp.tool()
async def type_text(selector: str, text: str) -> str:
    """指定されたセレクタの要素にテキストを入力します。
    
    Args:
        selector: 入力フィールドのCSSセレクタ
        text: 入力するテキスト
    
    Returns:
        入力操作の結果、またはエラーメッセージ
    """
    global current_page
    
    if not current_page:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        await current_page.fill(selector, text)
        return f"セレクタ '{selector}' の要素に「{text}」を入力しました。"
    except Exception as e:
        return f"テキスト入力に失敗しました: {str(e)}"

@mcp.tool()
async def take_screenshot() -> str:
    """現在のページのスクリーンショットを撮影します。
    
    Returns:
        スクリーンショットの結果、またはエラーメッセージ
    """
    global current_page
    
    if not current_page:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        # スクリーンショットのパスを設定
        screenshot_dir = "screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # タイムスタンプ付きのファイル名
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{screenshot_dir}/screenshot_{timestamp}.png"
        
        # スクリーンショットを撮影
        await current_page.screenshot(path=filename)
        
        return f"スクリーンショットを保存しました: {filename}"
    except Exception as e:
        return f"スクリーンショット撮影に失敗しました: {str(e)}"

@mcp.tool()
async def execute_javascript(script: str) -> str:
    """ページ上でJavaScriptを実行します。
    
    Args:
        script: 実行するJavaScriptコード
    
    Returns:
        JavaScriptの実行結果、またはエラーメッセージ
    """
    global current_page
    
    if not current_page:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        # JavaScriptを実行
        result = await current_page.evaluate(script)
        
        # 結果を文字列に変換
        if result is None:
            return "JavaScriptが実行されました。(戻り値なし)"
        
        if isinstance(result, (dict, list)):
            result_str = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            result_str = str(result)
        
        return f"JavaScript実行結果:\n{result_str}"
    except Exception as e:
        return f"JavaScript実行に失敗しました: {str(e)}"

@mcp.tool()
async def submit_form(selector: str) -> str:
    """指定されたフォームを送信します。
    
    Args:
        selector: フォームのCSSセレクタ
    
    Returns:
        フォーム送信の結果、またはエラーメッセージ
    """
    global current_page
    
    if not current_page:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        await current_page.evaluate(f"document.querySelector('{selector}').submit()")
        await current_page.wait_for_load_state("networkidle")
        return f"フォーム '{selector}' を送信しました。"
    except Exception as e:
        return f"フォーム送信に失敗しました: {str(e)}"

# メイン関数
if __name__ == "__main__":
    # サーバーを実行
    mcp.run() 