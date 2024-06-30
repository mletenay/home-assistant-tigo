"""Package for reading data from Tigo CCA."""

from dataclasses import dataclass
from html.parser import HTMLParser

import aiohttp
from aiohttp import ServerDisconnectedError


@dataclass
class PanelVersionInfo:
    """PV Panel / Tigo optimizer version info."""

    label: str = None
    mac: str = None
    fw: str = None
    hw: str = None

    def model(self) -> str:
        """Return panel unit model."""
        if "455" in self.hw:
            return "TS4-A-M"
        if "461" in self.hw or "462" in self.hw:
            return "TS4-A-O"
        if "466" in self.hw:
            return "TS4-A-S"
        if "481" in self.hw or "486" in self.hw or "488" in self.hw:
            return "TS4-A-F"
        if "484" in self.hw or "485" in self.hw or "487" in self.hw:
            return "TS4-A-2F"
        return "?"

    def __str__(self):
        """Return string representation of panel info."""
        result = f"Panel {self.label}\n"
        result += f"MAC: {self.mac}\n"
        result += f"FW: {self.fw}\n"
        result += f"HW: {self.hw}\n"
        return result


@dataclass
class PanelStatus:
    """PV Panel / Tigo optimizer status."""

    mac: str = None
    label: str = None
    voltage_in: float = None
    voltage_out: float = None
    current: float = None
    power: float = None
    pwm: int = None
    temperature: float = None
    status: int = None
    rssi: int = None

    def status_name(self) -> str:
        """Return string representation of status.

        The status int value is bitmap:
        bit 7: ?
        bit 6: panel on/off
        bit 5: ?
        bit 4: ?
        bit 3: ?
        bit 2: ?
        bit 1: ?
        bit 0: ?
        """
        return "?"

    def __str__(self):
        """Return string representation of panel status."""
        return f"Panel {self.label}: Pwr={self.power}, Tmp={self.temperature}"


class TigoCcaStatus:
    """Tigo CCA status."""

    def __init__(self) -> None:
        """Initialize the Tigo CCA status."""
        self.unit_id: str | None = None
        self.hw_platform: str | None = None
        self.fw_version: str | None = None
        self.temperature: float | None = None
        self.panels: dict[str, PanelStatus] = {}

    def get_panels(self) -> dict[str, PanelStatus]:
        """Return dict of panel stats."""
        return self.panels

    def __str__(self):
        """Return string representation of CCA status."""
        result = f"Tigo CCA #{self.unit_id}\n"
        result += f"FW: {self.fw_version}\n"
        result += f"HW: {self.hw_platform}\n"
        result += f"Temp: {self.temperature}\n"
        for each in self.panels.values():
            result += "\n"
            result += str(each)
        return result


class _CcaStatusPageParser(HTMLParser):
    def __init__(self, cca: TigoCcaStatus) -> None:
        """Initialize the CCA status page parser."""
        super().__init__()
        self._cca = cca
        self._in_td = False
        self._was_temp_td = False
        self._was_fw_version = False
        self._was_hw_platform = False

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self._in_td = True

    def handle_data(self, data):
        if self._in_td and data == "CC Temperature":
            self._was_temp_td = True
        elif self._in_td and self._was_temp_td:
            # previous <td> has "CC Temperature" value, so this is the actual temperature
            self._cca.temperature = float(data.replace(" C", ""))
            self._was_temp_td = False
        elif "Unit id" in data:
            # this is footer <td> with Unit Id:
            self._cca.unit_id = data.split(" ")[2]
        elif "Firmware Version" in data:
            self._was_fw_version = True
        elif data and self._was_fw_version and data.strip() != "0.0":
            self._cca.fw_version = data.strip()
            self._was_fw_version = False
        elif "Hardware Platform" in data:
            self._was_hw_platform = True
        elif data and self._was_hw_platform:
            self._cca.hw_platform = data.strip()
            self._was_hw_platform = False

    def handle_endtag(self, tag):
        self._in_td = False


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        """Initialize the table parser."""
        super().__init__()
        self._in_table: bool = False
        self._in_row: bool = False
        self._td_nr: int = 0
        self._td_done: bool = False

    def handle_starttag(self, tag, attrs):
        if tag == "table" and dict(attrs).get("class") == "list_tb":
            self._in_table = True
        elif tag == "tr" and self._in_table:
            self._in_row = True
        elif tag == "td" and self._in_row:
            self._td_nr += 1
            self._td_done = False

    def handle_data(self, data):
        if self._td_nr > 0 and data != "n/a" and not self._td_done:
            self._td_done = True
            self._on_td(self._td_nr, data)

    def handle_endtag(self, tag):
        if tag == "table" and self._in_table:
            self._in_table = False
        elif tag == "tr" and self._in_row and self._td_nr > 0:
            self._on_tr_end()
            self._in_row = False
            self._td_nr = 0

    def _on_td(self, nr: int, data: str) -> None:
        pass

    def _on_tr_end(self) -> None:
        pass


