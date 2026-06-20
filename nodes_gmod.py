from NodeGraphQt import BaseNode

# ==================== СТРОГАЯ ТИПИЗАЦИЯ ПОРТОВ ====================
PORT_EXEC = "exec"
PORT_NUMBER = "number"   # Числа с плавающей точкой/целые
PORT_BOOL = "bool"
PORT_STRING = "string"
PORT_PLAYER = "player"
PORT_VECTOR = "vector"   # Трехмерные координаты

PORT_COLORS = {
    PORT_EXEC: (50, 200, 50),
    PORT_NUMBER: (50, 150, 250),
    PORT_BOOL: (220, 140, 40),
    PORT_STRING: (200, 60, 120),
    PORT_PLAYER: (150, 80, 230),
    PORT_VECTOR: (240, 200, 30)
}

# ==================== БАЗОВЫЕ УЗЛЫ (ИНФРАСТРУКТУРА) ====================

class BlueprintNode(BaseNode):
    """Базовый класс узла с хелперами строгой типизации."""
    def __init__(self):
        super().__init__()

    def add_exec_input(self, name="Execute"):
        port = self.add_input(name, color=PORT_COLORS[PORT_EXEC], multi_input=True)
        port.custom_data_type = PORT_EXEC
        return port

    def add_exec_output(self, name="Then"):
        port = self.add_output(name, color=PORT_COLORS[PORT_EXEC], multi_output=False)
        port.custom_data_type = PORT_EXEC
        return port

    def add_typed_input(self, name, port_type):
        port = self.add_input(name, color=PORT_COLORS.get(port_type, (255, 255, 255)))
        port.custom_data_type = port_type
        return port

    def add_typed_output(self, name, port_type):
        port = self.add_output(name, color=PORT_COLORS.get(port_type, (255, 255, 255)))
        port.custom_data_type = port_type
        return port

    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        return 'nil'


class BaseEventNode(BlueprintNode):
    """Базовый класс для узлов событий."""
    HOOK_NAME:  str  = ''
    LUA_ARGS:   str  = ''
    EVENT_VARS: dict = {} 

    def __init__(self):
        super().__init__()
        self.add_exec_output('Then')
        for port_name, (port_type, _) in self.EVENT_VARS.items():
            self.add_typed_output(port_name, port_type)

    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        return ctx.get(port_name, 'nil')

    def compile_event(self, compiler) -> str:
        ctx_vars = {}
        for port_name, (_, lua_var) in self.EVENT_VARS.items():
            ctx_vars[port_name] = lua_var

        # Импортируем CompileContext локально в момент выполнения, чтобы избежать циклического импорта!
        from blueprints_editor import CompileContext
        
        ctx = CompileContext(variables=ctx_vars)
        hook_id = f'WB_{self.HOOK_NAME}_{hex(id(self))[2:]}'
        
        lua  = f'hook.Add("{self.HOOK_NAME}", "{hook_id}", function({self.LUA_ARGS})\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        lua += 'end)\n\n'
        return lua


# ==================== 1. КАТЕГОРИЯ: СОБЫТИЯ (EVENTS) ====================

class PlayerSpawnNode(BaseEventNode):
    __identifier__ = 'gmod.events'
    NODE_NAME  = 'Player Spawn'
    HOOK_NAME  = 'PlayerSpawn'
    LUA_ARGS   = 'ply'
    EVENT_VARS = {'Player': (PORT_PLAYER, 'ply')}
    def __init__(self): super().__init__(); self.set_name("On Player Spawn")

class PlayerDeathNode(BaseEventNode):
    __identifier__ = 'gmod.events'
    NODE_NAME  = 'Player Death'
    HOOK_NAME  = 'PlayerDeath'
    LUA_ARGS   = 'victim, inflictor, attacker'
    EVENT_VARS = {
        'Victim':    (PORT_PLAYER, 'victim'),
        'Inflictor': (PORT_PLAYER, 'inflictor'),
        'Attacker':  (PORT_PLAYER, 'attacker')
    }
    def __init__(self): super().__init__(); self.set_name("On Player Death")

