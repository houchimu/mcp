# Browser-Use MCP サーバー

このサーバーはブラウザの操作と情報取得のための機能を提供するMCPサーバーです。browser-useライブラリを使用してAIによるブラウザ自動化を実現します。

## 機能

このサーバーは以下の機能を提供します：

1. **initialize_browser()**: ブラウザを初期化します（他のツールを使用する前に必ず呼び出す必要があります）
2. **browse(url)**: 指定されたURLにアクセスします
3. **execute_task(task)**: 指定されたタスクをブラウザで自然言語指示に基づいて実行します
4. **get_page_info()**: 現在開いているページの情報を取得します
5. **find_elements(description)**: 指定された説明に一致する要素を自然言語で検索します
6. **click_element(description)**: 指定された説明に一致する要素を自然言語でクリックします
7. **fill_form(form_description, data)**: 指定されたフォームにデータを自然言語で入力します
8. **take_screenshot()**: 現在のページのスクリーンショットを撮影します
9. **submit_form(form_description)**: 指定されたフォームを自然言語で送信します
10. **close_browser()**: ブラウザを終了します（使い終わったら呼び出すことをお勧めします）

## 依存関係

このサーバーを実行するには以下の依存パッケージが必要です：

```
browser-use>=0.2.0
python-dotenv>=1.0.0
langchain-openai>=0.1.0
```

## 設定

このサーバーを使用するには、`.env`ファイルに適切なAPI設定を行う必要があります：

```bash
# .env ファイル例
OPENAI_API_KEY=your_openai_key_here
```

## 実行方法

サーバーは以下のコマンドで実行できます：

```bash
python server.py
```

## 使用例

```python
# ブラウザを初期化（最初に必ず実行）
await initialize_browser()

# URLにアクセス
await browse("https://example.com")

# 自然言語でタスクを実行
await execute_task("ページ内の最初のリンクをクリックして、次のページのタイトルを報告する")

# ページ情報を取得
info = await get_page_info()

# 自然言語で要素を検索
elements = await find_elements("ナビゲーションメニューの項目")

# 自然言語で要素をクリック
await click_element("ログインボタン")

# 自然言語でフォームに入力
await fill_form("ログインフォーム", "ユーザー名: test_user、パスワード: test123")

# スクリーンショットを撮影
await take_screenshot()

# 自然言語でフォームを送信
await submit_form("検索フォーム")

# 使い終わったらブラウザを終了
await close_browser()
```

## 特徴

- **AIによるブラウザ操作**: LLMによる自然言語理解を利用して、ブラウザを自動操作します
- **シンプルなインターフェース**: 複雑なCSSセレクタやXPathを覚える必要がなく、自然言語で操作できます
- **柔軟な対応**: ウェブサイトの変更に強く、要素の見た目や目的から適切な操作を実行します
- **LangChainとの連携**: LangChainエコシステムと連携し、様々なLLMを利用可能です

## 注意事項

- このサーバーを使用するには、OpenAIなどのLLM APIキーが必要です
- 処理時間はLLMの応答時間に依存するため、Playwrightなど低レベルのブラウザ自動化ツールよりも遅くなる場合があります
- LLMの判断に基づくため、完全に決定論的な動作は保証されません
- 必ず最初に`initialize_browser()`を呼び出し、使い終わったら`close_browser()`を呼び出してリソースを解放してください 