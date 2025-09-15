import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { config } from "dotenv";
import { Client } from '@elastic/elasticsearch';

config();

const inputSchema = z.object({
  ticker: z
    .string()
    .describe("Ticker symbol to search for."),
  size: z
    .number()
    .int()
    .min(1)
    .max(30)
    .default(10)
    .describe("Number of documents to retrieve (1-30), default 10."),
});

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

const executeTickerAnalyticsLookupTool = async (input: z.infer<typeof inputSchema>): Promise<z.infer<typeof outputSchema>> => {
  try {
    if (!process.env.ELASTIC_SEARCH_URL) {
      throw new Error("Elasticsearch URL is not set. Ensure ELASTIC_SEARCH_URL is defined in the .env file.");
    }

    if (!process.env.ES_API_KEY) {
      throw new Error("Elasticsearch API key is not set. Ensure ES_API_KEY is defined in the .env file.");
    }

    // Log input for debugging
    console.log("Input received:", input);

    // Extract parameters from input.context
    const { ticker, size } = input.context;

    // Validate ticker explicitly
    if (!ticker || typeof ticker !== 'string' || ticker.trim() === '') {
      throw new Error("The 'ticker' parameter is required and must be a non-empty string.");
    }

    // Validate input using zod schema
    const validatedInput = inputSchema.parse({ ticker, size });

    // Log validated input
    console.log("Validated input:", validatedInput);

    // Prepare search template parameters
    const templateParams: Record<string, any> = {
      ticker: validatedInput.ticker,
      size: validatedInput.size,
    };

    // Log template parameters
    console.log("Template parameters:", templateParams);

    // Use search template
    const response = await client.searchTemplate({
      index: 'ticker_analytics',
      id: 'ticker_analytics_lookup_template',
      params: templateParams
    });

    return {
      success: true,
      message: `Retrieved ${response.hits.hits.length} documents from Elasticsearch for ticker: ${validatedInput.ticker}.`,
      data: response.hits.hits,
    };
  } catch (error: any) {
    return {
      success: false,
      message: `Error querying Elasticsearch: ${error.message}`,
    };
  }
};

export const tickerAnalyticsLookupTool = createTool({
  id: "ticker-analytics-lookup-tool",
  description: "Search ticker analytics data from Elasticsearch using the ticker_analytics_lookup_template. Requires a ticker symbol.",
  inputSchema,
  outputSchema,
  execute: async (input: any) => {
    // Pass input directly to executeTickerAnalyticsLookupTool, letting zod handle defaults
    return executeTickerAnalyticsLookupTool(input);
  },
});
