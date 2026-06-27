#!/usr/bin/env python3
"""
yfinance MCP Server

株価データ、財務諸表、アナリストコンセンサス、価格ヒストリー、
ニュース、銘柄スクリーニングなどの金融データを提供するMCPサーバー。
"""

import asyncio
import json
from typing import Optional, List, Any
from enum import Enum

import yfinance as yf
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("yfinance_mcp")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PeriodEnum(str, Enum):
    ONE_DAY = "1d"
    FIVE_DAYS = "5d"
    ONE_MONTH = "1mo"
    THREE_MONTHS = "3mo"
    SIX_MONTHS = "6mo"
    ONE_YEAR = "1y"
    TWO_YEARS = "2y"
    FIVE_YEARS = "5y"
    TEN_YEARS = "10y"
    YTD = "ytd"
    MAX = "max"


class IntervalEnum(str, Enum):
    ONE_MINUTE = "1m"
    TWO_MINUTES = "2m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    SIXTY_MINUTES = "60m"
    NINETY_MINUTES = "90m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"
    FIVE_DAYS = "5d"
    ONE_WEEK = "1wk"
    ONE_MONTH = "1mo"
    THREE_MONTHS = "3mo"


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


# ---------------------------------------------------------------------------
# Input Models
# ---------------------------------------------------------------------------

class TickerInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    ticker: str = Field(..., description="ティッカーシンボル（例: 'AAPL', '7203.T', 'MSFT'）", min_length=1, max_length=20)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="出力フォーマット: 'markdown' または 'json'")


class PriceHistoryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    ticker: str = Field(..., description="ティッカーシンボル（例: 'AAPL', '7203.T'）", min_length=1, max_length=20)
    period: PeriodEnum = Field(default=PeriodEnum.ONE_YEAR, description="取得期間: '1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max'")
    interval: IntervalEnum = Field(default=IntervalEnum.ONE_DAY, description="足の間隔: '1d','1wk','1mo' など")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="出力フォーマット: 'markdown' または 'json'")


class FinancialsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    ticker: str = Field(..., description="ティッカーシンボル（例: 'AAPL', '7203.T'）", min_length=1, max_length=20)
    quarterly: bool = Field(default=False, description="True で四半期データ、False で年次データ")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="出力フォーマット: 'markdown' または 'json'")


class NewsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    ticker: str = Field(..., description="ティッカーシンボル（例: 'AAPL', '7203.T'）", min_length=1, max_length=20)
    count: int = Field(default=10, description="取得するニュース件数 (1〜50)", ge=1, le=50)


class ScreenerInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    query_type: str = Field(
        ...,
        description=(
            "スクリーニングクエリ種別。例: 'most_actives', 'day_gainers', 'day_losers', "
            "'growth_technology_stocks', 'undervalued_growth_stocks', 'aggressive_small_caps', "
            "'small_cap_gainers', 'undervalued_large_caps', 'most_shorted_stocks'"
        )
    )
    count: int = Field(default=25, description="取得する銘柄数 (1〜100)", ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="出力フォーマット: 'markdown' または 'json'")


class MultiTickerInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    tickers: List[str] = Field(..., description="ティッカーシンボルのリスト（例: ['AAPL','MSFT','GOOG']）", min_length=1, max_length=20)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="出力フォーマット: 'markdown' または 'json'")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_val(val: Any) -> Any:
    """pandas/numpy の値を JSON シリアライズ可能な Python 型に変換。"""
    try:
        import pandas as pd
        import numpy as np
        if pd.isna(val):
            return None
    except Exception:
        pass
    try:
        import numpy as np
        if isinstance(val, (np.integer,)):
            return int(val)
        if isinstance(val, (np.floating,)):
            return float(val)
    except Exception:
        pass
    return val


def _df_to_records(df) -> List[dict]:
    """DataFrame を JSON シリアライズ可能なレコードのリストに変換。"""
    if df is None or df.empty:
        return []
    records = []
    for idx, row in df.iterrows():
        record = {"date": str(idx)}
        for col in df.columns:
            record[str(col)] = _safe_val(row[col])
        records.append(record)
    return records


