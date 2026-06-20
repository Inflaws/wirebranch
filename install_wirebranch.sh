#!/usr/bin/env bash
# ============================================================
#  WireBranch Suite — Linux Installer Bootstrap
#  Поддерживаемые дистрибутивы:
#    • CachyOS / Arch Linux (pacman)
#    • Debian / Ubuntu / Linux Mint (apt)
#    • Fedora / RHEL (dnf)
# ============================================================

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BOLD}${CYAN}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║   WireBranch Suite — Linux Installer ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

# ── Определение дистрибутива ──────────────────────────────
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif command -v lsb_release &>/dev/null; then
        lsb_release -si | tr '[:upper:]' '[:lower:]'
    else
        echo "unknown"
    fi
}

DISTRO=$(detect_distro)
echo -e "  Дистрибутив: ${BOLD}$DISTRO${NC}"
echo -e "  Arch: $(uname -m)"
echo ""

# ── Установка системных зависимостей ─────────────────────
install_system_deps() {
    echo -e "${YELLOW}[*] Проверка системных зависимостей...${NC}"

    case "$DISTRO" in
        cachyos|arch|manjaro|endeavouros)
            echo -e "  Менеджер пакетов: ${BOLD}pacman${NC}"
            PKGS_NEEDED=()

            command -v python3 &>/dev/null || PKGS_NEEDED+=("python")
            python3 -c "import tkinter" 2>/dev/null || PKGS_NEEDED+=("tk")
            command -v pip3 &>/dev/null || PKGS_NEEDED+=("python-pip")

            if [ ${#PKGS_NEEDED[@]} -gt 0 ]; then
                echo -e "  Устанавливаю: ${PKGS_NEEDED[*]}"
                sudo pacman -S --noconfirm "${PKGS_NEEDED[@]}"
            else
                echo -e "  ${GREEN}Все системные зависимости уже установлены${NC}"
            fi

            # PyQt5 на Arch лучше ставить из пакетов
            if ! python3 -c "import PyQt5" 2>/dev/null; then
                echo -e "  Устанавливаю python-pyqt5..."
                sudo pacman -S --noconfirm python-pyqt5 2>/dev/null || true
            fi
            ;;

        debian|ubuntu|linuxmint|pop|kali)
            echo -e "  Менеджер пакетов: ${BOLD}apt${NC}"
            sudo apt-get update -qq

            APT_PKGS=()
            command -v python3 &>/dev/null || APT_PKGS+=("python3")
            python3 -c "import tkinter" 2>/dev/null || APT_PKGS+=("python3-tk")
            command -v pip3 &>/dev/null || APT_PKGS+=("python3-pip")

            if [ ${#APT_PKGS[@]} -gt 0 ]; then
                sudo apt-get install -y "${APT_PKGS[@]}"
            fi

            if ! python3 -c "import PyQt5" 2>/dev/null; then
                sudo apt-get install -y python3-pyqt5 2>/dev/null || true
            fi
            ;;

        fedora|rhel|centos|rocky)
            echo -e "  Менеджер пакетов: ${BOLD}dnf${NC}"
            DNF_PKGS=()
            command -v python3 &>/dev/null || DNF_PKGS+=("python3")
            python3 -c "import tkinter" 2>/dev/null || DNF_PKGS+=("python3-tkinter")
            command -v pip3 &>/dev/null || DNF_PKGS+=("python3-pip")

            if [ ${#DNF_PKGS[@]} -gt 0 ]; then
                sudo dnf install -y "${DNF_PKGS[@]}"
            fi

            if ! python3 -c "import PyQt5" 2>/dev/null; then
                sudo dnf install -y python3-qt5 2>/dev/null || true
            fi
            ;;

        *)
            echo -e "${YELLOW}  ⚠ Дистрибутив '$DISTRO' не распознан, пропускаю системные пакеты.${NC}"
            echo -e "  Убедитесь, что установлены: python3, python3-tk, python3-pip"
            ;;
    esac
}

# ── Проверка Python ───────────────────────────────────────
check_python() {
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}[ERROR] python3 не найден!${NC}"
        exit 1
    fi

    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

    echo -e "  ${GREEN}Python $PY_VER найден${NC}"

    if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]); then
        echo -e "${RED}[ERROR] Требуется Python 3.8+. Установлен $PY_VER${NC}"
        exit 1
    fi
}

# ── Установка pip-пакетов ──────────────────────────────────
install_pip_packages() {
    echo -e "\n${YELLOW}[*] Установка Python пакетов через pip...${NC}"

    PIP_CMD="pip3"
    command -v pip3 &>/dev/null || PIP_CMD="python3 -m pip"

    # Определяем флаги для pip (--break-system-packages нужен на Debian 12+ / Ubuntu 23+)
    PIP_FLAGS=""
    if python3 -m pip install --help 2>&1 | grep -q "break-system-packages"; then
        # Только если не в venv и есть externally-managed
        if python3 -c "import sys; exit(0 if sys.prefix != sys.base_prefix else 1)" 2>/dev/null; then
            PIP_FLAGS=""  # В venv — без флага
        elif [ -f "$(python3 -c 'import sysconfig; print(sysconfig.get_path("data"))')/EXTERNALLY-MANAGED" ] 2>/dev/null; then
            PIP_FLAGS="--break-system-packages"
        fi
    fi

    PACKAGES=("customtkinter" "PyQt5" "NodeGraphQt")

    for pkg in "${PACKAGES[@]}"; do
        if python3 -c "import ${pkg,,}" 2>/dev/null; then
            echo -e "  ${GREEN}✓ $pkg — уже установлен${NC}"
        else
            echo -e "  ⬇  Устанавливаю $pkg..."
            $PIP_CMD install "$pkg" --quiet $PIP_FLAGS && \
                echo -e "  ${GREEN}✓ $pkg установлен${NC}" || \
                echo -e "  ${YELLOW}⚠  $pkg не установился (попробуйте вручную)${NC}"
        fi
    done
}

# ── Запуск GUI инсталлятора ───────────────────────────────
launch_gui() {
    INSTALLER_PY="$SCRIPT_DIR/install_wirebranch.py"

    if [ ! -f "$INSTALLER_PY" ]; then
        echo -e "${RED}[ERROR] install_wirebranch.py не найден рядом со скриптом!${NC}"
        echo -e "  Ожидался путь: $INSTALLER_PY"
        exit 1
    fi

    echo -e "\n${GREEN}[*] Запуск графического инсталлятора...${NC}\n"
    python3 "$INSTALLER_PY"
}

# ── Главный поток ─────────────────────────────────────────
install_system_deps
check_python
install_pip_packages
launch_gui

echo -e "\n${GREEN}${BOLD}Установка завершена!${NC}"
