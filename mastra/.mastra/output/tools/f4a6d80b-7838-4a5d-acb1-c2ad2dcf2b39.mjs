import { createTool } from '@mastra/core/tools';
import { z } from 'zod';
import { config } from 'dotenv';
import { Client } from '@elastic/elasticsearch';

config();
const outputSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  data: z.record(z.string(), z.string()).optional()
});
const client = new Client({
  node: process.env.ELASTIC_SEARCH_URL,
  auth: {
    apiKey: process.env.ES_API_KEY
  }
});
const executeCrewAIChatTool = async () => {
  try {
    if (!process.env.ELASTIC_SEARCH_URL) {
      throw new Error("Elasticsearch URL is not set. Ensure ELASTIC_SEARCH_URL is defined in the .env file.");
    }
    if (!process.env.ES_API_KEY) {
      throw new Error("Elasticsearch API key is not set. Ensure ES_API_KEY is defined in the .env file.");
    }
    const response = await client.search({
      index: "stockpicker_agent",
      size: 1,
      // Get the latest document
      track_total_hits: true,
      sort: [
        { "date": { order: "desc" } }
      ],
      _source: [
        "date",
        "account_balance",
        "account_details",
        "cash_position_usd",
        "date",
        "etf_report",
        "final_report",
        "fundamental_report",
        "portfolio_report",
        "screen_report",
        "stock_position_usd",
        "stocks_owned",
        "technical_report"
      ]
    });
    const documentContents = {};
    if (response.hits.hits.length === 0) {
      return {
        success: true,
        message: "No documents found in Elasticsearch.",
        data: {}
      };
    }
    for (const hit of response.hits.hits) {
      if (hit._source) {
        const doc = hit._source;
        if (doc.date) {
          documentContents["date"] = doc.date;
        }
        if (doc.final_report) {
          documentContents["final_report"] = doc.final_report;
        }
        if (doc.etf_report) {
          documentContents["etf_report"] = doc.etf_report;
        }
        if (doc.fundamental_report) {
          documentContents["fundamental_report"] = doc.fundamental_report;
        }
        if (doc.portfolio_report) {
          documentContents["portfolio_report"] = doc.portfolio_report;
        }
        if (doc.screen_report) {
          documentContents["screen_report"] = doc.screen_report;
        }
        if (doc.technical_report) {
          documentContents["technical_report"] = doc.technical_report;
        }
        if (doc.account_details) {
          documentContents["account_details"] = JSON.stringify(doc.account_details, null, 2);
        }
        if (doc.stocks_owned && doc.stocks_owned.length > 0) {
          documentContents["stocks_owned"] = JSON.stringify(doc.stocks_owned, null, 2);
        }
        if (doc.account_balance !== void 0) {
          documentContents["account_balance"] = doc.account_balance.toString();
        }
        if (doc.cash_position_usd !== void 0) {
          documentContents["cash_position_usd"] = doc.cash_position_usd.toString();
        }
        if (doc.stock_position_usd !== void 0) {
          documentContents["stock_position_usd"] = doc.stock_position_usd.toString();
        }
        if (Object.keys(documentContents).length === 0 && doc.content) {
          const key = doc.title || `document_${hit._id}`;
          documentContents[key] = doc.content;
        }
        if (Object.keys(documentContents).length === 0) {
          documentContents[`document_${hit._id}`] = JSON.stringify(doc, null, 2);
        }
      }
    }
    return {
      success: true,
      message: `Retrieved ${response.hits.hits.length} documents from Elasticsearch. Latest data from ${response.hits.hits[0]?._source?.date || "unknown date"}.`,
      data: documentContents
    };
  } catch (error) {
    return {
      success: false,
      message: `Error querying Elasticsearch: ${error.message}`
    };
  }
};
const crewaiChatTool = createTool({
  id: "crewai-chat-tool",
  description: "Retrieve the latest stock picker agent data from Elasticsearch for context.",
  outputSchema,
  execute: async () => {
    return executeCrewAIChatTool();
  }
});

export { crewaiChatTool };
//# sourceMappingURL=f4a6d80b-7838-4a5d-acb1-c2ad2dcf2b39.mjs.map
