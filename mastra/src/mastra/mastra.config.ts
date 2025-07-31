import { Mastra } from "@mastra/core";
import { PinoLogger } from "@mastra/loggers";
 
export const mastra = new Mastra({
  // Other Mastra configuration...
  logger: new PinoLogger({
    name: "Mastra",
    level: "info",
  }),
});