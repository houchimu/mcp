# Weather MCP Server

これはClaudeから呼び出し可能な、天気情報を提供するMCPサーバーの実装例です。このサーバーは公式のMCP SDKを使用しています。

## 機能

- 指定された都市の天気情報を取得
- 対応都市: tokyo, osaka, sapporo, fukuoka

## セットアップ

### 1. 必要なライブラリのインストール

```bash
# MCPの依存関係をインストール
uv add mcp[cli] httpx

# または pip を使用する場合
# pip install mcp[cli] httpx
```

### 2. サーバーの起動方法

```bash
# 直接実行
python server.py

# または MCP CLI を使用（推奨）
mcp dev server.py
```

### 3. Claude for Desktopとの連携

Claude for Desktopの設定ファイル（`claude_desktop_config.json`）に以下のように設定を追加します：

```json
{
  "weather": {
    "command": "python",
    "args": [
      "C:\\workspace\\mcp\\servers\\weather\\server.py"
    ]
  }
}
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

このサーバーは公式のMCP SDK (`FastMCP`)を使用しています。さらなる拡張には以下が推奨されます:

1. 実際の天気API（OpenWeatherMapなど）との連携
2. より多くの都市への対応
3. 天気予報機能の追加

## ライセンス

MITライセンス 