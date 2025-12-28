class AbstractFlash:
    def read(self, addr: int, length: int) -> bytes:
        raise NotImplementedError("read method must be implemented")
    
    def write(self, addr: int, data: bytes):
        raise NotImplementedError("write method must be implemented")
    
    def erase_sector(self, addr: int):
        raise NotImplementedError("erase_sector method must be implemented")
    
    def capacity(self) -> int:
        raise NotImplementedError("capacity method must be implemented")