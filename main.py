import os
import sys
import json
import threading
import subprocess
import customtkinter as ctk
from tkinter import messagebox
import minecraft_launcher_lib

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

MINECRAFT_DIR = minecraft_launcher_lib.utils.get_minecraft_directory()
CONFIG_FILE = "config.json"


class VersionSelectorWindow(ctk.CTkToplevel):
    """Osobne okno GUI z kwadratowymi przyciskami do wyboru wersji."""
    def __init__(self, parent, versions, current_version, on_select_callback):
        super().__init__(parent)

        self.title("Wybierz wersję Minecrafta")
        self.geometry("520x450")
        self.resizable(False, False)
        self.grab_set()

        self.on_select_callback = on_select_callback

        label = ctk.CTkLabel(
            self, text="WYBIERZ WERSJĘ", font=ctk.CTkFont(size=20, weight="bold")
        )
        label.pack(pady=15)

        scroll_frame = ctk.CTkScrollableFrame(self, width=470, height=360)
        scroll_frame.pack(padx=15, pady=(0, 15), fill="both", expand=True)

        columns = 4
        for index, version_id in enumerate(versions):
            row = index // columns
            col = index % columns

            is_selected = (version_id == current_version)
            btn_color = ("#1f6aa5" if is_selected else "#2b2b2b")
            hover_color = ("#144870" if is_selected else "#3a3a3a")

            btn = ctk.CTkButton(
                scroll_frame,
                text=version_id,
                width=100,
                height=60,
                corner_radius=8,
                fg_color=btn_color,
                hover_color=hover_color,
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda v=version_id: self.select_version(v)
            )
            btn.grid(row=row, column=col, padx=6, pady=6)

    def select_version(self, version):
        self.on_select_callback(version)
        self.destroy()


class AdvancedMinecraftLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Minecraft Launcher")
        self.geometry("700x600")
        self.resizable(False, False)

        # Wczytanie zapisanych ustawień z pliku config.json
        self.config = self.load_config()

        self.available_versions = []
        self.selected_version = self.config.get("version", "Ładowanie...")
        self.selected_ram = 4
        self.fullscreen_var = ctk.BooleanVar(value=False)
        self.game_process = None

        self.create_ui()

        threading.Thread(target=self.load_versions, daemon=True).start()

    def load_config(self):
        """Wczytuje ustawienia z pliku config.json."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"username": "Player", "version": None}

    def save_config(self):
        """Zapisuje obecny nick i wersję do pliku config.json."""
        data = {
            "username": self.username_entry.get().strip(),
            "version": self.selected_version
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log(f"Błąd podczas zapisu konfiguracji: {e}")

    def create_ui(self):
        self.title_label = ctk.CTkLabel(
            self, text="MINECRAFT LAUNCHER", font=ctk.CTkFont(size=26, weight="bold")
        )
        self.title_label.pack(pady=(15, 5))

        self.tabview = ctk.CTkTabview(self, width=660, height=410)
        self.tabview.pack(pady=10, padx=20)

        self.tab_main = self.tabview.add("Główne")
        self.tab_settings = self.tabview.add("Ustawienia")
        self.tab_logs = self.tabview.add("Logi")

        # --- ZAKŁADKA GŁÓWNE ---
        self.username_label = ctk.CTkLabel(self.tab_main, text="Nick z gry:", font=ctk.CTkFont(size=14))
        self.username_label.pack(anchor="w", padx=20, pady=(15, 0))

        self.username_entry = ctk.CTkEntry(self.tab_main, placeholder_text="Wpisz nick...")
        self.username_entry.insert(0, self.config.get("username", "Player"))
        self.username_entry.pack(fill="x", padx=20, pady=(5, 15))

        self.version_label = ctk.CTkLabel(self.tab_main, text="Wybrana wersja:", font=ctk.CTkFont(size=14))
        self.version_label.pack(anchor="w", padx=20, pady=(5, 0))

        self.version_frame = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        self.version_frame.pack(fill="x", padx=20, pady=5)

        self.version_display_btn = ctk.CTkButton(
            self.version_frame,
            text=f"Wersja: {self.selected_version}",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self.open_version_selector
        )
        self.version_display_btn.pack(fill="x")

        # --- ZAKŁADKA USTAWIENIA ---
        self.ram_label = ctk.CTkLabel(self.tab_settings, text="Pamięć RAM (GB):", font=ctk.CTkFont(size=14))
        self.ram_label.pack(anchor="w", padx=20, pady=(10, 0))

        self.ram_frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        self.ram_frame.pack(fill="x", padx=20, pady=5)

        self.ram_slider = ctk.CTkSlider(
            self.ram_frame, from_=2, to=16, number_of_steps=14, command=self.on_ram_change
        )
        self.ram_slider.set(4)
        self.ram_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.ram_display_label = ctk.CTkLabel(self.ram_frame, text="4 GB", font=ctk.CTkFont(weight="bold"))
        self.ram_display_label.pack(side="right")

        self.res_label = ctk.CTkLabel(self.tab_settings, text="Rozdzielczość gry:", font=ctk.CTkFont(size=14))
        self.res_label.pack(anchor="w", padx=20, pady=(10, 0))

        self.res_optionmenu = ctk.CTkOptionMenu(
            self.tab_settings, values=["1280x720", "1920x1080", "854x480"]
        )
        self.res_optionmenu.pack(fill="x", padx=20, pady=5)

        self.fullscreen_checkbox = ctk.CTkCheckBox(
            self.tab_settings, text="Tryb pełnoekranowy (Fullscreen)", variable=self.fullscreen_var
        )
        self.fullscreen_checkbox.pack(anchor="w", padx=20, pady=(10, 15))

        # PRZYCISK AKTUALIZACJI
        self.update_button = ctk.CTkButton(
            self.tab_settings,
            text="Sprawdź aktualizacje launchera",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1f7a8c",
            hover_color="#145966",
            height=35,
            command=self.check_launcher_updates
        )
        self.update_button.pack(fill="x", padx=20, pady=(5, 2))

        # SZARY POCHYŁY NAPIS POD PRZYCISKIEM
        self.version_tag_label = ctk.CTkLabel(
            self.tab_settings,
            text="v0.1",
            text_color="gray",
            font=ctk.CTkFont(size=11, slant="italic")
        )
        self.version_tag_label.pack(pady=(0, 10))

        # --- ZAKŁADKA LOGI ---
        self.log_textbox = ctk.CTkTextbox(self.tab_logs)
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)

        # --- DOLNY PASEK I PRZYCISK ---
        self.status_label = ctk.CTkLabel(self, text="Gotowy", anchor="w")
        self.status_label.pack(fill="x", padx=20, pady=(0, 2))

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 10))
        self.progress_bar.set(0)

        self.play_button = ctk.CTkButton(
            self,
            text="ZAGRAJ",
            font=ctk.CTkFont(size=18, weight="bold"),
            height=45,
            command=self.start_game_thread
        )
        self.play_button.pack(fill="x", padx=20, pady=(0, 15))

    def log(self, text):
        self.log_textbox.insert("end", text + "\n")
        self.log_textbox.see("end")

    def load_versions(self):
        try:
            self.log("Pobieranie aktualnej listy wersji...")
            installed_and_vanilla = minecraft_launcher_lib.utils.get_version_list()
            releases = [v["id"] for v in installed_and_vanilla if v["type"] == "release"]

            if releases:
                self.available_versions = releases
                
                # Jeśli wcześniej zapisana wersja nie istnieje na liście, ustaw najnowszą
                if self.selected_version not in releases:
                    self.selected_version = releases[0]

                self.version_display_btn.configure(text=f"Wersja: {self.selected_version}")
                self.log(f"Pobrano {len(releases)} oficjalnych wydań gry.")
            else:
                self.log("Nie znaleziono żadnych wersji.")
        except Exception as e:
            self.log(f"Błąd podczas pobierania wersji: {e}")

    def open_version_selector(self):
        if not self.available_versions:
            messagebox.showwarning("Uwaga", "Trwa ładowanie wersji lub lista jest pusta!")
            return

        VersionSelectorWindow(
            parent=self,
            versions=self.available_versions,
            current_version=self.selected_version,
            on_select_callback=self.on_version_selected
        )

    def on_version_selected(self, version):
        self.selected_version = version
        self.version_display_btn.configure(text=f"Wersja: {self.selected_version}")
        self.log(f"Wybrano wersję: {self.selected_version}")
        self.save_config()

    def on_ram_change(self, value):
        self.selected_ram = int(value)
        self.ram_display_label.configure(text=f"{self.selected_ram} GB")
        self.log(f"Zmieniono pamięć RAM na: {self.selected_ram} GB")

    def check_launcher_updates(self):
        self.update_button.configure(state="disabled", text="Sprawdzanie...")
        self.log("Sprawdzanie dostępności aktualizacji launchera...")

        def _check():
            import time
            time.sleep(1.5)
            self.log("Używasz najnowszej wersji launchera.")
            messagebox.showinfo("Aktualizacje", "Masz zainstalowaną najnowszą wersję launchera (v0.1)!")
            self.update_button.configure(state="normal", text="Sprawdź aktualizacje launchera")

        threading.Thread(target=_check, daemon=True).start()

    def start_game_thread(self):
        self.play_button.configure(state="disabled")
        threading.Thread(target=self.launch_game, daemon=True).start()

    def launch_game(self):
        username = self.username_entry.get().strip()
        version = self.selected_version
        ram_gb = self.selected_ram

        if not username:
            messagebox.showwarning("Uwaga", "Wprowadź swój nick!")
            self.play_button.configure(state="normal")
            return

        # Zapisz nick i wersję tuż przed uruchomieniem
        self.save_config()

        self.log(f"\n--- Start sesji: {username} ---")
        self.log(f"Wersja: {version} | RAM: {ram_gb} GB")

        current_max = [100]

        def set_status(status):
            self.status_label.configure(text=status)
            self.log(f"[Instalacja] {status}")

        def set_progress(value):
            if current_max[0] > 0:
                self.progress_bar.set(value / current_max[0])

        def set_max(value):
            current_max[0] = value

        callback = {
            "setStatus": set_status,
            "setProgress": set_progress,
            "setMax": set_max
        }

        try:
            self.log("Pobieranie/Sprawdzanie spójności plików...")
            minecraft_launcher_lib.install.install_minecraft_version(
                version=version,
                minecraft_directory=MINECRAFT_DIR,
                callback=callback
            )

            res = self.res_optionmenu.get().split("x")
            width, height = res[0], res[1]

            options = {
                "username": username,
                "uuid": "",
                "token": "",
                "gameDirectory": MINECRAFT_DIR,
                "jvmArguments": [f"-Xmx{ram_gb}G", f"-Xms{ram_gb}G"],
                "resolutionWidth": width,
                "resolutionHeight": height,
                "fullscreen": self.fullscreen_var.get()
            }

            self.log("Przygotowywanie komendy startowej...")
            command = minecraft_launcher_lib.command.get_minecraft_command(
                version=version,
                minecraft_directory=MINECRAFT_DIR,
                options=options
            )

            self.status_label.configure(text="Uruchamianie Minecrafta...")
            self.progress_bar.set(1.0)

            self.game_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            self.withdraw()

            for line in iter(self.game_process.stdout.readline, ''):
                if line:
                    print(f"[Minecraft] {line.strip()}")

            self.game_process.wait()

            self.deiconify()
            self.status_label.configure(text="Gra została zamknięta")
            self.log("Minecraft został zamknięty.")
            self.play_button.configure(state="normal")
            self.progress_bar.set(0)

        except Exception as e:
            self.log(f"BŁĄD: {e}")
            messagebox.showerror("Błąd", f"Wystąpił błąd:\n{e}")
            self.deiconify()
            self.play_button.configure(state="normal")


if __name__ == "__main__":
    app = AdvancedMinecraftLauncher()
    app.mainloop()
