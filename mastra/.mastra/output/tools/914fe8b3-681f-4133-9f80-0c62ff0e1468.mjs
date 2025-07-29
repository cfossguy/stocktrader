import { createTool } from '@mastra/core/tools';
import { z } from 'zod';
import { spawn } from 'child_process';
import { config } from 'dotenv';

config();
const inputSchema = z.object({
  command: z.enum(["run"]).default("run").describe("Command options for CrewAI tool.")
});
const outputSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  details: z.record(z.string(), z.any()).optional()
});
let currentExecution = null;
const executeCrewAI = async (params) => {
  if (currentExecution) {
    return currentExecution;
  }
  currentExecution = new Promise(async (resolve) => {
    try {
      const { command } = params;
      const crewAIPath = process.env.PY_CREW_AI_PATH;
      if (!crewAIPath) {
        throw new Error("PY_CREW_AI_PATH is not set in .env");
      }
      console.log(`params: ${JSON.stringify(params)}`);
      console.log(`[CrewAITool] Executing command: ${command} in directory: ${crewAIPath}`);
      const child = spawn("crewai", [command], {
        cwd: crewAIPath,
        // Set the working directory to PY_CREW_AI_PATH
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"]
      });
      let stdoutBuffer = "";
      let stderrBuffer = "";
      child.stdout.on("data", (data) => {
        stdoutBuffer += data.toString();
        process.stdout.write(`[CrewAI stdout] ${data}`);
      });
      child.stderr.on("data", (data) => {
        stderrBuffer += data.toString();
        process.stderr.write(`[CrewAI stderr] ${data}`);
      });
      const startTime = Date.now();
      await new Promise((resolveChild, rejectChild) => {
        child.on("error", rejectChild);
        child.on("close", (code, signal) => {
          const endTime = Date.now();
          if (code === 0) {
            resolveChild(void 0);
            resolve({
              success: true,
              message: "CrewAI command executed successfully",
              details: {
                command,
                stdout: stdoutBuffer.split("\n"),
                // Store each line as an array entry
                stderr: stderrBuffer.split("\n"),
                executionTime: `${((endTime - startTime) / 6e4).toFixed(2)} minutes`
              }
            });
          } else {
            rejectChild(new Error(`CrewAI exited code=${code} signal=${signal ?? "none"}`));
          }
        });
      });
    } catch (error) {
      resolve({
        success: false,
        message: `Unexpected error: ${error.message}`,
        details: { error: error.message }
      });
    } finally {
      currentExecution = null;
    }
  });
  return currentExecution;
};
const crewaiTool = createTool({
  id: "crewai-tool",
  description: "Execute CrewAI commands",
  inputSchema,
  outputSchema,
  execute: async ({ context }) => {
    return executeCrewAI(context);
  }
});

export { crewaiTool };
//# sourceMappingURL=914fe8b3-681f-4133-9f80-0c62ff0e1468.mjs.map
