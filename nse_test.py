
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

NSE_URL = "https://mcp.nseindia.in/cmmkt/mcp"

async def main():
    print("Connecting to NSE CM Market...")

    async with streamable_http_client(
        NSE_URL,
        terminate_on_close=False
    ) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            tools = await session.list_tools()

            print("NSE connection successful")
            print("Available tools:", len(tools.tools))

            result = await session.call_tool(
                "cm_get_stock_quote",
                {"symbol": "RELIANCE"}
            )

            if result.is_error:
                raise Exception(result.content[0].text)

            data = json.loads(result.content[0].text)

            if "error" in data:
                raise Exception(data["error"])

            stock = data["stock"]

            print("\nNSE LIVE QUOTE")
            print("----------------------")
            print("Symbol:", stock.get("symbol"))
            print("CMP:", stock.get("lastTradedPrice"))
            print("Change:", stock.get("change"))
            print("Change %:", stock.get("perChange"))
            print("Open:", stock.get("open"))
            print("High:", stock.get("high"))
            print("Low:", stock.get("low"))
            print("Volume:", stock.get("volume"))
            print("Updated:", stock.get("latestTimestamp"))

if __name__ == "__main__":
    asyncio.run(main())
