from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="leafy-next-best-action-mcp",
    instructions="""
    You help generate Next Best Actions for shoppers.
    You can query session state, recommend products,
    and persist NBA actions.
    """
)

# Add health endpoint for Kanopy liveness checks
@mcp.get("/")
def health_check():
    """Health check endpoint for Kanopy container liveness"""
    return {"status": "healthy", "service": "retail-customer-retention-backend"}

# Register tools
import mcp_server.tools.session_tools
import mcp_server.tools.product_search_tools  # Single consolidated file
import mcp_server.tools.nba_tools
import mcp_server.tools.discount_tools
