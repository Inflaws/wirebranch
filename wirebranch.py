import os
import sys
import subprocess
import customtkinter as ctk
from tkinter import messagebox, filedialog

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ==================== ШАБЛОН SWEP ====================
SWEP_TEMPLATE = """-- Сгенерировано через WireBranch
SWEP.PrintName    = "{name}"
SWEP.Author       = "{author}"
SWEP.Instructions = "Создано через WireBranch."
SWEP.Spawnable    = true
SWEP.AdminSpawnable = true
SWEP.Base         = "{base}"
SWEP.Category     = "{category}"
SWEP.ViewModel    = "{viewmodel}"
SWEP.WorldModel   = "{worldmodel}"
SWEP.UseHands     = true
SWEP.HoldType     = "{holdtype}"

-- Основная атака
SWEP.Primary.Damage      = {damage}
SWEP.Primary.NumShots    = {num_shots}
SWEP.Primary.Delay       = {delay}
SWEP.Primary.Cone        = {cone}
SWEP.Primary.Recoil      = {recoil}
SWEP.Primary.TakeAmmo    = 1
SWEP.Primary.ClipSize    = {clip}
SWEP.Primary.DefaultClip = {clip}
SWEP.Primary.Ammo        = "{ammo}"
SWEP.Primary.Automatic   = {auto}
SWEP.Primary.Sound       = Sound("{sound}")

-- Настройки Zoom (ПКМ)
SWEP.Secondary.ClipSize    = -1
SWEP.Secondary.DefaultClip = -1
SWEP.Secondary.Automatic   = false
SWEP.Secondary.Ammo        = "none"
SWEP.EnableZoom            = {enable_zoom}

function SWEP:Initialize()
    self:SetHoldType(self.HoldType)
end

function SWEP:PrimaryAttack()
    if not self:CanPrimaryAttack() then return end
    local bullet = {}
    bullet.Num       = self.Primary.NumShots
    bullet.Src       = self.Owner:GetShootPos()
    bullet.Dir       = self.Owner:GetAimVector()
    bullet.Spread    = Vector(self.Primary.Cone, self.Primary.Cone, 0)
    bullet.Tracer    = 1
    bullet.Force     = 1
    bullet.Damage    = self.Primary.Damage
    bullet.AmmoType  = self.Primary.Ammo
    self.Owner:FireBullets(bullet)
    self:EmitSound(self.Primary.Sound)
    self:ShootEffects()

    local recoil = self.Primary.Recoil
    self.Owner:ViewPunch(Angle(-recoil, math.Rand(-recoil/2, recoil/2), 0))

    self:TakePrimaryAmmo(self.Primary.TakeAmmo)
    self:SetNextPrimaryFire(CurTime() + self.Primary.Delay)
end

function SWEP:SecondaryAttack()
    if not self.EnableZoom then return end
    if SERVER then
        if self.Owner:GetFOV() == 90 or self.Owner:GetFOV() == 0 then
            self.Owner:SetFOV(45, 0.2)
        else
            self.Owner:SetFOV(0, 0.2)
        end
    end
end

function SWEP:Holster()
    if SERVER and IsValid(self.Owner) then
        self.Owner:SetFOV(0, 0)
    end
    return true
end
"""

