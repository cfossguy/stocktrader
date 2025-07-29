import { createWorkflow, createStep } from "@mastra/core/workflows";
import { z } from "zod";
import { datapipelineTool } from "../tools/datapipeline-tool";
import { crewaiTool } from "../tools/crewai-tool";

// Step 1: Data Pipeline step
const runDataPipelineStep = createStep({
  id: "run-data-pipeline-step",
  description: "Runs the data pipeline to gather market data",
  inputSchema: z.object({}),
  outputSchema: z.object({
    pipelineSuccess: z.boolean(),
    message: z.string(),
    executionTime: z.string().optional()
  }),
  execute: async ({ runtimeContext }) => {
    // Execute the data pipeline tool
    const result = await datapipelineTool.execute({
      context: { scriptCommand: "run-data-pipeline" },
      runtimeContext
    });

    return {
      pipelineSuccess: result.success,
      message: result.message,
      executionTime: result.details?.executionTime
    };
  }
});

// Step 2: CrewAI step
const runCrewAIStep = createStep({
  id: "run-crewai-step",
  description: "Runs the CrewAI analysis on market data",
  inputSchema: z.object({
    pipelineSuccess: z.boolean(),
    message: z.string(),
    executionTime: z.string().optional()
  }),
  outputSchema: z.object({
    success: z.boolean(),
    message: z.string(),
    executionTime: z.string().optional()
  }),
  execute: async (params) => {
    // Only run CrewAI if data pipeline was successful
    if (!params.inputData.pipelineSuccess) {
      return {
        success: false,
        message: `CrewAI execution skipped. Data pipeline failed: ${params.inputData.message}`,
        executionTime: "0 minutes"
      };
    }

    // Execute the CrewAI tool
    const result = await crewaiTool.execute({
      context: { command: "run" },
      runtimeContext: params.runtimeContext
    });

    return {
      success: result.success,
      message: result.message,
      executionTime: result.details?.executionTime
    };
  }
});

// Define types for our step outputs
type StepOutputs = {
  "run-data-pipeline-step": {
    pipelineSuccess: boolean;
    message: string;
    executionTime?: string;
  };
  "run-crewai-step": {
    success: boolean;
    message: string;
    executionTime?: string;
  };
};

// Define the workflow
export const stockpickerWorkflow = createWorkflow({
  id: "stockpicker-workflow",
  description: "Workflow to run data pipeline and then CrewAI analysis",
  inputSchema: z.object({}),
  outputSchema: z.object({
    dataPipelineSuccess: z.boolean(),
    crewAISuccess: z.boolean(),
    finalMessage: z.string(),
    totalExecutionTime: z.string().optional()
  })
})
  .then(runDataPipelineStep)
  .then(runCrewAIStep)
  .map({
    dataPipelineSuccess: {
      value: (outputs: StepOutputs) => outputs["run-data-pipeline-step"].pipelineSuccess,
      schema: z.boolean()
    },
    crewAISuccess: {
      value: (outputs: StepOutputs) => outputs["run-crewai-step"].success,
      schema: z.boolean()
    },
    finalMessage: {
      value: (outputs: StepOutputs) => {
        return `Data Pipeline: ${outputs["run-data-pipeline-step"].message}. CrewAI: ${outputs["run-crewai-step"].message}`;
      },
      schema: z.string()
    },
    totalExecutionTime: {
      value: (outputs: StepOutputs) => {
        const pipelineOutput = outputs["run-data-pipeline-step"];
        const crewAIOutput = outputs["run-crewai-step"];
        
        if (pipelineOutput.executionTime && crewAIOutput.executionTime) {
          // Extract minutes from strings like "2.50 minutes"
          const pipelineTimeStr = pipelineOutput.executionTime || "0 minutes";
          const crewAITimeStr = crewAIOutput.executionTime || "0 minutes";
          
          const pipelineTime = parseFloat(pipelineTimeStr.split(" ")[0]) || 0;
          const crewAITime = parseFloat(crewAITimeStr.split(" ")[0]) || 0;
          
          return `${(pipelineTime + crewAITime).toFixed(2)} minutes`;
        }
        
        return "unknown";
      },
      schema: z.string()
    }
  })
  .commit();
