
import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { config } from "dotenv";
import { Client } from '@elastic/elasticsearch';

config();


const inputSchema = z.object({
  semantic: z
    .boolean()
    .default(false)
    .describe("Whether to perform semantic search. If true, query parameter is required."),
  query: z
    .string()
    .optional()
    .describe("Search query text for semantic search. Required when semantic is true."),
  size: z
    .number()
    .int()
    .min(1)
    .max(30)
    .default(10)
    .describe("Number of documents to retrieve (1-30), default 10."),
}).refine(
  (data) => !data.semantic || (data.semantic && data.query),
  {
    message: "Query parameter is required when semantic search is enabled",
    path: ["query"],
  }
);

const outputSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  data: z.array(z.any()).optional(),
});

// Initialize Elasticsearch client
const client = new Client({ 
  node: process.env.ELASTIC_SEARCH_URL!,
  auth: {
    apiKey: process.env.ES_API_KEY!
  }
});

// Type definition for Elasticsearch document
type StockPickerDoc = {
  account_balance?: number;
  account_details?: {
    account_id?: string;
    cash_position_usd?: string;
    stock_position_usd?: string;
  };
  cash_position_usd?: number;
  date?: string; // format: MM-dd-yyyy
  etf_report?: string;
  final_report?: string;
  fundamental_report?: string;
  portfolio_report?: string;
  screen_report?: string;
  stock_position_usd?: number;
  stocks_owned?: Array<{
    average_cost_per_share?: string;
    null?: string;
    ticker?: string;
    total_usd?: number;
  }>;
  technical_report?: string;
  // Keep original fields for backward compatibility
  content?: string;
  type?: string;
  title?: string;
};


const executeCrewAIChatTool = async (input: z.infer<typeof inputSchema>): Promise<z.infer<typeof outputSchema>> => {
  try {
    if (!process.env.ELASTIC_SEARCH_URL) {
      throw new Error("Elasticsearch URL is not set. Ensure ELASTIC_SEARCH_URL is defined in the .env file.");
    }
    
    if (!process.env.ES_API_KEY) {
      throw new Error("Elasticsearch API key is not set. Ensure ES_API_KEY is defined in the .env file.");
    }

    // Prepare search template parameters
    const templateParams: Record<string, any> = {
      semantic: input.semantic,
      size: input.size
    };

    // Add query parameter only for semantic search
    if (input.semantic && input.query) {
      templateParams.query = input.query;
    }

    // Use search template
    const response = await client.searchTemplate<StockPickerDoc>({
      index: 'stockpicker_agent',
      id: 'stockpicker_agent_template',
      params: templateParams
    });

    return {
      success: true,
      message: `Retrieved ${response.hits.hits.length} documents from Elasticsearch using ${input.semantic ? 'semantic' : 'default'} search${input.semantic && input.query ? ` for query: "${input.query}"` : ''}. Latest data from ${response.hits.hits[0]?._source?.date || 'unknown date'}.`,
      data: response.hits.hits,
    };
  } catch (error: any) {
    return {
      success: false,
      message: `Error querying Elasticsearch: ${error.message}`,
    };
  }
};

export const crewaiChatTool = createTool({
  id: "crewai-chat-tool",
  description: "Search stock picker agent data from Elasticsearch using the stockpicker_agent_template. Supports both semantic search (with query) and default search (without query).",
  inputSchema,
  outputSchema,
  execute: async (input: any) => {
    // Pass input directly to executeCrewAIChatTool, letting zod handle defaults
    return executeCrewAIChatTool(input);
  },
});
