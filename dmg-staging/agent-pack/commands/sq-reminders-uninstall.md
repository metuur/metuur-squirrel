---
description: Desinstala el daemon de recordatorios macOS. Uso: /sq-reminders-uninstall
allowed-tools: [Bash]
---

# /sq-reminders-uninstall

Detiene y desinstala el daemon de recordatorios de squirrel.

## Paso 1: Localizar el script de instalación

```bash
INSTALL_SCRIPT=$(find "${HOME}/.claude" "${HOME}/others" \
    -name install.sh -path "*/squirrel/companions/macos-reminders/*" \
    2>/dev/null | head -1)
[ -z "$INSTALL_SCRIPT" ] && echo "❌ install.sh no encontrado. Verificá la instalación del plugin." && exit 1
```

<!-- @spec INT-011 -->
## Paso 2: Ejecutar desinstalación

```bash
bash "$INSTALL_SCRIPT" --uninstall
```

Mostrar la salida completa al usuario.

Si el exit code es != 0, mostrar el error y sugerir revisar si el daemon fue instalado con `/sq-reminders-install`.
