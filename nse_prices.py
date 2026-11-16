
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

NSE_URL = "https://mcp.nseindia.in/cmmkt/mcp"

SYMBOL_MAP = {
    "Bajaj Finance": "BAJFINANCE",
    "Tata Motors": "TMPV",
    "ICICI Bank": "ICICIBANK",
    "NMDC": "NMDC",
    "Page Industries": "PAGEIND",
    "Hindustan Aeronautics": "HAL",
    "Tata Steel": "TATASTEEL",
    "Siemens": "SIEMENS",
    "DLF": "DLF",
    "Vodafone Idea": "IDEA",
    "Tata Power": "TATAPOWER",
    "Divi's Laboratories": "DIVISLAB",
    "Balkrishna": "BALKRISIND",
    "Voltas": "VOLTAS",
    "CDSL": "CDSL",
    "Prestige Estates": "PRESTIGE",
    "Sun TV": "SUNTV",
    "Hindalco": "HINDALCO",
    "Bank of Baroda": "BANKBARODA",
    "Mahindra & Mahindra": "M&M",
    "Bosch": "BOSCHLTD",
    "Fortis Healthcare": "FORTIS",
    "Mphasis": "MPHASIS"
}

async def main():
    source = json.loads(
        Path("picks.json").read_text(encoding="utf-8")
    )

    names = sorted({
        str(name).strip()
        for item in source.get("items", [])
        for name in item.get("stocks", [])
        if name
    })

    prices = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "NSE CM Market MCP",
        "delay_note": "NSE data may be delayed. Informational use only.",
        "stocks": {}
    }

    async with streamable_http_client(
        NSE_URL,
        terminate_on_close=False
    ) as (read, write):

        async with ClientSession(read, write) as session:
            await session.initialize()

            for name in names:
                symbol = SYMBOL_MAP.get(name, name.upper())

                try:
                    result = await session.call_tool(
                        "cm_get_stock_quote",
                        {"symbol": symbol}
                    )

                    if result.is_error:
                        raise RuntimeError("NSE request failed")

                    content = next(
                        (p.text for p in result.content
                         if hasattr(p, "text")),
                        ""
                    )

                    data = json.loads(content)
                    stock = data.get("stock", {})

                    cmp = stock.get("lastTradedPrice")

                    if cmp is None:
                        raise ValueError("CMP unavailable")

                    prices["stocks"][symbol] = {
                        "name": name,
                        "cmp": cmp,
                        "change": stock.get("change"),
                        "change_percent": stock.get("perChange"),
                        "open": stock.get("open"),
                        "high": stock.get("high"),
                        "low": stock.get("low"),
                        "volume": stock.get("volume"),
                        "timestamp": stock.get("latestTimestamp"),
                        "status": "success"
                    }

                    print("SUCCESS:", name, symbol, cmp)

                except Exception as error:
                    prices["stocks"][symbol] = {
                        "name": name,
                        "status": "unavailable",
                        "error": str(error)
                    }
                    print("FAILED:", name, symbol, error)

                await asyncio.sleep(1)

    Path("nse_prices.json").write_text(
        json.dumps(prices, indent=2),
        encoding="utf-8"
    )

    success = sum(
        1 for item in prices["stocks"].values()
        if item["status"] == "success"
    )

    print("Saved nse_prices.json")
    print("Total stocks:", len(names))
    print("Successful quotes:", success)

if __name__ == "__main__":
    asyncio.run(main())
