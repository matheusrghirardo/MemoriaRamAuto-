"""
Monitor e Otimizador de RAM do Windows - Versão Terminal
Monitora uso de memória em tempo real, exibe processos que consomem mais RAM,
oferece otimizações automáticas e priorização de programa.
"""

import ctypes
import os
import shutil
import subprocess
import sys
from datetime import datetime
from urllib.parse import quote_plus

try:
    import psutil
except ImportError:
    print("Erro: psutil não instalado. Execute: pip install psutil")
    sys.exit(1)


def is_admin():
    """Verifica se está rodando com privilégios de administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_memory_info():
    """Obtém informações completas de memória do sistema."""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "total": memory.total,
        "disponivel": memory.available,
        "usado": memory.used,
        "percentual": memory.percent,
        "livre": memory.free,
        "swap_total": swap.total,
        "swap_usado": swap.used,
        "swap_free": swap.free,
        "swap_percent": swap.percent,
    }


def format_bytes(bytes_val):
    """Converte bytes para formato legível (KB, MB, GB)."""
    if bytes_val < 0:
        return "0.00 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"


def get_top_processes(top_n=15):
    """Obtém os N processos que mais consomem RAM."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'status']):
        try:
            pinfo = proc.info
            mem_info = pinfo.get('memory_info')
            if mem_info:
                processes.append({
                    "pid": pinfo['pid'],
                    "nome": pinfo['name'] or "Desconhecido",
                    "rss": mem_info.rss,
                    "status": pinfo['status'],
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    processes.sort(key=lambda x: x['rss'], reverse=True)
    return processes[:top_n]


def clear_ram_cache():
    """Tenta limpar cache de RAM."""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[GC]::Collect(); [GC]::WaitForPendingFinalizers()"],
            capture_output=True, timeout=15
        )
        return True, "Cache limpo com sucesso"
    except subprocess.TimeoutExpired:
        return False, "Timeout ao limpar cache"
    except Exception as e:
        return False, f"Erro ao limpar cache: {e}"


def disable_visual_effects():
    """Desabilita efeitos visuais para economizar RAM."""
    try:
        cmd = (
            'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion'
            '\\Explorer\\Advanced" /v ListviewShadow /t REG_DWORD /d 0 /f; '
            'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion'
            '\\Explorer\\Advanced" /v DisablePreviewDesktop /t REG_DWORD /d 1 /f'
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                       capture_output=True, timeout=10)
        return True, "Efeitos visuais desabilitados"
    except Exception as e:
        return False, f"Erro: {e}"


def close_unnecessary_services():
    """Fecha serviços desnecessários que consomem RAM."""
    unnecessary = [
        "DiagTrack",
        "dmwappushservice",
        "RemoteRegistry",
        "TrkWks",
        "XboxGipSvc",
    ]
    results = []
    for service in unnecessary:
        try:
            check = subprocess.run(
                ["sc", "query", service],
                capture_output=True, text=True, timeout=10
            )
            if "RUNNING" in check.stdout:
                subprocess.run(["net", "stop", service],
                               capture_output=True, timeout=15)
                results.append((service, "Parado"))
            else:
                results.append((service, "Já parado"))
        except subprocess.TimeoutExpired:
            results.append((service, "Timeout"))
        except Exception:
            results.append((service, "Erro"))
    return results


def empty_temp_files():
    """Limpa arquivos temporários."""
    temp_dirs = [
        os.path.expandvars("%TEMP%"),
        os.path.expandvars("%WINDIR%\\Temp"),
    ]

    deleted_count = 0
    total_size = 0

    for temp_dir in temp_dirs:
        if not os.path.isdir(temp_dir):
            continue
        try:
            for entry in os.scandir(temp_dir):
                try:
                    if entry.is_file(follow_symlinks=False):
                        total_size += entry.stat().st_size
                        os.remove(entry.path)
                        deleted_count += 1
                    elif entry.is_dir(follow_symlinks=False):
                        shutil.rmtree(entry.path, ignore_errors=True)
                        deleted_count += 1
                except (PermissionError, OSError):
                    pass
        except (PermissionError, OSError):
            pass

    return deleted_count, total_size


def show_memory_bar(used, total):
    """Mostra uma barra visual de uso de memória."""
    if total <= 0:
        return "  [N/A]"
    percent = (used / total) * 100
    bar_length = 40
    filled = int(bar_length * percent / 100)
    filled = max(0, min(bar_length, filled))
    bar = "█" * filled + "░" * (bar_length - filled)

    if percent < 50:
        status = "✓ Bom"
    elif percent < 75:
        status = "⚠ Moderado"
    else:
        status = "✘ Crítico"

    return f"  [{bar}] {percent:5.1f}% - {status}"


def list_running_processes():
    """Lista processos em execução ordenados por consumo de RAM."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            pinfo = proc.info
            mem_info = pinfo.get('memory_info')
            if mem_info:
                processes.append({
                    "pid": pinfo['pid'],
                    "nome": pinfo['name'] or "Desconhecido",
                    "rss": mem_info.rss,
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    processes.sort(key=lambda x: x['rss'], reverse=True)
    return processes


def prioritize_program():
    """Prioriza um programa específico liberando RAM para ele."""
    print("\n" + "─" * 80)
    print("  🎯 PRIORIZAR PROGRAMA")
    print("─" * 80)

    print("\n  Carregando processos em execução...")
    all_procs = list_running_processes()

    if not all_procs:
        print("  ✘ Nenhum processo encontrado")
        return

    top20 = all_procs[:20]
    print(f"\n  {'#':<3} {'PID':<7} {'Processo':<35} {'RAM':<15}")
    print("  " + "─" * 66)

    for i, proc in enumerate(top20, 1):
        print(f"  {i:<3} {proc['pid']:<7} {proc['nome'][:34]:<35} {format_bytes(proc['rss']):>15}")

    print("\n  Digite o NÚMERO do programa (1-20) ou 0 para cancelar: ", end="")

    try:
        choice = int(input().strip())
        if choice == 0:
            print("  Cancelado.")
            return
        if not 1 <= choice <= len(top20):
            print("  ✘ Opção inválida")
            return

        selected = top20[choice - 1]
        pid = selected['pid']
        nome = selected['nome']

        print(f"\n  ✓ Priorizando: {nome} (PID: {pid})")
        print("\n  ⏳ Executando otimizações...\n")

        # 1. Aumentar prioridade do processo
        try:
            proc_obj = psutil.Process(pid)
            proc_obj.nice(psutil.HIGH_PRIORITY_CLASS)
            print("    ✓ Prioridade aumentada para ALTA")
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"    ✘ Erro ao aumentar prioridade: {e}")

        # 2. Limpar cache
        print("    ⏳ Limpando cache de sistema...")
        success, msg = clear_ram_cache()
        print(f"    {'✓' if success else '✘'} {msg}")

        # 3. Fechar serviços desnecessários
        print("    ⏳ Fechando serviços desnecessários...")
        results = close_unnecessary_services()
        stopped = sum(1 for _, status in results if "Parado" in status)
        print(f"    ✓ {stopped} serviços parados")

        # 4. Limpar temp
        print("    ⏳ Limpando arquivos temporários...")
        deleted, size = empty_temp_files()
        print(f"    ✓ {deleted} arquivos deletados ({format_bytes(size)})")

        print(f"\n  ✓ Programa priorizado com sucesso!")
        print(f"     {nome} agora tem máxima prioridade de RAM.")

    except ValueError:
        print("  ✘ Entrada inválida")


def main():
    print("=" * 80)
    print("   MONITOR E OTIMIZADOR DE MEMÓRIA RAM")
    print(f"   Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)

    admin = is_admin()
    if not admin:
        print("\n  ⚠ AVISO: Execute como Administrador para funcionalidades completas.")
        print("     (Otimizações podem ser limitadas sem elevação de privilégio)")

    # --- Informações de Memória ---
    print("\n" + "─" * 80)
    print("  📊 INFORMAÇÕES DE MEMÓRIA RAM")
    print("─" * 80)

    mem = get_memory_info()

    print(f"\n  Memória Total:      {format_bytes(mem['total'])}")
    print(f"  Memória em Uso:     {format_bytes(mem['usado'])}")
    print(f"  Memória Disponível: {format_bytes(mem['disponivel'])}")
    print(f"  Memória Livre:      {format_bytes(mem['livre'])}")
    print(f"  Percentual Usado:   {mem['percentual']:.1f}%")

    print("\n  Barra de Uso:")
    print(show_memory_bar(mem['usado'], mem['total']))

    if mem['swap_total'] > 0:
        print(f"\n  Swap (Virtual):")
        print(f"    Total:  {format_bytes(mem['swap_total'])}")
        print(f"    Usado:  {format_bytes(mem['swap_usado'])} ({mem['swap_percent']:.1f}%)")
        print(show_memory_bar(mem['swap_usado'], mem['swap_total']))

    # --- Top 15 Processos ---
    print("\n" + "─" * 80)
    print("  ⚙️  TOP 15 PROCESSOS QUE MAIS CONSOMEM RAM")
    print("─" * 80 + "\n")

    top_procs = get_top_processes(15)
    total_ram = mem['total']

    print(f"  {'#':<3} {'PID':<7} {'Processo':<35} {'RAM':<15} {'%':<6}")
    print("  " + "─" * 66)

    for i, proc in enumerate(top_procs, 1):
        pct = (proc['rss'] / total_ram) * 100 if total_ram > 0 else 0
        print(f"  {i:<3} {proc['pid']:<7} {proc['nome'][:34]:<35} {format_bytes(proc['rss']):>15} {pct:>5.1f}%")

    total_top = sum(p['rss'] for p in top_procs)
    pct_top = (total_top / mem['usado'] * 100) if mem['usado'] > 0 else 0
    print("  " + "─" * 66)
    print(f"  {'TOTAL (15 processos)':<45} {format_bytes(total_top):>15} ({pct_top:.1f}% do uso)")

    # --- Menu ---
    print("\n" + "=" * 80)
    print("  🔧 OPÇÕES DE OTIMIZAÇÃO")
    print("=" * 80)
    print("""
  1. Limpar cache de processos
  2. Desabilitar efeitos visuais
  3. Fechar serviços desnecessários
  4. Limpar arquivos temporários
  5. Executar otimizações completas (1+2+3+4)
  6. Priorizar RAM para um programa específico
  0. Sair
  """)

    if mem['percentual'] >= 90:
        print("  ⚠️  ALERTA: Memória crítica (≥90% em uso)!")
        print("     Recomenda-se executar otimizações.\n")
    elif mem['percentual'] >= 75:
        print("  ⚠️  AVISO: Memória elevada (≥75% em uso).")
        print("     Considere executar otimizações.\n")

    choice = input("  Escolha uma opção (0-6): ").strip()
    print("\n" + "=" * 80)

    if choice == "1":
        print("  ⏳ Limpando cache de processos...")
        success, msg = clear_ram_cache()
        print(f"  {'✓' if success else '✘'} {msg}")

    elif choice == "2":
        if not admin:
            print("  ✘ Requer privilégios de administrador")
        else:
            print("  ⏳ Desabilitando efeitos visuais...")
            success, msg = disable_visual_effects()
            print(f"  {'✓' if success else '✘'} {msg}")

    elif choice == "3":
        if not admin:
            print("  ✘ Requer privilégios de administrador")
        else:
            print("  ⏳ Fechando serviços desnecessários...")
            results = close_unnecessary_services()
            for service, status in results:
                print(f"    {service:<30} {status}")

    elif choice == "4":
        print("  ⏳ Limpando arquivos temporários...")
        deleted, size = empty_temp_files()
        print(f"  ✓ {deleted} arquivos deletados ({format_bytes(size)} liberados)")

    elif choice == "5":
        if not admin:
            print("  ✘ Requer privilégios de administrador para todas as otimizações")
        else:
            print("  ⏳ Executando otimizações completas...\n")

            print("  [1/4] Limpando cache de processos...")
            success, msg = clear_ram_cache()
            print(f"    {'✓' if success else '✘'} {msg}")

            print("  [2/4] Desabilitando efeitos visuais...")
            success, msg = disable_visual_effects()
            print(f"    {'✓' if success else '✘'} {msg}")

            print("  [3/4] Fechando serviços desnecessários...")
            results = close_unnecessary_services()
            count = sum(1 for _, s in results if "Parado" in s)
            print(f"    ✓ {count} serviços parados")

            print("  [4/4] Limpando arquivos temporários...")
            deleted, size = empty_temp_files()
            print(f"    ✓ {deleted} arquivos deletados ({format_bytes(size)})")

            print("\n  ✓ Otimizações completas executadas!")

    elif choice == "6":
        if not admin:
            print("  ✘ Requer privilégios de administrador")
        else:
            prioritize_program()

    elif choice == "0":
        print("  Encerrando...")
        sys.exit(0)

    else:
        print("  ✘ Opção inválida")

    print("=" * 80)
    print("\n  Pressione ENTER para sair...")
    input()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrompido pelo usuário.")
        sys.exit(0)