def _info_to_valuation(info: dict) -> dict:
    """info dict から主要なバリュエーション指標を抽出。"""
    fields = [
        "shortName", "longName", "symbol", "exchange", "currency",
        "currentPrice", "previousClose", "open", "dayLow", "dayHigh",
        "fiftyTwoWeekLow", "fiftyTwoWeekHigh",
        "marketCap", "enterpriseValue",
        "trailingPE", "forwardPE", "priceToBook",
        "trailingEps", "forwardEps",
        "dividendYield", "dividendRate", "exDividendDate",
        "beta", "volume", "averageVolume",
        "totalRevenue", "grossProfits", "ebitda", "netIncomeToCommon",
        "returnOnEquity", "returnOnAssets",
        "debtToEquity", "currentRatio", "quickRatio",
        "sector", "industry", "country", "website", "longBusinessSummary",
    ]
    return {k: _safe_val(info.get(k)) for k in fields}


def _format_valuation_md(data: dict, ticker: str) -> str:
    name = data.get("shortName") or data.get("longName") or ticker
    lines = [f"# {name} ({ticker}) バリュエーション概要", ""]

    def row(label: str, key: str, fmt: str = "") -> str:
        val = data.get(key)
        if val is None:
            return f"- **{label}**: N/A"
        if fmt == "pct":
            return f"- **{label}**: {val:.2%}"
        if fmt == "large":
            if abs(val) >= 1e12:
                return f"- **{label}**: {val/1e12:.2f}T"
            if abs(val) >= 1e9:
                return f"- **{label}**: {val/1e9:.2f}B"
            if abs(val) >= 1e6:
                return f"- **{label}**: {val/1e6:.2f}M"
            return f"- **{label}**: {val:,.0f}"
        if isinstance(val, float):
            return f"- **{label}**: {val:.2f}"
        return f"- **{label}**: {val}"

    lines += [
        "## 価格情報",
        row("現在値", "currentPrice"),
        row("前日終値", "previousClose"),
        row("52週高値", "fiftyTwoWeekHigh"),
        row("52週安値", "fiftyTwoWeekLow"),
        "",
        "## バリュエーション",
        row("時価総額", "marketCap", "large"),
        row("EV", "enterpriseValue", "large"),
        row("PER (実績)", "trailingPE"),
        row("PER (予想)", "forwardPE"),
        row("PBR", "priceToBook"),
        row("EPS (実績)", "trailingEps"),
        row("EPS (予想)", "forwardEps"),
        "",
        "## 配当",
        row("配当利回り", "dividendYield", "pct"),
        row("配当額", "dividendRate"),
        row("配当落日", "exDividendDate"),
        "",
        "## 財務健全性",
        row("ROE", "returnOnEquity", "pct"),
        row("ROA", "returnOnAssets", "pct"),
        row("D/E比率", "debtToEquity"),
        row("流動比率", "currentRatio"),
        "",
        "## 基本情報",
        f"- **セクター**: {data.get('sector') or 'N/A'}",
        f"- **業種**: {data.get('industry') or 'N/A'}",
        f"- **国**: {data.get('country') or 'N/A'}",
        f"- **通貨**: {data.get('currency') or 'N/A'}",
    ]
    summary = data.get("longBusinessSummary")
    if summary:
        lines += ["", "## 事業概要", summary[:500] + ("..." if len(summary) > 500 else "")]
    return "\n".join(lines)