class PlayerSayNode(BaseEventNode):
    """Событие: Игрок написал в чат"""
    __identifier__ = 'gmod.events'
    NODE_NAME  = 'Player Say'
    HOOK_NAME  = 'PlayerSay'
    LUA_ARGS   = 'ply, text, teamExit'
    EVENT_VARS = {
        'Player': (PORT_PLAYER, 'ply'),
        'Text':   (PORT_STRING, 'text')
    }
    def __init__(self): super().__init__(); self.set_name("On Player Say")


# ==================== 2. КАТЕГОРИЯ: ЗНАЧЕНИЯ И ПЕРЕМЕННЫЕ (VALUES) ====================

class NumberValueNode(BlueprintNode):
    __identifier__ = 'gmod.values'
    NODE_NAME = 'Number'
    def __init__(self):
        super().__init__()
        self.add_typed_output('Value', PORT_NUMBER)
        self.add_text_input('value', 'Value', text='100')
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        val = (self.get_property('value') or '0').replace(',', '.')
        try: float(val); return val
        except ValueError: return '0'

class BoolValueNode(BlueprintNode):
    __identifier__ = 'gmod.values'
    NODE_NAME = 'Boolean'
    def __init__(self):
        super().__init__()
        self.add_typed_output('Value', PORT_BOOL)
        self.add_combo_menu('value', 'Value', items=['True', 'False'])
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        return 'true' if self.get_property('value') == 'True' else 'false'

class StringValueNode(BlueprintNode):
    __identifier__ = 'gmod.values'
    NODE_NAME = 'String'
    def __init__(self):
        super().__init__()
        self.add_typed_output('Value', PORT_STRING)
        self.add_text_input('value', 'Text', text='Hello!')
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        return f'"{self.get_property("value") or ""}"'

class VectorValueNode(BlueprintNode):
    __identifier__ = 'gmod.values'
    NODE_NAME = 'Vector'
    def __init__(self):
        super().__init__()
        self.add_typed_output('Value', PORT_VECTOR)
        self.add_text_input('x', 'X', text='0.0')
        self.add_text_input('y', 'Y', text='0.0')
        self.add_text_input('z', 'Z', text='0.0')
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        x = (self.get_property('x') or '0').replace(',', '.')
        y = (self.get_property('y') or '0').replace(',', '.')
        z = (self.get_property('z') or '0').replace(',', '.')
        return f'Vector({x}, {y}, {z})'


# ---> НОВЫЕ НОДЫ ПЕРЕМЕННЫХ ТУТ <---

class SetVariableNode(BlueprintNode):
    __identifier__ = 'gmod.values'
    NODE_NAME = 'Set Variable'

    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_text_input('var_name', 'Var Name', text='my_variable')
        self.add_combo_menu('var_type', 'Type', items=['Number', 'Boolean', 'String', 'Player', 'Vector'])
        self.add_exec_output("Then")
        
        # Создаем входной порт один раз
        # Используем стандартный цвет, так как динамически менять его больше не будем
        port = self.add_input('Value', color=PORT_COLORS[PORT_NUMBER])
        port.custom_data_type = PORT_NUMBER
        
        self._update_variable_port()

    def set_property(self, key, value, **kwargs):
        super().set_property(key, value, **kwargs)
        if key == 'var_type':
            self._update_variable_port()

    def _update_variable_port(self):
        chosen_type = self.get_property('var_type') or 'Number'
        type_mapping = {
            'Number': PORT_NUMBER, 'Boolean': PORT_BOOL, 'String': PORT_STRING, 
            'Player': PORT_PLAYER, 'Vector': PORT_VECTOR
        }
        port_type = type_mapping.get(chosen_type, PORT_NUMBER)
        
        port = self.get_input('Value')
        if port:
            port.custom_data_type = port_type
            # Опционально: можно менять имя ноды для удобства
            self.set_name(f"Set {chosen_type}")

    def compile_node(self, compiler, ctx) -> str:
        var_name = (self.get_property('var_name') or 'variable').strip().replace(' ', '_')
        val = compiler.resolve_port_value(self.get_input('Value'), ctx, fallback='nil')
        lua = f'{ctx.indent}{var_name} = {val}\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua


class GetVariableNode(BlueprintNode):
    __identifier__ = 'gmod.values'
    NODE_NAME = 'Get Variable'

    def __init__(self):
        super().__init__()
        self.add_text_input('var_name', 'Var Name', text='my_variable')
        self.add_combo_menu('var_type', 'Type', items=['Number', 'Boolean', 'String', 'Player', 'Vector'])
        
        # Создаем выходной порт один раз
        port = self.add_output('Value', color=PORT_COLORS[PORT_NUMBER])
        port.custom_data_type = PORT_NUMBER
        
        self._update_variable_port()

    def set_property(self, key, value, **kwargs):
        super().set_property(key, value, **kwargs)
        if key == 'var_type':
            self._update_variable_port()

    def _update_variable_port(self):
        chosen_type = self.get_property('var_type') or 'Number'
        type_mapping = {
            'Number': PORT_NUMBER, 'Boolean': PORT_BOOL, 'String': PORT_STRING, 
            'Player': PORT_PLAYER, 'Vector': PORT_VECTOR
        }
        port_type = type_mapping.get(chosen_type, PORT_NUMBER)
        
        port = self.get_output('Value')
        if port:
            port.custom_data_type = port_type
            # Опционально: можно менять имя ноды для удобства
            self.set_name(f"Get {chosen_type}")

    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        var_name = (self.get_property('var_name') or 'variable').strip().replace(' ', '_')
        return var_name

# ==================== 3. КАТЕГОРИЯ: ЛОГИКА И МАТЕМАТИКА (LOGIC) ====================

class CompareNumbersNode(BlueprintNode):
    __identifier__ = 'gmod.logic'
    NODE_NAME = 'Compare Numbers'
    def __init__(self):
        super().__init__()
        self.add_typed_input('A', PORT_NUMBER)
        self.add_typed_input('B', PORT_NUMBER)
        self.add_typed_output('Result', PORT_BOOL)
        self.add_combo_menu('operation', 'Op', items=['==', '!=', '>', '<', '>=', '<='])
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        op = self.get_property('operation')
        lua_op = '~=' if op == '!=' else op
        a  = compiler.resolve_port_value(self.get_input('A'), ctx, fallback='0')
        b  = compiler.resolve_port_value(self.get_input('B'), ctx, fallback='0')
        return f'({a} {lua_op} {b})'
        
class CompareStringsNode(BlueprintNode):
    __identifier__ = 'gmod.logic'
    NODE_NAME = 'Compare Strings'
    def __init__(self):
        super().__init__()
        self.add_typed_input('A', PORT_STRING)
        self.add_typed_input('B', PORT_STRING)
        self.add_typed_output('Result', PORT_BOOL)
        self.add_combo_menu('operation', 'Op', items=['==', '!='])
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        op = self.get_property('operation')
        lua_op = '==' if op == '== ' else '~='
        a = compiler.resolve_port_value(self.get_input('A'), ctx, fallback='""')
        b = compiler.resolve_port_value(self.get_input('B'), ctx, fallback='""')
        return f'({a} {lua_op} {b})'

class StringContainsNode(BlueprintNode):
    __identifier__ = 'gmod.logic'
    NODE_NAME = 'String Contains'
    def __init__(self):
        super().__init__()
        self.add_typed_input('Substring (A)', PORT_STRING)
        self.add_typed_input('String (B)', PORT_STRING)
        self.add_typed_output('Result', PORT_BOOL)
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        sub = compiler.resolve_port_value(self.get_input('Substring (A)'), ctx, fallback='""')
        string = compiler.resolve_port_value(self.get_input('String (B)'), ctx, fallback='""')
        return f'(string.find({string}, {sub}, 1, true) ~= nil)'

