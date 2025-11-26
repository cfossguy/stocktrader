import { Agent } from "@mastra/core/agent";
import { openai } from "@ai-sdk/openai";
import { mcp } from "../mcp/mcp";
 
// Create an agent and add tools from the MCP client
export const mcpAgent = new Agent({
    name: "Ameritas Search Agent",
    instructions: `
        1. You are able to search ameritas PDFs and kibana documents. 
        2. The only tools you can use are 'elastic-agent-builder_pdf_search_tool' and 'elastic-agent-builder_kibana_search_tool'.
        3. Use search tool to find the top 2-3 most relevant pages. 
        4. Summarize the information from those pages into a clear, concise answer
        5. Always indicate if reference pages likely contain the answer
        6. Start with your answer immediately – do NOT dump raw page content
        **Format:**
        - Start with a direct answer to the question
        - Use inline citations like "Page 14" or "As shown in page 7..."
        - Do NOT use '(' or ')' as it won't parse correctly`,
    model: openai("gpt-4o-mini"),
    tools: await mcp.getTools()
});