def _format_analyst_md(info: dict, ticker: str) -> str:
    name = info.get("shortName") or ticker
    lines = [f"# {name} ({ticker}) アナリストコンセンサス", ""]
    fields = {
        "recommendationMean": "推奨スコア (1=強買, 5=強売)",
        "recommendationKey": "推奨キー",
        "numberOfAnalystOpinions": "アナリスト数",
        "targetHighPrice": "目標株価 (高)",
        "targetMeanPrice": "目標株価 (中央)",
        "targetLowPrice": "目標株価 (低)",
        "targetMedianPrice": "目標株価 (中央値)",
        "currentPrice": "現在株価",
    }
    for key, label in fields.items():
        val = _safe_val(info.get(key))
        lines.append(f"- **{label}**: {val if val is not None else 'N/A'}")

    # 推定リターン計算
    current = _safe_val(info.get("currentPrice"))
    mean_target = _safe_val(info.get("targetMeanPrice"))
    high_target = _safe_val(info.get("targetHighPrice"))
    low_target = _safe_val(info.get("targetLowPrice"))
    if current and current > 0:
        lines.append("")
        lines.append("## 推定リターン（目標株価ベース）")
        for scenario, target in [("強気", high_target), ("中立", mean_target), ("弱気", low_target)]:
            if target:
                ret = (target - current) / current
                lines.append(f"- **{scenario}シナリオ** ({target:.2f}): {ret:.2%}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="yfinance_get_valuation",
)
async def yfinance_get_valuation(params: TickerInput) -> str:
    """
    指定したティッカーの株価・バリュエーション指標を取得する。

    PER, PBR, 配当利回り, 時価総額, 52週高値/安値, ROE, ROA など主要指標を返す。

    Args:
        params (TickerInput):
            - ticker (str): ティッカーシンボル（例: 'AAPL', '7203.T'）
            - response_format (str): 'markdown' または 'json'

    Returns:
        str: バリュエーション指標（Markdown or JSON）

    Examples:
        - Appleの株価指標を調べたい → ticker='AAPL'
        - トヨタ自動車を調べたい → ticker='7203.T'
    """
    try:
        ticker = params.ticker.upper()
        info = await asyncio.to_thread(lambda: yf.Ticker(ticker).info)
        if not info or info.get("trailingPE") is None and info.get("currentPrice") is None:
            return f"Error: '{ticker}' のデータが見つかりません。ティッカーシンボルを確認してください。"
        data = _info_to_valuation(info)
        if params.response_format == ResponseFormat.MARKDOWN:
            return _format_valuation_md(data, ticker)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: データ取得に失敗しました: {type(e).__name__}: {e}"


