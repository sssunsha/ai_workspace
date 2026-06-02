#!/usr/bin/env bash
# 启动 claude-hunter，自动初始化虚拟环境和依赖

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
OPENSSL_PREFIX="/opt/homebrew/opt/openssl@3"
FALLBACK_PYVER="3.13.3"

cd "$SCRIPT_DIR"

# 找到一个可用的 Python（有 SSL 支持）
find_python() {
    # 优先使用 pyenv 中已安装的新版本
    for ver in $(pyenv versions --bare 2>/dev/null | grep -E "^3\.(1[2-9]|[2-9][0-9])\." | sort -rV); do
        py="$HOME/.pyenv/versions/$ver/bin/python3"
        if "$py" -c "import ssl" 2>/dev/null; then
            echo "$py"
            return
        fi
    done
    # 再检查当前 python3
    if python3 -c "import ssl" 2>/dev/null; then
        echo "python3"
        return
    fi
    echo ""
}

PYTHON=$(find_python)

if [ -z "$PYTHON" ]; then
    echo "⚠️  未找到支持 SSL 的 Python，正在安装 Python ${FALLBACK_PYVER}..."
    echo "（首次安装需要几分钟，请耐心等待）"

    LDFLAGS="-L${OPENSSL_PREFIX}/lib" \
    CPPFLAGS="-I${OPENSSL_PREFIX}/include" \
    CONFIGURE_OPTS="--with-openssl=${OPENSSL_PREFIX}" \
    pyenv install "$FALLBACK_PYVER"

    pyenv local "$FALLBACK_PYVER"
    PYTHON="$HOME/.pyenv/versions/${FALLBACK_PYVER}/bin/python3"
    echo "✅ Python ${FALLBACK_PYVER} 安装完成"
fi

echo "使用 Python: $($PYTHON --version)"

# 重建 venv（如果 Python 发生了变更）
if [ -d "$VENV_DIR" ] && ! "$VENV_DIR/bin/python" -c "import ssl" 2>/dev/null; then
    echo "重建虚拟环境..."
    rm -rf "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "初始化虚拟环境..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

pip install -q -r requirements.txt

python main.py "$@"