class MathOpNode(BlueprintNode):
    __identifier__ = 'gmod.logic'
    NODE_NAME = 'Math Operator'
    def __init__(self):
        super().__init__()
        self.add_typed_input('A', PORT_NUMBER)
        self.add_typed_input('B', PORT_NUMBER)
        self.add_typed_output('Result', PORT_NUMBER)
        self.add_combo_menu('operation', 'Op', items=['+', '-', '*', '/', '%'])
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        op = self.get_property('operation')
        a  = compiler.resolve_port_value(self.get_input('A'), ctx, fallback='0')
        b  = compiler.resolve_port_value(self.get_input('B'), ctx, fallback='0')
        return f'({a} {op} {b})'

class RandomNumberNode(BlueprintNode):
    __identifier__ = 'gmod.logic'
    NODE_NAME = 'Random Number'
    def __init__(self):
        super().__init__()
        self.add_typed_input('Min', PORT_NUMBER)
        self.add_typed_input('Max', PORT_NUMBER)
        self.add_typed_output('Result', PORT_NUMBER)
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        mn = compiler.resolve_port_value(self.get_input('Min'), ctx, fallback='1')
        mx = compiler.resolve_port_value(self.get_input('Max'), ctx, fallback='100')
        return f'math.random({mn}, {mx})'

class VectorDistanceNode(BlueprintNode):
    __identifier__ = 'gmod.logic'
    NODE_NAME = 'Vector Distance'
    def __init__(self):
        super().__init__()
        self.add_typed_input('A', PORT_VECTOR)
        self.add_typed_input('B', PORT_VECTOR)
        self.add_typed_output('Distance', PORT_NUMBER)
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        a = compiler.resolve_port_value(self.get_input('A'), ctx, fallback='Vector(0,0,0)')
        b = compiler.resolve_port_value(self.get_input('B'), ctx, fallback='Vector(0,0,0)')
        return f'({a}):Distance({b})'

class CreateVectorNode(BlueprintNode):
    __identifier__ = 'gmod.logic'
    NODE_NAME = 'Create Vector'
    def __init__(self):
        super().__init__()
        self.add_typed_input('X', PORT_NUMBER); self.add_typed_input('Y', PORT_NUMBER); self.add_typed_input('Z', PORT_NUMBER)
        self.add_typed_output('Vector', PORT_VECTOR)
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        x = compiler.resolve_port_value(self.get_input('X'), ctx, fallback='0')
        y = compiler.resolve_port_value(self.get_input('Y'), ctx, fallback='0')
        z = compiler.resolve_port_value(self.get_input('Z'), ctx, fallback='0')
        return f'Vector({x}, {y}, {z})'

class BreakVectorNode(BlueprintNode):
    __identifier__ = 'gmod.logic'
    NODE_NAME = 'Break Vector'
    def __init__(self):
        super().__init__()
        self.add_typed_input('Vector', PORT_VECTOR)
        self.add_typed_output('X', PORT_NUMBER); self.add_typed_output('Y', PORT_NUMBER); self.add_typed_output('Z', PORT_NUMBER)
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        vec = compiler.resolve_port_value(self.get_input('Vector'), ctx, fallback='Vector(0,0,0)')
        return f'({vec}).{port_name.lower()}'

class StringConcatNode(BlueprintNode):
    __identifier__ = 'gmod.logic'
    NODE_NAME = 'Concatenate Strings'
    def __init__(self):
        super().__init__()
        self.add_typed_input('A', PORT_STRING); self.add_typed_input('B', PORT_STRING)
        self.add_typed_output('Result', PORT_STRING)
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        a = compiler.resolve_port_value(self.get_input('A'), ctx, fallback='""')
        b = compiler.resolve_port_value(self.get_input('B'), ctx, fallback='""')
        return f'({a} .. {b})'