@mcp.tool(
    name="yfinance_get_price_history",
)
async def yfinance_get_price_history(params: PriceHistoryInput) -> str:
    """
    指定したティッカーの OHLCV（始値・高値・安値・終値・出来高）ヒストリーを取得する。

    日次・週次・月次など複数の時間軸に対応。テクニカル分析、VaR計算、
    相関分析などに活用できる。

    Args:
        params (PriceHistoryInput):
            - ticker (str): ティッカーシンボル
            - period (str): 取得期間（'1d','1mo','1y','5y','max' など）
            - interval (str): 足の間隔（'1d','1wk','1mo' など）
            - response_format (str): 'markdown' または 'json'

    Returns:
        str: OHLCV データ（Markdown テーブル or JSON レコード配列）
    """
    try:
        ticker = params.ticker.upper()
        hist = await asyncio.to_thread(
            lambda: yf.Ticker(ticker).history(
                period=params.period.value,
                interval=params.interval.value,
            )
        )
        if hist is None or hist.empty:
            return f"Error: '{ticker}' の価格ヒストリーが見つかりません。"

        records = _df_to_records(hist)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"ticker": ticker, "period": params.period.value, "interval": params.interval.value, "records": records}, ensure_ascii=False, indent=2)

        # Markdown テーブル（直近50件まで表示）
        show = records[-50:]
        lines = [
            f"# {ticker} 価格ヒストリー ({params.period.value} / {params.interval.value})",
            f"全 {len(records)} 件 （直近 {len(show)} 件表示）",
            "",
            "| 日付 | 始値 | 高値 | 安値 | 終値 | 出来高 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for r in show:
            o = f"{r.get('Open'):.2f}" if r.get("Open") is not None else "N/A"
            h = f"{r.get('High'):.2f}" if r.get("High") is not None else "N/A"
            lo = f"{r.get('Low'):.2f}" if r.get("Low") is not None else "N/A"
            c = f"{r.get('Close'):.2f}" if r.get("Close") is not None else "N/A"
            v = f"{r.get('Volume'):,}" if r.get("Volume") is not None else "N/A"
            lines.append(f"| {r['date'][:10]} | {o} | {h} | {lo} | {c} | {v} |")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: データ取得に失敗しました: {type(e).__name__}: {e}"


@mcp.tool(
    name="yfinance_get_income_statement",
)
async def yfinance_get_income_statement(params: FinancialsInput) -> str:
    """
    指定したティッカーの損益計算書（P/L）を取得する。

    売上高、売上総利益、営業利益、純利益など主要項目を返す。
    年次または四半期データを選択可能。

    Args:
        params (FinancialsInput):
            - ticker (str): ティッカーシンボル
            - quarterly (bool): True で四半期データ、False で年次データ（デフォルト）
            - response_format (str): 'markdown' または 'json'

    Returns:
        str: 損益計算書データ（Markdown or JSON）
    """
    try:
        ticker = params.ticker.upper()
        t = yf.Ticker(ticker)
        stmt = await asyncio.to_thread(lambda: t.quarterly_income_stmt if params.quarterly else t.income_stmt)
        if stmt is None or stmt.empty:
            return f"Error: '{ticker}' の損益計算書データが見つかりません。"

        period_label = "四半期" if params.quarterly else "年次"
        if params.response_format == ResponseFormat.JSON:
            data = {}
            for col in stmt.columns:
                data[str(col)[:10]] = {str(idx): _safe_val(stmt.loc[idx, col]) for idx in stmt.index}
            return json.dumps({"ticker": ticker, "type": "income_statement", "period": period_label, "data": data}, ensure_ascii=False, indent=2)

        lines = [f"# {ticker} 損益計算書 ({period_label})", ""]
        cols = [str(c)[:10] for c in stmt.columns]
        header = "| 項目 | " + " | ".join(cols) + " |"
        sep = "| --- | " + " | ".join(["---:"] * len(cols)) + " |"
        lines += [header, sep]
        for idx in stmt.index:
            vals = []
            for col in stmt.columns:
                v = _safe_val(stmt.loc[idx, col])
                if v is None:
                    vals.append("N/A")
                elif isinstance(v, (int, float)):
                    vals.append(f"{v/1e6:,.1f}M" if abs(v) >= 1e6 else f"{v:,.0f}")
                else:
                    vals.append(str(v))
            lines.append(f"| {idx} | " + " | ".join(vals) + " |")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: データ取得に失敗しました: {type(e).__name__}: {e}"


@mcp.tool(
    name="yfinance_get_balance_sheet",
)
async def yfinance_get_balance_sheet(params: FinancialsInput) -> str:
    """
    指定したティッカーの貸借対照表（B/S）を取得する。

    総資産、総負債、自己資本など主要項目を返す。
    年次または四半期データを選択可能。

    Args:
        params (FinancialsInput):
            - ticker (str): ティッカーシンボル
            - quarterly (bool): True で四半期データ、False で年次データ
            - response_format (str): 'markdown' または 'json'

    Returns:
        str: 貸借対照表データ（Markdown or JSON）
    """
    try:
        ticker = params.ticker.upper()
        t = yf.Ticker(ticker)
        stmt = await asyncio.to_thread(lambda: t.quarterly_balance_sheet if params.quarterly else t.balance_sheet)
        if stmt is None or stmt.empty:
            return f"Error: '{ticker}' の貸借対照表データが見つかりません。"

        period_label = "四半期" if params.quarterly else "年次"
        if params.response_format == ResponseFormat.JSON:
            data = {}
            for col in stmt.columns:
                data[str(col)[:10]] = {str(idx): _safe_val(stmt.loc[idx, col]) for idx in stmt.index}
            return json.dumps({"ticker": ticker, "type": "balance_sheet", "period": period_label, "data": data}, ensure_ascii=False, indent=2)

        lines = [f"# {ticker} 貸借対照表 ({period_label})", ""]
        cols = [str(c)[:10] for c in stmt.columns]
        header = "| 項目 | " + " | ".join(cols) + " |"
        sep = "| --- | " + " | ".join(["---:"] * len(cols)) + " |"
        lines += [header, sep]
        for idx in stmt.index:
            vals = []
            for col in stmt.columns:
                v = _safe_val(stmt.loc[idx, col])
                if v is None:
                    vals.append("N/A")
                elif isinstance(v, (int, float)):
                    vals.append(f"{v/1e6:,.1f}M" if abs(v) >= 1e6 else f"{v:,.0f}")
                else:
                    vals.append(str(v))
            lines.append(f"| {idx} | " + " | ".join(vals) + " |")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: データ取得に失敗しました: {type(e).__name__}: {e}"


@mcp.tool(
    name="yfinance_get_cash_flow",
)
async def yfinance_get_cash_flow(params: FinancialsInput) -> str:
    """
    指定したティッカーのキャッシュフロー計算書（C/F）を取得する。

    営業CF、投資CF、財務CF、フリーCFなど主要項目を返す。
    年次または四半期データを選択可能。

    Args:
        params (FinancialsInput):
            - ticker (str): ティッカーシンボル
            - quarterly (bool): True で四半期データ、False で年次データ
            - response_format (str): 'markdown' または 'json'

    Returns:
        str: キャッシュフロー計算書データ（Markdown or JSON）
    """
    try:
        ticker = params.ticker.upper()
        t = yf.Ticker(ticker)
        stmt = await asyncio.to_thread(lambda: t.quarterly_cashflow if params.quarterly else t.cashflow)
        if stmt is None or stmt.empty:
            return f"Error: '{ticker}' のキャッシュフローデータが見つかりません。"

        period_label = "四半期" if params.quarterly else "年次"
        if params.response_format == ResponseFormat.JSON:
            data = {}
            for col in stmt.columns:
                data[str(col)[:10]] = {str(idx): _safe_val(stmt.loc[idx, col]) for idx in stmt.index}
            return json.dumps({"ticker": ticker, "type": "cash_flow", "period": period_label, "data": data}, ensure_ascii=False, indent=2)

        lines = [f"# {ticker} キャッシュフロー計算書 ({period_label})", ""]
        cols = [str(c)[:10] for c in stmt.columns]
        header = "| 項目 | " + " | ".join(cols) + " |"
        sep = "| --- | " + " | ".join(["---:"] * len(cols)) + " |"
        lines += [header, sep]
        for idx in stmt.index:
            vals = []
            for col in stmt.columns:
                v = _safe_val(stmt.loc[idx, col])
                if v is None:
                    vals.append("N/A")
                elif isinstance(v, (int, float)):
                    vals.append(f"{v/1e6:,.1f}M" if abs(v) >= 1e6 else f"{v:,.0f}")
                else:
                    vals.append(str(v))
            lines.append(f"| {idx} | " + " | ".join(vals) + " |")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: データ取得に失敗しました: {type(e).__name__}: {e}"


@mcp.tool(
    name="yfinance_get_analyst_consensus",
)
async def yfinance_get_analyst_consensus(params: TickerInput) -> str:
    """
    指定したティッカーのアナリストコンセンサス情報を取得する。

    目標株価（高値/中央/安値）、レーティング、アナリスト数、
    および現在株価からの推定リターン（3シナリオ）を返す。

    Args:
        params (TickerInput):
            - ticker (str): ティッカーシンボル
            - response_format (str): 'markdown' または 'json'

    Returns:
        str: アナリストコンセンサスと推定リターン（Markdown or JSON）
    """
    try:
        ticker = params.ticker.upper()
        t = yf.Ticker(ticker)
        info = await asyncio.to_thread(lambda: t.info)
        if not info:
            return f"Error: '{ticker}' のデータが見つかりません。"

        analyst_fields = [
            "shortName", "currentPrice",
            "recommendationMean", "recommendationKey", "numberOfAnalystOpinions",
            "targetHighPrice", "targetMeanPrice", "targetLowPrice", "targetMedianPrice",
        ]
        data = {k: _safe_val(info.get(k)) for k in analyst_fields}

        # 推定リターン
        current = data.get("currentPrice")
        returns = {}
        if current and current > 0:
            for scenario, key in [("bull", "targetHighPrice"), ("base", "targetMeanPrice"), ("bear", "targetLowPrice")]:
                target = data.get(key)
                if target:
                    returns[scenario] = round((target - current) / current, 4)
        data["estimated_returns"] = returns

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"ticker": ticker, **data}, ensure_ascii=False, indent=2)
        return _format_analyst_md(info, ticker)
    except Exception as e:
        return f"Error: データ取得に失敗しました: {type(e).__name__}: {e}"


