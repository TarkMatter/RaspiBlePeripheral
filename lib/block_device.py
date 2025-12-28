from lib.abstract_flash import AbstractFlash

class BlockDevice:
    def __init__(self, flash: AbstractFlash, block_size=4096):
        self._flash = flash
        self.block_size = block_size
        self.total_size = self._flash.capacity()  # 必要に応じて属性化

    def readblocks(self, block_num, buf, offset=0):
        addr = block_num * self.block_size + offset
        # SPI Flashの read(addr, size) -> bytes を buf[:] に書き込む
        data = self._flash.read(addr, len(buf))
        for i in range(len(buf)):
            buf[i] = data[i]

    def writeblocks(self, block_num, buf, offset=None):
        if offset is None:
            # 書き込み前にブロック単位で消去
            for i in range((len(buf) + self.block_size - 1) // self.block_size):
                self.ioctl(6, block_num + i)
            offset = 0

        addr = block_num * self.block_size + offset
        self._flash.write(addr, buf)

    def ioctl(self, op, arg):
        if op == 1:
            # 初期化（必要ならフラッシュ初期化）
            print("IOCTL 1: init")
            return 0
        elif op == 2:
            # シャットダウン（特に処理なし）
            print("IOCTL 2: shutdown")
            return 0
        elif op == 3:
            # 同期（特に処理なし）
            print("IOCTL 3: sync")
            return 0
        elif op == 4:
            # ブロック数を返す
            return self.total_size // self.block_size
        elif op == 5:
            # ブロックサイズを返す
            return self.block_size
        elif op == 6:
            # 指定ブロックを消去
            erase_addr = arg * self.block_size
            self._flash.erase_sector(erase_addr)
            return 0
        else:
            raise ValueError("Unsupported ioctl operation:", op)