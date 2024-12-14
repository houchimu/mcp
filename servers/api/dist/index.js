import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListResourcesRequestSchema, ListToolsRequestSchema, ReadResourceRequestSchema, } from "@modelcontextprotocol/sdk/types.js";
const server = new Server({
    name: "example-server",
    version: "1.0.0",
}, {
    capabilities: {
        resources: {},
        tools: {} // この行を追加
    }
});
server.setRequestHandler(ListResourcesRequestSchema, async () => {
    return {
        resources: [
            {
                uri: "file:///example.txt",
                name: "Example Resource",
            },
        ],
    };
});
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    if (request.params.uri === "file:///example.txt") {
        return {
            contents: [
                {
                    uri: "file:///example.txt",
                    mimeType: "text/plain",
                    text: "This is the content of the example resource.",
                },
            ],
        };
    }
    else {
        throw new Error("Resource not found");
    }
});
const testapi = {
    name: "test",
    description: "てすとです",
    inputSchema: {
        type: "object",
        properties: {
            block_id: {
                type: "string",
                description: "The ID of the parent block. It should be a 32-character string (excluding hyphens) formatted as 8-4-4-4-12 with hyphens (-).",
            },
            children: {
                type: "array",
                description: "Array of block objects to append",
            },
        },
        required: ["block_id", "children"],
    },
};
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    console.error("Received CallToolRequest:", request);
    if (!request.params.arguments) {
        throw new Error("No arguments provided");
    }
    switch (request.params.name) {
        case "test": {
            const response = { test: "test" };
            return {
                content: [{ type: "text", text: JSON.stringify(response) }],
            };
        }
        default: return {
            content: [{ type: "text", text: "default" }],
        };
    }
});
server.setRequestHandler(ListToolsRequestSchema, async () => {
    console.error("Received ListToolsRequest");
    return {
        tools: [
            testapi
        ],
    };
});
const transport = new StdioServerTransport();
await server.connect(transport);