class _PanelsStatusPageParser(_TableParser):
    def __init__(self, cca: TigoCcaStatus) -> None:
        """Initialize the panel status page parser."""
        super().__init__()
        self._cca: TigoCcaStatus = cca
        self._status: PanelStatus = None
        self._age: str = None

    def _on_td(self, nr: int, data: str) -> None:
        match nr:
            case 1:
                self._status = PanelStatus()
            case 2:
                self._status.mac = data.strip()
            case 3:
                self._status.label = data.strip()
            case 4:
                self._age = data
            case 13:
                self._status.voltage_in = float(data)
            case 14:
                self._status.voltage_out = float(data)
            case 15:
                self._status.current = float(data)
            case 16:
                self._status.power = float(data)
            case 17:
                self._status.pwm = int(data)
            case 18:
                self._status.temperature = float(data)
            case 21:
                self._status.status = int(data, 16)
            case 22:
                self._status.rssi = int(data)
            case _:
                pass

    def _on_tr_end(self) -> None:
        if self._status and "hrs" not in self._age and "min" not in self._age:
            self._cca.panels[self._status.label] = self._status
        self._status = None


class _PanelsVersionPageParser(_TableParser):
    def __init__(self, infos: dict[str, PanelVersionInfo]) -> None:
        """Initialize the panels versions page parser."""
        super().__init__()
        self._infos: dict[str, PanelVersionInfo] = infos
        self._info: PanelVersionInfo = None

    def _on_td(self, nr: int, data: str) -> None:
        match self._td_nr:
            case 1:
                self._info = PanelVersionInfo()
            case 2:
                self._info.label = data
            case 7:
                self._info.fw = data
            case 9:
                self._info.hw = data
            case _:
                pass

    def _on_tr_end(self) -> None:
        if self._info:
            self._infos[self._info.label] = self._info


class _PanelsInfoPageParser(_TableParser):
    def __init__(self, infos: dict[str, PanelVersionInfo]) -> None:
        """Initialize the panels versions page parser."""
        super().__init__()
        self._infos: dict[str, PanelVersionInfo] = infos
        self._mac: str = None

    def _on_td(self, nr: int, data: str) -> None:
        match self._td_nr:
            case 2:
                self._mac = data
            case 3:
                self._infos[data.strip()].mac = self._mac
            case _:
                pass


class TigoCCA:
    """Tigo CCA."""

    def __init__(self, ip_address, username, password) -> None:
        """Initialize the Tigo CCA object."""
        self.url_root = "http://" + ip_address
        self.auth = aiohttp.BasicAuth(username, password) if username else None
        self.panels: dict[str, PanelVersionInfo] = {}

    async def _get(self, url):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.url_root + url, auth=self.auth) as response:
                    return await response.text()
            except ServerDisconnectedError as ex:
                if ex.message.code != 303:
                    raise

    async def read_config(self) -> None:
        """Read the CCA and panels configuration."""
        self.panels = {}
        parser = _PanelsVersionPageParser(self.panels)
        parser.feed(await self._get("/cgi-bin/meshnodever"))
        parser.close()
        parser = _PanelsInfoPageParser(self.panels)
        parser.feed(await self._get("/cgi-bin/meshnodeinfo"))
        parser.close()

    async def get_status(self) -> TigoCcaStatus:
        """Get the latest status of the CCA itself."""
        status = TigoCcaStatus()
        parser = _CcaStatusPageParser(status)
        parser.feed(await self._get("/cgi-bin/lmudui"))
        parser.close()
        parser = _PanelsStatusPageParser(status)
        parser.feed(await self._get("/cgi-bin/meshdatapower"))
        parser.close()
        return status

    async def turn_modules_off(self) -> None:
        """Turn all modules OFF."""
        await self._get("/cgi-bin/lmudui?State=3")

    async def turn_modules_on(self) -> None:
        """Turn all modules ON."""
        await self._get("/cgi-bin/lmudui?State=1")
