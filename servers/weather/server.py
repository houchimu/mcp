from mcp.server.fastmcp import FastMCP
import asyncio
import httpx

# FastMCPを使用してサーバーを作成
mcp = FastMCP("Weather Server")

# 簡易的な天気データ（実際のAPIでは外部APIを呼び出す）
weather_data = {
    "tokyo": {"condition": "晴れ", "temperature": 25, "humidity": 60},
    "osaka": {"condition": "曇り", "temperature": 23, "humidity": 65},
    "sapporo": {"condition": "雨", "temperature": 15, "humidity": 80},
    "fukuoka": {"condition": "晴れ", "temperature": 27, "humidity": 55}
}

# get_weatherツールの定義
@mcp.tool()
async def get_weather(city: str) -> str:
    """指定された都市の天気情報を取得します。
    
    Args:
        city: 天気を取得したい都市名（例: tokyo, osaka）
    
    Returns:
        指定された都市の天気情報（気温、湿度、天気状態）
    """
    city = city.lower()
    
    if city in weather_data:
        data = weather_data[city]
        return f"{city}の天気: {data['condition']}、気温: {data['temperature']}°C、湿度: {data['humidity']}%"
    else:
        return f"申し訳ありませんが、{city}の天気情報は利用できません。"

# メイン関数
if __name__ == "__main__":
    # サーバーを実行
    mcp.run() 