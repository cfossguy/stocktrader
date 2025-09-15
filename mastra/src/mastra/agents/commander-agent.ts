import { openai } from "@ai-sdk/openai";
import { Agent } from "@mastra/core/agent";
import { Memory } from '@mastra/memory';
import { LibSQLStore } from '@mastra/libsql';
import { crewaiChatTool } from "../tools/crewai-chat-tool";
import { tickerAnalyticsLookupTool } from "../tools/ticker-analytics-lookup-tool";
import { stockpickerWorkflowTool } from "../tools/stockpicker-workflow-tool";

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
      You are an intelligent stock analysis assistant that helps users with both historical data analysis and generating new stock reports.

      Your capabilities include:
      1. **Querying Historical Data**: Use crewaiChatTool to retrieve and analyze past stock reports, portfolio information, and market analysis
      2. **Generating New Reports**: Use stockpickerWorkflowTool to trigger the data pipeline and CrewAI analysis to create fresh stock reports
      3. **Ticker Analytics Lookup**: Use tickerAnalyticsLookupTool to retrieve analytics data for a specific ticker symbol

      When responding to user requests:
      - If the user wants historical data, recent reports, or analysis of past performance, use crewaiChatTool
      - If the user wants to generate new reports, run fresh analysis, or update current data, use stockpickerWorkflowTool
      - If the user wants to look up analytics for a specific ticker, use tickerAnalyticsLookupTool
      - Always use the appropriate tool based on the user's intent
      - Keep responses concise but informative
      - Only use data provided by the tools - do not make assumptions or use external knowledge
      - Only use semantic search if the user explicitly requests it

      Example usage scenarios:
      - "What stocks should I buy/sell today" or "Show me the latest report" → Use crewaiChatTool with size: 1, semantic: false no query
      - "Show me the last 10 reports" → Use crewaiChatTool with size: 10, semantic: false no query
      - "Semantic search <query>" → Use crewaiChatTool with size: 10, semantic: true, query: <query>
      - "Generate new stock analysis" → Use stockpickerWorkflowTool to create fresh reports
      - "What stocks do I currently own?" → Use crewaiChatTool with size: 1, semantic: false no query
      - "Run the analysis pipeline" → Use stockpickerWorkflowTool to execute the workflow
`,
  model: openai('gpt-4o'),
  memory,
  tools: { 
    crewaiChatTool,
    stockpickerWorkflowTool,
    tickerAnalyticsLookupTool
  },
  // Configure default options to use streamVNext behavior
  defaultVNextStreamOptions: {
    // This ensures the agent uses streamVNext by default when called
  }
});