# ==================== ОКНО ГЕНЕРАТОРА ОРУЖИЯ ====================
class SWEPGeneratorWindow(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("WireBranch - SWEP Generator")
        self.geometry("620x980")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        self.label_title = ctk.CTkLabel(self, text="🔫 SWEP Generator", font=ctk.CTkFont(size=24, weight="bold"))
        self.label_title.pack(pady=15)

        self.gmod_path_frame = ctk.CTkFrame(self)
        self.gmod_path_frame.pack(pady=8, padx=20, fill="x")
        self.entry_gmod_path = ctk.CTkEntry(self.gmod_path_frame, placeholder_text="Путь к папке Garry's Mod")
        self.entry_gmod_path.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=10)
        self.btn_browse = ctk.CTkButton(self.gmod_path_frame, text="Обзор", width=90, command=self.browse_gmod_path)
        self.btn_browse.pack(side="right", padx=(5, 10), pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=580, height=680)
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.create_section_label("1. Основная информация")
        self.create_labeled_input("Название оружия (PrintName):", "entry_name", "Например: Wire AK-47")
        self.create_labeled_input("Автор (Author):", "entry_author", "Твой ник")
        self.entry_author.insert(0, "WireBranch User")

        self.create_section_label("2. Базовые настройки SWEP")
        self.create_labeled_combo("SWEP.Base (Базовый класс):", 
            ["weapon_base", "weapon_pistol", "weapon_smg1", "weapon_ar2", "weapon_shotgun", "weapon_crossbow", "weapon_357"], 
            "combo_base", "weapon_base")
        
        self.create_labeled_combo("SWEP.HoldType (Хват):", 
            ["ar2", "pistol", "shotgun", "smg", "revolver", "rpg", "melee", "knife", "camera"], 
            "combo_holdtype", "ar2")

        self.create_section_label("3. Характеристики стрельбы")
        self.create_labeled_input("Урон (Damage):", "entry_damage", "12")
        self.entry_damage.insert(0, "12")
        self.create_labeled_input("Кол-во пуль (NumShots):", "entry_num_shots", "1 (винтовка), 6-12 (дробовик)")
        self.entry_num_shots.insert(0, "1")
        self.create_labeled_input("Задержка (Delay, сек):", "entry_delay", "0.5")
        self.entry_delay.insert(0, "0.5")
        self.create_labeled_input("Разброс (Cone):", "entry_cone", "0.02")
        self.entry_cone.insert(0, "0.02")
        self.create_labeled_input("Отдача (Recoil):", "entry_recoil", "1.0")
        self.entry_recoil.insert(0, "1.0")

        self.create_section_label("4. Боеприпасы и модель")
        self.create_labeled_input("Магазин (Clip Size):", "entry_clip", "30")
        self.entry_clip.insert(0, "30")
        self.create_labeled_combo("Тип патронов (Ammo):", 
            ["AR2", "Pistol", "SMG1", "Buckshot", "357"], "combo_ammo", "AR2")
        self.create_labeled_combo("Звук выстрела:", 
            ["Weapon_AR2.Single", "Weapon_Pistol.Single", "Weapon_SMG1.Single", "Weapon_Shotgun.Single", "Weapon_357.Single"], 
            "combo_sound", "Weapon_AR2.Single")
        self.create_labeled_combo("ViewModel:", 
            ["models/weapons/c_ar2.mdl", "models/weapons/c_smg1.mdl", "models/weapons/c_shotgun.mdl", "models/weapons/c_pistol.mdl", "models/weapons/c_357.mdl"], 
            "combo_viewmodel", "models/weapons/c_ar2.mdl")
        self.create_labeled_combo("WorldModel:", 
            ["models/weapons/w_ar2.mdl", "models/weapons/w_smg1.mdl", "models/weapons/w_shotgun.mdl", "models/weapons/w_pistol.mdl"], 
            "combo_worldmodel", "models/weapons/w_ar2.mdl")

        self.create_section_label("5. Дополнительно")
        self.create_labeled_combo("Категория в Q-меню:", 
            ["Rifles", "Pistols", "Shotguns", "SMGs", "Other", "WireBranch"], "combo_category", "Rifles")

        self.switch_auto = ctk.CTkSwitch(self.scroll_frame, text="Автоматический огонь")
        self.switch_auto.select()
        self.switch_auto.pack(anchor="w", padx=20, pady=12)

        self.switch_zoom = ctk.CTkSwitch(self.scroll_frame, text="Прицеливание (Zoom на ПКМ)")
        self.switch_zoom.select()
        self.switch_zoom.pack(anchor="w", padx=20, pady=12)

        self.btn_generate = ctk.CTkButton(self, text="⚡ Generate & Deploy", 
                                          command=self.generate_and_enable,
                                          font=ctk.CTkFont(size=16, weight="bold"), 
                                          fg_color="#2b712b", height=45)
        self.btn_generate.pack(pady=20, padx=20, fill="x")

        self.autodetect_gmod()

    def create_section_label(self, text):
        lbl = ctk.CTkLabel(self.scroll_frame, text=text, font=ctk.CTkFont(size=15, weight="bold"), text_color="#1f538d")
        lbl.pack(anchor="w", padx=20, pady=(18, 6))

    def create_labeled_input(self, label_text, attr_name, placeholder):
        lbl = ctk.CTkLabel(self.scroll_frame, text=label_text, font=ctk.CTkFont(size=13))  
        lbl.pack(anchor="w", padx=20, pady=(6, 2))
        entry = ctk.CTkEntry(self.scroll_frame, placeholder_text=placeholder, height=32)
        entry.pack(fill="x", padx=20, pady=(0, 8))
        setattr(self, attr_name, entry)

    def create_labeled_combo(self, label_text, values, attr_name, default):
        lbl = ctk.CTkLabel(self.scroll_frame, text=label_text, font=ctk.CTkFont(size=13))
        lbl.pack(anchor="w", padx=20, pady=(6, 2))
        combo = ctk.CTkComboBox(self.scroll_frame, values=values, height=32)
        combo.set(default)
        combo.pack(fill="x", padx=20, pady=(0, 8))
        setattr(self, attr_name, combo)

    def browse_gmod_path(self):
        directory = filedialog.askdirectory(title="Выберите корневую папку Garry's Mod")
        if directory:
            self.entry_gmod_path.delete(0, "end")
            self.entry_gmod_path.insert(0, directory)

    def autodetect_gmod(self):
        possible_paths = [
            r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod",
            r"C:\Program Files\Steam\steamapps\common\GarrysMod",
            r"D:\SteamLibrary\steamapps\common\GarrysMod",
            r"E:\SteamLibrary\steamapps\common\GarrysMod",
            r"F:\SteamLibrary\steamapps\common\GarrysMod",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                self.entry_gmod_path.delete(0, "end")
                self.entry_gmod_path.insert(0, path)
                return

    def generate_and_enable(self):
        gmod_base_path = self.entry_gmod_path.get().strip()
        weapon_name = self.entry_name.get().strip()
        
        if not gmod_base_path or not os.path.exists(gmod_base_path):
            messagebox.showerror("Ошибка", "Путь к Garry's Mod не найден!")
            return
        if not weapon_name:
            messagebox.showerror("Ошибка", "Введите название оружия!")
            return

        try:
            damage_val = int(self.entry_damage.get().strip())
            num_shots_val = int(self.entry_num_shots.get().strip())
            clip_val = int(self.entry_clip.get().strip())
            delay_val = float(self.entry_delay.get().strip())
            cone_val = float(self.entry_cone.get().strip())
            recoil_val = float(self.entry_recoil.get().strip())
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте числовые поля!")
            return

        gmod_lua_path = os.path.join(gmod_base_path, "garrysmod", "addons", "wirebranch_autogen", "lua", "weapons")
        os.makedirs(gmod_lua_path, exist_ok=True)

        file_id = weapon_name.lower().replace(" ", "_").replace("-", "_")
        final_file_path = os.path.join(gmod_lua_path, f"{file_id}.lua")

        try:
            lua_code = SWEP_TEMPLATE.format(
                name=weapon_name,
                author=self.entry_author.get().strip() or "WireBranch User",
                base=self.combo_base.get(),
                category=self.combo_category.get(),
                viewmodel=self.combo_viewmodel.get(),
                worldmodel=self.combo_worldmodel.get(),
                holdtype=self.combo_holdtype.get(),
                damage=damage_val,
                num_shots=num_shots_val,
                delay=delay_val,
                cone=cone_val,
                recoil=recoil_val,
                clip=clip_val,
                ammo=self.combo_ammo.get(),
                auto="true" if self.switch_auto.get() else "false",
                sound=self.combo_sound.get(),
                enable_zoom="true" if self.switch_zoom.get() else "false",
            )

            with open(final_file_path, "w", encoding="utf-8") as f:
                f.write(lua_code)

            messagebox.showinfo("Успех!", f"Оружие создано!\n\nПуть: {final_file_path}\n\nНе забудь ввести в консоль GMod: spawnmenu_reload")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{e}")


# ==================== ГЛАВНЫЙ ЛАУНЧЕР ====================
class WireBranchLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WireBranch Hub")
        self.geometry("420x320")
        self.resizable(False, False)
        self.center_window()

        self.header = ctk.CTkLabel(self, text="🔷 WireBranch Suite", font=ctk.CTkFont(size=28, weight="bold"))
        self.header.pack(pady=(30, 10))
        
        self.subheader = ctk.CTkLabel(self, text="Выберите инструмент для разработки GMod аддонов", font=ctk.CTkFont(size=14), text_color="#888888")
        self.subheader.pack(pady=(0, 30))

        self.btn_swep = ctk.CTkButton(self, text="🔫 Генератор оружия (Template)", font=ctk.CTkFont(size=16, weight="bold"), 
                                      height=50, command=self.open_swep_generator)
        self.btn_swep.pack(pady=10, padx=40, fill="x")

        self.btn_blueprint = ctk.CTkButton(self, text="🔷 Blueprint Editor (Nodes)", font=ctk.CTkFont(size=16, weight="bold"), 
                                           height=50, command=self.open_blueprint_editor,
                                           fg_color="#2b5f9e")
        self.btn_blueprint.pack(pady=10, padx=40, fill="x")

        self.footer = ctk.CTkLabel(self, text="Powered by Python & GMod GLua", font=ctk.CTkFont(size=11), text_color="#555555")
        self.footer.pack(side="bottom", pady=15)

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def open_swep_generator(self):
        # Проверяем, не открыто ли уже окно
        if hasattr(self, 'swep_window') and self.swep_window.winfo_exists():
            self.swep_window.lift()
            self.swep_window.focus_set()
            return
        self.swep_window = SWEPGeneratorWindow(self)

    def open_blueprint_editor(self):
        try:
            editor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blueprints_editor.py")
            if not os.path.exists(editor_path):
                messagebox.showerror("Ошибка", "Файл 'blueprints_editor.py' не найден в папке проекта!")
                return
            
            # Запускаем в отдельном процессе, чтобы избежать конфликта Tkinter/PyQt5 mainloop
            subprocess.Popen([sys.executable, editor_path])
        except Exception as e:
            messagebox.showerror("Ошибка запуска", f"Не удалось открыть Blueprint Editor:\n{e}")


if __name__ == "__main__":
    app = WireBranchLauncher()
    app.mainloop()