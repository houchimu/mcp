# Browser-Use MCP サーバー

このサーバーはブラウザの情報を取得するための機能を提供するMCPサーバーです。

## 機能

このサーバーは以下の機能を提供します：

1. **browse(url)**: 指定されたURLにアクセスします
2. **get_page_title()**: 現在開いているページのタイトルを取得します
3. **get_page_content()**: 現在開いているページのテキスト内容を取得します
4. **find_elements(selector)**: 指定されたCSSセレクタに一致する要素を検索します
5. **get_current_url()**: 現在開いているページのURLを取得します

## 依存関係

このサーバーを実行するには以下の依存パッケージが必要です：

```
httpx>=0.24.0
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

# 現在のURLを取得
current_url = await get_current_url()
```

## 制限事項

- 現在の実装では、BeautifulSoupなどの本格的なHTMLパーサーを使用していないため、HTML解析機能は簡易的なものになっています。
- JavaScriptが動的に生成するコンテンツは取得できません。
- 複雑なブラウザの操作（フォーム入力、クリックなど）はサポートしていません。 