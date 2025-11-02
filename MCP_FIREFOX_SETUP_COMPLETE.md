# Firefox MCP Server Setup

Der Firefox MCP Server wurde erfolgreich installiert und konfiguriert!

## Installierte MCP Server:
- **Playwright MCP Server** mit Firefox Support
- **Chrome DevTools MCP Server** 
- **Browser MCP Server**

## Konfiguration:
Die MCP Server sind in `.vscode/settings.json` konfiguriert:

```json
{
    "mcp.servers": {
        "playwright-firefox": {
            "command": "npx",
            "args": ["-y", "@playwright/mcp", "--browser", "firefox", "--headless"],
            "env": {}
        },
        "playwright-chrome": {
            "command": "npx", 
            "args": ["-y", "@playwright/mcp", "--browser", "chrome", "--headless"],
            "env": {}
        }
    }
}
```

## Verfügbare Browser:
- ✅ Firefox (Playwright build v1495)
- ✅ Chrome (System Installation)

## Nächste Schritte:
1. **VS Code neu starten** um die MCP Server zu aktivieren
2. Die MCP Tools sollten dann in der Copilot-Chat verfügbar sein
3. Sie können dann Browser-Automatisierung durchführen

## Test-Befehle:
```bash
# Firefox headless testen
npx @playwright/mcp --browser firefox --headless

# Chrome headless testen  
npx @playwright/mcp --browser chrome --headless
```

## Verfügbare Funktionen:
- Webseiten öffnen und navigieren
- Screenshots erstellen
- Elemente finden und klicken
- Formulare ausfüllen
- JavaScript ausführen
- PDF generieren
- Video aufnehmen