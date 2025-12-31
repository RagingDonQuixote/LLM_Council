# Konsens-Strategien & Multi-Agent Orchestrierung

Dieses Dokument beschreibt die theoretischen Grundlagen und die Roadmap für die Implementierung verschiedener Konsens-Mechanismen im LLM Council.

## 1. Übersicht der Konsens-Mechanismen

| Strategie | Prinzip | Komplexität | Anwendungsfall |
| :--- | :--- | :--- | :--- |
| **Borda-Count (Voting)** | Punktesystem für Rankings | Niedrig | Auswahl von Begriffen, Priorisierung |
| **Average Consensus** | Numerischer Durchschnitt | Niedrig | Ratings, Mengenangaben, Budgets |
| **Chairman Cut** | Entscheidung durch den Chair | Niedrig | Zeitkritische Entscheidungen, Pattsituationen |
| **Feedback-Loop** | Gezielte Korrektur von Outliern | Mittel | Harmonisierung extremer Meinungen |
| **Cluster-Consensus** | Gruppenbildung bei vielen Membern | Hoch | Skalierung auf 10+ Member |

---

## 2. Implementierungs-Roadmap (Top-Down)

Wir sollten die Strategien in Phasen implementieren, um das System stabil zu halten:

### **Phase 1: Fundament & Basis-Wahlverfahren (Kurzfristig)**
- **Mathematisches Voting (Borda-Count):** Implementierung einer Logik, die Listen von Membern konsolidiert.
- **Manual Override (Chairman Cut):** Der AI-Chair erhält die explizite Anweisung, nach Runde 2 eine Entscheidung zu erzwingen, falls kein Konsens vorliegt.
- **State Persistence:** Erweiterung des Backends, um Zwischenergebnisse der Runden (Vorschlagslisten) strukturiert zu speichern.

### **Phase 2: Dynamische Orchestrierung (Mittelfristig)**
- **Rollenbasierte Delegation:** Der Chair weist Membern Aufgaben zu (z.B. "Member A recherchiert, Member B prüft").
- **Stage 0 (Alignment):** Einführung des Dialogs zwischen Human-Chair und AI-Chair zur Planverfeinerung.
- **Context-Tracking:** Anzeige von Token-Verbrauch und Kosten im Terminal.

### **Phase 3: Adaptive Mechanismen (Langfristig)**
- **Feedback-Steuerung:** Chair erkennt "sture" Modelle und reduziert deren Gewichtung.
- **Strategie-Profile:** Vordefinierte Modi wie "Brainstorming" vs. "Striktes Protokoll" im Frontend wählbar machen.
- **Shared Workspace:** Ein persistenter Speicherbereich für den Chair, um Wissen über Runden hinweg zu verwalten.

---

## 3. Konzept: Human Chairman Dashboard

Um die Flexibilität zu erhöhen, sollte das klassische Prompt-Fenster zu einem **Dashboard** erweitert werden:

### **Vorgeschlagene Parameter-Steuerung:**
1. **Arbeitsmodus (Select):**
   - *Brainstorming:* Maximaler Output, wenig Filter.
   - *Consensus:* Fokus auf Einigung.
   - *Task-Force:* Fokus auf Arbeitsteilung.
2. **Konsens-Strenge (Slider):**
   - Von "Locker" (Chair entscheidet schnell) bis "Strikt" (Mehrere Runden bis zur Einigung).
3. **Budget-Deckel (Input):**
   - Max. Token oder Dollar-Betrag für diese Session.
4. **Member-Konfiguration:**
   - Ein/Ausschalten bestimmter Modelle während der Session.

---

## 4. Technische Vision: "The Intelligent Orchestrator"

Das Endziel ist ein System, das nicht mehr nur "Frage -> 3 Antworten -> Synthese" macht, sondern wie ein echtes Projektteam agiert. Der AI-Chair wird vom Moderator zum **Manager**, der Human-Chair vom Nutzer zum **Strategen**.
