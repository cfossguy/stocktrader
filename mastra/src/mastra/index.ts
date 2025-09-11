import { Mastra } from "@mastra/core/mastra";
import { crewaiAgent } from "./agents/crewai-agent";
import { stockpickerWorkflow } from "./workflows/stockpicker-workflow";

 
export const mastra = new Mastra({
  agents: { crewaiAgent },
  workflows: { stockpickerWorkflow }
});