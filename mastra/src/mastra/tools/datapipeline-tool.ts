import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { spawn } from "child_process";
import { config } from 'dotenv';

config();

const inputSchema = z.object({
  scriptCommand: z.enum(['run-data-pipeline', 'test-logging']).describe("Command options for python tool.")
});

const outputSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  details: z.record(z.string(), z.any()).optional(),
});

const scriptPaths: Record<string, string> = {
  'run-data-pipeline': process.env.PY_PIPELINE_PATH ?? '',
  'test-logging': process.env.PY_PIPELINE_PATH ?? ''
};

let currentExecution: Promise<z.infer<typeof outputSchema>> | null = null;

const executePython = async (params: z.infer<typeof inputSchema>): Promise<z.infer<typeof outputSchema>> => {
  if (currentExecution) {
    return currentExecution; // Wait for the ongoing execution to complete
  }

  currentExecution = new Promise(async (resolve) => {
    try {
      const { scriptCommand } = params;

      const scriptPath = scriptPaths[scriptCommand];
      const resolvedScriptPath = scriptPath || process.env.PY_PIPELINE_PATH;

      if (!resolvedScriptPath) {
        throw new Error('Script path is not specified and PY_PIPELINE_PATH is not set in .env');
      }

      console.log(`params: ${JSON.stringify(params)}`);
      console.log(`[PythonTool] Executing script: ${resolvedScriptPath} with command: ${scriptCommand}`);

      const args = ["-u", resolvedScriptPath, scriptCommand]; // -u = unbuffered stdout
      const child = spawn("python", args, {
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"],
      });

      let stdoutBuffer = "";
      let stderrBuffer = "";

      child.stdout.on("data", (data) => {
        stdoutBuffer += data.toString();
        process.stdout.write(`[Python stdout] ${data}`);
      });

      child.stderr.on("data", (data) => {
        stderrBuffer += data.toString();
        process.stderr.write(`[Python stderr] ${data}`);
      });

      const startTime = Date.now();
      await new Promise((resolveChild, rejectChild) => {
        child.on("error", rejectChild);
        child.on("close", (code, signal) => {
          const endTime = Date.now();
          if (code === 0) {
            resolveChild(undefined);
            resolve({
              success: true,
              message: "Python script executed successfully",
              details: {
                scriptPath: resolvedScriptPath,
                command: scriptCommand,
                stdout: stdoutBuffer.split("\n"), // Store each line as an array entry
                stderr: stderrBuffer.split("\n"),
                executionTime: `${((endTime - startTime) / 60000).toFixed(2)} minutes`,
              },
            });
          } else {
            rejectChild(new Error(`Python exited code=${code} signal=${signal ?? "none"}`));
          }
        });
      });
    } catch (error: any) {
      resolve({
        success: false,
        message: `Unexpected error: ${error.message}`,
        details: { error: error.message },
      });
    } finally {
      currentExecution = null; // Reset the execution tracker
    }
  });

  return currentExecution;
};

export const datapipelineTool = createTool({
  id: 'datapipeline-tool',
  description: 'Execute data pipeline commands',
  inputSchema,
  outputSchema,
  execute: async ({ context }) => {
    return executePython(context); // Directly await the result of executePython
  },
});
