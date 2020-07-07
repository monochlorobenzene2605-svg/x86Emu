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

class EFLAGS:
    CARRY = 0b1
    ZERO = (0b1 << 6)
    SIGN = (0b1 << 7)
    OVERFLOW = (0b1 << 11)

#TODO: オーバーフロー時32ビットに丸めたほうがいいか考える

class Emulator:
    def __init__(self, memory_size, eip=0x0000, esp=0x0000):
        self.env = Environment(memory_size, eip, esp)
        self.memory_size = memory_size
        self.instructions = [0]*256
        self._init_instructions()

    def _init_instructions(self):
        self.instructions[0x01] = self._add_rm32_r32

        self.instructions[0x3B] = self.cmp_r32_rm32

        for i in range(8):#0x50~0x57
            self.instructions[0x50+i] = self._push_r32
        for i in range(8):#0x58~0x5F
            self.instructions[0x58+i] = self._pop_r32
        self.instructions[0x68] = self._push_imm32
        self.instructions[0x6A] = self._push_imm8

        self.instructions[0x70] = self._jo
        self.instructions[0x71] = self._jno
        self.instructions[0x72] = self._jc
        self.instructions[0x73] = self._jnc
        self.instructions[0x74] = self._jz
        self.instructions[0x75] = self._jnz
        self.instructions[0x78] = self._js
        self.instructions[0x79] = self._jns
        self.instructions[0x7C] = self._jl
        self.instructions[0x7E] = self._jle

        self.instructions[0x83] = self._calc_rm32_imm8

        self.instructions[0x89] = self._move_rm32_r32
        self.instructions[0x8B] = self._move_r32_rm32
        for i in range(8):#0xB8~0xBF
            self.instructions[0xB8+i] = self._move_imm32
        self.instructions[0xC3] = self._ret
        self.instructions[0xC7] = self._move_rm32_imm32
        self.instructions[0xC9] = self._leave
        self.instructions[0xE8] = self._call_rel32
        self.instructions[0xE9] = self._near_jump
        self.instructions[0xEB] = self._short_jump

        self.instructions[0xFF] = self._code_ff

    def load_program(self, file):
        f = open(file, mode="rb").read()
        for i,byte in enumerate(f):
            self.env.memory[i+0x7c00] = byte

    def run(self):
        while self.env.eip<self.memory_size:
            self.tick()
            if self.env.eip==0x00: break
        print("--------------------------------------------------")
        print("------------------終わったよ----------------------")
        print("--------------------------------------------------")

    def tick(self):
        code = self.fetch_code()
        print("EIP = {0:08x}, Code = {1:08x}".format(self.env.eip-1,code))
        self.exec(code)

    def fetch_code(self):
        code = self._get_code8()
        return code

    def exec(self,code):
        self.instructions[code]()

    def show_env(self):
        regnames = ["EAX", "ECX", "EDX", "EBX", "ESP", "EBP", "ESI", "EDI"]
        for i in range(self.env.REGISTERS_COUNT):
            print("{0} = {1:08x}".format(regnames[i], self.env.registers[i]))
        print("\nEIP = {:08x}".format(self.env.eip))
        #TODO: メモリの内容も表示する
        
    def _mod_rm(self, index=0):
        byte = self._get_code8(index)
        mod = (byte & 0b11000000) >> 6
        rm = (byte & 0b00000111)
        reg = (byte & 0b00111000) >> 3
        disp = 0
        ## TODO: SIBがある場合対応 dispおよびimm32が後ろに1バイトずれる (mod!=11)&&(rm==100)の場合SIBアリ
        if mod == 0b01:
            disp = self._get_code8(0)
        elif  mod == 0b10:
            disp = self._get_code32(0)
        ptr = self.env.registers[rm] + disp
        return (mod, reg, rm, ptr)

    def cmp_r32_rm32(self): #OP:0x3B
        (mod, reg, rm, ptr) = self._mod_rm()
        operand1 = self.env.registers[reg]
        if mod == 0b11:
            result = self.env.registers[reg] - self.env.registers[rm]
            operand2 = self.env.registers[rm]
        else :
            result = self.env.registers[reg] - self._get_memory32(ptr)
            operand2 = self._get_memory32(ptr)
        self._update_eflags(operand1, operand2, result)

    def _update_eflags(self,op1,op2,result):
        is_carry = ((result >> 32) != 0)
        self._set_flag(self.env.eflags,EFLAGS.CARRY,is_carry)
        is_zero = (result == 0)
        self._set_flag(self.env.eflags,EFLAGS.ZERO,is_zero)
        is_negative = ((result>>31)&1)
        self._set_flag(self.env.eflags,EFLAGS.SIGN,is_negative)
        sign1 = op1 >> 31
        sign2 = op2 >> 31
        sign_result = (result >> 31) & 1
        is_overflow = (sign1!=sign2) or (sign1!=sign_result) # ???? こういうものらしいっぽい
        self._set_flag(self.env.eflags,EFLAGS.OVERFLOW,is_overflow)
        
    def _set_flag(self, old_flags, target_flag, new_flag):
        if (new_flag):
            old_flags |= target_flag
        else:
            old_flags &= ~target_flag
        self.env.eflags = old_flags

    def _jo(self):#OP:0x70
        diff = self._get_sign_code8()
        is_overflow = (self.env.eflags & EFLAGS.OVERFLOW)
        if is_overflow:
            self.env.eip += diff
    def _jno(self):#OP:0x71
        diff = self._get_sign_code8()
        is_overflow = (self.env.eflags & EFLAGS.OVERFLOW)
        if not is_overflow:
            self.env.eip += diff
    def _jc(self):#OP:0x72
        diff = self._get_sign_code8()
        is_carry = (self.env.eflags & EFLAGS.CARRY)
        if is_carry:
            self.env.eip += diff
    def _jnc(self):#OP:0x73
        diff = self._get_sign_code8()
        is_carry = (self.env.eflags & EFLAGS.CARRY)
        if not is_carry:
            self.env.eip += diff
    def _jz(self):#OP:0x74
        diff = self._get_sign_code8()
        is_zero = (self.env.eflags & EFLAGS.ZERO)
        if is_zero:
            self.env.eip += diff
    def _jnz(self):#OP:0x75
        diff = self._get_sign_code8()
        is_zero = (self.env.eflags & EFLAGS.ZERO)
        if not is_zero:
            self.env.eip += diff
    def _js(self):#OP:0x78
        diff = self._get_sign_code8()
        is_sign = (self.env.eflags & EFLAGS.SIGN)
        if is_sign:
            self.env.eip += diff
    def _jns(self):#OP:0x79
        diff = self._get_sign_code8()
        is_sign = (self.env.eflags & EFLAGS.SIGN)
        if not is_sign:
            self.env.eip += diff
    def _jl(self):#OP:0x7c
        diff = self._get_sign_code8()
        is_sign = (self.env.eflags & EFLAGS.SIGN)
        is_overflow = (self.env.eflags & EFLAGS.OVERFLOW)
        is_less = (is_sign != is_overflow)
        if is_less:
            self.env.eip += diff
    def _jle(self):#OP:0x7e
        diff = self._get_sign_code8()
        is_sign = (self.env.eflags & EFLAGS.SIGN)
        is_overflow = (self.env.eflags & EFLAGS.OVERFLOW)
        is_zero = (self.env.eflags & EFLAGS.ZERO)
        is_less = (is_sign != is_overflow)
        is_less_or_equal = (is_zero or is_less)
        if is_less_or_equal:
            self.env.eip += diff

    def _push_r32(self): #OP:0x50~0x57
        self.env.eip -= 1
        reg = self._get_code8() - 0x50
        val = self.env.registers[reg]
        self._push32(val)

    def _push_imm32(self): # OP:0x68
        val = self._get_code32()
        self._push32(val)
    
    def _push_imm8(self): # OP:0x6A
        val = self._get_code8()
        self._push32(val)

    def _push32(self,val):
        self.env.registers[REGISTERS_NAME.ESP] -= 0x04
        self._set_memory32(self.env.registers[REGISTERS_NAME.ESP],val)

    def _pop_r32(self): #OP:0x58~0x5F
        self.env.eip -= 1
        reg = self._get_code8() - 0x58
        self.env.registers[reg] = self._pop32()
    
    def _pop32(self):
        ret = self._get_memory32(self.env.registers[REGISTERS_NAME.ESP])
        self.env.registers[REGISTERS_NAME.ESP] += 0x04
        return ret

    def _ret(self): #OP:0xC3
        self.env.eip = self._pop32()

    def _call_rel32(self): #OP:0xE8
        jmp_to = self._get_sign_code32()
        self._push32(self.env.eip)
        self.env.eip += jmp_to

    def _leave(self): #OP:0xC9
        self.env.registers[REGISTERS_NAME.ESP] = self.env.registers[REGISTERS_NAME.EBP]
        self.env.registers[REGISTERS_NAME.EBP] = self._pop32()

    def _move_rm32_r32(self): #OP:0x89
        (mod,reg,rm,_) = self._mod_rm()
        #TODO: 今回はまだmodRM対応してないのでする
        if mod == 0b11:
            self.env.registers[rm] = self.env.registers[reg]

    def _move_r32_rm32(self): #OP:0x8B
        (mod,reg,rm,ptr) = self._mod_rm()
        if mod == 0b11:
            self.env.registers[reg] = self.env.registers[rm]
        else:
            self.env.registers[reg] = self._get_memory32(ptr)
        
    def _code_ff(self): # TODO: None なところは要実装
        (mod,reg,rm,ptr) = self._mod_rm()
        if reg == 0: # INC
            val = self._get_memory32(ptr) + 1
            self._set_memory32(ptr,val)
        elif reg == 1: # DEC
            val = self._get_memory32(ptr) - 1
            self._set_memory32(ptr,val)
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
        if val > 0xFF: None # TODO: 例外でも投げとけ
        self.env.memory[ptr] = val
    
    def _set_memory32(self,ptr,val):
        for i in range(4):
            v2 = val & 0x00_00_00_FF
            self._set_memory8(ptr+i,v2)
            val >>= 8

    def _add_rm32_r32(self): #OP:0x01
        (mod,reg,rm,ptr) = self._mod_rm()
        if mod == 0b11 :
            old_val = self.env.registers[rm]
        else :
            old_val = self._get_memory32(ptr)
        val = self.env.registers[reg]
        val += old_val
        if mod == 0b11 :
            self.env.registers[rm] = val
        else :
            self._set_memory32(ptr,val)

    def _move_rm32_imm32(self): #OP:0xC7
        (mod,reg,rm,ptr) = self._mod_rm()
        val = self._get_code32()
        self._set_memory32(ptr,val)

    def _move_imm32(self): #OP:0xB8~0xBF
        self.env.eip -= 1
        reg = self._get_code8() - 0xB8 # オペコードにレジスタ指定が含まれるため-0xB8して取り出す
        val = self._get_code32(0)
        self.env.registers[reg] = val

    def _calc_rm32_imm8(self): #OP:0x83 ## TODO: None なところは要実装
        (mod,reg,rm,_) = self._mod_rm()
        val = self._get_code8()
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
            op1 = self.env.registers[rm]
            op2 = val
            result = op1-op2
            self._update_eflags(op1, op2, result)
            self.env.registers[rm] = result
        elif reg == 6: # XOR
            self.env.registers[rm] ^= val
        elif reg == 7: # CMP
            op1 = self.env.registers[rm]
            op2 = val
            result = op1-op2
            self._update_eflags(op1, op2, result)

    def _short_jump(self):#OP:EB
        diff = self._get_sign_code8()
        self.env.eip += diff

    def _near_jump(self):#OP:E9
        diff = self._get_sign_code32()
        self.env.eip += diff


    def _get_code8(self, index=0):
        code = self.env.memory[self.env.eip+index]
        self.env.eip += 1
        return code

    def _get_sign_code8(self, index=0):
        ret = self._get_code8(index).to_bytes(1,byteorder='big')
        ret = int.from_bytes(ret,byteorder='big', signed=True)
        return ret

    def _get_code32(self, index=0):
        ret = 0
        for i in range(4):
            ret |= self._get_code8(index) << (i*8)
        return ret

    def _get_sign_code32(self, index=0):
        ret = self._get_code32(index).to_bytes(4,byteorder="little")
        ret = int.from_bytes(ret,byteorder='little', signed=True)
        return ret



class Environment:
    REGISTERS_COUNT = 8
    def __init__(self, memory_size, eip, esp):
        self.registers = [0x0000]*Environment.REGISTERS_COUNT
        self.eflags = 0x0000
        self.memory = [0x0000]*memory_size
        self.eip = eip
        self.registers[REGISTERS_NAME.ESP] = esp
