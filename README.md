# Kairon Alert

Te avisa por Telegram cuando aparece un usado nuevo **con stock** en Kairon Music.

## 1. Crear tu bot de Telegram

1. Abrí Telegram y buscá **@BotFather** (tiene tilde azul).
2. Mandale `/newbot`.
3. Elegí un nombre, por ejemplo `Kairon Alert`.
4. Elegí un usuario que termine en `bot`, por ejemplo `alertas_kairon_tunombre_bot`.
5. BotFather te va a dar un token. Copialo, pero no lo compartas.
6. Abrí el bot que acabás de crear y apretá **Start**.

## 2. Conseguir tu chat ID

Con el bot ya iniciado, abrí en el navegador (reemplazá `TU_TOKEN`):

`https://api.telegram.org/botTU_TOKEN/getUpdates`

En el resultado buscá algo como `"chat":{"id":123456789`. Ese número es tu `TELEGRAM_CHAT_ID`.

## 3. Configurar y probar

1. Copiá `.env.example` y renombralo a `.env`.
2. Pegá el token y tu chat ID.
3. En la carpeta del proyecto ejecutá:

```bash
python3 monitor.py --once --notify-start
```

Te tiene que llegar el mensaje de conexión correcta. La primera ejecución crea una base de productos actuales y no manda una alerta por cada uno.

## 4. Dejarlo corriendo

En la misma carpeta:

```bash
python3 monitor.py
```

Revisa cada 5 minutos por defecto. Para detenerlo, presioná `Ctrl + C`.

## Para que funcione 24/7

La carpeta incluye `.github/workflows/kairon-alert.yml`. Al subirla a un repositorio privado de GitHub y configurar los secretos `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`, GitHub ejecuta el monitor periódicamente aunque tu PC esté apagada. También puede probarse manualmente desde **Actions > Kairon Alert > Run workflow**.

## Seguridad

- No compartas el token de BotFather.
- `.env` y `state.json` están excluidos de Git.
- El monitor usa la página pública de Kairon y la API oficial de Telegram.
