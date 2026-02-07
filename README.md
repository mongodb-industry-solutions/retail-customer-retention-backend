> ⚠️ **WORK IN PROGRESS** - This repository is currently under active development and not yet ready for production use. 

# Retail Customer Retention Backend

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    MongoDB Change Stream                        │
│  - Watches session_signals collection                           │
│  - Detects high-intent, search-friction, exit-risk signals      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          │ Real-time Events
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Retail Agent (LLM Powered)                      │
│  - Processes behavior signals                                   │
│  - Generates personalized NBAs                                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          │ MCP Protocol
                          │
                          ▼
┌───────────────────────────────────────────────────────────────┐
│                      MCP Server                               │
│                                                               │
├─────────────┬─────────────┬─────────────┬─────────────────────┤
│ Product     │ Session     │ NBA Tools   │ Discount Tools      │
│ Search      │ Management  │             │                     │
│ Tools       │ Tools       │             │                     │
│             │             │             │                     │
│• Vector     │• Session    │• Create     │• Dynamic Discount   │
│  Search     │  Intent     │  Next Best  │  Messages           │
│• Text       │  Tracking   │  Actions    │• Severity Based     │
│  Search     │             │• Persist    │  Logic              │
│• Category   │             │  Actions    │                     │
│  Filter     │             │             │                     │
└─────────────┴─────────────┴─────────────┴─────────────────────┘
              │           │           │             │
              │           │           │             │
              │       External Service Calls.       │
              │           │           │             │
              │           │           │             │
              ▼           ▼           ▼             ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ VoyageAI    │ │ MongoDB     │ │ MongoDB     │ │ LLM         │
    │ Embeddings  │ │ Session     │ │ Next Best   │ │ Generated   │
    │             │ │ State       │ │ Actions     │ │ Content     │
    │• Embedding  │ │ Collection  │ │ Collection  │ │             │
    │  Models     │ │             │ │             │ │• UX Writing │
    │• voyage-    │ │• User       │ │• Discount   │ │• Bedrock    │
    │  3-large    │ │  Intent     │ │  Offers     │ │             │
    │             │ │• Session    │ │• Product    │ │             │
    │             │ │  Tracking   │ │  Recomm.    │ │             │
    │             │ │             │ │             │ │             │
    │             │ │             │ │             │ │             │
    └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
                                          │
                                          │
                                          ▼
                              ┌─────────────────────┐
                              │  Customer Frontend  │
                              │  Real-time Actions  │
                              │                     │
                              │• Social Proof       │
                              │  Notifications      │
                              │• Product            │
                              │  Recommendations    │
                              │• Discount Offers    │
                              └─────────────────────┘
```

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
│       ├── discount_tools.py   # Discount message generation tools
│       ├── nba_tools.py        # Next Best Action tools
│       ├── product_search_tools.py # Product search tools (vector & text search)
│       └── session_tools.py    # Session management tools
├── mongo.py                     # MongoDB integration
├── requirements.txt             # Python dependencies
└── voyageai_client.py          # VoyageAI embedding integration
```

## Local Development Setup

### Prerequisites

- Python 3.12+ installed
- MongoDB instance running (local or cloud)
- AWS credentials configured for Bedrock access
- VoyageAI API key

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd retail-customer-retention-backend
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the root directory:
   ```env
        MONGODB_URI=
        AWS_REGION=
        AWS_ACCESS_KEY_ID=
        AWS_SECRET_ACCESS_KEY=
        VOYAGE_API_KEY=
   ```

### Running the Application

1. **Start the application** (this starts both MCP server and change stream monitor)
   ```bash
   python main.py
   ```

## Authors & Contributors

### Lead Authors   

[Rodrigo Leal](https://www.mongodb.com/blog/authors/rodrigo-leal) - Principal

[Genevieve Broadhead](https://www.mongodb.com/blog/authors/genevieve-broadhead) - Global lead, retail solutions

[Angie Guemes](https://www.mongodb.com/developer/author/angie-guemes-estrada/) – Developer & Maintainer 

[Florencia Arin](https://www.mongodb.com/blog/authors/florencia-arin) – Developer & Maintainer 

### Contributors  


## License

© 2025 MongoDB. All rights reserved.

This repository is intended solely for demonstration and educational purposes.  
No support or warranty is provided. Use at your own risk.
.
