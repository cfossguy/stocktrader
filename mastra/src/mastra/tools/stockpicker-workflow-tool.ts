import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { stockpickerWorkflow } from "../workflows/stockpicker-workflow";

const inputSchema = z.object({
  // No input parameters needed - the tool execution itself indicates intent to run workflow
});

const outputSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  workflowResult: z.object({
    dataPipelineSuccess: z.boolean(),
    crewAISuccess: z.boolean(),
    workflowCompleted: z.boolean(),
    finalMessage: z.string(),
    completionMessage: z.string(),
    totalExecutionTime: z.string()
  }).optional(),
});

const executeWorkflowTool = async (input: z.infer<typeof inputSchema>): Promise<z.infer<typeof outputSchema>> => {
  const startTime = Date.now();
  
  try {
    // Execute the stockpicker workflow directly
    const run = await stockpickerWorkflow.createRunAsync();
    const result = await run.start({
      inputData: {},
    });

    // Calculate total execution time
    const endTime = Date.now();
    const totalExecutionTimeMinutes = ((endTime - startTime) / 1000 / 60).toFixed(2);
    const totalExecutionTime = `${totalExecutionTimeMinutes} minutes`;

    if (result.status === 'success') {
      // Update the workflow result with the captured timing
      const workflowResult = {
        ...result.result,
        totalExecutionTime: result.result.totalExecutionTime || totalExecutionTime
      };

      return {
        success: true,
        message: `Stockpicker workflow executed successfully in ${totalExecutionTime}. Data pipeline: ${result.result.dataPipelineSuccess ? 'Success' : 'Failed'}, CrewAI: ${result.result.crewAISuccess ? 'Success' : 'Failed'}`,
        workflowResult,
      };
    } else if (result.status === 'failed') {
      return {
        success: false,
        message: `Stockpicker workflow failed after ${totalExecutionTime}: ${result.error}`,
        workflowResult: {
          dataPipelineSuccess: false,
          crewAISuccess: false,
          workflowCompleted: false,
          finalMessage: `Workflow failed: ${result.error}`,
          completionMessage: `Workflow execution failed after ${totalExecutionTime}`,
          totalExecutionTime
        }
      };
    } else {
      return {
        success: false,
        message: `Stockpicker workflow was suspended after ${totalExecutionTime}: ${JSON.stringify(result.suspended)}`,
        workflowResult: {
          dataPipelineSuccess: false,
          crewAISuccess: false,
          workflowCompleted: false,
          finalMessage: `Workflow was suspended: ${JSON.stringify(result.suspended)}`,
          completionMessage: `Workflow execution was suspended after ${totalExecutionTime}`,
          totalExecutionTime
        }
      };
    }
  } catch (error: any) {
    const endTime = Date.now();
    const totalExecutionTimeMinutes = ((endTime - startTime) / 1000 / 60).toFixed(2);
    const totalExecutionTime = `${totalExecutionTimeMinutes} minutes`;

    return {
      success: false,
      message: `Error executing stockpicker workflow after ${totalExecutionTime}: ${error.message}`,
      workflowResult: {
        dataPipelineSuccess: false,
        crewAISuccess: false,
        workflowCompleted: false,
        finalMessage: `Error: ${error.message}`,
        completionMessage: `Workflow execution failed with error after ${totalExecutionTime}`,
        totalExecutionTime
      }
    };
  }
};

export const stockpickerWorkflowTool = createTool({
  id: "stockpicker-workflow-tool",
  description: "Execute the stockpicker workflow which runs the data pipeline and CrewAI analysis to generate new stock reports.",
  inputSchema,
  outputSchema,
  execute: async (input: any) => {
    return executeWorkflowTool(input);
  },
});
