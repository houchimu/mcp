import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequest,
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";

const NTFY_TOPIC = "https://ntfy.sh/ns-holdings-en-kuchikomi";

const server = new Server(
  { name: "ntfy-notification", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

interface SendNotificationParams {
  date: string;
  url: string;
}

const sendNotificationTool: Tool = {
  name: "send_kuchikomi_notification",
  description: "NS Holdingsの新しい口コミをntfy.shで通知します",
  inputSchema: {
    type: "object",
    properties: {
      date: {
        type: "string",
        description: "日付（例: 2026-06-06）",
      },
    },
    required: ["date"],
  },
};

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [sendNotificationTool],
}));

server.setRequestHandler(
  CallToolRequestSchema,
  async (request: CallToolRequest) => {
    switch (request.params.name) {
      case "send_kuchikomi_notification": {
        const { date, url } = request.params.arguments as unknown as SendNotificationParams;
        const message = `There's a new KUCHIKOMI at NS-Holdings!!!!! Date: ${date}. URL: https://en-hyouban.com/company/10100939769/user_list/`;

        const response = await fetch(NTFY_TOPIC, {
          method: "POST",
          headers: {
            "Title": "NS Holdings - New Review Posted",
            "Content-Type": "text/plain; charset=utf-8",
          },
          body: message,
        });

        if (!response.ok) {
          return {
            content: [{ type: "text", text: `送信失敗: HTTP ${response.status}` }],
          };
        }

        return {
          content: [{ type: "text", text: `通知を送信しました。ステータス: ${response.status}` }],
        };
      }
      default:
        return {
          content: [{ type: "text", text: "サポートされていない操作です" }],
        };
    }
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
