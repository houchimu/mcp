# yfinance MCP Server

yfinance ライブラリを使った金融データ取得 MCP サーバー。

## 提供ツール

| ツール名 | 概要 |
| --- | --- |
| `yfinance_get_valuation` | PER/PBR/配当利回り/時価総額/52週高値安値など主要バリュエーション指標 |
| `yfinance_get_price_history` | 日次・週次・月次 OHLCV（最大数十年分） |
| `yfinance_get_income_statement` | 損益計算書（年次/四半期） |
| `yfinance_get_balance_sheet` | 貸借対照表（年次/四半期） |
| `yfinance_get_cash_flow` | キャッシュフロー計算書（年次/四半期） |
| `yfinance_get_analyst_consensus` | 目標株価/レーティング/アナリスト数 + 3シナリオ推定リターン |
| `yfinance_get_news` | 最新ニュース（タイトル・URL・要約） |
| `yfinance_screen_stocks` | プリセットクエリで銘柄スクリーニング |
| `yfinance_compare_tickers` | 複数銘柄のバリュエーション比較表 |

## セットアップ

```bash
pip install mcp[cli] yfinance pydantic
```

## Claude Desktop 設定

`claude_desktop_config.json` に追加:

```json
{
  "mcpServers": {
    "yfinance": {
      "command": "python",
      "args": ["C:\\workspace\\mcp\\servers\\yfinance\\server.py"]
    }
  }
}
```

## 使用例

- `AAPL のPERと時価総額を教えて` → `yfinance_get_valuation`
- `トヨタ(7203.T)の過去5年の株価推移` → `yfinance_get_price_history`
- `Appleの直近年次損益計算書` → `yfinance_get_income_statement`
- `AAPLのアナリスト目標株価と推定リターン` → `yfinance_get_analyst_consensus`
- `AAPL, MSFT, GOOG を比較して` → `yfinance_compare_tickers`
- `成長テクノロジー株をスクリーニング` → `yfinance_screen_stocks`
