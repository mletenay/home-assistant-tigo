"""Simple test script to check Tigo CCA communication."""

import asyncio
import logging
import sys

from custom_components.tigo.tigo_cca import TigoCCA

logging.basicConfig(
    format="%(asctime)-15s %(funcName)s(%(lineno)d) - %(levelname)s: %(message)s",
    stream=sys.stderr,
    level=getattr(logging, "DEBUG", None),
)


async def _test_command():
    tigo = TigoCCA("192.168.1.125", "Tigo", "$olar")
    status = await asyncio.wait_for(tigo.read_config(), 1)
    print(tigo.panels)
    status = await asyncio.wait_for(tigo.get_status(), 1)
    print(status)


asyncio.run(_test_command())
