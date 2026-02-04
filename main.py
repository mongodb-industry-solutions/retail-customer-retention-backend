from threading import Thread
from mcp_server.server import mcp
from change_stream import watch_customer_behavior

if __name__ == "__main__":
    Thread(target=watch_customer_behavior, daemon=True).start()
    mcp.run()
