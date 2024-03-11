# switchExample1: Simple Alpaca switch device

import uasyncio
import wlancred   # contains WLAN SSID and password
from src.alpacaserver import AlpacaServer
from src.starget import Starget

# Asyncio coroutine
async def main():
    await AlpacaServer.startServer()


# Create Alpaca Server
srv = AlpacaServer("Starget Server", "Sylvain BROCAS", "1", "Unknown")

# Install switch device
srv.installDevice("telescope", 0, Starget(0, "Starget", "2fba39e5-e84b-4d68-8aa5-fae287abc02d", "scope_config.json"))

# Connect to WLAN
#AlpacaServer.startAccessPoint(wlancred.ssid, wlancred.password)
AlpacaServer.connectStationMode(wlancred.ssid, wlancred.password)
# run main function via asyncio
uasyncio.run(main())
