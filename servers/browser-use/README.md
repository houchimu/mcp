# Browser-Use MCP サーバー

このサーバーはブラウザの操作と情報取得のための機能を提供するMCPサーバーです。Playwrightを使用して実際のブラウザを制御します。

## 機能

このサーバーは以下の機能を提供します：

1. **browse(url)**: 指定されたURLにアクセスします
2. **get_page_title()**: 現在開いているページのタイトルを取得します
3. **get_page_content()**: 現在開いているページのテキスト内容を取得します
4. **find_elements(selector)**: 指定されたCSSセレクタに一致する要素を検索します
5. **get_current_url()**: 現在開いているページのURLを取得します
6. **click(selector)**: 指定されたセレクタの要素をクリックします
7. **type_text(selector, text)**: 指定されたセレクタの要素にテキストを入力します
8. **take_screenshot()**: 現在のページのスクリーンショットを撮影します
9. **execute_javascript(script)**: ページ上でJavaScriptを実行します
10. **submit_form(selector)**: 指定されたフォームを送信します

## 依存関係

このサーバーを実行するには以下の依存パッケージが必要です：

```
playwright>=1.38.0
python-dotenv>=1.0.0
```

初回実行時には、以下のコマンドでPlaywrightのブラウザをインストールする必要があります：

```bash
playwright install
```

## 実行方法

サーバーは以下のコマンドで実行できます：

```bash
python server.py
```

## 使用例

```python
# URLにアクセス
await browse("https://example.com")

# ページタイトルを取得
title = await get_page_title()

# ページ内容を取得
content = await get_page_content()

# 要素を検索
elements = await find_elements("div.main")

# 要素をクリックする
await click("button.submit")

# フォームに入力する
await type_text("#search-input", "検索キーワード")

# フォームを送信する
await submit_form("form#search")

# JavaScriptを実行する
await execute_javascript("return document.title")

# スクリーンショットを撮影する
await take_screenshot()

# 現在のURLを取得
current_url = await get_current_url()
```

## 特徴

- **実際のブラウザエンジン**: Chromiumブラウザを使用して、JavaScript対応のWebページも正確に表示・操作できます
- **シンプルなAPI**: 複雑なブラウザ操作も簡単なAPIで利用可能です
- **非同期操作**: すべての操作は非同期的に行われ、効率的な実行が可能です
- **スクリーンショット機能**: 現在の表示状態を画像として保存できます

## 注意事項

- このサーバーを実行するには、Playwrightがサポートする環境が必要です
- 初回実行時にはブラウザのダウンロードが行われるため、インターネット接続が必要です
- スクリーンショットはサーバーのローカルディスクに保存されます 