from machine import Timer
from machine import I2C,Pin,ADC,SPI,RTC
import machine
import ubluetooth
import ubinascii
import struct
import time
import asyncio
import aioble
from micropython import const
import struct
import random

import os
from lib.displaySsd1306 import DisplaySsd1306
from lib.rx8025nb import RX8025NB
from lib.w25q import W25Q
from lib.flash_io import FlashIO
from lib.block_device import BlockDevice
from lib.simple_queue import SimpleQueue

from lib.ads1x15 import ADS1115

# machine.soft_reset()

_YEAR = const(0)
_MONTH = const(1)
_DAY = const(2)
_WEEKDAY = const(3)
_HOUR = const(4)
_MINUTE = const(5)
_SECOND = const(6)

_BUFFER_STOCK_AMONT = const(10)

_MEASUREMENT_HISTORY_DIRECTORY_NAME = const("/flash/logs")
# _EXTENSION_NAME = const(".csv")
_EXTENSION_NAME = const("")

PERIPHERAL_NAME = "ABCDEF"

_ALLOW_ADDRESS =["08:be:ac:34:ce:79",""]


DEVICE_NAME:str = "ABCDEf"
# DEVICE_NAME:str = "CurrentSensor_ABCD"

#　カスタムサービスおよび特徴のUUID
SERVICE_UUID = ubluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")
AUTH_UUID = ubluetooth.UUID("12345678-1234-5678-1234-56789abcdef2")
GET_CONDITION_UUID=ubluetooth.UUID("12345678-1234-5678-1234-56789abcdef3")
WRITE_UUID = ubluetooth.UUID("12345678-1234-5678-1234-56789abcdef4")
INDICATE_UUID = ubluetooth.UUID("12345678-1234-5678-1234-56789abcdef5")

_ADV_INERVAL_US = const(25000)

led = machine.Pin(22,machine.Pin.OUT)

start_switch =machine.Pin(21,machine.Pin.IN,machine.Pin.PULL_UP)

#-----
current_service:aioble.Service = aioble.Service(SERVICE_UUID)
auth:aioble.Characteristic = aioble.Characteristic(current_service,AUTH_UUID,write = True,capture = True)
get_condition:aioble.Characteristic = aioble.Characteristic(current_service,GET_CONDITION_UUID,write = True,capture = True)
current_write:aioble.Characteristic = aioble.Characteristic(current_service,WRITE_UUID,read=True,write = True,capture=True)
current_indicate:aioble.Characteristic = aioble.Characteristic(current_service,INDICATE_UUID,read=True,notify=True,indicate=True)
# current_read:aioble.Characteristic = aioble.Characteristic(current_service,TEST_UUID,read=True,indicate=True)

aioble.register_services(current_service)
#--------------------------------------------------
#内部温度センサ
class InternalTempSensor:
    coe=3.3/65535
    
    def __init__(self):
        self._tempSensor = ADC(4)
        
    def GetTemp(self):
        coeff=3.3/65535
        temprature =self._tempSensor.read_u16()*coeff
        return 27 - (temprature - 0.706)/0.001721

#--------------------------------------------------
DISPLAY_SCL = 17
DISPLAY_SDA = 16
RTC_SCL = 19
RTC_SDA = 18
RTC_FREQ = 400000
INTERRUPT_PIN = 15

