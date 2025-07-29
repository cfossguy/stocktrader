import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { config } from "dotenv";
import { Client } from '@elastic/elasticsearch';

config();

const outputSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  data: z.record(z.string(), z.string()).optional(),
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

const executeCrewAIChatTool = async (): Promise<z.infer<typeof outputSchema>> => {
  try {
    if (!process.env.ELASTIC_SEARCH_URL) {
      throw new Error("Elasticsearch URL is not set. Ensure ELASTIC_SEARCH_URL is defined in the .env file.");
    }
    
    if (!process.env.ES_API_KEY) {
      throw new Error("Elasticsearch API key is not set. Ensure ES_API_KEY is defined in the .env file.");
    }

    // Query Elasticsearch for the latest documents
    const response = await client.search<StockPickerDoc>({
      index: 'stockpicker_agent',
      size: 1, // Get up to 10 latest documents
      track_total_hits: true,
      sort: [
        { 'date': { order: 'desc' as const } }
      ],
      _source: [
        'date',
        'account_balance',
        'account_details',
        'cash_position_usd',
        'date',
        'etf_report',
        'final_report',
        'fundamental_report',
        'portfolio_report',
        'screen_report',
        'stock_position_usd',
        'stocks_owned',
        'technical_report'
      ]
    });

    // Format the results into a record
    const documentContents: Record<string, string> = {};
    
    if (response.hits.hits.length === 0) {
      return {
        success: true,
        message: "No documents found in Elasticsearch.",
        data: {},
      };
    }

    // Process each document and add it to the record
    for (const hit of response.hits.hits) {
      if (hit._source) {
        const doc = hit._source;
        
        // Add date information if available
        if (doc.date) {
          documentContents['date'] = doc.date;
        }
        
        // Create entries for each report type if available
        if (doc.final_report) {
          documentContents['final_report'] = doc.final_report;
        }
        
        if (doc.etf_report) {
          documentContents['etf_report'] = doc.etf_report;
        }
        
        if (doc.fundamental_report) {
          documentContents['fundamental_report'] = doc.fundamental_report;
        }
        
        if (doc.portfolio_report) {
          documentContents['portfolio_report'] = doc.portfolio_report;
        }
        
        if (doc.screen_report) {
          documentContents['screen_report'] = doc.screen_report;
        }
        
        if (doc.technical_report) {
          documentContents['technical_report'] = doc.technical_report;
        }
        
        // If there's account details, add it as structured data
        if (doc.account_details) {
          documentContents['account_details'] = JSON.stringify(doc.account_details, null, 2);
        }
        
        // If there's stocks owned data, add it as structured data
        if (doc.stocks_owned && doc.stocks_owned.length > 0) {
          documentContents['stocks_owned'] = JSON.stringify(doc.stocks_owned, null, 2);
        }
        
        // Add account balance and positions if available
        if (doc.account_balance !== undefined) {
          documentContents['account_balance'] = doc.account_balance.toString();
        }
        
        if (doc.cash_position_usd !== undefined) {
          documentContents['cash_position_usd'] = doc.cash_position_usd.toString();
        }
        
        if (doc.stock_position_usd !== undefined) {
          documentContents['stock_position_usd'] = doc.stock_position_usd.toString();
        }
        
        // Fallback to original fields if none of the specific reports are available
        if (Object.keys(documentContents).length === 0 && doc.content) {
          const key = doc.title || `document_${hit._id}`;
          documentContents[key] = doc.content;
        }
        
        // If we still have nothing, add the raw document
        if (Object.keys(documentContents).length === 0) {
          documentContents[`document_${hit._id}`] = JSON.stringify(doc, null, 2);
        }
      }
    }

    return {
      success: true,
      message: `Retrieved ${response.hits.hits.length} documents from Elasticsearch. Latest data from ${response.hits.hits[0]?._source?.date || 'unknown date'}.`,
      data: documentContents,
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
  description: "Retrieve the latest stock picker agent data from Elasticsearch for context.",
  outputSchema,
  execute: async () => {
    return executeCrewAIChatTool();
  },
});
