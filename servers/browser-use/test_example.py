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
    click = Tool("click")
    type_text = Tool("type_text")
    take_screenshot = Tool("take_screenshot")
    execute_javascript = Tool("execute_javascript")
    submit_form = Tool("submit_form")
    
    # 1. URLにアクセス
    print("1. Google.comにアクセスします...")
    result = await browse(url="https://www.google.com")
    print(result)
    
    # 2. ページタイトルを取得
    print("\n2. ページタイトルを取得します...")
    title = await get_page_title()
    print(title)
    
    # 3. 現在のURLを確認
    print("\n3. 現在のURLを確認します...")
    current_url = await get_current_url()
    print(current_url)
    
    # 4. 検索フォームに入力
    print("\n4. 検索フォームに「Playwright Python」と入力します...")
    await type_text("input[name='q']", "Playwright Python")
    
    # 5. セレクタを使って要素を検索
    print("\n5. 検索ボタンを検索します...")
    elements = await find_elements("input[type='submit']")
    print(elements)
    
    # 6. スクリーンショットを撮影
    print("\n6. 入力前の状態をスクリーンショットで保存します...")
    screenshot = await take_screenshot()
    print(screenshot)
    
    # 7. JavaScriptを実行してドキュメントタイトルを取得
    print("\n7. JavaScriptを実行してタイトルを取得します...")
    js_result = await execute_javascript("return document.title")
    print(js_result)
    
    # 8. 検索フォームを送信
    print("\n8. 検索フォームを送信します...")
    await submit_form("form")
    print("フォームを送信しました")
    
    # 9. 結果ページを表示
    print("\n9. 検索結果ページが表示されました")
    
    # 10. 結果ページのタイトルを取得
    print("\n10. 結果ページのタイトルを取得します...")
    title = await get_page_title()
    print(title)
    
    # 11. 検索結果の要素を検索
    print("\n11. 検索結果の要素を検索します...")
    results = await find_elements("h3")
    print(results)
    
    # 12. ページ内容を取得
    print("\n12. ページ内容を取得します...")
    content = await get_page_content()
    print(content[:200] + "...") # 長いので最初の部分だけ表示

if __name__ == "__main__":
    # 非同期関数を実行
    asyncio.run(test_browser_use()) 