#--------------------------------------------------
#--------------------------------------------------
#--------------------------------------------------
class Peripheral:
    tempSensor:InternalTempSensor
    coeff=3.3/65535
    #------------------------------
    #コンストラクタ
    def __init__(self):
        # フィールド
        self._is_advertise:bool = True
        self._is_connecting:bool
        self._watch_write_running:bool
        self._watch_write_task = None

        self._stockData1=bytearray() # バッファデータ１
        self._stockData2=bytearray() # バッファデータ2
        self._isFirstData:bool = True # バッファデータ切替フラグ

        self._clock_time = None
        self._previous_date = time.localtime()

        self._is_recording:bool = False
        self._stockCount:int = 0

        self._i2c_disp:I2C
        self._ic2_rtc:I2C
        self._disp:DisplaySsd1306
        self._internal_rtc:RTC
        self._ex_rtc:RX8025NB
        self._ex_timer:Pin
        self._flash_io:FlashIO

        self.adc0:ADC # 電流値取得ピン

        self._write_queue:SimpleQueue # 通知ストックキュー

        self._is_external_rtc:bool = False # 外部RTC有効無効

        self._now_current:int = 0 # 現在の電流値(100倍値)

        #I2C初期化
        self._i2c_disp = I2C(0, scl=Pin(DISPLAY_SCL), sda=Pin(DISPLAY_SDA))
        self._ic2_rtc = I2C(1, scl=Pin(RTC_SCL), sda=Pin(RTC_SDA),freq=RTC_FREQ)

        print(self._i2c_disp.scan())
        # self._i2c_adc = I2C(0,scl=Pin(13),sda=Pin(12))
        # self._adc0 = ADS1115(self._i2c_adc)
        # print(self._i2c_adc.scan())
        
        # flash memory初期化
        self._spi = SPI(0,baudrate=10_000_000, polarity=0, phase=0,sck=Pin(2),mosi=Pin(3),miso=Pin(4))
        cs = Pin(5,Pin.OUT)

        # flashインスタンス作成
        w25q = W25Q(self._spi,cs)

        # littleFs用Device作成
        bd = BlockDevice(w25q)

        # littleFsにDevice登録
        self._flash_io = FlashIO(bd)

        try:
            self._flash_io.mount("/")

        except OSError as e:
            # pass
            print(f"Formatting SPI flash : {e} {str(e)}")
            self._flash_io.make_file_system()
            self._flash_io.mount("/")

        # 外部RTCモジュールが接続されているか
        if self._ic2_rtc.scan() == []:
            print("Set internal RTC")
            self._is_external_rtc = False
            # 内部RTCのインスタンスの作成
            self._internal_rtc = RTC()
        else:
            print("Set external RTC")
            self._is_external_rtc = True
            # 外部RTCインスタンスの設定
            self._setting_external_rtc()

        # 現在時刻の仮設定
        self._clock_time = self.rtc_get_datetime()
        self._previous_date = self.rtc_get_datetime()


        #ディスプレイインスタンスの作成
        self._disp = DisplaySsd1306(self._i2c_disp)
        self._adc0 = ADS1115(self._i2c_disp,0x48,2)
        val = self._adc0.read(1,0,1)
        print(f"val is {val}")

        #内部温度センサインスタンスの作成
        self.tempSensor = InternalTempSensor()

        #アナログ信号取得ピン初期化
        self.adc0 =ADC(0)

        self.interrupt_hander_setting(self.on_rtc_tick)

        self._write_queue:SimpleQueue

    #------------------------------
    # 外部RTCインスタンスの設定
    def _setting_external_rtc(self):
        #外部RTCモジュール(RX-8025NB)のインスタンスの作成
        self._ex_rtc = RX8025NB(self._ic2_rtc)

        # 割り込み信号ピンの設定
        self._timer = Pin(INTERRUPT_PIN,Pin.IN,Pin.PULL_UP)

        # 現在時刻の設定
        # self._ex_rtc.set_datetime(time.localtime())
        self._ex_rtc.set_datetime((2025,5,17,0,15,59,50,0))

        #24時間表記に
        self._ex_rtc.change_hour_dispaly(False)

        #1秒毎の割り込み信号設定
        self._ex_rtc.enable_1hz_interrupt()

    #------------------------------
    # 割り込みハンドラ
    def on_rtc_tick(self,pin):
        self.measure_timer(None)
        self.display_timer(None)

    #------------------------------
    # 現在時刻の取得
    def rtc_get_datetime(self):
        if self._is_external_rtc:
            return self._ex_rtc.get_datetime()
        else:
            return self._internal_rtc.datetime()

    #------------------------------
    # 現在時刻の設定
    def rtc_set_datetime(self,data_array):
        # 日時を設定（年, 月, 日, 曜日, 時, 分, 秒, ミリ秒）/ 曜日は無視されます
        if self._is_external_rtc:
            print(data_array)
            self._ex_rtc.set_datetime((data_array[0],data_array[1],data_array[2],0,
                                        data_array[3],data_array[4],data_array[5],0))
            self._previous_date = self._ex_rtc.get_datetime()
        else:
            self._internal_rtc.datetime((data_array[0],data_array[1],data_array[2],0,
                                        data_array[3],data_array[4],data_array[5],0))
            self._previous_date = self._internal_rtc.datetime()
            
    #------------------------------
    # 割り込みハンドラの設定
    def interrupt_hander_setting(self,callback):
        if self._is_external_rtc:
            self._timer.irq(trigger=Pin.IRQ_FALLING,handler=callback)
        else:
            self.timer =Timer(-1)
            self.timer.init(mode=Timer.PERIODIC,period=1000,callback=callback)

    #------------------------------
    #バッファ先の判定
    def change_stock_target(self):
        self._isFirstData = not self._isFirstData

    #------------------------------
    #年月日の文字列変換
    def change_date_str(self,now)->str:
        yaer = now[0]
        month = now[1]
        day = now[2]
        return f"{yaer:04}/{month:02}/{day:02}"

    #------------------------------
    #年月日の文字列変換2(西暦は下２桁)
    def change_date_str2(self,now)->str:
        yaer = str(now[_YEAR])[-2:]
        month = now[_MONTH]
        day = now[_DAY]
        return f"{yaer:02}/{month:02}/{day:02}"

    #------------------------------
    #時間秒の文字列変換
    def change_time_str(self,now)->str:
        hour = now[_HOUR]
        minute = now[_MINUTE]
        second = now[_SECOND]
        return f"{hour:02}:{minute:02}:{second:02}"

    #------------------------------
    #年月日からファイル名生成
    def get_filename_by_datetime(self,now):
        year = now[0]
        month = now[1]
        day = now[2]
        return f"{year:04}{month:02}{day:02}{_EXTENSION_NAME}"

    #------------------------------
    #メモリへのデータ保存～バッファのリセット
    async def write_memory(self,date):
        try:
            filename = self.get_filename_by_datetime(date)
            path = f'{_MEASUREMENT_HISTORY_DIRECTORY_NAME}/{filename}'
            # return
            print("Write to memory ...")
            if self._isFirstData:
                print(f"data2:{self._stockData2}")
                # if fileIO.OutputText(path,self._stockData2):
                if self._flash_io.append_to_byte_file(path,self._stockData2):
                    self._stockData2 = bytearray()
            else:
                print(f"data1:{self._stockData1}")
                # if fileIO.OutputText(path,self._stockData1):
                if self._flash_io.append_to_byte_file(path,self._stockData1):
                    self._stockData1 = bytearray()
            os.sync()
            print("Correct write to memory !")
        except Exception as e:
            print(f"Error in write_memory method : {e}")

    #------------------------------
    #電流値の取得
    def read_current_mA(self) -> int:
        import math
        samples =[]
        for _ in range(60):
            val = self._adc0.read(5,0,1)
            val = self._adc0.raw_to_v(val)
            # voltage = val * 2.048 / 32768
            samples.append(val)
            time.sleep_ms(0)
        
        offset = sum(samples) / len(samples)
        # offset = 0
        squared = [(v -offset) **2 for v in samples]
        mean = sum(squared) / len(squared)
        print(f"mean : {mean}")
        rms_voltage = math.sqrt(mean)
        current = rms_voltage  * 3000/20.25
        # current = int(current * 1000)
        print(f"voltage: {rms_voltage:.3f} V / current : {current:.3f} A")
        # return int(current*100)

        a=ADC(0)
        coeff=3.3/65535
        v=a.read_u16()*coeff
        return int(v*100)
        # 実際はADCなどから取得するコードに置き換える
        return(int)(2300 + random.uniform(-1,1) * 10) # 0000mA
    
    #------------------------------
    #バッファへのデータ保存
    def save_to_buffer(self,value,date):
        print(f"{self._isFirstData} : {value} / {date}")
        dateStr = date.split(':')
        hour =int(dateStr[0])
        minute=int(dateStr[1])
        second=int(dateStr[2])
        current = value
        if self._isFirstData:
            packed = struct.pack("<BBBH",hour,minute,second,current) + b'\n'
            self._stockData1.extend(packed)
        else:
            packed = struct.pack("<BBBH",hour,minute,second,current) + b'\n'
            self._stockData2.extend(packed)
    
    #------------------------------
    #測定値ストックタイマー
    def measure_timer(self,timer=None):
        #現在日時を取得
        now = self.rtc_get_datetime()

        #測定値を取得
        self._now_current = self.read_current_mA()

        # 測定開始していなければメモリに保存しない
        if not self._is_recording:
            led.off()
            return

        if (self._previous_date[_DAY] != now[_DAY]) | (self._stockCount >= _BUFFER_STOCK_AMONT):
            #データのバッファ先を変更
            self.change_stock_target()
            #カウントをリセット
            self._stockCount = 0

        #前回取得日を更新
        self._previous_date = now

        #現在日時を文字列に変換
        current_time = self.change_time_str(now)

        #現在のデータをバッファに保存
        self.save_to_buffer(self._now_current,current_time)

        #取得回数をカウント
        self._stockCount = self._stockCount + 1

        #測定中はLED点滅
        led.toggle()

    #--------------------------------------------------
    #測定記録タスク
    async def measure_record_task(self):
        _previous_data = self.rtc_get_datetime()
        self._previous_date =self.rtc_get_datetime()

        while True:
            # 記録開始されるまで待機
            while not self._is_recording:
                await asyncio.sleep_ms(0)
            
            print("Start recording ...")
            self._nowTarget1 = self._isFirstData
            while True:
                # 測定が中止されたら
                if not self._is_recording:
                    print("Stop recording !")
                    break

                # 保存バッファ先が切り替わったらメモリに保存
                if self._nowTarget1 != self._isFirstData:
                    self._nowTarget1 = self._isFirstData
                    await self.write_memory(_previous_data)
            
                await asyncio.sleep_ms(500)

    #--------------------------------------------------
    #接続タスク
    async def peripheral_task(self):
        # 接続されるデバイス
        connection:aioble.DeviceConnection = None

        # 書き込み監視タスク
        self._watch_write_task = None

        # 接続フラグ
        self._is_connecting = False

        # BLE接続待受
        while True:
            if not self._is_advertise:
                continue

            # 既に接続中なら何もしない
            if connection is not None:
                continue

            # アドバタイズ開始
            print("Start Advertise ...")
            connection = await aioble.advertise(
                _ADV_INERVAL_US,
                name = "ABCDEf",
                services=[SERVICE_UUID],
            )

            if not self._is_advertise:
                print("Stop advertise.")
                continue

            # 接続されたクライアント
            async with connection:
                print(f"connected client : {connection}")
                # MacAddress確認
                addr = ":".join(ubinascii.hexlify(connection.device.addr).decode()[i:i+2] for i in range(0, 12, 2))
                print(f"client address : {addr}")

                # 許可アドレスか確認
                if addr not in _ALLOW_ADDRESS:
                    print(f"Unauthorisez device : {connection.device}")
                    await connection.disconnect()
                    continue
                
                # 許可されたなら次の処理へ
                print(f"Authorized device : {connection.device}")

                try:

                    # #認証プロセス
                    # secret_key:bytes = b"my_secret_key"
                    # auth.write(secret_key)

                    # #クライアントからの応答待機
                    # response = await auth.written(timeout_ms=5000)
                    # if response[1] != secret_key:
                    #     print("Authentication failed!")
                    #     await connection.disconnect()
                    #     continue

                    # 認証通過
                    print("Authentication successfull!")

                    print("Connection from : ",connection.device)
                    await asyncio.sleep_ms(1)

                    # 接続開始時間を取得
                    start_time = time.ticks_ms()

                    # 書き込みコマンドを受け取るQueueを初期化
                    self._write_queue = SimpleQueue()

                    #接続フラグON
                    self._is_connecting = True
                    # 書き込み検知タスク起動
                    self._watch_write_running = True
                    self._watch_write_task = asyncio.create_task(self.watch_get_condition())

                    print("watch_write task started")

                    # 接続中処理
                    try:
                        while True:
                            # 一定時間が経過したら接続を切断
                            if time.ticks_diff(time.ticks_ms(),start_time) > min(_ADV_INERVAL_US,10000):
                                print(f'[Pico] from central no signal...')
                                break

                            # 書き込みQueueから最新のコマンドを非同期で取得
                            cmd = self.check_written_nowait()

                            #取得コマンドにより処理分岐
                            #----------
                            # 現在電流値の場合
                            if cmd == "NowCurrent":
                                while True:
                                    # 一定時間が経過したら接続を切断
                                    if time.ticks_diff(time.ticks_ms(),start_time) > min(_ADV_INERVAL_US,10000):
                                        print(f'[Pico] from central no signal...')
                                        break
                                    
                                    # 書き込みQueueから最新のコマンドを非同期で取得
                                    end_cmd = self.check_written_nowait()
                                    #　終了コマンドが来たら終了
                                    if end_cmd == 'PING':
                                        print("[Pico] 'PING' Received. Connect continue.")
                                        start_time = time.ticks_ms()
                                    elif end_cmd == 'END':
                                        print("[Pico] 'END' received. Stop notifying.")
                                        break
                                    
                                    # 保持している現在電流値をエンコードして通知
                                    current = struct.pack("<h",self._now_current)
                                    print(f"current : {self._now_current}")
                                    await current_indicate.indicate(connection,current)
                                    
                                    # １秒待機
                                    await asyncio.sleep(1)
                                
                            #----------
                            # 時刻設定の場合
                            elif cmd == "SetTime":
                                    try:    
                                        connection,data = await current_write.written(timeout_ms=_ADV_INERVAL_US)
                                        self._set_time(data)
                                        await current_indicate.indicate(connection,b'SUCCESS')
                                    except Exception as e:
                                        print(f"SetTime Error Occured : {e}")
                                        await current_indicate.indicate(connection,b'FAILED')
                                        raise

                                    # １秒待機
                                    await asyncio.sleep(1)

                            #----------
                            # ファイルリスト取得の場合
                            elif cmd == "GetList":
                                try:
                                    files = self._flash_io.get_file_list(f"{_MEASUREMENT_HISTORY_DIRECTORY_NAME}")
                                    for file in files:
                                        file_name,_,_,_ = file
                                        name = file_name.encode()
                                        print(name)
                                        await current_indicate.indicate(connection,name)
                                        await asyncio.sleep(1)

                                    await current_indicate.indicate(connection,b'END')

                                    break
                                except Exception as e:
                                    print(f"GetList Error occured : {e}")
                                    raise

                            #----------
                            # ログ取得の場合
                            elif cmd == "GetLogs":
                                try:
                                    connection,data = await current_write.written(timeout_ms=_ADV_INERVAL_US)
                                    file_name = data.decode()
                                    lines = self._flash_io.get_read_data(f"{_MEASUREMENT_HISTORY_DIRECTORY_NAME}/{file_name}")
                                    if lines is None:
                                        print(f"Get data is None !")
                                        raise

                                    for line in lines:
                                        print(line)
                                        await current_indicate.indicate(connection,line)
                                        await asyncio.sleep(1)

                                    await current_indicate.indicate(connection,b'END')

                                    break
                                except Exception as e:
                                    print(f"GetList Error occured : {e}")
                                    raise
                            
                            #----------
                            # ログ削除の場合
                            elif cmd == "DeleteLog":
                                    try:    
                                        connection,data = await current_write.written(timeout_ms=_ADV_INERVAL_US)
                                        file_name = data.decode()
                                        print(file_name)
                                        self._flash_io.remove_file(f"{_MEASUREMENT_HISTORY_DIRECTORY_NAME}/{file_name}")
                                        # self._set_time(data)
                                        await current_indicate.indicate(connection,b'SUCCESS')
                                    except Exception as e:
                                        print(f"SetTime Error Occured : {e}")
                                        await current_indicate.indicate(connection,b'FAILED')
                                        raise
                                        # break
