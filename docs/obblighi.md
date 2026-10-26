# Gli obblighi del sistema: `deck obligations`

Il paradigma deciso il 25/10/2026 ([architettura.md](architettura.md), 7.4 bis): l'agente è uno strumento senza
cognizione propria, ed è il sistema operativo a usarlo per il proprio funzionamento corretto. Un **obbligo** è un
dovere che il sistema dà all'agente quando succede qualcosa. Per ora gli obblighi **avvisano soltanto**: la loro
forza si decide con l'uso (task O10.T8).

Codice:
- [../deck/agentdeck/obligations.py](../deck/agentdeck/obligations.py): modello, archivio, nascita, chiusura da sé;
- [../deck/agentdeck/components/obligations.py](../deck/agentdeck/components/obligations.py): la schermata
  `/obligations`;
- [../deck/system/95-agentdeck-obligations.hook](../deck/system/95-agentdeck-obligations.hook) e
  [../deck/system/obligations-hook.sh](../deck/system/obligations-hook.sh): l'hook di pacman.

Test: [../deck/tests/test_obligations.py](../deck/tests/test_obligations.py). Indice: [README.md](README.md).

## Il primo obbligo: il profilo dei programmi nuovi

**`PROFILE_NEEDED`**, livello `warning`. Dopo l'installazione di un pacchetto, ogni programma che il pacchetto mette
in `/usr/bin` deve avere il suo profilo dell'adattatore ([adattatore.md](adattatore.md)), così le sue domande
vengono riconosciute.

1. **Nasce dal sistema, non dall'agente.** pacman, a ogni installazione e chiunque la faccia (Bash, `deck term`,
   `deck update`), esegue l'hook `95-agentdeck-obligations.hook`. Lo script, che pacman esegue come root, sta in
   `/usr/local/lib/agentdeck/`, di root, e chiama come utente `agent` `deck obligations installed
   packages=<nomi>`. Non fa mai fallire la transazione.
2. `deck` legge dal database locale di pacman (`/var/lib/pacman/local`) i programmi del pacchetto. Per ogni
   pacchetto che ha programmi senza profilo apre **un** obbligo, con il pacchetto e i programmi nei dati.
3. **Si chiude da sé** quando il sistema lo può verificare: tutti i programmi hanno il profilo
   (`resolved_by: profiles_written`), oppure il pacchetto non c'è più (`package_removed`).
4. **Altrimenti lo chiude l'agente:**
   - con `deck obligations done id=<id> note=...`, per esempio quando i programmi non fanno domande;
   - con `dismiss`, se l'obbligo non si applica, dicendo perché.

   Reinstallare un pacchetto non riapre un obbligo chiuso.

## Dove li vede l'agente

- **In ogni schermata di `deck`**, nel campo `obligations` (protocollo, sezione 6 bis,
  [protocollo.md](protocollo.md)):
  - i 5 più recenti, più un riepilogo `OBLIGATIONS_MORE` se ce ne sono altri;
  - lo stesso vale per i risultati degli strumenti MCP;
  - la schermata `/obligations` li ha tutti nei dati, con gli ultimi 10 chiusi.
- **Negli hook di Claude Code** ([claude-code.md](claude-code.md), "Autoprompting: gli hook"):
  - all'inizio della sessione;
  - dopo un comando Bash o la modifica di un file;
  - all'inizio di un turno, se sono nuovi.

```bash
deck obligations                                  # aperti e chiusi di recente
deck obligations show id=1adb3d                   # uno, con il messaggio del sistema
deck obligations done id=1adb3d note="cowsay e cowthink non fanno domande"
deck obligations dismiss id=7bd578 reason="editor a tutto schermo, si guida con term key"
```

## Formato e sicurezza

- **Archivio:** `~/.local/state/agentdeck/obligations.json` dell'utente `agent`, con tutti gli aperti e gli ultimi
  50 chiusi. Ogni obbligo ha:
  - `id`: 6 caratteri esadecimali, ricavati dal codice e dal pacchetto, quindi niente doppioni;
  - `code`, `status` (`open`, `done`, `dismissed`), `created`, `updated`, `source`;
  - `subject`: pacchetto e programmi;
  - `note` e `resolved_by`.
- **INV-4:**
  - il messaggio di un obbligo nasce sempre dal modello del suo codice, scritto in `obligations.py`. Nel testo
    entra solo un nome di pacchetto validato, che altrimenti si omette;
  - programmi, note e motivi restano nei dati;
  - una voce dell'archivio con un id o un codice non validi viene ignorata, perché l'archivio è scrivibile
    dall'agente.
- **Solo avvisi:** nessun hook blocca per un obbligo aperto.

## Verifiche del 26/10/2026

Da sessioni di Claude Code sulla Deck (`claude -p`, strumenti MCP):
- **installazione vera di `cowsay`** con l'adattatore:
  - l'hook di pacman ha aperto `PROFILE_NEEDED 1adb3d` per `cowsay` e `cowthink`;
  - l'agente lo ha ricevuto nel campo `obligations` e dall'hook dopo un comando Bash;
  - ha controllato con `deck term` che i due programmi non fanno domande, e lo ha chiuso con una nota;
  - poi `cowsay` è stato rimosso;
- **due turni:**
  - nel primo l'agente ha registrato `vim` (`obligations_installed`);
  - all'inizio del secondo l'hook del turno gli ha portato `PROFILE_NEEDED 7bd578`, che l'agente ha citato
    testualmente e scartato con il motivo.

## Prossimi obblighi possibili

Da decidere con l'uso, insieme alla forza (avviso o blocco). Ad esempio:
- documentare nel rapporto ogni modifica a `/etc`;
- verificare un servizio dopo un aggiornamento che lo riguarda;
- riscrivere un profilo che non riconosce più le domande dopo l'aggiornamento di un programma.
