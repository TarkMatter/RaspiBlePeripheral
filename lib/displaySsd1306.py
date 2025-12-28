import ssd1306

class DisplaySsd1306:
    def __init__(self,i2cInfo):
        self.i2c = i2cInfo
        self.display = ssd1306.SSD1306_I2C(128, 32, self.i2c) #(幅, 高さ, I2Cオブジェクト)

    #--------------------------------------------------
    #LCD表示
    def oled_text_scaled(self,text:str, x, y, scale, character_width=8, character_height=8):
        # temporary buffer for the text
        width = character_width * len(text)
        height = character_height
        temp_buf = bytearray(width * height)
        temp_fb = ssd1306.framebuf.FrameBuffer(temp_buf, width, height, ssd1306.framebuf.MONO_VLSB)

        # write text to the temporary framebuffer
        temp_fb.text(text, 0, 0, 1)

        # scale and write to the display
        for i in range(width):
            for j in range(height):
                pixel = temp_fb.pixel(i, j)
                if pixel:  # If the pixel is set, draw a larger rectangle
                    self.display.fill_rect(x + i * scale, y + j * scale, scale, scale, 1)
    
    #--------------------------------------------------
    #ディスプレイへの２行表示
    def TwoLineText(self,txt1:str,txt2:str):
        self.Clear()
        self.oled_text_scaled(txt1, 0, 0, 2)
        self.oled_text_scaled(txt2, 0, 16, 2)
        self.Show()
    
    #--------------------------------------------------
    #ディスプレイのクリア
    def Clear(self):
        self.display.fill(0)
        
    #--------------------------------------------------
    #ディスプレイの表示
    def Show(self):
        self.display.show()