class BranchNode(BlueprintNode):
    __identifier__ = 'gmod.logic'
    NODE_NAME = 'Branch'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Condition", PORT_BOOL)
        self.add_exec_output("True"); self.add_exec_output("False")  
    def compile_node(self, compiler, ctx) -> str:
        cond = compiler.resolve_port_value(self.get_input('Condition'), ctx, fallback='false')
        lua = f'{ctx.indent}if {cond} then\n'
        lua += compiler.compile_exec_chain(self.get_output('True'), ctx.indented())
        lua += f'{ctx.indent}else\n'
        lua += compiler.compile_exec_chain(self.get_output('False'), ctx.indented())
        lua += f'{ctx.indent}end\n'
        return lua

class DelayNode(BlueprintNode):
    __identifier__ = 'gmod.logic'
    NODE_NAME = 'Delay'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_text_input('time', 'Duration (s)', text='1.0')
        self.add_exec_output("Then")
    def compile_node(self, compiler, ctx) -> str:
        duration = self.get_property('time') or '1.0'
        lua = f'{ctx.indent}timer.Simple({duration}, function()\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx.indented())
        lua += f'{ctx.indent}end)\n'
        return lua


# ==================== 4. КАТЕГОРИЯ: ДЕЙСТВИЯ (ACTIONS) ====================

class PrintChatNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Print Chat Message'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Target (Player)", PORT_PLAYER); self.add_typed_input("Message", PORT_STRING)
        self.add_exec_output("Then")
    def compile_node(self, compiler, ctx) -> str:
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        msg = compiler.resolve_port_value(self.get_input('Message'), ctx, fallback='""')
        if tgt == 'nil': lua = f'{ctx.indent}PrintMessage(HUD_PRINTTALK, {msg})\n'
        else:
            lua = f'{ctx.indent}if IsValid({tgt}) and {tgt}:IsPlayer() then\n'
            lua += f'{ctx.indent}    {tgt}:ChatPrint({msg})\n'
            lua += f'{ctx.indent}end\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua

class PrintHintNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Print Hint'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Target (Player)", PORT_PLAYER)
        self.add_typed_input("Message", PORT_STRING)
        self.add_exec_output("Then")
        
    def compile_node(self, compiler, ctx) -> str:
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        msg = compiler.resolve_port_value(self.get_input('Message'), ctx, fallback='""')
        lua = f'{ctx.indent}if IsValid({tgt}) and {tgt}:IsPlayer() then\n'
        lua += f'{ctx.indent}    {tgt}:PrintMessage(HUD_PRINTCENTER, {msg})\n'
        lua += f'{ctx.indent}end\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua

class SetHealthNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Set Health'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Target (Player)", PORT_PLAYER); self.add_typed_input("Health", PORT_NUMBER)
        self.add_exec_output("Then")
    def compile_node(self, compiler, ctx) -> str:
        hp = compiler.resolve_port_value(self.get_input('Health'), ctx, fallback='100')
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        lua = f'{ctx.indent}if IsValid({tgt}) then {tgt}:SetHealth(tonumber({hp}) or 100) end\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua

class KickPlayerNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Kick Player'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Target (Player)", PORT_PLAYER); self.add_typed_input("Reason", PORT_STRING)
        self.add_exec_output("Then")
    def compile_node(self, compiler, ctx) -> str:
        reason = compiler.resolve_port_value(self.get_input('Reason'), ctx, fallback='"Kicked"')
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        lua = f'{ctx.indent}if IsValid({tgt}) then {tgt}:Kick({reason}) end\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua

class GetPlayerNameNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Get Player Name'
    def __init__(self):
        super().__init__()
        self.add_typed_input("Target (Player)", PORT_PLAYER)
        self.add_typed_output("Name", PORT_STRING)
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        return f'(IsValid({tgt}) and {tgt}:Name() or "Unknown")'

class GetPlayerPosNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Get Player Position'
    def __init__(self):
        super().__init__()
        self.add_typed_input("Target (Player)", PORT_PLAYER)
        self.add_typed_output("Position", PORT_VECTOR)
    def resolve_port_output_value(self, port_name: str, compiler, ctx) -> str:
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        return f'(IsValid({tgt}) and {tgt}:GetPos() or Vector(0,0,0))'

class SetPlayerPosNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Set Player Position'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Target (Player)", PORT_PLAYER); self.add_typed_input("Position", PORT_VECTOR)
        self.add_exec_output("Then")
    def compile_node(self, compiler, ctx) -> str:
        pos = compiler.resolve_port_value(self.get_input('Position'), ctx, fallback='Vector(0,0,0)')
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        lua = f'{ctx.indent}if IsValid({tgt}) then {tgt}:SetPos({pos}) end\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua

class SetPlayerVelocityNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Set Player Velocity'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Target (Player)", PORT_PLAYER); self.add_typed_input("Velocity (Vector)", PORT_VECTOR)
        self.add_exec_output("Then")
    def compile_node(self, compiler, ctx) -> str:
        vel = compiler.resolve_port_value(self.get_input('Velocity (Vector)'), ctx, fallback='Vector(0,0,0)')
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        lua = f'{ctx.indent}if IsValid({tgt}) and {tgt}:IsPlayer() then {tgt}:SetVelocity({vel}) end\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua

class IgnitePlayerNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Ignite Player'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Target (Player)", PORT_PLAYER); self.add_typed_input("Duration", PORT_NUMBER)
        self.add_exec_output("Then")
    def compile_node(self, compiler, ctx) -> str:
        dur = compiler.resolve_port_value(self.get_input('Duration'), ctx, fallback='5')
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        lua = f'{ctx.indent}if IsValid({tgt}) then {tgt}:Ignite(tonumber({dur}) or 5) end\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua

class FreezePlayerNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Freeze Player'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Target (Player)", PORT_PLAYER); self.add_typed_input("Freeze", PORT_BOOL)
        self.add_exec_output("Then")
    def compile_node(self, compiler, ctx) -> str:
        frz = compiler.resolve_port_value(self.get_input('Freeze'), ctx, fallback='false')
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        lua = f'{ctx.indent}if IsValid({tgt}) and {tgt}:IsPlayer() then {tgt}:Freeze({frz}) end\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua

class SetPlayerScaleNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Set Player Scale'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Target (Player)", PORT_PLAYER); self.add_typed_input("Scale", PORT_NUMBER)
        self.add_exec_output("Then")
    def compile_node(self, compiler, ctx) -> str:
        scale = compiler.resolve_port_value(self.get_input('Scale'), ctx, fallback='1.0')
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        lua = f'{ctx.indent}if IsValid({tgt}) and {tgt}:IsPlayer() then {tgt}:SetModelScale(tonumber({scale}) or 1, 0) end\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua

class GodModeNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'God Mode'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Target (Player)", PORT_PLAYER); self.add_typed_input("Enable", PORT_BOOL)
        self.add_exec_output("Then")
    def compile_node(self, compiler, ctx) -> str:
        enable = compiler.resolve_port_value(self.get_input('Enable'), ctx, fallback='false')
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        lua = f'{ctx.indent}if IsValid({tgt}) and {tgt}:IsPlayer() then\n'
        lua += f'{ctx.indent}    if {enable} then {tgt}:GodEnable() else {tgt}:GodDisable() end\n'
        lua += f'{ctx.indent}end\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua

class StripWeaponsNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Strip Weapons'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Target (Player)", PORT_PLAYER)
        self.add_exec_output("Then")
    def compile_node(self, compiler, ctx) -> str:
        tgt = compiler.resolve_port_value(self.get_input('Target (Player)'), ctx, fallback='nil')
        lua = f'{ctx.indent}if IsValid({tgt}) and {tgt}:IsPlayer() then {tgt}:StripWeapons() end\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua

class SpawnExplosionNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Spawn Explosion'
    def __init__(self):
        super().__init__()
        self.add_exec_input("Execute")
        self.add_typed_input("Position", PORT_VECTOR); self.add_typed_input("Damage", PORT_NUMBER); self.add_typed_input("Radius", PORT_NUMBER)
        self.add_exec_output("Then")
    def compile_node(self, compiler, ctx) -> str:
        pos = compiler.resolve_port_value(self.get_input('Position'), ctx, fallback='Vector(0,0,0)')
        dmg = compiler.resolve_port_value(self.get_input('Damage'), ctx, fallback='100')
        rad = compiler.resolve_port_value(self.get_input('Radius'), ctx, fallback='200')
        
        lua = f'{ctx.indent}local explode = ents.Create("env_explosion")\n'
        lua += f'{ctx.indent}if IsValid(explode) then\n'
        lua += f'{ctx.indent}    explode:SetPos({pos})\n'
        lua += f'{ctx.indent}    explode:SetKeyValue("iMagnitude", tostring({dmg}))\n'
        lua += f'{ctx.indent}    explode:SetKeyValue("iRadiusOverride", tostring({rad}))\n'
        lua += f'{ctx.indent}    explode:Spawn()\n'
        lua += f'{ctx.indent}    explode:Fire("Explode", "", 0)\n'
        lua += f'{ctx.indent}end\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua

class ScreenShakeNode(BlueprintNode):
    __identifier__ = 'gmod.actions'
    NODE_NAME = 'Screen Shake'
    def __init__(self):
        super().__init__()
        self.add_exec_input()
        self.add_typed_input('Position', PORT_VECTOR)
        self.add_typed_input('Amplitude', PORT_NUMBER)
        self.add_typed_input('Frequency', PORT_NUMBER)
        self.add_typed_input('Duration', PORT_NUMBER)
        self.add_typed_input('Radius', PORT_NUMBER)
        self.add_exec_output('Then')
        
    def compile_node(self, compiler, ctx) -> str:
        pos = compiler.resolve_port_value(self.get_input('Position'), ctx, fallback='Vector(0,0,0)')
        amp = compiler.resolve_port_value(self.get_input('Amplitude'), ctx, fallback='10')   
        frq = compiler.resolve_port_value(self.get_input('Frequency'), ctx, fallback='40')   
        dur = compiler.resolve_port_value(self.get_input('Duration'), ctx, fallback='1.5')  
        rad = compiler.resolve_port_value(self.get_input('Radius'), ctx, fallback='1500')   
        
        lua = f'{ctx.indent}util.ScreenShake({pos}, {amp}, {frq}, {dur}, {rad})\n'
        lua += compiler.compile_exec_chain(self.get_output('Then'), ctx)
        return lua


# ==================== ОБЩИЙ СПИСОК КЛАССОВ ДЛЯ ИМПОРТА ====================

ALL_NODE_CLASSES = [
    PlayerSpawnNode, PlayerDeathNode, PlayerSayNode,
    NumberValueNode, BoolValueNode, StringValueNode, VectorValueNode,
    SetVariableNode, GetVariableNode,                                      # <-- НОДЫ ДОБАВЛЕНЫ СЮДА
    CompareNumbersNode, MathOpNode, RandomNumberNode, VectorDistanceNode, 
    CreateVectorNode, BreakVectorNode, StringConcatNode, BranchNode, DelayNode,
    PrintChatNode, PrintHintNode, SetHealthNode, KickPlayerNode, GetPlayerNameNode,
    GetPlayerPosNode, SetPlayerPosNode, SetPlayerVelocityNode, IgnitePlayerNode,
    FreezePlayerNode, SetPlayerScaleNode, GodModeNode, StripWeaponsNode, SpawnExplosionNode, ScreenShakeNode,
    CompareStringsNode, StringContainsNode
]