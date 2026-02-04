# Retail Customer Retention Backend

## Project Structure

```
retail-customer-retention-backend/
├── .env                          # Environment variables
├── .git/                         # Git repository metadata
├── .github/                      # GitHub configuration
│   ├── CODEOWNERS               # Code ownership rules
│   └── dependabot.yml           # Dependabot configuration
├── .gitignore                   # Git ignore patterns
├── .venv/                       # Python virtual environment
├── Dockerfile                   # Docker container configuration
├── LICENSE                      # Project license
├── README.md                    # Project documentation
├── __pycache__/                # Python bytecode cache
├── agent.py                     # Agent implementation
├── bedrock.py                   # AWS Bedrock integration
├── change_stream.py             # Database change stream handler
├── config.py                    # Configuration management
├── main.py                      # Application entry point
├── mcp_server/                  # Model Context Protocol server
│   ├── __pycache__/            # Python bytecode cache
│   ├── server.py               # MCP server implementation
│   └── tools/                  # MCP tools directory
│       ├── __init__.py         # Python package initializer
│       ├── __pycache__/        # Python bytecode cache
│       ├── nba_tools.py        # NBA-related tools
│       ├── product_tools.py    # Product management tools
│       └── session_tools.py    # Session management tools
├── mongo.py                     # MongoDB integration
└── requirements.txt             # Python dependencies
```
