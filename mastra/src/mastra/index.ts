import { Mastra } from "@mastra/core/mastra";
import { commanderAgent } from "./agents/commander-agent";
import { stockpickerWorkflow } from "./workflows/stockpicker-workflow";

 
export const mastra = new Mastra({
  agents: { commanderAgent },
  workflows: { stockpickerWorkflow }
});