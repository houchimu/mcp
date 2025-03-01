from mcp.server.fastmcp import FastMCP
import asyncio
import httpx
from typing import Optional, Dict, Any, List

# FastMCPを使用してサーバーを作成
mcp = FastMCP("Browser Use Server")

# ブラウザセッションを模擬するための変数
current_page = {
    "url": "",
    "title": "",
    "content": "",
    "html": ""
}

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
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # ページ情報を更新
            current_page["url"] = url
            current_page["title"] = extract_title(response.text)
            current_page["content"] = extract_text_content(response.text)
            current_page["html"] = response.text
            
            return f"URLにアクセスしました: {url}"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

@mcp.tool()
async def get_page_title() -> str:
    """現在開いているページのタイトルを取得します。
    
    Returns:
        ページのタイトル、またはエラーメッセージ
    """
    if not current_page["url"]:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    return f"ページタイトル: {current_page['title']}"

@mcp.tool()
async def get_page_content() -> str:
    """現在開いているページのテキスト内容を取得します。
    
    Returns:
        ページのテキスト内容、またはエラーメッセージ
    """
    if not current_page["url"]:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    # 長いコンテンツは切り詰める
    content = current_page["content"]
    if len(content) > 1000:
        content = content[:997] + "..."
    
    return f"ページ内容:\n{content}"

@mcp.tool()
async def find_elements(selector: str) -> str:
    """現在のページから指定されたCSSセレクタに一致する要素を検索します。
    
    Args:
        selector: 検索するCSSセレクタ
    
    Returns:
        見つかった要素のテキスト、またはエラーメッセージ
    """
    if not current_page["url"]:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        # 実際には、BeautifulSoupなどを使って要素を検索する処理を実装します
        # ここでは簡易的な実装としています
        return f"セレクタ '{selector}' の検索結果:\n" + \
               f"（注: この機能は簡易的な実装です。実際のDOM解析には追加の実装が必要です）"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

@mcp.tool()
async def get_current_url() -> str:
    """現在開いているページのURLを取得します。
    
    Returns:
        現在のURL、またはエラーメッセージ
    """
    if not current_page["url"]:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    return f"現在のURL: {current_page['url']}"

# HTMLからタイトルを抽出するヘルパー関数
def extract_title(html: str) -> str:
    """HTMLからタイトルを抽出する簡易関数"""
    start = html.find("<title>")
    if start == -1:
        return "タイトルなし"
    
    start += 7  # <title>の長さ
    end = html.find("</title>", start)
    if end == -1:
        return "タイトルなし"
    
    return html[start:end].strip()

# HTMLからテキスト内容を抽出するヘルパー関数（簡易版）
def extract_text_content(html: str) -> str:
    """HTMLからテキスト内容を抽出する簡易関数"""
    # 実際のプロダクションコードでは、BeautifulSoupなどのパーサーを使用すべきです
    # 以下は非常に簡易的な実装です
    result = html
    
    # タグを除去（簡易的な実装）
    while "<" in result and ">" in result:
        start = result.find("<")
        end = result.find(">", start)
        if start == -1 or end == -1:
            break
        result = result[:start] + " " + result[end+1:]
    
    # 連続する空白を1つに
    import re
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result

# メイン関数
if __name__ == "__main__":
    # サーバーを実行
    mcp.run() 