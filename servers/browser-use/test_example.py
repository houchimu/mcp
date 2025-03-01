import asyncio
from mcp.client import Tool

async def test_browser_use():
    """browser-useサーバーの機能をテストするサンプルコード"""
    
    # ツールのインスタンスを作成
    browse = Tool("browse")
    execute_task = Tool("execute_task")
    get_page_info = Tool("get_page_info")
    find_elements = Tool("find_elements")
    click_element = Tool("click_element")
    fill_form = Tool("fill_form")
    take_screenshot = Tool("take_screenshot")
    submit_form = Tool("submit_form")
    
    # 1. Googleにアクセス
    print("1. Google.comにアクセスします...")
    result = await browse(url="https://www.google.com")
    print(result)
    
    # 2. ページ情報を取得
    print("\n2. ページ情報を取得します...")
    info = await get_page_info()
    print(info)
    
    # 3. 検索フォームを検索
    print("\n3. 検索フォームを検索します...")
    search_elements = await find_elements(description="検索フォーム")
    print(search_elements)
    
    # 4. フォームに入力
    print("\n4. 検索フォームに「browser-use python」と入力します...")
    await fill_form(form_description="検索フォーム", data="browser-use python")
    
    # 5. スクリーンショットを撮影
    print("\n5. 入力後の状態をスクリーンショットで保存します...")
    screenshot = await take_screenshot()
    print(screenshot)
    
    # 6. フォームを送信
    print("\n6. 検索フォームを送信します...")
    submit_result = await submit_form(form_description="検索フォーム")
    print(submit_result)
    
    # 7. 複合タスクを実行
    print("\n7. 複合タスクを実行します...")
    complex_task = await execute_task(
        task="検索結果から最初の3つのリンクのタイトルを抽出して、それらを箇条書きで返してください"
    )
    print(complex_task)
    
    # 8. 要素をクリック
    print("\n8. 最初の検索結果をクリックします...")
    click_result = await click_element(description="最初の検索結果")
    print(click_result)
    
    # 9. 最終ページの情報を取得
    print("\n9. 遷移先ページの情報を取得します...")
    final_info = await get_page_info()
    print(final_info)

if __name__ == "__main__":
    # 非同期関数を実行
    asyncio.run(test_browser_use()) 