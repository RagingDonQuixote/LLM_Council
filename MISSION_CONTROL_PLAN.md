# Mission Control Center: LLM Council Architektur-Plan

Dieses Dokument beschreibt die geplante Erweiterung des LLM Council zu einem dynamischen, agentenbasierten Orchestrierungssystem. Der Fokus liegt auf der Zusammenarbeit zwischen dem Human Chair und dem AI Council durch einen visuellen Ereignisbaum.

## 1. Vision: Das "Mission Control" Layout
Die Benutzeroberfläche wird von einem reinen Chat in ein dreigeteiltes Kontrollzentrum transformiert:

*   **Links: Kommunikations-Panel (Chat)**
    *   Interaktion mit dem Council.
    *   Echtzeit-Output der Modelle.
*   **Mitte: Strategie-Panel (Ereignisbaum / Blueprint)**
    *   Visuelle Darstellung des Projektverlaufs.
    *   Knotenpunkte repräsentieren Aufgaben, Sub-Councils oder Breakpoints.
*   **Rechts: Ressourcen-Panel (Member & Skills)**
    *   Anzeige der aktiven Modelle und deren Fähigkeiten (Skills).
    *   Status der Token-Nutzung und Performance.

---

## 2. Kernkonzepte

### A. Stage 0: Der Council Blueprint
In der Vorbereitungsphase (Stage 0) erarbeiten der Human Chair und der AI Chair gemeinsam den Schlachtplan:
*   Der AI Chair schlägt eine Struktur (Baum) vor.
*   Der Human Chair definiert **Breakpoints** an kritischen Stellen.
*   Festlegung der benötigten Ressourcen (Modelle mit spezifischen Skills wie Vision, Coding, Audit).

### B. Der Dynamische Ereignisbaum (Ereignisbaum)
Jeder Knoten im Baum ist ein logischer Schritt:
*   **Aufgaben-Knoten:** Delegation an ein oder mehrere Modelle.
*   **Entscheidungs-Knoten:** Auswahl zwischen verschiedenen Pfaden (z.B. Kosten vs. Qualität).
*   **Breakpoint-Knoten:** Erzwungener Stopp für menschliches Feedback.

### C. Human-in-the-Loop: Breakpoint-Aktionen
An jedem Breakpoint hat der Human Chair drei primäre Optionen:
1.  **Absegnen (Approve):** Das Ergebnis ist korrekt, der Council macht am nächsten Knoten weiter.
2.  **Steuern (Input):** Zusätzliche Anweisungen geben, die als "High Priority" in den Kontext der folgenden Stages einfließen.
3.  **Abbrechen & Neustart (Reset):** Den aktuellen Ast des Baumes verwerfen und mit geänderten Parametern (andere Modelle, andere Strategie) neu beginnen.

---

## 3. Technische Anforderungen

### Backend (Python/FastAPI/SQLite)
*   **State Snapshots:** Speicherung des kompletten Zustands (Prompt, Modelle, Ergebnisse) pro Knoten.
*   **Skill-Matrix:** Erweiterte Datenbank für Modelle mit detaillierten Fähigkeits-Tags.
*   **Branching-Logik:** Unterstützung für parallele oder alternative Pfade im Baum.

### Frontend (React)
*   **Flow-Visualisierung:** Integration einer Library (z.B. React Flow) zur Darstellung des Baums.
*   **Prompt Explorer 2.0:** Kachelansicht mit Ratings, Statistiken und Tag-Filtern (UND/ODER Logik).
*   **Stage-Synchronisation:** Echtzeit-Update der UI, wenn das Backend eine neue Stage oder einen Knoten erreicht.

---

## 4. Taskliste zur Umsetzung

### Phase 1: Datenbasis & Prompt-Management [In Arbeit]
- [x] SQLite-Erweiterung für `prompts` Tabelle.
- [x] CRUD API für Prompts.
- [x] UI: Prompt-Manager Tab in den Settings.
- [x] Vorbefüllung mit Beispiel-Prompts & Tags.
- [ ] **[Neu]** Erweiterung der `prompts` Tabelle um `rating` (Integer) und `usage_count` (Integer).

### Phase 2: UI Transformation (Mission Control)
- [ ] Implementierung des dreigeteilten Hauptlayouts.
- [ ] Integration einer Flow-Library für den Ereignisbaum in der Mitte.
- [ ] Entwicklung der Breakpoint-UI (Interaktions-Karten im Chat).
- [ ] Prompt Explorer: Kachel- vs. Vollbildmodus oberhalb des Chats.
- [ ] Tag-Filter mit UND/ODER Logik implementieren.

### Phase 3: Der Ereignisbaum & Stage-Logik
- [ ] Stage 0: Blueprint-Generator (AI Chair erstellt Baum-Vorschlag).
- [ ] Backend-Logik für Breakpoints und "Human-Approval".
- [ ] Skill-Based Routing: Automatisches Buchen von Modellen basierend auf Task-Anforderungen.
- [ ] Snapshot-System für "Backtracking" im Baum.

### Phase 4: Monitoring & Analytics
- [ ] Statistik-Anzeige für Prompt-Nutzung und Board-Erfolg.
- [ ] Visualisierung der "Prompt Evolution" (Stage 0 vs. Stage 4).
- [ ] Kostenschätzung pro Blueprint-Pfad.
