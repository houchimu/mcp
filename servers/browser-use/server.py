from mcp.server.fastmcp import FastMCP
import os
import asyncio
import sys
import logging
import io
import builtins
import json
from contextlib import redirect_stdout, redirect_stderr
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, Browser

# サーバー起動前の準備
# -------------------------------

# 元のprint関数を保存
original_print = builtins.print

# 無効なprint関数
def noop_print(*args, **kwargs):
    pass

# printを無効化
builtins.print = noop_print

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
    def write(self, *args, **kwargs):
        return 0
    
    def read(self, *args, **kwargs):
        return ''
    
    def flush(self, *args, **kwargs):
        pass

# 標準出力をリダイレクト
sys.stdout = NullIO()
sys.stderr = NullIO()

# asyncioのデバッグを無効化
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# 環境変数をロード
load_dotenv()

# サーバー設定
# -------------------------------

# FastMCP サーバーの作成 - 最小限の設定
mcp = FastMCP(
    "Browser Use Server",
)

# Playwrightセッション管理
playwright = None
browser = None
page = None
current_url = ""

# サーバーツール定義 
# -------------------------------

@mcp.tool()
async def initialize_browser() -> str:
    """ブラウザを初期化します。他のツールを使用する前に必ずこれを呼び出してください。
    
    Returns:
        初期化結果のメッセージ
    """
    global playwright, browser, page
    
    try:
        # 既存のインスタンスをクローズ
        if page:
            await page.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
            
        # Playwrightを起動
        playwright = await async_playwright().start()
        # Chromiumブラウザを起動（ヘッドレスモード）
        browser = await playwright.chromium.launch(headless=True)
        # 新しいページを開く
        page = await browser.new_page()
        
        return "ブラウザが正常に初期化されました"
    except Exception as e:
        # エラーをキャッチしてメッセージを返す
        return f"ブラウザの初期化に失敗しました: {str(e)}"

@mcp.tool()
async def browse(url: str) -> str:
    """指定されたURLにアクセスします。
    
    Args:
        url: アクセスしたいWebページのURL
    
    Returns:
        アクセス結果のメッセージ
    """
    global page, current_url
    
    if not page:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        # URLに移動
        await page.goto(url, wait_until="networkidle")
        current_url = url
        
        # ページタイトルを取得
        title = await page.title()
        
        # ページコンテンツの一部を取得
        content = await page.content()
        content_preview = content[:500] + "..." if len(content) > 500 else content
        
        return f"URLにアクセスしました: {url}\nタイトル: {title}\n\nページプレビュー: {content_preview}"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

@mcp.tool()
async def execute_task(task: str) -> str:
    """指定されたタスクをブラウザで実行します。
    
    Args:
        task: 実行するタスク内容（例: 「検索ボタンをクリック」「ログインフォームに入力」など）
    
    Returns:
        タスク実行の結果、またはエラーメッセージ
    """
    global page
    
    if not page:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        # タスクを解析して実行（基本的な例）
        if "クリック" in task or "click" in task.lower():
            # クリック操作を想定したテキスト解析（簡易版）
            element_text = task.split("クリック")[0].strip()
            if not element_text:
                element_text = task.lower().split("click")[0].strip()
            
            # テキストに一致する要素をクリック
            await page.click(f"text={element_text}")
            return f"「{element_text}」をクリックしました"
            
        elif "入力" in task or "type" in task.lower() or "fill" in task.lower():
            # 入力操作の簡易解析
            parts = task.split("入力")
            if len(parts) < 2:
                parts = task.lower().split("type")
            if len(parts) < 2:
                parts = task.lower().split("fill")
            
            if len(parts) >= 2:
                field = parts[0].strip()
                text = parts[1].strip()
                
                # 指定されたフィールドに入力
                await page.fill(f"input[placeholder*='{field}'], textarea[placeholder*='{field}'], [aria-label*='{field}']", text)
                return f"「{field}」に「{text}」を入力しました"
            
        # その他のタスクは単純なスクリーンショットを撮って返す
        screenshot_path = "screenshot.png"
        await page.screenshot(path=screenshot_path)
        
        return f"タスク「{task}」を実行し、スクリーンショットを保存しました: {screenshot_path}"
    except Exception as e:
        return f"タスク実行に失敗しました: {str(e)}"

