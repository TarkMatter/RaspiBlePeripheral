from machine import SPI, Pin
import time

from lib.abstract_flash  import AbstractFlash

class W25Q(AbstractFlash):
    CMD_READ_ID = 0x90
    CMD_READ_DATA = 0x03
    CMD_PAGE_PROGRAM = 0x02
    CMD_SECTOR_ERASE = 0x20
    CMD_WRITE_ENABLE = 0x06
    CMD_READ_STATUS = 0x05

    PAGE_SIZE = 256
    SECTOR_SIZE = 4096
    TOTAL_SIZE = 16 * 1024 * 1024  # 16MB

    def __init__(self, spi: SPI, cs: Pin):
        self.spi = spi
        self.cs = cs
        self.cs.init(Pin.OUT, value=1)

        self._check_id()

    def _check_id(self):
        self.cs.value(0)
        self.spi.write(bytearray([self.CMD_READ_ID, 0x00, 0x00, 0x00]))
        id_bytes = self.spi.read(2)
        self.cs.value(1)
        manufacturer_id, device_id = id_bytes
        print(f"[W25Q] ID: {manufacturer_id:02X} {device_id:02X}")
        if manufacturer_id != 0xEF:
            raise RuntimeError("Unknown manufacturer ID (not Winbond)")

    def _write_enable(self):
        self.cs.value(0)
        self.spi.write(bytearray([self.CMD_WRITE_ENABLE]))
        self.cs.value(1)

    def _wait_busy(self):
        while True:
            self.cs.value(0)
            self.spi.write(bytearray([self.CMD_READ_STATUS]))
            status = self.spi.read(1)[0]
            self.cs.value(1)
            if not (status & 0x01):
                break
            time.sleep_ms(1)

    def read(self, addr: int, length: int) -> bytes:
        self.cs.value(0)
        cmd = bytearray([self.CMD_READ_DATA,
                        (addr >> 16) & 0xFF,
                        (addr >> 8) & 0xFF,
                        addr & 0xFF])
        self.spi.write(cmd)
        data = self.spi.read(length)
        self.cs.value(1)
        return data

    def write(self, addr: int, data: bytes):
        assert len(data) <= self.PAGE_SIZE
        self._write_enable()
        self.cs.value(0)
        cmd = bytearray([self.CMD_PAGE_PROGRAM,
                        (addr >> 16) & 0xFF,
                        (addr >> 8) & 0xFF,
                        addr & 0xFF])
        self.spi.write(cmd)
        self.spi.write(data)
        self.cs.value(1)
        self._wait_busy()

    def erase_sector(self, addr: int):
        self._write_enable()
        self.cs.value(0)
        cmd = bytearray([self.CMD_SECTOR_ERASE,
                        (addr >> 16) & 0xFF,
                        (addr >> 8) & 0xFF,
                        addr & 0xFF])
        self.spi.write(cmd)
        self.cs.value(1)
        self._wait_busy()

    def capacity(self) -> int:
        return self.TOTAL_SIZE