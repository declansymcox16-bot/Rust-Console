import asyncio
import json
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import websockets
import os
from datetime import datetime

# CONFIGURATION
RCON_IP = "192.168.0.202"
RCON_PORT = 5678
#leave blank if RCON is not Password protected
RCON_PASSWORD = ""
LOG_FILE_PATH = "server_console_history.txt"
BAN_FILE = "ban_registry.json"

class RustDashboardApp:
    def __init__(self, root):
        self.root = root
        #Titel here :) small dark 
        self.root.title("Dec's Server - RUST Absolute Master Administration Hub")
        self.root.geometry("1500x850")
        self.root.configure(bg="#2b2d31")  # Dark theme

        self.websocket = None
        self.loop = None

        # Grid Layout Setup
        self.root.grid_columnconfigure(0, weight=1)  # Left panel (Stats & Moderation)
        self.root.grid_columnconfigure(1, weight=2)  # Middle panel (Console)
        self.root.grid_columnconfigure(2, weight=1)  # Right panel (Scrollable Macros)
        self.root.grid_rowconfigure(0, weight=1)

        # ================= LEFT PANEL (STATS & PLAYER MODERATION) =================
        self.left_panel = tk.Frame(self.root, bg="#1e1f22", width=320, padx=15, pady=15)
        self.left_panel.grid(row=0, column=0, sticky="nsew")
        self.left_panel.grid_propagate(False)
        #Title Large
        tk.Label(self.left_panel, text="R.U.S.T", font=("Courier New", 24, "bold"), fg="#e05a47", bg="#1e1f22").pack(anchor="w")
        tk.Label(self.left_panel, text="Dec's Absolute Hub", font=("Arial", 9, "italic"), fg="#949ba4", bg="#1e1f22").pack(anchor="w", pady=(0, 10))

        # Core Metrics Display
        self.lbl_status = self.create_stat_widget("Core Status", "OFFLINE", "#e05a47")
        self.lbl_players = self.create_stat_widget("Players Online", "0 / 9999", "#5865f2")
        self.lbl_fps = self.create_stat_widget("Engine Speed", "0 FPS", "#23a55a")
        self.lbl_memory = self.create_stat_widget("RAM Allocation", "0.00 GB", "#ffffff")

        # --- MODULE 1: LIVE PLAYER MODERATION PANEL & UNDO LOG ---
        tk.Label(self.left_panel, text="PLAYER MODERATION PANEL", font=("Arial", 8, "bold"), fg="#949ba4", bg="#1e1f22").pack(anchor="w", pady=(15, 2))
        
        mod_frame = tk.Frame(self.left_panel, bg="#2b2d31", padx=10, pady=10)
        mod_frame.pack(fill="x", pady=5)
        
        tk.Label(mod_frame, text="Target Player Name / SteamID:", font=("Arial", 8), fg="#dbdee1", bg="#2b2d31").pack(anchor="w")
        self.player_entry = tk.Entry(mod_frame, font=("Arial", 10), bg="#383a40", fg="white", bd=0, highlightthickness=1, highlightbackground="#1e1f22")
        self.player_entry.pack(fill="x", pady=5, ipady=4)

        # Mod Action Grid Layout
        btn_grid = tk.Frame(mod_frame, bg="#2b2d31")
        btn_grid.pack(fill="x", pady=5)
        btn_grid.grid_columnconfigure(0, weight=1)
        btn_grid.grid_columnconfigure(1, weight=1)

        tk.Button(btn_grid, text="🥾 KICK", font=("Arial", 8, "bold"), bg="#faa61a", fg="white", bd=0, pady=6, command=lambda: self.run_mod_action("kick")).grid(row=0, column=0, sticky="ew", padx=(0,2), pady=2)
        tk.Button(btn_grid, text="🔨 BAN", font=("Arial", 8, "bold"), bg="#e05a47", fg="white", bd=0, pady=6, command=lambda: self.run_mod_action("ban")).grid(row=0, column=1, sticky="ew", padx=(2,0), pady=2)
        tk.Button(btn_grid, text="🔇 MUTE", font=("Arial", 8, "bold"), bg="#4f545c", fg="white", bd=0, pady=6, command=lambda: self.run_mod_action("mute")).grid(row=1, column=0, sticky="ew", padx=(0,2), pady=2)
        tk.Button(btn_grid, text="🔊 UNMUTE", font=("Arial", 8, "bold"), bg="#23a55a", fg="white", bd=0, pady=6, command=lambda: self.run_mod_action("unmute")).grid(row=1, column=1, sticky="ew", padx=(2,0), pady=2)

        # Dynamic Undo Tracking Box
        tk.Label(self.left_panel, text="RECENT ACTIONS (CLICK TO UNDO)", font=("Arial", 8, "bold"), fg="#949ba4", bg="#1e1f22").pack(anchor="w", pady=(10, 2))
        
        undo_frame = tk.Frame(self.left_panel, bg="#2b2d31", padx=5, pady=5)
        undo_frame.pack(fill="x", pady=5)
        
        self.undo_listbox = tk.Listbox(undo_frame, font=("Courier New", 9), bg="#1e1f22", fg="#dbdee1", highlightthickness=0, bd=0, height=4, selectbackground="#383a40")
        self.undo_listbox.pack(fill="x", side="left", expand=True)
        self.undo_listbox.bind("<Double-Button-1>", lambda event: self.trigger_undo_action())
        self.action_history = [] 

        # --- MODULE 2: PERMANENT BAN REGISTRY & DIRECT UNBAN PORTAL ---
        tk.Label(self.left_panel, text="GLOBAL BAN REGISTRY (QUICK UNBAN)", font=("Arial", 8, "bold"), fg="#949ba4", bg="#1e1f22").pack(anchor="w", pady=(10, 2))
        
        ban_registry_frame = tk.Frame(self.left_panel, bg="#2b2d31", padx=10, pady=10)
        ban_registry_frame.pack(fill="x", pady=5)
        
        self.ban_registry_listbox = tk.Listbox(ban_registry_frame, font=("Courier New", 9), bg="#1e1f22", fg="#dbdee1", highlightthickness=0, bd=0, height=4, selectbackground="#383a40")
        self.ban_registry_listbox.pack(fill="x", pady=(0, 5))
        self.ban_registry_listbox.bind("<Double-Button-1>", lambda event: self.trigger_registry_unban())
        
        unban_input_frame = tk.Frame(ban_registry_frame, bg="#2b2d31")
        unban_input_frame.pack(fill="x")
        unban_input_frame.grid_columnconfigure(0, weight=2)
        unban_input_frame.grid_columnconfigure(1, weight=1)
        
        self.unban_entry = tk.Entry(unban_input_frame, font=("Arial", 9), bg="#383a40", fg="white", bd=0, highlightthickness=1, highlightbackground="#1e1f22")
        self.unban_entry.grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 4))
        
        tk.Button(unban_input_frame, text="🔓 UNBAN", font=("Arial", 8, "bold"), bg="#23a55a", fg="white", bd=0, command=self.run_manual_unban).grid(row=0, column=1, sticky="nsew")
        self.ban_registry_history = []
        self.load_bans()

        # Core Options Buttons
        tk.Label(self.left_panel, text="CORE FUNCTIONS", font=("Arial", 8, "bold"), fg="#949ba4", bg="#1e1f22").pack(anchor="w", pady=(10, 2))
        self.create_admin_button("💾 Force Backup Save", lambda: self.send_rcon_cmd("server.save"), "#23a55a")
        self.create_admin_button("📢 Broadcast Notification", self.prompt_broadcast, "#5865f2")
        
        self.auto_save_var = tk.BooleanVar(value=True)
        self.chk_autosave = tk.Checkbutton(self.left_panel, text="Auto-Save World (5 min)", variable=self.auto_save_var, onvalue=True, offvalue=False, bg="#1e1f22", fg="#dbdee1", selectcolor="#2b2d31", activebackground="#1e1f22", activeforeground="white", font=("Arial", 10))
        self.chk_autosave.pack(anchor="w", pady=5)
        # --- AUTO UPDATER CONTROLLER BUTTON ---
        self.run_updater = False  # Hidden setting to track status
        self.btn_toggle_updater = tk.Button(
            self.left_panel, 
            text="⏸️ Pause FPS Tracking", 
            font=("Arial", 9, "bold"), 
            bg="#f0b232", 
            fg="black", 
            bd=0, 
            pady=8, 
            command=self.toggle_updater_loop
        )
        self.btn_toggle_updater.pack(fill="x", pady=4)

        # ================= MIDDLE PANEL (CONSOLE STREAM) =================
        self.middle_panel = tk.Frame(self.root, bg="#2b2d31", padx=15, pady=15)
        self.middle_panel.grid(row=0, column=1, sticky="nsew")
        self.middle_panel.grid_rowconfigure(1, weight=1)
        self.middle_panel.grid_columnconfigure(0, weight=1)

        tk.Label(self.middle_panel, text="Live Server Logging Console", font=("Arial", 12, "bold"), fg="#ffffff", bg="#2b2d31").grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.console_box = scrolledtext.ScrolledText(self.middle_panel, wrap=tk.WORD, font=("Courier New", 10), bg="#1e1f22", fg="#dbdee1", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#3f4147")
        self.console_box.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.console_box.config(state=tk.DISABLED)
        
        self.console_box.tag_config("sys", foreground="#e05a47", font=("Courier New", 10, "bold"))
        self.console_box.tag_config("cmd", foreground="#43b581", font=("Courier New", 10, "italic"))
        self.console_box.tag_config("join", foreground="#5865f2")
        self.console_box.tag_config("warn", foreground="#faa61a")

        self.input_frame = tk.Frame(self.middle_panel, bg="#2b2d31")
        self.input_frame.grid(row=2, column=0, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.cmd_entry = tk.Entry(self.input_frame, font=("Arial", 11), bg="#383a40", fg="#f2f3f5", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#1e1f22")
        self.cmd_entry.grid(row=0, column=0, sticky="ew", ipady=8, padx=(0, 10))
        self.cmd_entry.bind("<Return>", lambda event: self.submit_input_cmd())

        self.btn_send = tk.Button(self.input_frame, text="EXECUTE", font=("Arial", 9, "bold"), bg="#248046", fg="white", activebackground="#1a6535", bd=0, padx=20, command=self.submit_input_cmd)
        self.btn_send.grid(row=0, column=1, sticky="ns")

        # ================= RIGHT PANEL (SCROLLABLE MACROS SHIELD) =================
        self.right_panel = tk.Frame(self.root, bg="#1e1f22", width=360, padx=15, pady=15)
        self.right_panel.grid(row=0, column=2, sticky="nsew")
        self.right_panel.grid_propagate(False)

        canvas = tk.Canvas(self.right_panel, bg="#1e1f22", bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.right_panel, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#1e1f22")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        tk.Label(scroll_frame, text="ADMIN QUICK MACROS", font=("Arial", 12, "bold"), fg="#ffffff", bg="#1e1f22").pack(anchor="w", pady=(0, 10))

        self.create_macro_section_advanced(scroll_frame, "🧙‍♂️ Admin Character Cheats", [
            ("Enable God Mode", "god true"),
            ("Disable God Mode", "god false"),
            ("Turn On Invisible Mode", "invisible true"),
            ("Turn Off Invisible Mode", "invisible false"),
            ("Enable Infinite Ammo", "infinitenoammo true"),
            ("Disable Infinite Ammo", "infinitenoammo false"),
            ("Unlock All Blueprints", "blueprint.all")
        ])

        self.create_macro_section_advanced(scroll_frame, "⏱️ Time Control Engine", [
            ("Set to Morning (8AM)", "env.time 8"),
            ("Set to Noon (12PM)", "env.time 12"),
            ("Set to Night (11PM)", "env.time 23"),
            ("Freeze Time Progress", "env.progression false"),
            ("Resume Time Progress", "env.progression true")
        ])
        
        self.create_macro_section_advanced(scroll_frame, "🌤️ Weather Environments", [
            ("Clear Sky (Sunny)", "weather.rain 0; weather.clouds 0; weather.fog 0; weather.wind 0"),
            ("Heavy Rainstorm", "weather.rain 1; weather.clouds 0.8; weather.wind 0.4"),
            ("Thick Heavy Fog", "weather.fog 1; weather.clouds 0.6"),
            ("Blizzard (Snowstorm)", "weather.snow 1; weather.clouds 0.9"),
            ("Reset Weather to Auto", "weather.rain -1; weather.clouds -1; weather.fog -1")
        ])

        self.create_macro_section_advanced(scroll_frame, "🛡️ Server Environment Rules", [
            ("Set Server to PvE Only", "server.pve true"),
            ("Set Server to PvP Only", "server.pve false"),
            ("Enable Fall Damage", "falldamage.enabled true"),
            ("Disable Fall Damage", "falldamage.enabled false"),
            ("Enable Server Chat", "server.globalchat true"),
            ("Disable Server Chat", "server.globalchat false")
        ])

        self.create_macro_section_advanced(scroll_frame, "🚁 Global World Events", [
            ("Call Patrol Helicopter", "heli.call"),
            ("Kill Patrol Helicopter", "heli.drop"),
            ("Call Cargo Ship Engine", "cargoship.call"),
            ("Trigger Supply Airdrop", "supply.call"),
            ("Call Chinook Helicopter", "ch47helicopter.call")
        ])

        self.create_macro_section_advanced(scroll_frame, "🚗 Spawn Vehicles at Crosshair", [
            ("Spawn Minicopter", "spawn minicopter.entity"),
            ("Spawn Attack Heli", "spawn attackhelicopter"),
            ("Spawn Transport Heli", "spawn scraptransporthelicopter"),
            ("Spawn Tugboat Ship", "spawn tugboat"),
            ("Spawn Armored Horse", "spawn horse")
        ])

        self.create_macro_section_advanced(scroll_frame, "🚨 Entity Cleaners & Stability", [
            ("Kill ALL Wild Animals", "ai.killanimals"),
            ("Kill ALL Wild Scientists", "ai.killscientists"),
            ("Clear Dropped Ground Junk", "physics.dropped_count; del assets/prefabs/misc/item drop/item_drop.prefab"),
            ("Run RAM Garbage Collector", "gc.collect")
        ])

        # Start Async Pipeline Network
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.start_async_loop, args=(self.loop,), daemon=True)
        self.thread.start()
        asyncio.run_coroutine_threadsafe(self.rcon_listener(), self.loop)
        asyncio.run_coroutine_threadsafe(self.autosave_timer(), self.loop)

    def create_stat_widget(self, title, value, color):
        frame = tk.Frame(self.left_panel, bg="#2b2d31", padx=10, pady=4)
        frame.pack(fill="x", pady=4)
        tk.Label(frame, text=title.upper(), font=("Arial", 8, "bold"), fg="#949ba4", bg="#2b2d31").pack(anchor="w")
        lbl = tk.Label(frame, text=value, font=("Arial", 12, "bold"), fg=color, bg="#2b2d31")
        lbl.pack(anchor="w", pady=(1, 0))
        return lbl

    def create_admin_button(self, text, command, bg_color):
        btn = tk.Button(self.left_panel, text=text, font=("Arial", 9, "bold"), bg=bg_color, fg="white", bd=0, pady=8, command=command)
        btn.pack(fill="x", pady=4)
        return btn

    def create_macro_section_advanced(self, parent, section_title, commands_list):
        tk.Label(parent, text=section_title.upper(), font=("Arial", 8, "bold"), fg="#949ba4", bg="#1e1f22").pack(anchor="w", pady=(12, 2))
        frame = tk.Frame(parent, bg="#2b2d31", padx=5, pady=5)
        frame.pack(fill="x", pady=(0, 5))
        
        for name, cmd in commands_list:
            btn = tk.Button(frame, text=name, font=("Arial", 9), bg="#383a40", fg="#dbdee1", activebackground="#4e5058", activeforeground="white", bd=0, pady=4, anchor="w", padx=8, command=lambda c=cmd: self.send_rcon_cmd(c))
            btn.pack(fill="x", pady=2)

    def run_mod_action(self, action_type):
        """Grabs the player entry string and maps it to a fast moderation string using numbers."""
        target = self.player_entry.get().strip()
        if not target:
            messagebox.showwarning("Input Target Missing", "Please input a player name or 17-digit SteamID into the mod field box first.")
            return
        
        # Smart Conversion: If you type "Declan Dykes", this scans your active console view 
        # text widget to hunt down and isolate your real 17-digit SteamID automatically!
        if action_type == "ban" and not target.isdigit():
            console_text = self.console_box.get("1.0", tk.END)
            import re
            steam_ids = re.findall(r"7656\d{13}", console_text)
            if steam_ids and target in console_text:
                target = steam_ids[-1]  # Grab the most recent matching 17-digit ID found
        
        if action_type == "kick": 
            command = f'kick "{target}" "Kicked by Server Controller Admin."'
        elif action_type == "ban": 
            command = f'banid "{target}" "Banned by Server Controller Admin."'  # Swapped to safer banid
        elif action_type == "mute": 
            command = f'mute "{target}"'
        elif action_type == "unmute": 
            command = f'unmute "{target}"'
        if not target:
            messagebox.showwarning("Input Target Missing", "Please input a player name or 17-digit SteamID into the mod field box first.")
            return
        
        if action_type == "kick": 
            command = f'kick "{target}" "Kicked by Server Controller Admin."'
        elif action_type == "ban": 
            command = f'ban "{target}" "Banned by Server Controller Admin."'
        elif action_type == "mute": 
            command = f'mute "{target}"'
        elif action_type == "unmute": 
            command = f'unmute "{target}"'
        
        self.send_rcon_cmd(command)
        self.send_rcon_cmd(command)

        # Log into Recent Action History Array
        action_label = f"{action_type.upper()}: {target}"
        self.action_history.insert(0, (action_type, target))
        self.undo_listbox.insert(0, action_label)
        if self.undo_listbox.size() > 5:
            self.undo_listbox.delete(tk.END)
            self.action_history.pop()
            
        if action_type == "ban":
            ban_data = {
                "name": self.player_entry.get().strip(),
                "steamid": target
            }
            self.ban_registry_history.insert(0, ban_data)
            self.ban_registry_listbox.insert(0, f"🚫 {ban_data['name']} - {ban_data['steamid']}")
            self.save_bans()
            if self.ban_registry_listbox.size() > 10:
                self.ban_registry_listbox.delete(tk.END)
                self.ban_registry_history.pop()
                self.save_bans()
        
        self.player_entry.delete(0, tk.END)

    def trigger_undo_action(self):
        """Triggers when an administrator double clicks an action history row item."""
        try:
            selection_index = self.undo_listbox.curselection()
            if not selection_index:
                return
                
            idx = selection_index[0]
            action_type, target = self.action_history[idx]
            
            if action_type == "ban":
                undo_cmd = f'unban "{target}"'
                alert_text = f"Successfully triggered UNBAN macro routine for {target}."
                for i, ban in enumerate(self.ban_registry_history):
                    if ban["steamid"] == target:
                        self.ban_registry_listbox.delete(i)
                        self.ban_registry_history.pop(i)
                        self.save_bans()
                        break
            elif action_type == "mute":
                undo_cmd = f'unmute "{target}"'
                alert_text = f"Successfully triggered UNMUTE macro routine for {target}."
            elif action_type == "unmute":
                undo_cmd = f'mute "{target}"'
                alert_text = f"Successfully re-applied MUTE parameters to {target}."
            else:
                messagebox.showinfo("Undo Invalid", "Kicked players cannot be undone via console commands because they have already been disconnected from the server.")
                return
                
            self.send_rcon_cmd(undo_cmd)
            self.append_console(f">>>> [System Countermeasure]: Undoing previous action. Executed: {undo_cmd}", "sys")
            
            self.undo_listbox.delete(idx)
            self.action_history.pop(idx)
            messagebox.showinfo("Undo Completed", alert_text)
        except Exception as e:
            self.append_console(f">>> [UI Error]: Undo callback failed: {e}", "sys")

    def run_manual_unban(self):
        """Fires an instant unban command using the input string from the Ban Registry sub-bar."""
        target = self.unban_entry.get().strip()
        if not target:
            messagebox.showwarning("Target Missing", "Please input a SteamID or Name into the unban entry box first.")
            return
        
        undo_cmd = f'unban "{target}"'
        self.send_rcon_cmd(undo_cmd)
        self.append_console(f">>> [Registry Action]: Transmitted Global Unban Request for {target}", "sys")
        
        for i, ban in enumerate(self.ban_registry_history):
            if ban["steamid"] == target:
                self.ban_registry_listbox.delete(i)
                self.ban_registry_history.pop(i)
                self.save_bans()
                break
            
        self.unban_entry.delete(0, tk.END)
        messagebox.showinfo("Unban Sent", f"Transmitted Global Unban command for: {target}")

    def trigger_registry_unban(self):
        """Triggers when an administrator double clicks an active row inside the Ban Registry listbox."""
        try:
            selection_index = self.ban_registry_listbox.curselection()
            if not selection_index:
                return
                
            idx = selection_index[0]
            target = self.ban_registry_history[idx]["steamid"]
            
            undo_cmd = f'unban "{target}"'
            self.send_rcon_cmd(undo_cmd)
            self.append_console(f">>> [Registry Action]: Double-Click Unban triggered for {target}", "sys")
            
            self.ban_registry_listbox.delete(idx)
            self.ban_registry_history.pop(idx)
            messagebox.showinfo("Unban Sent", f"Successfully unbanned profile: {target}")
        except Exception as e:
            self.append_console(f">>> [UI Error]: Registry unban callback failed: {e}", "sys")

    def save_bans(self):
        try:
            with open(BAN_FILE, "w", encoding="utf-8") as f:
                json.dump(self.ban_registry_history, f, indent=4)
        except Exception as e:
            self.append_console(f">>> Failed to save bans: {e}", "warn")

    def load_bans(self):
        self.ban_registry_history = []
        if os.path.exists(BAN_FILE):
            try:
                with open(BAN_FILE, "r", encoding="utf-8") as f:
                    self.ban_registry_history = json.load(f)
                self.ban_registry_listbox.delete(0, tk.END)
                for ban in self.ban_registry_history:
                    self.ban_registry_listbox.insert(tk.END, f"🚫 {ban['name']} - {ban['steamid']}")
            except Exception as e:
                self.append_console(f">>> Failed to load bans: {e}", "warn")

    def append_console(self, text, tag=None):
        self.console_box.config(state=tk.NORMAL)
        
        if not tag:
            if "warning" in text.lower() or "error" in text.lower() or "failed" in text.lower(): tag = "warn"
            elif "system alert" in text.lower() or ">>>" in text or "connected" in text.lower(): tag = "sys"
            elif "joined" in text.lower() or "connecting" in text.lower(): tag = "join"
            elif "> sent" in text.lower(): tag = "cmd"

        if tag:
            self.console_box.insert(tk.END, text + "\n", tag)
        else:
            self.console_box.insert(tk.END, text + "\n")
            
        self.console_box.see(tk.END)
        self.console_box.config(state=tk.DISABLED)
        
        try:
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as file:
                timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
                file.write(timestamp + text + "\n")
        except:
            pass

    def start_async_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def rcon_listener(self):
        uri = f"ws://{RCON_IP}:{RCON_PORT}/{RCON_PASSWORD}"
        while True:
            try:
                self.root.after(0, lambda: self.lbl_status.config(text="CONNECTING...", fg="#f0b232"))
                async with websockets.connect(uri, ping_interval=None) as websocket:
                    self.websocket = websocket
                    self.root.after(0, lambda: self.lbl_status.config(text="ONLINE", fg="#23a55a"))
                    self.root.after(0, lambda: self.append_console(">>> Core data link secured. Master console grid fully operational.", "sys"))
                    
                    while True:
                        response = await websocket.recv()
                        data = json.loads(response)
                        if "Message" in data:
                            msg = data["Message"].strip()
                            if msg:
                                self.root.after(0, lambda m=msg: self.append_console(m))
                                if "fps" in msg.lower() and "players" in msg.lower():
                                    self.parse_metrics(msg)
            except Exception as e:
                self.websocket = None
                self.root.after(0, lambda: self.lbl_status.config(text="OFFLINE", fg="#e05a47"))
                self.root.after(0, lambda: self.append_console(f">>> Network system link dropped: {e}. Attempting reconnect pipeline...", "sys"))
                await asyncio.sleep(4)

    async def autosave_timer(self):
        while True:
            await asyncio.sleep(300)
            if self.auto_save_var.get() and self.websocket:
                self.root.after(0, lambda: self.append_console(">>> Triggering Automated Auto-Save Loop Task...", "sys"))
                payload = {"Identifier": 1, "Message": "server.save", "Name": "WebRcon"}
                try:
                    await self.websocket.send(json.dumps(payload))
                except:
                    pass

    def send_rcon_cmd(self, cmd_text):
        if not self.websocket:
            messagebox.showwarning("Pipeline Failure", "Cannot process command string. Server controller link is offline.")
            return
        # FIXED: Swapped "Message": "server.save" to use the dynamic cmd_text input!
        payload = {"Identifier": 1, "Message": cmd_text, "Name": "WebRcon"}
        asyncio.run_coroutine_threadsafe(self.websocket.send(json.dumps(payload)), self.loop)
        self.root.after(0, lambda: self.append_console(f"> Sent Console Command: {cmd_text}", "cmd"))

    def submit_input_cmd(self):
        cmd = self.cmd_entry.get().strip()
        if cmd:
            self.send_rcon_cmd(cmd)
            self.cmd_entry.delete(0, tk.END)

    def prompt_broadcast(self):
        broadcast_win = tk.Toplevel(self.root)
        broadcast_win.title("Global Alert Broadcast")
        broadcast_win.geometry("400x130")
        broadcast_win.configure(bg="#2b2d31")
        tk.Label(broadcast_win, text="Message to push live onto player monitors:", fg="white", bg="#2b2d31").pack(pady=10)
        entry = tk.Entry(broadcast_win, width=45)
        entry.pack(pady=5)
        entry.focus_set()
        
        def send():
            msg = entry.get().strip()
            if msg:
                self.send_rcon_cmd(f'say "[ADMIN]: {msg}"')
                broadcast_win.destroy()
                
        tk.Button(broadcast_win, text="Send Live Broadcast", bg="#5865f2", fg="white", bd=0, padx=10, command=send).pack(pady=10)

    def parse_metrics(self, msg):
        try:
            msg_lower = msg.lower().strip()
            
            # Handle direct manual status responses from background checker
            if "fps" in msg_lower and "players" not in msg_lower:
                clean_fps = msg_lower.replace("fps", "").replace(":", "").strip()
                if clean_fps.isdigit():
                    self.root.after(0, lambda v=clean_fps: self.lbl_fps.config(text=f"{v} FPS"))
                    return

            parts = msg_lower.split(",")
            for part in parts:
                if "fps" in part and ":" in part:
                    raw_fps = part.split(":")[1].strip().split()[0]
                    self.root.after(0, lambda v=raw_fps: self.lbl_fps.config(text=f"{v} FPS"))
                elif "players" in part and ":" in part:
                    raw_players = part.split(":")[1].strip()
                    self.root.after(0, lambda v=raw_players: self.lbl_players.config(text=v))
                elif "memory" in part or "mem" in part:
                    if ":" in part:
                        raw_mem = part.split(":")[1].strip().upper()
                        self.root.after(0, lambda v=raw_mem: self.lbl_memory.config(text=v))
        except:
            pass

    def toggle_updater_loop(self):
        """Swaps the tracking rules and alters the physical button colours on your left panel layout."""
        self.run_updater = not self.run_updater
        if self.run_updater:
            self.btn_toggle_updater.config(text="⏸️ Pause FPS Tracking", bg="#f0b232", fg="black")
            self.append_console(">>> [System Notification]: Automated background status updates RESUMED.", "sys")
        else:
            self.btn_toggle_updater.config(text="▶️ Resume FPS Tracking", bg="#23a55a", fg="white")
            self.append_console(">>> [System Notification]: Automated background status updates PAUSED.", "sys")

    async def metrics_updater_loop(self):
        """Forces secret automated background data queries every 5 seconds if not paused by owner."""
        while True:
            await asyncio.sleep(5)
            # Checked directly against the left panel button's status rule
            if self.websocket and self.run_updater:
                payload = {"Identifier": 2, "Message": "status", "Name": "WebRcon"}
                try:
                    await self.websocket.send(json.dumps(payload))
                except:
                    pass

if __name__ == "__main__":
    window = tk.Tk()
    app = RustDashboardApp(window)
    asyncio.run_coroutine_threadsafe(app.metrics_updater_loop(), app.loop)
    window.mainloop()
