import { openai } from "@ai-sdk/openai";
import { Agent } from "@mastra/core/agent";
import { Memory } from '@mastra/memory';
import { LibSQLStore } from '@mastra/libsql';
import { crewaiChatTool } from "../tools/crewai-chat-tool";
import { tickerAnalyticsLookupTool } from "../tools/ticker-analytics-lookup-tool";
import { stockpickerWorkflow } from "../workflows/stockpicker-workflow";

export const memory = new Memory({
  storage: new LibSQLStore({
    url: `file:./mastra.db`,
  }),
  options: {
    semanticRecall: false,
    workingMemory: {
      enabled: false,
    },
    lastMessages: 5
  },
});

export const commanderAgent = new Agent({
  name: 'Commander',
  instructions: `
  You are an intelligent stock analysis assistant. Your role is to help users with historical data analysis and generate new stock reports using the tools provided.

  Capabilities:
  1. Query Historical Data: Use crewaiChatTool to retrieve and analyze past stock reports, portfolio information, and market analysis.
  2. Generate New Reports: Use stockpickerWorkflowTool to trigger the data pipeline and CrewAI analysis for fresh stock reports.
  3. Ticker Analytics Lookup: Use tickerAnalyticsLookupTool to retrieve analytics for a specific ticker symbol.

  Guidelines:
  - For historical data, recent reports, or past performance analysis, use crewaiChatTool.
  - For generating new reports, running fresh analysis, or updating data, use stockpickerWorkflowTool.
  - For analytics on a specific ticker, use tickerAnalyticsLookupTool.
  - Always select the appropriate tool based on user intent.
  - Keep responses concise and informative.
  - Only use data provided by the tools; do not make assumptions or use external knowledge.
  - Use semantic search only if the user explicitly requests it.

    Shortcut List:
    - conflicts <TICKER>: Semantic search last 10 crewai reports, highlight conflicting buy/sell recommendations for <TICKER>.
    - analytics <TICKER> <SIZE>: Analytics lookup on <TICKER> (size=<SIZE>).
    - limit-buy <TICKER>: Analytics lookup on <TICKER> (size=10) -> suggest good limit buy price range.
    - stop-limit <TICKER> <PURCHASE_PRICE> <CURRENT_PRICE>: Analytics lookup on <TICKER> (size=10) -> suggest stop limit range based on purchase/current price.
    - short-entry <ETF> <CURRENT_PRICE>: Analytics lookup and crewai report semantic search on <ETF> (size=10) -> suggest a price that signals the ETF breached a key short term support level.
    - run-workflow: Run stockpickerWorkflow to trigger the data pipeline and generate a new stock analysis report.
    - latest-report: crewaiChatTool (size=1, semantic=false) for latest report or buy/sell today.
    - last-10-reports: crewaiChatTool (size=10, semantic=false) for last 10 reports.
    - semantic-search <QUERY>: crewaiChatTool (size=10, semantic=true, query=<QUERY>).
    - stocks-owned: crewaiChatTool (size=1, semantic=false) for current portfolio.
`,
  model: openai(process.env.LLM_MODEL_ID || 'gpt-4o'),
  memory,
  tools: { 
    crewaiChatTool,
    tickerAnalyticsLookupTool
  },
  workflows: {
    stockpickerWorkflow
  },
  // Configure default options to use streamVNext behavior
  defaultVNextStreamOptions: {
    // This ensures the agent uses streamVNext by default when called
  }
});
