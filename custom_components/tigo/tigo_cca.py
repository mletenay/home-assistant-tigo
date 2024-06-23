"""Package for reading data from Tigo CCA."""

from dataclasses import dataclass
from html.parser import HTMLParser

import aiohttp
from aiohttp import ServerDisconnectedError


@dataclass
class PanelStatus:
    """PV Panel / Tigo optimizer status."""

    mac: str = None
    label: str = None
    voltage_in: float = None
    voltage_out: float = None
    current: float = None
    power: float = None
    power_perc: float = None
    temperature: float = None
    rssi: int = None
    bypass: bool = None

    def __str__(self):
        """Return string representation of panel status."""
        return f"Panel {self.label}: Pwr={self.power}, Tmp={self.temperature}"


class TigoCcaStatus:
    """Tigo CCA status."""

    def __init__(self) -> None:
        """Initialize the Tigo CCA status."""
        self.unit_id: str | None = None
        self.panels: dict[str, PanelStatus] = {}

    def get_panels(self) -> dict[str, PanelStatus]:
        """Return dict of panel stats."""
        return self.panels

    def __str__(self):
        """Return string representation of CCA status."""
        result = f"Tigo CCA #{self.unit_id}"
        for each in self.panels.values():
            result += "\n"
            result += str(each)
        return result


class _PanelsStatusPageParser(HTMLParser):
    def __init__(self, cca: TigoCcaStatus) -> None:
        """Initialize the panel status page parser."""
        super().__init__()
        self._cca = cca
        self._in_table = False
        self._in_row = False
        self._td_nr = 0
        self._td_done = False
        self._status = None

    def handle_starttag(self, tag, attrs):
        if tag == "table" and dict(attrs).get("class") == "list_tb":
            self._in_table = True
            self._cca.panels.clear()
        elif (
            tag == "tr"
            and dict(attrs).get("class") != "tb_red_title"
            and self._in_table
        ):
            self._in_row = True
            self._status = PanelStatus()
        elif tag == "td" and self._in_row:
            self._td_nr += 1
            self._td_done = False

    def handle_data(self, data):
        if self._td_nr > 0 and self._status and data != "n/a" and not self._td_done:
            self._td_done = True
            match self._td_nr:
                case 1:
                    self._status.label = data
                case 3:
                    self._status.mac = data
                case 4:
                    self._status.voltage_in = float(data)
                case 6:
                    self._status.voltage_out = float(data)
                case 8:
                    self._status.current = float(data)
                case 9:
                    self._status.power = float(data)
                case 10:
                    self._status.power_perc = float(data.replace("%", ""))
                case 11:
                    self._status.temperature = float(data)
                case 12:
                    self._status.rssi = int(data)
                case 19:
                    self._status.bypass = data != "off"
                case _:
                    pass
        elif "Unit id" in data:
            self._cca.unit_id = data.split(" ")[2]

    def handle_endtag(self, tag):
        if tag == "table" and self._in_table:
            self._in_table = False
        elif tag == "tr" and self._in_row:
            self._in_row = False
            self._td_nr = 0
            self._cca.panels[self._status.label] = self._status

    def error(self, message):
        pass


class TigoCCA:
    """Tigo CCA."""

    def __init__(self, ip_address, username, password) -> None:
        """Initialize the Tigo CCA object."""
        self.url_root = "http://" + ip_address
        self.auth = aiohttp.BasicAuth(username, password) if username else None
        self.unit_id: str | None = None
        self.hw_platform: str | None = None
        self.fw_version: str | None = None

    async def _get(self, url):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.url_root + url, auth=self.auth) as response:
                    return await response.text()
            except ServerDisconnectedError as ex:
                if ex.message.code != 303:
                    raise

    async def get_status(self) -> TigoCcaStatus:
        """Get the latest data from the source and updates the state."""
        status = TigoCcaStatus()
        parser = _PanelsStatusPageParser(status)
        parser.feed(await self._get("/cgi-bin/mmdstatus"))
        parser.close()
        return status
