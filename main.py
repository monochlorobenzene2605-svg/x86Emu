import sys
import struct
from Emulator import Emulator

if __name__ == '__main__':
    args = sys.argv
    bin_path = args[1]    # コマンド引数から実行バイナリのパスを取得
    MEMORY_SIZE = (1024*1024) # メモリは1MB
    eip = 0x7c00
    esp = 0x7c00
    emu = Emulator(MEMORY_SIZE, eip, esp)
    emu.load_program(bin_path)
    emu.run()
    emu.show_env()
