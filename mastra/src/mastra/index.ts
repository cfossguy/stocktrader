import { Mastra } from "@mastra/core/mastra";
import { weatherAgent } from "./agents/weather-agent";
import { crewaiAgent } from "./agents/crewai-agent";
import { stockpickerWorkflow } from "./workflows/stockpicker-workflow";

 
export const mastra = new Mastra({
  agents: { weatherAgent, crewaiAgent },
  workflows: { stockpickerWorkflow }
});