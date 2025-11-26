import { MCPClient } from "@mastra/mcp";
 
// Configure MCPClient to connect to your server(s)
export const mcp = new MCPClient({
  servers: {
    "elastic-agent-builder": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://agentbuilder-4257b4.kb.us-west2.gcp.elastic-cloud.com/api/agent_builder/mcp",
        "--header",
        "Authorization:${AUTH_HEADER}"
      ],
      "env": {
        "KIBANA_URL": "${KIBANA_URL}",
        "AUTH_HEADER": "ApiKey U1YxOHc1a0J2QS1tOWwtZnd1dmU6YUdJUGlndFRJN2o0UTFXdmVtS09RZw=="
      }
    }
  },
});
