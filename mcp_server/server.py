from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="leafy-next-best-action-mcp",
    instructions="""
    You help generate Next Best Actions for shoppers.
    You can query session state, recommend products,
    and persist NBA actions.
    """
)

# Register tools
import mcp_server.tools.session_tools
import mcp_server.tools.product_tools
import mcp_server.tools.nba_tools
