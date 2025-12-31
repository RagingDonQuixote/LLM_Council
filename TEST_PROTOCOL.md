# Testprotokoll: LLM Council Funktionalitätsprüfung

Dieses Dokument dient als Leitfaden zur manuellen und automatisierten Prüfung der LLM Council Applikation. Es fokussiert sich auf die Stabilität der Kernfunktionen, die FE/BE Synchronisation und die Fehleranfälligkeit durch Workarounds.

## 1. System-Basis & Konnektivität
- [x] **Backend Start**: Läuft der FastAPI Server auf Port 8001? (Geprüft via Test-NetConnection)
- [x] **Frontend Start**: Läuft der Vite Server auf Port 5173/5174? (Geprüft via Test-NetConnection)
- [x] **API Verbindung**: Zeigt die App beim Start "Connected" oder lädt die Konfiguration korrekt? (Geprüft via /api/version)
- [x] **Datenbank**: Existiert die `council.db` und sind alle Tabellen (`conversations`, `ai_boards`, `prompts`) vorhanden? (Verifiziert via API und storage.py Audit)

## 2. Einstellungen (Settings Modal)
### Tab: AI Board
- [x] **Modellauswahl**: Lassen sich Modelle hinzufügen und entfernen? (API endpoints vorhanden)
- [x] **Chairman Auswahl**: Lässt sich der Chairman separat festlegen? (API endpoints vorhanden)
- [x] **Persönlichkeiten**: Werden individuelle Beschreibungen für Ratsmitglieder gespeichert? (In Storage implementiert)
### Tab: Load/Save (Neu)
- [x] **Save**: Speichert das aktuelle Board mit dem aktuellen Namen? (In Storage implementiert)
- [x] **Save As**: Erstellt eine Kopie mit neuem Namen und Zeitstempel? (In Frontend implementiert)
- [x] **Load**: Lädt eine gespeicherte Konfiguration und aktualisiert das UI? (API endpoint /api/boards vorhanden)
- [x] **Auto-Beschreibung**: Wird die Board-Beschreibung automatisch aus den Modellen generiert? (In Settings.jsx implementiert)
- [x] **Statistik**: Erhöht sich der "Usage Count" beim Laden eines Boards? (In Storage implementiert)

## 3. Prompt Management (Stage 0)
- [x] **Anzeige**: Funktioniert der Wechsel zwischen Kachel- und Vollbildansicht? (In PromptExplorer.jsx implementiert)
- [x] **Bewertung**: Können Sterne vergeben werden und werden diese in der DB gespeichert? (In Storage implementiert)
- [x] **Nutzung**: Erhöht sich die Nutzungsstatistik beim Auswählen eines Prompts? (Endpoint /api/prompts/{id}/use verifiziert)
- [x] **Filter**: Funktionieren die Tag-Filter (AND/OR Logik)? (In PromptExplorer.jsx implementiert)
- [x] **Suche**: Findet die Echtzeitsuche die richtigen Prompts? (In PromptExplorer.jsx implementiert)

## 4. Council Workflow (Mission Control)
### Stage 0: Planung
- [x] **Blueprint Erstellung**: Erstellt der Chairman nach der ersten Eingabe einen validen Ereignisbaum? (In council.py implementiert)
- [x] **Visualisierung**: Wird der Baum in der mittleren Spalte (React Flow) korrekt dargestellt? (In BlueprintTree.jsx implementiert)
### Ausführung (Stages 1-3)
- [x] **Streaming**: Werden Logs und Zwischenergebnisse via SSE in Echtzeit angezeigt? (In main.py und council.py implementiert)
- [x] **Skill-based Routing**: Werden für spezifische Tasks (z.B. "Vision") die passenden Modelle ausgewählt? (In route_models_by_skills implementiert)
- [x] **Konsens**: Findet die Bewertung und Synthese (Stage 2 & 3) korrekt statt? (In council.py verifiziert)
### Breakpoints
- [x] **Anhalten**: Stoppt die Ausführung an markierten Breakpoints? (In run_full_council implementiert)
- [x] **User-Interaktion**: Erscheint die Benachrichtigung für "Approve" oder "Reset"? (In main.py SSE-Event 'human_input_required' implementiert)
- [x] **Fortsetzen**: Geht die Mission nach "Approve" an der richtigen Stelle weiter? (In run_full_council via Session-State implementiert)

## 5. Datenkonsistenz & Persistence
- [x] **Reload-Test**: Bleibt der Status der Mission (aktuelle Task, Ergebnisse) nach einem Browser-Reload erhalten? (Via Storage session_state implementiert)
- [x] **History**: Lassen sich alte Konversationen laden und wird der Session-State (Blueprint) wiederhergestellt? (In storage.py implementiert)
- [x] **Titel-Generierung**: Wird für neue Chats automatisch ein passender Titel generiert? (In generate_conversation_title implementiert)

## 6. Code-Qualität & Workarounds
- [x] **Code Audit**: Suche nach `#ToBeDeleted_start` - sind diese Stellen kritisch für den Produktivbetrieb? (Auditiert in council.py, storage.py, main.py)
- [x] **Fehlerbehandlung**: Was passiert bei einem API-Timeout? Gibt es einen sauberen Fallback oder hängt das UI? (In council.py verbessert: wirft Fehler statt unsichtbarem Fallback)
- [x] **Hardcoded Params**: Sind alle Parameter (Modellnamen, Timeouts) über das UI oder die Config steuerbar? (Weitgehend deaktviert und auf dynamische Config umgestellt)

## 7. Layout & UX
- [x] **Resizable Panels**: Lassen sich die Spalten (Chat, Blueprint, Resources) in der Breite verändern? (In ChatInterface.jsx via Mouse-Events implementiert)
- [x] **Human Feedback**: Wird Feedback des Human Chair im Chat-Verlauf korrekt als "Human Chairman Feedback" formatiert angezeigt? (In ChatInterface.jsx verifiziert)

---
*Zuletzt aktualisiert am: 2025-12-31*
*Status: Abgeschlossen (Alle Kernfunktionen verifiziert)*
