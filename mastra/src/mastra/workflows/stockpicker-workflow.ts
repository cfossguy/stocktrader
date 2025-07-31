import { createWorkflow, createStep } from "@mastra/core/workflows";
import { z } from "zod";
import { pythonTool } from "../tools/python-tool";  


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
    const result = await pythonTool.execute({
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

    const result = await pythonTool.execute({
      context: { scriptCommand: "run-crewai" },
      runtimeContext: params.runtimeContext
    });

    return {
      success: result.success,
      message: result.message,
      executionTime: result.details?.executionTime
    };
  }
});

// Step 3: Completion step
const completionStep = createStep({
  id: "completion-step",
  description: "Finalizes the workflow process and handles any cleanup or notifications",
  inputSchema: z.object({
    success: z.boolean(),
    message: z.string(),
    executionTime: z.string().optional()
  }),
  outputSchema: z.object({
    completed: z.boolean(),
    completionMessage: z.string(),
    completionTime: z.string()
  }),
  execute: async (params) => {
    const startTime = Date.now();
    
    // Determine overall success based on CrewAI step
    const overallSuccess = params.inputData.success;
    
    // Create completion message
    let completionMessage = `Workflow execution ${overallSuccess ? 'completed successfully' : 'completed with issues'}. `;
    
    if (overallSuccess) {
      completionMessage += "All reports have been generated and are ready for review.";
      
      // Here you could add additional logic like:
      // - Send notifications
      // - Archive reports
      // - Log completion status
      // - etc.
    } else {
      completionMessage += "There were issues during execution. Please check the logs for details.";
    }
    
    // Calculate execution time
    const completionTime = ((Date.now() - startTime) / 1000 / 60).toFixed(2);
    
    return {
      completed: true,
      completionMessage,
      completionTime: `${completionTime} minutes`
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
  "completion-step": {
    completed: boolean;
    completionMessage: string;
    completionTime: string;
  };
};

// Define the workflow
export const stockpickerWorkflow = createWorkflow({
  id: "stockpicker-workflow",
  description: "Workflow to run data pipeline and then CrewAI analysis with completion step",
  inputSchema: z.object({}),
  outputSchema: z.object({
    dataPipelineSuccess: z.boolean(),
    crewAISuccess: z.boolean(),
    workflowCompleted: z.boolean(),
    finalMessage: z.string(),
    completionMessage: z.string(),
    totalExecutionTime: z.string().optional()
  })
})
  .then(runDataPipelineStep)
  .then(runCrewAIStep)
  .then(completionStep)
  .map({
    dataPipelineSuccess: {
      value: (outputs: StepOutputs) => outputs["run-data-pipeline-step"].pipelineSuccess,
      schema: z.boolean()
    },
    crewAISuccess: {
      value: (outputs: StepOutputs) => outputs["run-crewai-step"].success,
      schema: z.boolean()
    },
    workflowCompleted: {
      value: (outputs: StepOutputs) => outputs["completion-step"].completed,
      schema: z.boolean()
    },
    finalMessage: {
      value: (outputs: StepOutputs) => {
        return `Data Pipeline: ${outputs["run-data-pipeline-step"].message}. CrewAI: ${outputs["run-crewai-step"].message}`;
      },
      schema: z.string()
    },
    completionMessage: {
      value: (outputs: StepOutputs) => outputs["completion-step"].completionMessage,
      schema: z.string()
    },
    totalExecutionTime: {
      value: (outputs: StepOutputs) => {
        const pipelineOutput = outputs["run-data-pipeline-step"];
        const crewAIOutput = outputs["run-crewai-step"];
        const completionOutput = outputs["completion-step"];
        
        if (pipelineOutput.executionTime && crewAIOutput.executionTime) {
          // Extract minutes from strings like "2.50 minutes"
          const pipelineTimeStr = pipelineOutput.executionTime || "0 minutes";
          const crewAITimeStr = crewAIOutput.executionTime || "0 minutes";
          const completionTimeStr = completionOutput.completionTime || "0 minutes";
          
          const pipelineTime = parseFloat(pipelineTimeStr.split(" ")[0]) || 0;
          const crewAITime = parseFloat(crewAITimeStr.split(" ")[0]) || 0;
          const completionTime = parseFloat(completionTimeStr.split(" ")[0]) || 0;
          
          return `${(pipelineTime + crewAITime + completionTime).toFixed(2)} minutes`;
        }
        
        return "unknown";
      },
      schema: z.string()
    }
  })
  .commit();
