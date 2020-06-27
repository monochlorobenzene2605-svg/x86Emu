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
        self.instructions[0x01] = self._add_rm32_r32
        self.instructions[0x83] = self._calc_rm32_imm8
        self.instructions[0x89] = self._move_rm32_r32
        self.instructions[0x8B] = self._move_r32_rm32
        for i in range(8):
            self.instructions[0xB8+i] = self._move_imm32
        self.instructions[0xC7] = self._move_rm32_imm32
        self.instructions[0xEB] = self._short_jump
        self.instructions[0xE9] = self._near_jump
        self.instructions[0xFF] = self._code_ff

    def load_program(self, file):
        f = open(file, mode="rb").read()
        for i,byte in enumerate(f):
            self.env.memory[i+0x7c00] = byte

    def _mod_rm(self, index):
        byte = self.get_code8(index)
        mod = (byte & 0b11000000) >> 6
        rm = (byte & 0b00000111)
        reg = (byte & 0b00111000) >> 3
        return (mod, reg, rm)

    def _move_rm32_r32(self): #OP:0x89
        (mod,reg,rm) = self._mod_rm(1)
        #TODO: 今回はまだmodRM対応してないのでする
        if mod == 0b11:
            self.env.registers[rm] = self.env.registers[reg]
            self.env.eip += 2

    def _move_r32_rm32(self): #OP:0x8B
        (mod,reg,rm) = self._mod_rm(1)
        if mod == 0b11:
            self.env.registers[reg] = self.env.registers[rm]
            self.env.eip += 2
            return
        disp = 0
        if mod == 0b01:
            disp = self.get_code8(2)
            self.env.eip += 3
        elif  mod == 0b10:
            disp = self.get_code32(2)
            self.env.eip += 6
        ptr = self.env.registers[rm] + disp
        self.env.registers[reg] = self._get_memory32(ptr)
        
    def _code_ff(self): # TODO: None なところは要実装
        (mod,reg,rm) = self._mod_rm(1)
        if reg == 0: # INC
            disp = self.get_code8(2)
            ptr = self.env.registers[rm] + disp
            val = self._get_memory32(ptr) + 1
            self._set_memory32(ptr,val)
            self.env.eip += 3
        elif reg == 1: # DEC
            val = self._get_memory32(rm) - 1
            self._set_memory32(rm,val)
        elif reg == 2: # CALL rm32
            None
        elif reg == 3: # CALL m16:32
            None
        elif reg == 4: # JMP rm32
            None
        elif reg == 5: # JMP m16:32
            None
        elif reg == 6: # PUSH
            None
        elif reg == 7: # not defined? https://www.wdic.org/w/SCI/%E3%82%AA%E3%83%9A%E3%82%B3%E3%83%BC%E3%83%89%20(IA-32) にはのってない
            None

    def _get_memory8(self,ptr):
        return self.env.memory[ptr]

    def _get_memory32(self,ptr):
        ret = 0
        for i in range(4):
            ret |= self._get_memory8(ptr+i) << (i*8)
        return ret
    
    def _set_memory8(self,ptr,val):
        if val < 0xFF: None # TODO: 例外でも投げる
        self.env.memory[ptr] = val
    
    def _set_memory32(self,ptr,val):
        for i in range(4):
            v2 = val & 0x00_00_00_FF
            self._set_memory8(ptr+i,v2)
            val >>= 8

    def _add_rm32_r32(self): #OP:0x01
        (mod,reg,rm) = self._mod_rm(1)
        disp = 0
        ## TODO: modrmのこの辺の処理はくくりだす
        ## TODO: SIBがある場合対応 dispおよびimm32が後ろに1バイトずれる (mod!=11)&&(rm==100)の場合SIBアリ
        if mod == 0b01:
            disp = self.get_code8(2)
            self.env.eip += 3
        elif  mod == 0b10:
            disp = self.get_code32(2)
            self.env.eip += 6
        ptr = self.env.registers[rm] + disp
        old_val = self._get_memory32(ptr)
        val = self.env.registers[reg]
        val += old_val
        self._set_memory32(ptr,val)

    def _move_rm32_imm32(self): #OP:0xC7
        (mod,reg,rm) = self._mod_rm(1)
        disp = 0
        ## TODO: SIBがある場合対応 dispおよびimm32が後ろに1バイトずれる (mod!=11)&&(rm==100)の場合SIBアリ
        if mod == 0b01:
            disp = self.get_code8(2)
            self.env.eip += 3
        elif mod == 0b10:
            disp = self.get_code32(2)
            self.env.eip += 6
        val = self.get_code32()
        self.env.eip += 4
        ptr = self.env.registers[rm] + disp
        self._set_memory32(ptr,val)

    def _move_imm32(self): #OP:0xB8~0xBF
        op_size = 5
        reg = self.get_code8() - 0xB8 # オペコードにレジスタ指定が含まれるため-0xB8して取り出す
        val = self.get_code32(1)
        self.env.registers[reg] = val
        self.env.eip += op_size

    def _calc_rm32_imm8(self): #OP:0x83 ## TODO: None なところは要実装
        (mod,reg,rm) = self._mod_rm(1)
        val = self.get_code8(2)
        if reg == 0: # ADD
            self.env.registers[rm] += val
        elif reg == 1: # OR
            self.env.registers[rm] |= val
        elif reg == 2: # ADC
            None
        elif reg == 3: # sbb
            None
        elif reg == 4: # AND
            self.env.registers[rm] &= val
        elif reg == 5: # SUB
            self.env.registers[rm] -= val
        elif reg == 6: # XOR
            self.env.registers[rm] ^= val
        elif reg == 7: # CMP
            None
        self.env.eip += 3

    def _short_jump(self):#OP:EB
        op_size = 2
        diff = self.get_sign_code8(index=1)
        self.env.eip += (diff+op_size)

    def _near_jump(self):#OP:E9
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
        ret = self.get_code8(index).to_bytes(1,byteorder='big')
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
