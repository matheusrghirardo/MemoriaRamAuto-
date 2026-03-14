"""
Monitor e Otimizador de RAM - Versão Final GUI
Interface gráfica moderna com monitoramento em tempo real e otimizações.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import os
import shutil
import subprocess
import sys

try:
    import psutil
except ImportError:
    print("Erro: psutil não instalado. Execute: pip install psutil")
    sys.exit(1)


def format_bytes(bytes_val):
    """Converte bytes para formato legível."""
    if bytes_val < 0:
        return "0.00 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"


class RAMMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor e Otimizador de RAM")
        self.root.geometry("1100x750")
        self.root.minsize(1000, 650)

        # Cores
        self.bg = "#0d1117"
        self.fg = "#c9d1d9"
        self.accent = "#58a6ff"
        self.green = "#3fb950"
        self.yellow = "#d29922"
        self.red = "#f85149"
        self.panel = "#161b22"

        self.root.configure(bg=self.bg)
        self.monitoring = True

        self.create_widgets()
        self.schedule_update()

    def create_widgets(self):
        """Cria toda a interface."""
        # === Header ===
        header = tk.Frame(self.root, bg=self.accent, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="💾  MONITOR DE MEMÓRIA RAM",
            font=tkFont.Font(family="Segoe UI", size=14, weight="bold"),
            bg=self.accent, fg=self.bg
        ).pack(pady=12)

        # === Main ===
        main = tk.Frame(self.root, bg=self.bg)
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # --- Left Panel ---
        left = tk.Frame(main, bg=self.bg)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        tk.Label(left, text="📊 Uso de RAM em Tempo Real",
                 font=("Segoe UI", 11, "bold"), bg=self.bg, fg=self.accent
                 ).pack(anchor=tk.W, pady=(0, 5))

        self.canvas = tk.Canvas(left, bg=self.panel, height=200, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Info
        info = tk.LabelFrame(left, text=" Informações de Memória ",
                             bg=self.panel, fg=self.accent,
                             font=("Segoe UI", 10, "bold"), padx=15, pady=10)
        info.pack(fill=tk.X)

        self.lbl_ram = tk.Label(info, text="RAM: ...", bg=self.panel, fg=self.fg,
                                font=("Segoe UI", 10))
        self.lbl_ram.pack(anchor=tk.W, pady=3)

        self.lbl_pct = tk.Label(info, text="Uso: ...", bg=self.panel, fg=self.green,
                                font=("Segoe UI", 10, "bold"))
        self.lbl_pct.pack(anchor=tk.W, pady=3)

        self.lbl_avail = tk.Label(info, text="Disponível: ...", bg=self.panel, fg=self.fg,
                                  font=("Segoe UI", 10))
        self.lbl_avail.pack(anchor=tk.W, pady=3)

        self.lbl_swap = tk.Label(info, text="Swap: ...", bg=self.panel, fg=self.yellow,
                                 font=("Segoe UI", 9))
        self.lbl_swap.pack(anchor=tk.W, pady=3)

        # --- Right Panel ---
        right = tk.Frame(main, bg=self.bg, width=320)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right.pack_propagate(False)

        tk.Label(right, text="⚙️ Top 10 Processos",
                 font=("Segoe UI", 11, "bold"), bg=self.bg, fg=self.accent
                 ).pack(anchor=tk.W, pady=(0, 8))

        proc_frame = tk.Frame(right, bg=self.panel)
        proc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        scroll = ttk.Scrollbar(proc_frame, orient=tk.VERTICAL)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.proc_text = tk.Text(proc_frame, bg=self.panel, fg=self.fg,
                                 font=("Consolas", 9), height=15,
                                 yscrollcommand=scroll.set,
                                 state=tk.DISABLED, highlightthickness=0,
                                 borderwidth=0, padx=8, pady=5)
        self.proc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.proc_text.yview)

        # Botões
        tk.Label(right, text="🔧 Otimizações",
                 font=("Segoe UI", 11, "bold"), bg=self.bg, fg=self.accent
                 ).pack(anchor=tk.W, pady=(0, 8))

        btn_frame = tk.Frame(right, bg=self.bg)
        btn_frame.pack(fill=tk.X)

        buttons = [
            ("🗑️  Limpar Cache", self.do_clear_cache),
            ("📁  Limpar Temp", self.do_clear_temp),
            ("🚀  Otimizar Tudo", self.do_optimize_all),
        ]
        for text, cmd in buttons:
            btn = tk.Button(btn_frame, text=text, command=cmd,
                            bg=self.accent, fg=self.bg,
                            font=("Segoe UI", 9, "bold"),
                            activebackground=self.green,
                            relief=tk.FLAT, cursor="hand2", pady=8)
            btn.pack(fill=tk.X, pady=3)

        self.lbl_status = tk.Label(right, text="✓ Monitorando...",
                                   bg=self.bg, fg=self.green,
                                   font=("Segoe UI", 9))
        self.lbl_status.pack(anchor=tk.W, pady=(10, 0))

    def schedule_update(self):
        """Agenda atualização periódica."""
        if not self.monitoring:
            return
        try:
            self.update_all()
        except Exception as e:
            print(f"Erro na atualização: {e}")
        self.root.after(1500, self.schedule_update)

    def update_all(self):
        """Atualiza memória, gráfico e processos."""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        used_gb = mem.used / (1024 ** 3)
        total_gb = mem.total / (1024 ** 3)
        avail_gb = mem.available / (1024 ** 3)
        swap_used = swap.used / (1024 ** 3)
        swap_total = swap.total / (1024 ** 3)

        self.lbl_ram.config(text=f"RAM: {used_gb:.2f} GB / {total_gb:.2f} GB")

        if mem.percent >= 90:
            color = self.red
        elif mem.percent >= 75:
            color = self.yellow
        else:
            color = self.green

        self.lbl_pct.config(text=f"Uso: {mem.percent:.1f}%", fg=color)
        self.lbl_avail.config(text=f"Disponível: {avail_gb:.2f} GB")
        self.lbl_swap.config(text=f"Swap: {swap_used:.2f} GB / {swap_total:.2f} GB")

        self.draw_bar(mem.percent)
        self.update_processes()

    def draw_bar(self, percent):
        """Desenha barra de progresso no canvas."""
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1:
            return

        margin = 50
        bar_h = 40
        bar_y = (h - bar_h) // 2

        # Fundo
        self.canvas.create_rectangle(margin, bar_y, w - margin, bar_y + bar_h,
                                     fill="#30363d", outline=self.accent, width=2)
        # Preenchimento
        fill_w = max(0, (w - 2 * margin) * (percent / 100))
        if percent >= 90:
            color = self.red
        elif percent >= 75:
            color = self.yellow
        else:
            color = self.green

        self.canvas.create_rectangle(margin, bar_y, margin + fill_w, bar_y + bar_h,
                                     fill=color, outline="")

        # Texto central
        self.canvas.create_text(w // 2, bar_y + bar_h // 2,
                                text=f"{percent:.1f}%",
                                font=("Segoe UI", 16, "bold"), fill="#ffffff")

        # Labels laterais
        self.canvas.create_text(margin - 5, bar_y + bar_h // 2,
                                text="0%", font=("Segoe UI", 8), fill=self.fg, anchor=tk.E)
        self.canvas.create_text(w - margin + 5, bar_y + bar_h // 2,
                                text="100%", font=("Segoe UI", 8), fill=self.fg, anchor=tk.W)

    def update_processes(self):
        """Atualiza lista de processos."""
        try:
            procs = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    info = proc.info
                    mem = info.get('memory_info')
                    if mem:
                        procs.append((info['pid'], info['name'] or "?", mem.rss))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            procs.sort(key=lambda x: x[2], reverse=True)

            self.proc_text.config(state=tk.NORMAL)
            self.proc_text.delete("1.0", tk.END)

            for i, (pid, name, rss) in enumerate(procs[:10], 1):
                mb = rss / (1024 ** 2)
                self.proc_text.insert(tk.END, f"{i:>2}. {name[:22]:<22} {mb:>8.1f} MB\n")

            self.proc_text.config(state=tk.DISABLED)
        except Exception:
            pass

    def do_clear_cache(self):
        """Limpar cache."""
        self.lbl_status.config(text="⏳ Limpando cache...", fg=self.yellow)
        self.root.update_idletasks()
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[GC]::Collect(); [GC]::WaitForPendingFinalizers()"],
                capture_output=True, timeout=10
            )
            self.lbl_status.config(text="✓ Cache limpo!", fg=self.green)
            messagebox.showinfo("Sucesso", "Cache de processos limpo!")
        except Exception as e:
            self.lbl_status.config(text="✘ Erro", fg=self.red)
            messagebox.showerror("Erro", str(e))

    def do_clear_temp(self):
        """Limpar temp."""
        self.lbl_status.config(text="⏳ Limpando Temp...", fg=self.yellow)
        self.root.update_idletasks()

        deleted = 0
        freed = 0
        for d in [os.path.expandvars("%TEMP%"), os.path.expandvars("%WINDIR%\\Temp")]:
            if not os.path.isdir(d):
                continue
            try:
                for entry in os.scandir(d):
                    try:
                        if entry.is_file(follow_symlinks=False):
                            freed += entry.stat().st_size
                            os.remove(entry.path)
                            deleted += 1
                        elif entry.is_dir(follow_symlinks=False):
                            shutil.rmtree(entry.path, ignore_errors=True)
                            deleted += 1
                    except (PermissionError, OSError):
                        pass
            except (PermissionError, OSError):
                pass

        self.lbl_status.config(text="✓ Temp limpo!", fg=self.green)
        messagebox.showinfo("Sucesso",
                            f"Deletados: {deleted} itens\n"
                            f"Espaço liberado: {format_bytes(freed)}")

    def do_optimize_all(self):
        """Todas as otimizações."""
        self.lbl_status.config(text="⏳ Otimizando tudo...", fg=self.yellow)
        self.root.update_idletasks()

        try:
            # Cache
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[GC]::Collect(); [GC]::WaitForPendingFinalizers()"],
                capture_output=True, timeout=10
            )

            # Temp
            for d in [os.path.expandvars("%TEMP%"), os.path.expandvars("%WINDIR%\\Temp")]:
                if os.path.isdir(d):
                    for entry in os.scandir(d):
                        try:
                            if entry.is_file(follow_symlinks=False):
                                os.remove(entry.path)
                            elif entry.is_dir(follow_symlinks=False):
                                shutil.rmtree(entry.path, ignore_errors=True)
                        except (PermissionError, OSError):
                            pass

            self.lbl_status.config(text="✓ Otimização completa!", fg=self.green)
            messagebox.showinfo("Sucesso", "Todas as otimizações executadas!")
        except Exception as e:
            self.lbl_status.config(text="✘ Erro", fg=self.red)
            messagebox.showerror("Erro", str(e))

    def on_closing(self):
        """Fechar aplicação."""
        self.monitoring = False
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = RAMMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
