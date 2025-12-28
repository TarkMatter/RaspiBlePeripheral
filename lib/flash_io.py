import vfs
from vfs import VfsLfs2

from lib.block_device import BlockDevice

class FlashIO:
    DIRECTORY_TYPE = 16384
    FILE_TYPE = 32768
    # ------------------------------
    def __init__(self,bd:BlockDevice):
        self._block_device = bd
        self._exfs:VfsLfs2

    # ------------------------------
    # ファイルシステム構築
    def make_file_system(self):
        """
        フラッシュメモリのファイルシステム構築
        """
        vfs.VfsLfs2.mkfs(self._block_device) # ファイルシステム構築

    # ------------------------------
    # マウント
    def mount(self,path:str):
        """
        フラッシュメモリのマウント
        """
        self._exfs = vfs.VfsLfs2(self._block_device) # DeviceをVfsLfs2に登録
        vfs.mount(self._exfs,path)
        print(f"[VfsLfs2] : mount {path}")

    # ------------------------------
    # アンマウント
    def unmount(self):
        """
        フラッシュメモリのアンマウント
        """
        self._exfs.umount()
        print(f"[VfsLfs2] : unmount ...")

    # ------------------------------
    # ディレクトリ作成
    def mkdir(self,path:str):
        """
        ディレクトリの作成

        Args:
            path(str):ディレクトリのパス
        """
        self._exfs.mkdir(path)
        print(f"[VfsLfs2] : make directory / {path}")

    # ------------------------------
    # ディレクトリ削除
    def rmdir(self,path:str):
        """
        ディレクトリの削除

        Args:
            path(str):ディレクトリのパス
        """
        if len(self._exfs.ilistdir(path)) != 0:
            print("Directory is not Enpty !")
            raise OSError(39)
        else:
            self._exfs.rmdir(path)
            print(f"[VfsLfs2] : Remove directory / {path}")

    # ------------------------------
    # バイナリファイル作成
    def create_byte_file(self,path:str):
        """
        バイナリファイルへ作成

        Args:
            path(str):データファイルのパス
        """
        try:
            self._exfs.stat(path)
            print("[VfsLfs2]: File already exist")
            return
        except OSError as e:
            with self._exfs.open(path,"wb") as f:
                print(f"[VfsLfs2] : Create file / {path}")

    # ------------------------------
    # バイナリファイルへ追記
    def append_to_byte_file(self,path:str,array:bytearray) -> bool:
        """
        バイナリファイルへ追記
        既存のバイナリファイルへデータの追記
        ファイルがない場合、新規作成を兼ねることもできる

        Args:
            path(str):データファイルのパス
            array(bytearray):バイナリデータリスト
        
        Returns:
            bool:成功したか
        """
        try:
            with self._exfs.open(path,"ab") as f:
                f.write(array)
                print(f"[VfsLfs2] : Append to {path}")
                print(f"[VfsLfs2] : Append data / {array}")
            return True
        except OSError as e:
            print(f"Error occured in append_to_byte_file method : {e}")
            return False

    # ------------------------------
    # ファイルの削除
    def remove_file(self,path:str):
        """
        ファイルの削除

        Args:
            path(str):データファイルのパス
        """
        self._exfs.remove(path)
        print(f"[VfsLfs2] : Removed {path}")

    # ------------------------------
    # ファイルの読み取り取得
    def get_read_data(self,path:str) -> list | None:
        """
        データのリスト取得

        Args:
            path(str):データファイルのパス
        """
        try:
            data_array = []

            status = self._exfs.stat(path)
            mode,_,_,_,_,_,_,_,_,_ = status

            if mode != self.FILE_TYPE:
                print("[VfsLfs2] : Not file !")
                return None

            with self._exfs.open(path,"rb") as f:
                data = f.read()
                lines = [line for line in data.split(b'\n') if line]
                for line in lines:
                    data_array.append(line)
                return data_array
        except OSError as e:
            print("[VfsLfs2]: File not exist")

    # ------------------------------
    #　全容量・空き容量表示
    def show_capacity(self,path:str):
        stat = self._exfs.statvfs(str)

        block_size = stat[0]
        total_blocks = stat[2]
        free_blocks = stat[3]

        total_size = block_size * total_blocks
        free_size = block_size * free_blocks

        print(f"Full capacity: {total_size // 1024} KB")
        print(f"Free capacity: {free_size // 1024} KB")

    def show_item_list(self,path:str):
        for entry in self._exfs.ilistdir(path):
            nameStr,typeInt,_,sizeInt = entry
            if(typeInt == self.FILE_TYPE):
                print(f"File name : {nameStr} - file size : {sizeInt}")
            else:
                print(f"Directory name : {nameStr}")

    # ------------------------------
    #　全容量・空き容量表示
    def get_file_list(self,path:str) -> list:
        list = []
        for entry in self._exfs.ilistdir(path):
            nameStr,typeInt,_,sizeInt = entry
            if(typeInt == self.FILE_TYPE):
                list.append(entry)
                # print(f"File name : {nameStr} - file size : {sizeInt}")
        return list