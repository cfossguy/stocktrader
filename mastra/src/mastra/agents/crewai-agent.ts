import { openai } from "@ai-sdk/openai";
import { Agent } from "@mastra/core/agent";
import { crewaiChatTool } from "../tools/crewai-chat-tool";

export const crewaiAgent = new Agent({
  name: 'CrewAI Agent',
  instructions: `
      You are a helpful assistant that interacts with Elasticsearch.

      Your primary function is to help users query, summarize, and analyze the content of stockpicker_agent data. When responding:
      - Always use crewaiChatTool to load data into context before answering any questions.
      - Only use the data provided by crewaiChatTool to answer questions. Do not make assumptions or use external knowledge.
      - Keep responses concise but informative.

      Always use crewaiChatTool to answer questions.
`,
  model: openai('gpt-4o-mini'),
  tools: { crewaiChatTool }
});
