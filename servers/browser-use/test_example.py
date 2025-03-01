import asyncio
from mcp.client import Tool

async def test_browser_use():
    """browser-useサーバーの機能をテストするサンプルコード"""
    
    # ツールのインスタンスを作成
    browse = Tool("browse")
    get_page_title = Tool("get_page_title")
    get_page_content = Tool("get_page_content")
    find_elements = Tool("find_elements")
    get_current_url = Tool("get_current_url")
    
    # 1. URLにアクセス
    result = await browse(url="https://example.com")
    print(result)
    
    # 2. ページタイトルを取得
    title = await get_page_title()
    print(title)
    
    # 3. 現在のURLを確認
    current_url = await get_current_url()
    print(current_url)
    
    # 4. セレクタを使って要素を検索
    elements = await find_elements(selector="h1")
    print(elements)
    
    # 5. ページ内容を取得
    content = await get_page_content()
    print(content[:150] + "...") # 長いので最初の部分だけ表示
    
    # 6. 存在しないURLにアクセスしてエラー処理を確認
    try:
        result = await browse(url="https://this-url-does-not-exist-123456789.com")
        print(result)
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    # 非同期関数を実行
    asyncio.run(test_browser_use()) 