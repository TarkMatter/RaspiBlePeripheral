from machine import I2C

class Register:
    ADDR: int
    BITS: int

    def __init__(self,addr:int,bits:int):
        self.ADDR = addr
        self.BITS =bits

class RX8025NB_Register:
    class Control1:
        ADDR = 0xE0

        DISP1224 =Register(ADDR,0b00100000)
        Hz2 = Register(ADDR,0b00000010)
        Hz1 = Register(ADDR,0b00000011)
        PerSecond = Register(ADDR,0b00000100)
        PerMinute = Register(ADDR,0b00000101)
        PerHour = Register(ADDR,0b00000110)
        PerMonth = Register(ADDR,0b00000111)


class RX8025NB:
    def __init__(self, i2c: I2C, addr: int = 0x32):
        self.i2c = i2c
        self.addr = addr

    # 1バイトのレジスタを読み取る
    def read_register(self, reg_addr: int) -> int:
        return self.i2c.readfrom_mem(self.addr, reg_addr, 1)[0]

    # 1バイトのレジスタに書き込む
    def write_register(self, reg_addr: int, value: int):
        self.i2c.writeto_mem(self.addr, reg_addr, bytes([value]))

    # 指定したビットを立てる（1にする）
    def _set_bits(self, reg_addr: int, bit_mask: int):
        val = self.read_register(reg_addr)
        val |= bit_mask
        self.write_register(reg_addr, val)

    # 指定したビットを立てる（1にする）/ Register指定
    def set_bits(self,register:Register):
        self._set_bits(register.ADDR,register.BITS)

    # 指定したビットを下げる（0にする）
    def _clear_bits(self, reg_addr: int, bit_mask: int):
        val = self.read_register(reg_addr)
        val &= ~bit_mask
        self.write_register(reg_addr, val)

    # 指定したビットを下げる（0にする）/ Register指定
    def clear_bits(self,register:Register):
        self._clear_bits(register.ADDR,register.BITS)

    # 指定したビットをトグル（反転）する
    def toggle_bits(self, reg_addr: int, bit_mask: int):
        val = self.read_register(reg_addr)
        val ^= bit_mask
        self.write_register(reg_addr, val)
    
    # 指定レジスタからマスクされたビットを読み出す
    def read_bits(self, addr, reg, mask):
        value = self.i2c.readfrom_mem(addr, reg, 1)[0]
        return value & mask

    # BCDから10進数への変換
    def bcd2dec(self, b):
        return (b >> 4) * 10 + (b & 0x0F)

    # 10進数からBCDへの変換
    def dec2bcd(self, d):
        return ((d // 10) << 4) | (d % 10)

    # 時刻の取得
    def get_datetime(self):
        data = self.i2c.readfrom_mem(self.addr, 0x00, 7)
        sec = self.bcd2dec(data[0] & 0x7F)
        minute = self.bcd2dec(data[1])
        hour = self.bcd2dec(data[2])
        weekday = self.bcd2dec(data[3])
        day = self.bcd2dec(data[4])
        month = self.bcd2dec(data[5])
        year = self.bcd2dec(data[6]) + 2000
        return (year, month, day, weekday, hour, minute, sec, 0)

    # 時刻の設定
    def set_datetime(self, dt):
        year, month, day, weekday, hour, minute, sec, _ = dt
        data = bytearray(7)
        data[0] = self.dec2bcd(sec)
        data[1] = self.dec2bcd(minute)
        data[2] = self.dec2bcd(hour)
        data[3] = self.dec2bcd(weekday)
        data[4] = self.dec2bcd(day)
        data[5] = self.dec2bcd(month)
        data[6] = self.dec2bcd(year - 2000)
        self.i2c.writeto_mem(self.addr, 0x00, data)

    def enable_1hz_interrupt(self):
        self.set_bits(RX8025NB_Register.Control1.Hz1)

    def change_hour_dispaly(self,ampm:bool):
        if ampm:
            self.clear_bits(RX8025NB_Register.Control1.DISP1224)
        else:
            self.set_bits(RX8025NB_Register.Control1.DISP1224)