import asyncio
from mcp.client import MCPClient

async def test_browser_use():
    """browser-useサーバーの機能をテストするサンプルコード"""
    
    # MCPクライアントを初期化
    client = MCPClient(server_name="browser-use")
    
    try:
        # 0. ブラウザを初期化
        print("0. ブラウザを初期化します...")
        init_result = await client.call("initialize_browser")
        print(init_result)
        
        # 1. Googleにアクセス
        print("\n1. Google.comにアクセスします...")
        result = await client.call("browse", url="https://www.google.com")
        print(result)
        
        # 2. ページ情報を取得
        print("\n2. ページ情報を取得します...")
        info = await client.call("get_page_info")
        print(info)
        
        # 3. 検索フォームを検索
        print("\n3. 検索フォームを検索します...")
        search_elements = await client.call("find_elements", description="検索フォーム")
        print(search_elements)
        
        # 4. フォームに入力
        print("\n4. 検索フォームに「browser-use python」と入力します...")
        await client.call("fill_form", form_description="検索フォーム", data="browser-use python")
        
        # 5. スクリーンショットを撮影
        print("\n5. 入力後の状態をスクリーンショットで保存します...")
        screenshot = await client.call("take_screenshot")
        print(screenshot)
        
        # 6. フォームを送信
        print("\n6. 検索フォームを送信します...")
        submit_result = await client.call("submit_form", form_description="検索フォーム")
        print(submit_result)
        
        # 7. 複合タスクを実行
        print("\n7. 複合タスクを実行します...")
        complex_task = await client.call(
            "execute_task",
            task="検索結果から最初の3つのリンクのタイトルを抽出して、それらを箇条書きで返してください"
        )
        print(complex_task)
        
        # 8. 要素をクリック
        print("\n8. 最初の検索結果をクリックします...")
        click_result = await client.call("click_element", description="最初の検索結果")
        print(click_result)
        
        # 9. 最終ページの情報を取得
        print("\n9. 遷移先ページの情報を取得します...")
        final_info = await client.call("get_page_info")
        print(final_info)
    
    finally:
        # 10. ブラウザを終了
        print("\n10. ブラウザを終了します...")
        close_result = await client.call("close_browser")
        print(close_result)

if __name__ == "__main__":
    # 非同期関数を実行
    asyncio.run(test_browser_use()) 