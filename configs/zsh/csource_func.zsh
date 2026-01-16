# csource - 在 zsh 中 source csh 脚本
# 用法: csource <csh-script> [args...]

csource() {
    if [ $# -eq 0 ]; then
        echo "Usage: csource <csh-script> [args...]" >&2
        return 1
    fi

    local script="$1"
    shift

    if [ ! -f "$script" ]; then
        echo "Error: script not found: $script" >&2
        return 1
    fi

    # 获取脚本绝对路径
    script=$(cd "$(dirname "$script")" && pwd)/$(basename "$script")

    # 获取执行前的环境
    local before_env=$(mktemp)
    env > "$before_env"

    # 创建临时文件存储执行后的环境
    local after_env=$(mktemp)

    # 在 csh 中执行脚本
    csh << EOCSH > /dev/null 2>&1
source "$script" $@
env > "$after_env"
EOCSH

    # 比较环境变量
    typeset -A before_vars
    while IFS='=' read -r key value; do
        if [ -n "$key" ]; then
            before_vars["$key"]="$value"
        fi
    done < "$before_env"

    while IFS='=' read -r key value; do
        if [ -n "$key" ]; then
            # 跳过内部 shell 变量
            case "$key" in
                PWD|OLDPWD|SHLVL|_|PPID|BASH_SUBSHELL|ZSH_SUBSHELL)
                    continue
                    ;;
            esac

            # 如果变量被新增或修改，导入到当前环境
            if [ "${before_vars[$key]}" != "$value" ]; then
                export "$key"="$value"
            fi
        fi
    done < "$after_env"

    # 清理临时文件
    rm -f "$before_env" "$after_env"
}