@mcp.tool()
async def get_page_info() -> str:
    """現在開いているページの情報を取得します。
    
    Returns:
        ページの情報、またはエラーメッセージ
    """
    global page, current_url
    
    if not page:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    if not current_url:
        return "まだページが開かれていません。browse()を使用してURLにアクセスしてください。"
    
    try:
        # ページタイトルを取得
        title = await page.title()
        
        # 現在のURL
        url = page.url
        
        # メタディスクリプションを取得
        description = await page.evaluate("() => { const meta = document.querySelector('meta[name=\"description\"]'); return meta ? meta.getAttribute('content') : ''; }")
        
        # メインコンテンツを取得 (h1, h2, pタグなど)
        headings = await page.evaluate("""() => {
            const h1s = Array.from(document.querySelectorAll('h1')).map(h => h.innerText);
            const h2s = Array.from(document.querySelectorAll('h2')).slice(0, 3).map(h => h.innerText);
            return { h1s, h2s };
        }""")
        
        # 結果をフォーマット
        result = f"ページ情報:\n"
        result += f"タイトル: {title}\n"
        result += f"URL: {url}\n"
        result += f"説明: {description}\n\n"
        
        result += "見出し:\n"
        if headings['h1s']:
            result += "H1: " + "\n    ".join(headings['h1s']) + "\n"
        if headings['h2s']:
            result += "H2: " + "\n    ".join(headings['h2s']) + "\n"
        
        return result
    except Exception as e:
        return f"ページ情報の取得に失敗しました: {str(e)}"

@mcp.tool()
async def find_elements(selector: str) -> str:
    """指定されたセレクタに一致する要素を検索します。
    
    Args:
        selector: CSSセレクタまたはテキスト（例: 'div.content', 'button', 'text=ログイン'）
    
    Returns:
        見つかった要素の情報、またはエラーメッセージ
    """
    global page
    
    if not page:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        # セレクタが「text=」で始まっていない場合は追加
        if not selector.startswith("text=") and not any(char in selector for char in "[]#.:>+"):
            selector = f"text={selector}"
        
        # 要素を検索
        elements = await page.$$(selector)
        
        if not elements:
            return f"セレクタ '{selector}' に一致する要素は見つかりませんでした。"
        
        # 最大10個の要素情報を収集
        result = []
        for i, element in enumerate(elements[:10]):
            # 要素のテキストを取得
            text = await page.evaluate("el => el.textContent", element)
            # 要素のタグ名を取得
            tag_name = await page.evaluate("el => el.tagName", element)
            # 要素の属性を取得
            attrs = await page.evaluate("""el => {
                const result = {};
                for (const attr of el.attributes) {
                    result[attr.name] = attr.value;
                }
                return result;
            }""", element)
            
            # 結果に追加
            result.append({
                "index": i + 1,
                "tag": tag_name,
                "text": text.strip() if text else "",
                "attributes": attrs
            })
        
        # 結果をフォーマット
        output = f"検索結果: {len(elements)} 要素が見つかりました (最大10件表示)\n\n"
        
        for item in result:
            output += f"{item['index']}. <{item['tag'].lower()}"
            
            # 主要な属性を表示
            if 'id' in item['attributes']:
                output += f" id=\"{item['attributes']['id']}\""
            if 'class' in item['attributes']:
                output += f" class=\"{item['attributes']['class']}\""
            
            output += ">\n"
            output += f"   テキスト: {item['text'][:100]}{'...' if len(item['text']) > 100 else ''}\n"
            
            # 追加の重要な属性を表示
            for key in ['href', 'src', 'value', 'type', 'name']:
                if key in item['attributes']:
                    output += f"   {key}: {item['attributes'][key]}\n"
            
            output += "\n"
        
        return output
    except Exception as e:
        return f"要素の検索に失敗しました: {str(e)}"

@mcp.tool()
async def click_element(selector: str) -> str:
    """指定されたセレクタに一致する要素をクリックします。
    
    Args:
        selector: クリックする要素のCSSセレクタまたはテキスト
    
    Returns:
        クリック操作の結果、またはエラーメッセージ
    """
    global page
    
    if not page:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        # セレクタが「text=」で始まっていない場合は追加
        if not selector.startswith("text=") and not any(char in selector for char in "[]#.:>+"):
            selector = f"text={selector}"
        
        # 要素が見つかるまで待機してからクリック
        await page.wait_for_selector(selector, timeout=5000)
        await page.click(selector)
        
        # クリック後のページタイトルを取得
        title = await page.title()
        current_url = page.url
        
        return f"要素 '{selector}' をクリックしました\n新しいページ: {title} ({current_url})"
    except Exception as e:
        return f"クリックに失敗しました: {str(e)}"

