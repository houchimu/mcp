import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListResourcesRequestSchema, ListToolsRequestSchema, ReadResourceRequestSchema, } from "@modelcontextprotocol/sdk/types.js";
const server = new Server({
    name: "shakespeare-info-server",
    version: "1.0.0",
}, {
    capabilities: {
        resources: {},
        tools: {}
    }
});
const getShakespeareTool = {
    name: "get_shakespeare_info",
    description: "シェイクスピアの情報を取得します",
    inputSchema: {
        type: "object",
        properties: {},
        required: [],
    },
};
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    switch (request.params.name) {
        case "get_shakespeare_info": {
            try {
                const response = await fetch('https://umayadia-apisample.azurewebsites.net/api/persons/Shakespeare');
                const apiData = await response.json();
                // APIのレスポンスを指定された形式に変換
                const responseData = {
                    success: true,
                    data: {
                        name: apiData.name,
                        note: apiData.note,
                        age: apiData.age,
                        registerDate: apiData.registerDate
                    }
                };
                return {
                    content: [{ type: "text", text: JSON.stringify(responseData) }],
                };
            }
            catch (error) {
                // エラーの場合は success: false を返す
                const errorResponse = {
                    success: false,
                    data: {
                        name: "",
                        note: "",
                        age: 0,
                        registerDate: ""
                    }
                };
                return {
                    content: [{ type: "text", text: JSON.stringify(errorResponse) }],
                };
            }
        }
        default: return {
            content: [{ type: "text", text: "サポートされていない操作です" }],
        };
    }
});
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [getShakespeareTool],
    };
});
server.setRequestHandler(ListResourcesRequestSchema, async () => {
    return { resources: [] };
});
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    throw new Error("リソースが見つかりません");
});
const transport = new StdioServerTransport();
await server.connect(transport);
