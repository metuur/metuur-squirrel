---
description: Instala el daemon de recordatorios macOS (launchd). Solo macOS. Uso: /sq-reminders-install
allowed-tools: [Bash]
---

# /sq-reminders-install

Instala y activa el daemon de recordatorios de squirrel en macOS.

## Paso 1: Verificar OS

```bash
uname
```

Si no es `Darwin`, mostrar: "ℹ️  El daemon de recordatorios solo está disponible en macOS." y detener.

## Paso 2: Localizar el script de instalación

```bash
INSTALL_SCRIPT=$(find "${HOME}/.claude" "${HOME}/others" \
    -name install.sh -path "*/squirrel/companions/macos-reminders/*" \
    2>/dev/null | head -1)
[ -z "$INSTALL_SCRIPT" ] && echo "❌ install.sh no encontrado. Verificá la instalación del plugin." && exit 1
```

<!-- @spec INT-010 -->
## Paso 3: Ejecutar el instalador

```bash
bash "$INSTALL_SCRIPT"
```

Mostrar la salida completa del instalador al usuario.

Si el exit code es != 0, mostrar el error y sugerir revisar `~/.squirrel/reminders-daemon.log`.