@mcp.tool()
async def fill_form(selector: str, text: str) -> str:
    """指定されたセレクタに一致するフォーム要素にテキストを入力します。
    
    Args:
        selector: 入力フィールドのCSSセレクタまたはラベルテキスト
        text: 入力するテキスト
    
    Returns:
        フォーム入力の結果、またはエラーメッセージ
    """
    global page
    
    if not page:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        # セレクタをテキストベースに変換（必要な場合）
        if not any(char in selector for char in "[]#.:>+"):
            # 入力フィールドの一般的なセレクタパターンを試行
            try:
                # ラベルに基づくセレクタ
                await page.wait_for_selector(f"text={selector}", timeout=1000)
                label_element = await page.query_selector(f"text={selector}")
                
                if label_element:
                    # ラベルのforを確認
                    for_id = await page.evaluate("""el => {
                        if (el.getAttribute('for')) return el.getAttribute('for');
                        return null;
                    }""", label_element)
                    
                    if for_id:
                        selector = f"#{for_id}"
                    else:
                        # ラベルに関連する入力を探す
                        selector = f"label:has-text('{selector}') input, label:has-text('{selector}') textarea"
                else:
                    # プレースホルダ属性で探す
                    selector = f"input[placeholder*='{selector}'], textarea[placeholder*='{selector}']"
            except:
                # 直接的なテキストセレクタに戻る
                selector = f"input[placeholder*='{selector}'], textarea[placeholder*='{selector}'], [aria-label*='{selector}']"
        
        # 要素を待機して入力
        await page.wait_for_selector(selector, timeout=5000)
        await page.fill(selector, text)
        
        return f"'{selector}' に「{text}」を入力しました"
    except Exception as e:
        return f"フォーム入力に失敗しました: {str(e)}"

@mcp.tool()
async def take_screenshot() -> str:
    """現在のページのスクリーンショットを撮影します。
    
    Returns:
        スクリーンショットの結果、またはエラーメッセージ
    """
    global page
    
    if not page:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        # スクリーンショットのパスを設定
        screenshot_dir = "screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # タイムスタンプ付きのファイル名
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{screenshot_dir}/screenshot_{timestamp}.png"
        
        # スクリーンショットを撮影
        await page.screenshot(path=filename)
        
        # 現在のURLとタイトルも取得
        title = await page.title()
        url = page.url
        
        return f"スクリーンショット撮影成功:\nファイル: {filename}\nページ: {title} ({url})"
    except Exception as e:
        return f"スクリーンショット撮影に失敗しました: {str(e)}"

@mcp.tool()
async def submit_form(form_selector: str = "form") -> str:
    """指定されたフォームを送信します。
    
    Args:
        form_selector: 送信するフォームのセレクタ (デフォルト: "form")
    
    Returns:
        フォーム送信の結果、またはエラーメッセージ
    """
    global page
    
    if not page:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        # フォームセレクタが指定されていない場合は、単純に Enter キーを押す
        if form_selector.lower() == "form":
            await page.press("input:focus", "Enter")
        else:
            # フォームを見つけて送信ボタンをクリック
            if not any(char in form_selector for char in "[]#.:>+"):
                # テキストベースのセレクタの場合
                await page.click(f"text={form_selector}")
            else:
                # CSS セレクタの場合
                form = await page.query_selector(form_selector)
                if form:
                    # 送信ボタンを探す
                    submit_button = await form.query_selector("input[type=submit], button[type=submit], button:has-text('送信'), button:has-text('Submit')")
                    if submit_button:
                        await submit_button.click()
                    else:
                        # ボタンが見つからない場合は、フォームをJavaScriptで送信
                        await page.evaluate(f"document.querySelector('{form_selector}').submit()")
                else:
                    return f"フォーム '{form_selector}' が見つかりませんでした"
        
        # ページが読み込まれるのを待つ
        await page.wait_for_load_state("networkidle")
        
        # 新しいページ情報を取得
        title = await page.title()
        url = page.url
        
        return f"フォームを送信しました\n新しいページ: {title} ({url})"
    except Exception as e:
        return f"フォーム送信に失敗しました: {str(e)}"

@mcp.tool()
async def evaluate_javascript(script: str) -> str:
    """JavaScriptコードをページ上で実行します。
    
    Args:
        script: 実行するJavaScriptコード
    
    Returns:
        実行結果、またはエラーメッセージ
    """
    global page
    
    if not page:
        return "まだブラウザが初期化されていません。initialize_browser()を最初に呼び出してください。"
    
    try:
        # JavaScriptを実行
        result = await page.evaluate(f"() => {{ try {{ return {script} }} catch(e) {{ return 'エラー: ' + e.message }} }}")
        
        # 結果をJSON文字列化（オブジェクトの場合）
        if isinstance(result, (dict, list)):
            result = json.dumps(result, ensure_ascii=False, indent=2)
        
        return f"JavaScriptの実行結果:\n{result}"
    except Exception as e:
        return f"JavaScriptの実行に失敗しました: {str(e)}"

# ブラウザを確実にクローズするための関数
async def close_browser():
    global playwright, browser, page
    
    try:
        if page:
            await page.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
    except:
        pass

# メイン関数
if __name__ == "__main__":
    try:
        # サーバー起動
        mcp.run()
    except Exception as e:
        # 例外情報をファイルに記録
        with open("browser_use_error.log", "a") as f:
            f.write(f"{str(e)}\n")
        # ブラウザをクローズ
        asyncio.run(close_browser())
        sys.exit(1)