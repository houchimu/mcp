import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequest,
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";

const server = new Server({
  name: "shakespeare-info-server",
  version: "1.0.0",
}, {
  capabilities: {
    resources: {},
    tools: {}
  }
});

// APIレスポンスの型定義
interface ApiPerson {
  id: number;
  name: string;
  age: number;
  note: string;
  registerDate: string;
}

// クライアントレスポンスの型定義
interface ShakespeareResponse {
  success: boolean;
  data: {
    name: string;
    note: string;
    age: number;
    registerDate: string;
  };
}

const getShakespeareTool: Tool = {
  name: "get_shakespeare_info",
  description: "シェイクスピアの情報を取得します",
  inputSchema: {
    type: "object",
    properties: {},
    required: [],
  },
};

server.setRequestHandler(
  CallToolRequestSchema,
  async (request: CallToolRequest) => {
    switch (request.params.name) {
      case "get_shakespeare_info": {
        try {
          const response = await fetch('https://umayadia-apisample.azurewebsites.net/api/persons/Shakespeare');
          const apiData: ApiPerson = await response.json();

          // APIのレスポンスを指定された形式に変換
          const responseData: ShakespeareResponse = {
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
        } catch (error) {
          // エラーの場合は success: false を返す
          const errorResponse: ShakespeareResponse = {
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
      }
    }
  }
);

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