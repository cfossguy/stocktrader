import { Mastra } from "@mastra/core/mastra";
import { commanderAgent } from "./agents/commander-agent";
import { stockpickerWorkflow } from "./workflows/stockpicker-workflow";
import { mcpAgent } from "./agents/mcp-agent";

 
export const mastra = new Mastra({
  agents: { commanderAgent, mcpAgent },
  workflows: { stockpickerWorkflow }
});