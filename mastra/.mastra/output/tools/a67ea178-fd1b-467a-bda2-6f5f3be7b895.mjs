import { createTool } from '@mastra/core/tools';
import { z } from 'zod';

const weatherTool = createTool({
  id: "get-weather",
  description: "Get current weather for a location",
  inputSchema: z.object({
    location: z.string().describe("City name")
  }),
  outputSchema: z.object({
    output: z.string()
  }),
  execute: async () => {
    return {
      output: "The weather is sunny"
    };
  }
});

export { weatherTool };
//# sourceMappingURL=a67ea178-fd1b-467a-bda2-6f5f3be7b895.mjs.map
