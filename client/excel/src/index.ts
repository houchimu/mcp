import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { ListToolsResultSchema, CallToolResultSchema } from "@modelcontextprotocol/sdk/types.js";
import OpenAI from 'openai';
import { ChatCompletionTool } from 'openai/resources/chat/completions';
import { config } from 'dotenv';
import readline from 'readline';

// Load environment variables
config();

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
if (!OPENAI_API_KEY) {
    throw new Error("OPENAI_API_KEY not found in environment variables");
}

const MODEL = "gpt-4o-mini";

interface ExcelSheet {
    name: string;
    data: Record<string, any>[];
}

interface ExcelData {
    sheets: ExcelSheet[];
}

interface ToolResult {
    type: string;
    text?: string;
    data?: string;
    mimeType?: string;
}

class MCPClient {
    private client!: Client;
    private transport!: StdioClientTransport;
    private openai: OpenAI;

    constructor() {
        this.openai = new OpenAI({
            apiKey: OPENAI_API_KEY
        });
    }

    async connect(serverScriptPath: string): Promise<void> {
        // Validate script extension
        const isPython = serverScriptPath.endsWith('.py');
        const isJs = serverScriptPath.endsWith('.js');
        if (!(isPython || isJs)) {
            throw new Error("Server script must be a .py or .js file");
        }

        // Initialize transport
        this.transport = new StdioClientTransport({
            command: isPython ? "python" : "node",
            args: [serverScriptPath]
        });

        // Initialize client
        this.client = new Client({
            name: "excel-client",
            version: "1.0.0",
        }, {
            capabilities: {}
        });

        // Connect to server
        await this.client.connect(this.transport);

        // List available tools
        const response = await this.client.request(
            { method: "tools/list" },
            ListToolsResultSchema
        );

        console.log("\nConnected to server with tools:", 
            response.tools.map(tool => tool.name));
    }

    private processToolResult(data: ToolResult[] | string | ExcelData): string | ExcelData {
        if (Array.isArray(data)) {
            const textResult = data.find(item => item.type === 'text');
            if (textResult && textResult.text) {
                return textResult.text;
            }
            
            const binaryResult = data.find(item => item.type === 'binary');
            if (binaryResult && binaryResult.data) {
                return binaryResult.data;
            }
            
            return "データが見つかりませんでした";
        }
        return data;
    }

    private summarizeExcelData(rawData: ToolResult[] | string | ExcelData, maxLength: number = 2000): string {
        try {
            const data = this.processToolResult(rawData);
            const excelData: ExcelData = typeof data === 'string' ? JSON.parse(data) : data;
            
            const summaryParts: string[] = [];
            
            for (const sheet of excelData.sheets) {
                const sheetName = sheet.name || 'Unknown';
                const sheetData = sheet.data;
                
                if (!sheetData || sheetData.length === 0) {
                    summaryParts.push(
                        `\n=== シート: ${sheetName} ===`,
                        "データなし"
                    );
                    continue;
                }
                
                const headers = Object.keys(sheetData[0]);
                const previewCount = 5;
                const previewData = sheetData.slice(0, previewCount);
                
                summaryParts.push(
                    `\n=== シート: ${sheetName} ===`,
                    `総行数: ${sheetData.length}行`,
                    `カラム: ${headers.join(', ')}`,
                    "\n=== データサンプル ===",
                    ...previewData.map(row => JSON.stringify(row))
                );
            }
            
            return summaryParts.join('\n');
        } catch (error) {
            if (error instanceof SyntaxError) {
                return String(rawData);
            }
            return `データの解析中にエラーが発生しました: ${error instanceof Error ? error.message : String(error)}`;
        }
    }

    async processQuery(query: string): Promise<string> {
        try {
            // Get available tools
            const response = await this.client.request(
                { method: "tools/list" },
                ListToolsResultSchema
            );

            const availableTools: ChatCompletionTool[] = response.tools.map(tool => ({
                type: "function",
                function: {
                    name: tool.name,
                    description: tool.description || undefined,
                    parameters: {
                        type: "object",
                        properties: tool.inputSchema?.properties || {},
                        required: tool.inputSchema?.required || []
                    }
                }
            }));

            console.log("Available tools:", JSON.stringify(availableTools, null, 2));

            // First GPT call to decide tool usage
            const initialResponse = await this.openai.chat.completions.create({
                model: MODEL,
                messages: [{ role: "user", content: query }],
                tools: availableTools,
                tool_choice: "auto"
            });

            const message = initialResponse.choices[0].message;
            if (!message.tool_calls || message.tool_calls.length === 0) {
                return message.content || "";
            }

            // Process tool calls
            const finalText: string[] = [];
            for (const toolCall of message.tool_calls) {
                const toolName = toolCall.function.name;
                const toolArgs = JSON.parse(toolCall.function.arguments);
                console.log(`Tool call: ${toolName}, args:`, toolArgs);

                // Execute tool call
                const result = await this.client.request(
                    {
                        method: "tools/call",
                        params: {
                            name: toolName,
                            arguments: toolArgs
                        }
                    },
                    CallToolResultSchema
                );

                const summarizedContent = this.summarizeExcelData(result.content);

                // Create a new chat to analyze the summarized data
                const analysisResponse = await this.openai.chat.completions.create({
                    model: MODEL,
                    messages: [{
                        role: "user",
                        content: `以下のExcelデータを分析して、主なポイントをまとめてください:\n\n${summarizedContent}`
                    }]
                });

                finalText.push(
                    "=== Excelファイルの内容 ===",
                    summarizedContent,
                    "\n=== 分析結果 ===",
                    analysisResponse.choices[0].message.content || ""
                );
            }

            return finalText.join('\n');

        } catch (error) {
            console.error("Error details:", error);
            return `エラーが発生しました: ${error instanceof Error ? error.message : String(error)}`;
        }
    }

    async chatLoop(): Promise<void> {
        console.log("\nMCP Client Started!");
        console.log("Type your queries or 'quit' to exit.");

        const rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });

        try {
            while (true) {
                const query = await new Promise<string>((resolve) => {
                    rl.question("\nQuery: ", resolve);
                });

                if (query.toLowerCase() === 'quit') {
                    break;
                }

                const response = await this.processQuery(query);
                console.log("\n" + response);
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'SIGINT') {
                console.log("\nChat loop interrupted by user");
            } else {
                console.error("\nError:", error);
            }
        } finally {
            rl.close();
        }
    }

    async cleanup(): Promise<void> {
        if (this.client) {
            try {
                await this.client.close();
            } catch (error) {
                console.error("Cleanup error:", error);
            }
        }
    }
}

async function main(): Promise<void> {
    const client = new MCPClient();
    try {
        await client.connect("C:\\workspace\\mcp\\servers\\excel\\dist\\index.js");
        await client.chatLoop();
    } finally {
        await client.cleanup();
    }
}

if (import.meta.url === `file://${process.argv[1]}`) {
    main().catch(console.error);
}

await main();

export default MCPClient;