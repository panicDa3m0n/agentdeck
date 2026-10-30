# Componenti di AgentDeck: indice

Dal 30/10/2026, per decisione del proprietario, lo sviluppo di AgentDeck si organizza per **componenti**. Un
componente è un organo del sistema: una o più sezioni tecniche e architetturali legate allo stesso scopo. Ogni
componente ha qui una scheda con:
- lo scopo;
- come funziona oggi;
- i comandi collegati;
- il confronto fra **previsto** e **fatto**;
- le issue aperte e gli obiettivi tecnici e architetturali.

La governance (`~/claude-rules/bin/wf.sh`) è **spenta** su questo progetto dallo stesso giorno. I suoi file
(`.claude/workflow/`, `PROGETTO.md`, `ROADMAP.md`) restano nel repository solo per controllo e per un'eventuale
riattivazione. Le sigle O*n*.T*n* (obiettivi e task), N*n* (annotazioni), P*n* (trappole), R*n* (richieste) e
A*n*.*n* (proposte di [../architettura.md](../architettura.md)) che compaiono nelle schede rimandano a quella storia.

**Come si tiene aggiornato.** Una modifica a un componente aggiorna la sua scheda nello stesso commit: stato,
previsto/fatto, issue (INV-9). Quando nasce un componente nuovo si aggiunge qui. Gli stati sono:

| Stato | Significato |
|---|---|
| **attivo** | Fa il suo lavoro sulla Deck, provato davvero; può avere issue minori |
| **parziale** | Una parte funziona, una parte prevista non c'è ancora o non è provata dal vero |
| **previsto** | Solo progettato o proposto: nessun codice in uso |
| **sospeso** | C'è, ma è spento di proposito (il motivo è nella scheda) |

## I componenti

Stato al 30/10/2026, versione 0.5.14.

| # | Componente (organo) | Stato | Comandi principali | Cosa manca o va guardato |
|---|---|---|---|---|
| 01 | [Sistema base e avvio](01-sistema-base.md), lo scheletro | attivo | `deck status` | Avvio robusto (A1.*), safe mode |
| 02 | [Accesso e rete](02-accesso-rete.md), i polmoni | attivo | `deck network`, `ssh agentdeck` | sshguard protetto (O12.T2), ritenta del Wi-Fi (O12.T3), firewall |
| 03 | [Reversibilità: snapshot, aggiornamenti, backup](03-reversibilita.md), il sistema immunitario | parziale | `deck snapshot`, `deck update` | Backup fuori dalla Deck, stati buoni, politica degli snapshot |
| 04 | [Interfaccia agentica `deck`](04-interfaccia-deck.md), il sistema nervoso | attivo | `deck`, `deck mcp`, `deck service`, `deck logs` | API native e servizio varlink (A2.2-A2.3), `deck package` e `deck access` |
| 05 | [Adattatore dei programmi interattivi](05-adattatore.md), le mani | attivo | `deck term`, `deck obligations` | Menu a frecce (N61), obblighi troppo larghi (N65), sincronizzazione dei profili |
| 06 | [Regole, guardia e autoprompting](06-regole-guardia.md), la coscienza | attivo | hook di Claude Code, `CLAUDE.md` di sistema | Limiti tecnici per l'agente interno, falsi positivi, arbitro e tabella delle richieste |
| 07 | [Harness: Claude Code e sessioni](07-harness-claude.md), il corpo dell'agente | attivo | `deck claude`, `deck claude/version` | Prova con Remote Control (O12.T5), versione 2.1.312 disponibile |
| 08 | [Schermo e interfacce effimere](08-schermo.md), il volto | parziale | `deck claude` (pagina), servizio `agentdeck-ui` | Prova al tocco (O15.T3), schermo terminale spento |
| 09 | [Servizi ospitati](09-servizi.md), gli organi del proprietario | parziale | `deck service`, `agentdeck-servizio@<nome>` | `deck servizi` (O13.T1), snapshot di `@servizi`, firewall |
| 10 | [Sviluppo e rilascio](10-sviluppo-rilascio.md), la crescita | attivo | `deck release`, `git`, `gh` | Governance spenta, ora le schede dei componenti |
| 11 | [Agente interno e agenti di background](11-agente-interno.md), l'autonomia | parziale, timer **sospeso** | `deck agent` | Limiti nella guardia, poi il timer, poi gli agenti di background |
| 12 | [Canali con il proprietario](12-canali-proprietario.md), la voce | parziale | `deck secret`, `deck ask`, `deck telegram` | Bot Telegram (R8), tabella delle richieste (O19.T2) |
| 13 | [Brain: memoria e contesto](13-brain.md), la memoria | parziale | `brain`, `brain mcp` | Pacchetti di contesto, ricerca ibrida, manutenzione, copia del database |
| 14 | [Osservabilità ed eventi](14-osservabilita.md), i sensi | parziale | `deck status`, `deck logs` | Raccoglitore di eventi, registro delle azioni, avvisi con storia |
| 15 | [Sicurezza, identità e privilegi](15-sicurezza.md), le difese | parziale | `deck secret` | Broker dei privilegi, identità per agente, segreti cifrati, audit |

## Priorità tecniche aperte (30/10/2026)

1. **Agente interno sotto controllo** (11, 06): limiti tecnici nella guardia per l'agente interno, prima di
   riaccendere il timer. Il 30/10 alle 00:17 ha aggiornato e riavviato la Deck da solo.
2. **Agenti di background via MiniMax** (11, 13): manutenzione nei momenti di inattività, richiesta del proprietario
   del 30/10. Dipendono dal punto 1.
3. **Brain** (13): pacchetti di contesto automatici (manca la decisione su INV-4, strada A o B), copia del database,
   ricerca ibrida con modelli locali da scegliere insieme (ADR su INV-7).
4. **Bot Telegram** (12): la consegna di token e chat id si fa con `deck secret request name=telegram`.
5. **Copia fuori dalla Deck e safe mode** (03, 01): ultimi punti del piano del 29/10.

## Documenti di riferimento

- [../piano.md](../piano.md): il piano del 29/10/2026, punto per punto, con le decisioni.
- [../architettura.md](../architettura.md): lo studio agent-first, con le proposte A*n*.*n* e le decisioni D1-D8.
- [../README.md](../README.md): l'indice dei documenti per argomento.
- [../../CHANGELOG.md](../../CHANGELOG.md): la storia delle versioni.
