# Weather MCP Server

これはClaudeから呼び出し可能な、天気情報を提供するMCPサーバーの実装例です。

## 機能

- 指定された都市の天気情報を取得
- 対応都市: tokyo, osaka, sapporo, fukuoka

## セットアップ

### 1. 必要なライブラリのインストール

```bash
# 特別なライブラリは現時点で不要
# 必要に応じて外部APIを使用する場合はrequestsなどをインストール
# pip install requests
```

### 2. サーバーの起動方法

```bash
python server.py
```

## 使用方法

このサーバーはMCPプロトコルに準拠しており、Claudeなどのクライアントから呼び出すことができます。

### ツール

#### get_weather

指定された都市の天気情報を取得します。

**入力パラメータ**:
- `city`: 天気を取得したい都市名（例: tokyo, osaka）

**出力**:
- 指定された都市の天気、気温、湿度情報

## 開発者向け情報

このサーバーは簡易的なMCP実装を使用しています。実際のプロダクション環境では、以下の拡張が推奨されます:

1. 本格的なMCP SDK（pythonであれば`modelcontextprotocol-python`など）の使用
2. 実際の天気API（OpenWeatherMapなど）との連携
3. エラーハンドリングの強化
4. ロギング機能の追加

## ライセンス

MITライセンス 