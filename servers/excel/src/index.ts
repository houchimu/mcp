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
import { read, utils, Sheet2JSONOpts } from 'xlsx';
import * as fs from 'fs/promises';

const server = new Server({
  name: "excel-reader",
  version: "1.0.0",
}, {
  capabilities: {
    resources: {},
    tools: {}
  }
});

type CellValue = string | number | boolean | Date | null;

type SheetData = {
  [key: string]: CellValue;
}[];

interface ExcelData {
  sheets: {
    name: string;
    data: SheetData;
  }[];
}

interface ReadExcelParams {
  filePath: string;
}

const readExcelTool: Tool = {
  name: "read_excel",
  description: "Excelファイルを読み取り、データを返します",
  inputSchema: {
    type: "object",
    properties: {
      filePath: {
        type: "string",
        description: "Excelファイルのパス"
      }
    },
    required: ["filePath"],
  },
};

server.setRequestHandler(
  CallToolRequestSchema,
  async (request: CallToolRequest) => {
    switch (request.params.name) {
      case "read_excel": {
        try {
          const params = request.params.arguments as unknown as ReadExcelParams;
          const filePath = params.filePath;
          
          // ファイルを非同期で読み込む
          const buffer = await fs.readFile(filePath);
          
          // バッファからワークブックを読み込む
          const workbook = read(buffer, {
            type: 'buffer',
            cellStyles: true,
            cellFormula: true,
            cellDates: true,
            cellNF: true,
            sheetStubs: true,
            codepage: 932  // Shift-JIS用のコードページ
          });

          const result: ExcelData = {
            sheets: []
          };

          // 各シートのデータを処理
          for (const sheetName of workbook.SheetNames) {
            const worksheet = workbook.Sheets[sheetName];
            const options: Sheet2JSONOpts = {
              raw: true,  // 生データを取得
              dateNF: 'yyyy-mm-dd',
              defval: null  // 空セルの扱い
            };
            
            const sheetData = utils.sheet_to_json(worksheet, options) as SheetData;
            
            // データの後処理
            const processedData = sheetData.map(row => {
              const processedRow: { [key: string]: CellValue } = {};
              for (const [key, value] of Object.entries(row)) {
                // 日付型の処理
                if (value instanceof Date) {
                  processedRow[key] = value.toISOString().split('T')[0];
                } else {
                  processedRow[key] = value as CellValue;
                }
              }
              return processedRow;
            });

            result.sheets.push({
              name: sheetName,
              data: processedData
            });
          }

          return {
            content: [{ type: "text", text: JSON.stringify(result) }],
          };
        } catch (error: any) {
          console.error('Excel読み取りエラー:', error);
          const errorMessage = error instanceof Error ? error.message : '不明なエラーが発生しました';
          return {
            content: [{ type: "text", text: JSON.stringify({ 
              error: "Excelファイルの読み取りに失敗しました",
              details: errorMessage
            }) }],
          };
        }
      }
      default: 
        return {
          content: [{ type: "text", text: "サポートされていない操作です" }],
        };
    }
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [readExcelTool],
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