# 
                                    # １秒待機
                                    await asyncio.sleep(1)

                            #他の処理を実行
                            await asyncio.sleep(1)

                    except Exception as e:
                        print(f"Error : {e}")
                        await connection.disconnect()
                    finally:
                        # 書き込み監視タスクを停止して、タスクをキャンセル～終了を待機
                        print("finally - cleaning up")
                        # 監視フラグをOFFに
                        self._watch_write_running = False
                        # タスクの存在チェック
                        if self._watch_write_task:
                            # タスクがあればキャンセル
                            self._watch_write_task.cancel()
                            try:
                                # キャンセルされたタスクが終了するまで待機
                                await self._watch_write_task
                            except asyncio.CancelledError:
                                print("[Pico] watch_write cancelled")

                    #接続が切断されるまで待機
                    await connection.disconnected()
                    print("Disconnect from :",connection.device)

                except Exception as e:
                    print(f"Error during connection : {e}")
                    await connection.disconnect()
            
            # 接続先をクリア
            connection = None
            await asyncio.sleep_ms(1)

    #--------------------------------------------------
    # クライアント書き込みデータの監視  
    def check_written_nowait(self):
        try:
            return self._write_queue.get_nowait()
        except Exception:
            return None

    #--------------------------------------------------
    # 書き込みデータを取得
    async def watch_get_condition(self):
        try:
            while self._watch_write_running:
                try:
                    # writeイベントを待つ
                    _, data = await get_condition.written(timeout_ms=0)

                    # 受け取ったバイナリデータをデコードして空白文字を除去
                    cmd = data.decode().strip()

                    print(f"[Pico] Received: {cmd}")

                    # コマンド文字列をキューに即時格納
                    self._write_queue.put_nowait(cmd)

                # except TimeoutError as e:
                #     print(f"[Pico] watch_write error: {e}")
                except Exception as e:
                    print(f"[Pico] watch_write error: {type(e)} - {e}")
                    self._is_connecting = False
                    # raise asyncio.CancelledError()
                    break
        except asyncio.CancelledError as e:
            print("[Pico] watch_write task was cancelled cleanly")
            raise

    def _set_time(self,data):
        try:
            # 受け取ったバイナリデータをデコードして空白文字を除去
            date = data.decode().strip()
            data_array = list(map(int, date.split("/")))

            # 現在時刻を設定
            self.rtc_set_datetime(data_array)
            
            print("set time success !")
        except Exception as e:
            raise

    #--------------------------------------------------
    # ディスプレイ表示タイマー
    def display_timer(self,timer):
        self._clock_time = self.rtc_get_datetime()
            
        dateStr = self.change_date_str2(self._clock_time)
        timeStr = self.change_time_str(self._clock_time)
        self._disp.TwoLineText(dateStr,timeStr)
    
    #--------------------------------------------------
    # 外部入力監視タスク
    async def external_input_task(self):
        while True:
            # #STARTボタンが押されるまで開始待機
            if start_switch.value() == 0:
                self._is_recording = not self._is_recording
                await asyncio.sleep_ms(500)
            await asyncio.sleep_ms(0)


async def main3():
    ble =Peripheral()
    t1 = asyncio.create_task(ble.peripheral_task())
    t2 = asyncio.create_task(ble.measure_record_task())
    t3= asyncio.create_task(ble.external_input_task())
    await asyncio.gather(t1,t2,t3)


try:
    asyncio.run(main3())
except KeyboardInterrupt as e:
    led.off()
    print("KeyboardInterrupt!")