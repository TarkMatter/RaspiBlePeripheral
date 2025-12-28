import os,time
#--------------------------------------------------
#テキストの保存
def OutputText(path:str,txt:bytearray):
    fp = open(path,'ab')
    try:
        fp.write(txt)
        fp.flush()
        os.sync()
        # DisplayText("Write","correct!")
        print("Write correct!")
        return True
    except Exception as e:
        # DisplayText("Write","Failed!")
        print("Write Failed!")
        return False
    finally:
        fp.close()
        # time.sleep(1.5)
        
#--------------------------------------------------
#テキストの取得
def ReadText(path:str):
    try:
        fp = open(path,'r')
    except OSError as e:
        if e.errno == 2:
            print("FileNotFoundError!")
            raise OSError(2, "FileNotFoundError: 指定されたファイルが見つかりません")
        else:
            print(f"message:{e}")
            raise OSError(e)

    try :
        retText = fp.read()
        # DisplayText("Read","correct!")
        print("Read correct!")
        return retText
    except:
        # DisplayText("Read","Failed!")
        print("Read Failed!")
    finally:
        fp.close()
        time.sleep(1.5)