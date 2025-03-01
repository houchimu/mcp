import json
import sys
from typing import Any, Dict, List, Optional, TypedDict, Union

# MCPサーバーの基本クラスと型定義
class MCPServer:
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.handlers = {}
        
    def register_handler(self, method: str, handler):
        self.handlers[method] = handler
        
    async def handle_request(self, request):
        method = request.get("method")
        if method in self.handlers:
            return await self.handlers[method](request)
        else:
            return {"error": {"code": -32601, "message": f"Method {method} not found"}}
            
    async def start(self):
        # STDINからリクエストを読み取り、STDOUTにレスポンスを書き込む
        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = await self.handle_request(request)
                print(json.dumps(response), flush=True)
            except Exception as e:
                error_response = {
                    "id": request.get("id"),
                    "error": {"code": -32603, "message": str(e)}
                }
                print(json.dumps(error_response), flush=True)

# 天気情報を提供するツール
class WeatherTool:
    def __init__(self):
        # 簡易的な天気データ（実際のAPIでは外部APIを呼び出す）
        self.weather_data = {
            "tokyo": {"condition": "晴れ", "temperature": 25, "humidity": 60},
            "osaka": {"condition": "曇り", "temperature": 23, "humidity": 65},
            "sapporo": {"condition": "雨", "temperature": 15, "humidity": 80},
            "fukuoka": {"condition": "晴れ", "temperature": 27, "humidity": 55}
        }
    
    def get_tool_definition(self):
        return {
            "name": "get_weather",
            "description": "指定された都市の天気情報を取得します",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "天気を取得したい都市名（例: tokyo, osaka）"
                    }
                },
                "required": ["city"]
            }
        }
    
    async def execute(self, params):
        city = params.get("city", "").lower()
        
        if city in self.weather_data:
            data = self.weather_data[city]
            response_text = f"{city}の天気: {data['condition']}、気温: {data['temperature']}°C、湿度: {data['humidity']}%"
            return {
                "content": [
                    {"type": "text", "text": response_text}
                ]
            }
        else:
            return {
                "content": [
                    {"type": "text", "text": f"申し訳ありませんが、{city}の天気情報は利用できません。"}
                ]
            }

# MCPサーバーのメイン処理
async def main():
    server = MCPServer("weather-server", "1.0.0")
    weather_tool = WeatherTool()
    
    # tools/listハンドラーの登録
    async def handle_list_tools(request):
        return {
            "id": request.get("id"),
            "result": {
                "tools": [weather_tool.get_tool_definition()]
            }
        }
    
    # tools/callハンドラーの登録
    async def handle_call_tool(request):
        params = request.get("params", {})
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        if tool_name == "get_weather":
            result = await weather_tool.execute(tool_args)
            return {
                "id": request.get("id"),
                "result": result
            }
        else:
            return {
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Tool {tool_name} not found"
                }
            }
    
    server.register_handler("tools/list", handle_list_tools)
    server.register_handler("tools/call", handle_call_tool)
    
    # サーバー起動
    await server.start()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 