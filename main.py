from enum import IntEnum
class REGISTERS_NAME(IntEnum):
    EAX=0
    ECX=1
    EDX=2
    EBX=3
    ESP=4
    EBP=5
    ESI=6
    EDI=7

class Emulator:
    def __init__(self, memory_size, eip=0x0000, esp=0x0000):
        self.env = Environment(memory_size, eip, esp)
        self.memory_size = memory_size
        self.instructions = [0]*256
        self._init_instructions()

    def _init_instructions(self):
        for i in range(8):
            self.instructions[0xB8+i] = self._move
        self.instructions[0xEB] = self._short_jump
        self.instructions[0xE9] = self._near_jump

    def _move(self):
        op_size = 5
        reg = self.get_code8() - 0xB8 # オペコードにレジスタ指定が含まれるため-0xB8して取り出す
        val = self.get_code32(1)
        self.env.registers[reg] = val
        self.env.eip += op_size

    def _short_jump(self):
        op_size = 2
        diff = self.get_sign_code8(index=1)
        self.env.eip += (diff+op_size)

    def _near_jump(self):
        op_size = 5
        diff = self.get_sign_code32(1)
        self.env.eip += (diff+op_size)

    def run(self):
        while self.env.eip<self.memory_size:
            self.tick()
            if self.env.eip==0x00: break
        print("--------------------------------------------------")
        print("------------------終わったよ----------------------")
        print("--------------------------------------------------")

    def tick(self):
        code = self.fetch_code()
        print("EIP = {0:08x}, Code = {1:08x}".format(self.env.eip,code))
        self.exec(code)

    def fetch_code(self):
        return self.get_code8()

    def exec(self,code):
        self.instructions[code]()

    def get_code8(self, index=0):
        return self.env.memory[self.env.eip+index]

    def get_sign_code8(self, index=0):
        ret = self.get_code8.to_bytes(1,byteorder='big')
        ret = int.from_bytes(ret,byteorder='big', signed=True)
        return ret

    def get_code32(self, index=0):
        ret = 0
        for i in range(4):
            ret |= self.get_code8(index+i) << (i*8)
        return ret

    def get_sign_code32(self, index=0):
        ret = self.get_code32(index).to_bytes(4,byteorder="little")
        ret = int.from_bytes(ret,byteorder='little', signed=True)
        return ret

    def show_env(self):
        regnames = ["EAX", "ECX", "EDX", "EBX", "ESP", "EBP", "ESI", "EDI"]
        for i in range(self.env.REGISTERS_COUNT):
            print("{0} = {1:08x}".format(regnames[i], self.env.registers[i]))
        print("EIP = {:08x}".format(self.env.eip))

class Environment:
    REGISTERS_COUNT = 8
    def __init__(self, memory_size, eip, esp):
        self.registers = [0x0000]*Environment.REGISTERS_COUNT
        self.eflags = 0x0000
        self.memory = [0x0000]*memory_size
        self.eip = eip
        self.registers[REGISTERS_NAME.ESP] = esp

def read_program(env, file):
    f = open(file, mode="rb").read()
    for i,byte in enumerate(f):
        env.memory[i+0x7c00] = byte

import sys
import struct
if __name__ == '__main__':
    args = sys.argv
    bin_path = args[1]    # コマンド引数から実行バイナリのパスを取得
    MEMORY_SIZE = (1024*1024) # メモリは1MB
    eip = 0x7c00
    esp = 0x7c00
    emu = Emulator(MEMORY_SIZE, eip, esp)
    read_program(emu.env, bin_path)
    emu.run()
    emu.show_env()