@mcp.tool(
    name="yfinance_get_news",
)
async def yfinance_get_news(params: NewsInput) -> str:
    """
    指定したティッカーの最新ニュースを取得する。

    各記事のタイトル、URL、公開日時、要約（利用可能な場合）を返す。
    定性的な情報収集やセンチメント分析の入力として活用できる。

    Args:
        params (NewsInput):
            - ticker (str): ティッカーシンボル
            - count (int): 取得するニュース件数（1〜50、デフォルト10）

    Returns:
        str: ニュース記事一覧（Markdown フォーマット）
    """
    try:
        ticker = params.ticker.upper()
        t = yf.Ticker(ticker)
        news = await asyncio.to_thread(lambda: t.news)
        if not news:
            return f"'{ticker}' のニュースが見つかりません。"

        articles = news[: params.count]
        lines = [f"# {ticker} 最新ニュース ({len(articles)} 件)", ""]
        for i, article in enumerate(articles, 1):
            content = article.get("content", {})
            title = content.get("title") or article.get("title", "タイトル不明")
            url = content.get("canonicalUrl", {}).get("url") or article.get("link", "")
            pub = content.get("pubDate") or article.get("providerPublishTime", "")
            summary = content.get("summary") or ""
            provider = content.get("provider", {}).get("displayName") or article.get("publisher", "")

            lines.append(f"## {i}. {title}")
            if provider:
                lines.append(f"- **媒体**: {provider}")
            if pub:
                lines.append(f"- **公開日時**: {str(pub)[:19]}")
            if url:
                lines.append(f"- **URL**: {url}")
            if summary:
                lines.append(f"- **要約**: {summary[:300]}{'...' if len(summary) > 300 else ''}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: データ取得に失敗しました: {type(e).__name__}: {e}"


@mcp.tool(
    name="yfinance_screen_stocks",
)
async def yfinance_screen_stocks(params: ScreenerInput) -> str:
    """
    Yahoo Finance のプリセットクエリで銘柄をスクリーニングする。

    60以上の取引所に対応。主要なクエリ種別:
    - most_actives: 売買高上位
    - day_gainers: 本日の値上がり上位
    - day_losers: 本日の値下がり上位
    - growth_technology_stocks: 成長テクノロジー株
    - undervalued_growth_stocks: 割安成長株
    - aggressive_small_caps: 積極的な小型株
    - small_cap_gainers: 小型株上昇銘柄
    - undervalued_large_caps: 割安大型株
    - most_shorted_stocks: 空売り上位

    Args:
        params (ScreenerInput):
            - query_type (str): スクリーニングクエリ種別
            - count (int): 取得銘柄数 (1〜100、デフォルト25)
            - response_format (str): 'markdown' または 'json'

    Returns:
        str: スクリーニング結果の銘柄一覧（Markdown or JSON）
    """
    try:
        screener = yf.Screener()
        body = {
            "offset": 0,
            "size": params.count,
            "sortField": "percentchange",
            "sortType": "DESC",
            "quoteType": "EQUITY",
            "query": {"operator": "and", "operands": []},
            "userId": "",
            "userIdType": "guid",
        }

        def _run():
            screener.set_predefined_body(params.query_type)
            screener.size = params.count
            return screener.response

        result = await asyncio.to_thread(_run)

        quotes = result.get("quotes", [])
        if not quotes:
            return f"'{params.query_type}' のスクリーニング結果が見つかりません。"

        if params.response_format == ResponseFormat.JSON:
            simplified = []
            for q in quotes:
                simplified.append({
                    "symbol": q.get("symbol"),
                    "shortName": q.get("shortName"),
                    "regularMarketPrice": _safe_val(q.get("regularMarketPrice")),
                    "regularMarketChangePercent": _safe_val(q.get("regularMarketChangePercent")),
                    "regularMarketVolume": _safe_val(q.get("regularMarketVolume")),
                    "marketCap": _safe_val(q.get("marketCap")),
                    "trailingPE": _safe_val(q.get("trailingPE")),
                })
            return json.dumps({"query_type": params.query_type, "count": len(simplified), "quotes": simplified}, ensure_ascii=False, indent=2)

        lines = [
            f"# スクリーニング結果: {params.query_type} ({len(quotes)} 銘柄)",
            "",
            "| シンボル | 社名 | 現在値 | 騰落率 | 時価総額 | PER |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
        for q in quotes:
            sym = q.get("symbol", "")
            name = q.get("shortName", "")[:20]
            price = q.get("regularMarketPrice")
            chg = q.get("regularMarketChangePercent")
            mcap = q.get("marketCap")
            pe = q.get("trailingPE")
            price_s = f"{price:.2f}" if price is not None else "N/A"
            chg_s = f"{chg:+.2f}%" if chg is not None else "N/A"
            mcap_s = f"{mcap/1e9:.1f}B" if mcap and mcap >= 1e9 else (f"{mcap/1e6:.1f}M" if mcap else "N/A")
            pe_s = f"{pe:.1f}" if pe is not None else "N/A"
            lines.append(f"| {sym} | {name} | {price_s} | {chg_s} | {mcap_s} | {pe_s} |")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: スクリーニングに失敗しました: {type(e).__name__}: {e}"


@mcp.tool(
    name="yfinance_compare_tickers",
)
async def yfinance_compare_tickers(params: MultiTickerInput) -> str:
    """
    複数のティッカーを並べてバリュエーション指標を比較する。

    最大20銘柄のPER, PBR, 配当利回り, 時価総額, ROE などを一覧表示する。

    Args:
        params (MultiTickerInput):
            - tickers (List[str]): ティッカーシンボルのリスト（例: ['AAPL','MSFT','GOOG']）
            - response_format (str): 'markdown' または 'json'

    Returns:
        str: 銘柄比較表（Markdown or JSON）
    """
    try:
        tickers = [t.upper() for t in params.tickers]

        async def fetch_one(sym: str) -> dict:
            info = await asyncio.to_thread(lambda: yf.Ticker(sym).info)
            return {"ticker": sym, **_info_to_valuation(info)}

        results = await asyncio.gather(*[fetch_one(sym) for sym in tickers], return_exceptions=True)

        data = []
        for r in results:
            if isinstance(r, Exception):
                data.append({"ticker": "ERROR", "error": str(r)})
            else:
                data.append(r)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(data, ensure_ascii=False, indent=2)

        lines = [
            "# 銘柄比較",
            "",
            "| ティッカー | 社名 | 現在値 | PER | PBR | 配当利回り | 時価総額 | ROE |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for d in data:
            sym = d.get("ticker", "")
            name = (d.get("shortName") or "")[:20]
            price = d.get("currentPrice")
            pe = d.get("trailingPE")
            pb = d.get("priceToBook")
            dy = d.get("dividendYield")
            mcap = d.get("marketCap")
            roe = d.get("returnOnEquity")
            price_s = f"{price:.2f}" if price is not None else "N/A"
            pe_s = f"{pe:.1f}" if pe is not None else "N/A"
            pb_s = f"{pb:.2f}" if pb is not None else "N/A"
            dy_s = f"{dy:.2%}" if dy is not None else "N/A"
            mcap_s = f"{mcap/1e9:.1f}B" if mcap and mcap >= 1e9 else (f"{mcap/1e6:.1f}M" if mcap else "N/A")
            roe_s = f"{roe:.2%}" if roe is not None else "N/A"
            lines.append(f"| {sym} | {name} | {price_s} | {pe_s} | {pb_s} | {dy_s} | {mcap_s} | {roe_s} |")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: データ取得に失敗しました: {type(e).__name__}: {e}"


if __name__ == "__main__":
    mcp.run()

