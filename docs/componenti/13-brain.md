# 13 Brain: memoria e contesto. La memoria

**Stato:** parziale. La memoria è attiva; contesto automatico, ricerca ibrida e manutenzione sono previsti.
Indice: [README.md](README.md).

## Scopo

Il cervello dell'agente, separato da `deck` (che lavora sul sistema). Tiene la memoria fra le sessioni, con la sua
provenienza, e in futuro porta da sé nel contesto ciò che serve. È costruito a componenti isolati
([../brain.md](../brain.md), piano punto 7).

## Come funziona oggi

- **`brain` e `brain mcp`:** stesso motore e stesso protocollo di `deck`, strumenti `mcp__brain__*`.
- **`/memory`**, archivio [../../deck/agentdeck/brain/memory.py](../../deck/agentdeck/brain/memory.py):
  - pacchetti piccoli in SQLite con FTS5: id, tipo, testo fino a 1000 caratteri, etichette, stato, origine
    (sessione e messaggio, presi da sé), revisione e collegamenti;
  - azioni `search`, `show`, `save` (con le memorie simili), `edit`, `deprecate`, `restore`, `supersede`, `merge`,
    e `forget`, distruttiva e senza tracce;
  - segreti rifiutati, testi solo nei dati (INV-4).
- **Dove sta:** `~/.local/share/agentdeck/brain/brain.db`, in `@home`.
- **Chi lo usa:** tutte le sessioni di Claude Code (regola "Memory is `brain`") e l'agente interno. Il 30/10 c'erano
  8 memorie, scritte da 4 sessioni diverse, fra cui l'agente interno e una sessione del progetto `frugale`.

## Comandi collegati

`brain`, `brain /memory`, `brain memory <azione> nome=valore`, strumenti `mcp__brain__memory_*`.

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Comando e server MCP separati da `deck`, componenti isolati | O22.T1 | ✔ v0.5.13 |
| Memorie con provenienza, ricerca testuale, modifica, revisioni, accorpamenti | O22.T1 | ✔ |
| Pacchetti di contesto automatici negli hook: bacheca, ultime 3 sessioni, memorie richiamate con il numero delle scartate | O22.T2 | ✖ aspetta la decisione su INV-4 (strada A: blocco JSON di dati; strada B: solo id) |
| Riassunti delle sessioni preparati in background | piano punto 7 | ✖ (componente 11) |
| Ricerca ibrida: embedding, ricerca testuale e altre fonti, con la fonte di provenienza | O22.T3 | ✖ |
| Reranker cross-encoder multilingue locale, niente Laya | decisione del 29/10 | ✖ da provare sulla Deck e far approvare; serve l'ADR che aggiorna INV-7 |
| Manutenzione ciclica: integrità, accorpamenti, deprecazioni, profili dell'adattatore | O22.T4 | ✖ (candidata per gli agenti di background) |
| Copia del database | N71 | ✖ |
| Decidere se importare la memoria a file di Claude Code e spegnerla | N70 | ✖ con O22.T2 |

## Issue aperte

- Nessuna copia del database: `@home` non ha snapshot.
- Nessun richiamo automatico: le memorie arrivano solo se l'agente le cerca.
- Due memorie convivono: `brain` e la memoria a file di Claude Code.
- INV-7 dice ancora "nessun modello in locale": la modifica del proprietario del 29/10 va scritta in un ADR prima
  di O22.T3.

## Obiettivi tecnici

1. Decisione A o B su INV-4, poi O22.T2.
2. Copia periodica del database, anche come primo lavoro degli agenti di background.
3. ADR su INV-7, poi la prova dei modelli (embedding e reranker) sulla Deck.
