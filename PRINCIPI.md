# Principi del progetto

Steam Deck trasformata in un server domestico gestito interamente da un agente AI.
Ogni scelta tecnica si verifica contro questi principi. Indice della documentazione: [docs/README.md](docs/README.md).

## 1. Agent-first

L'agente è l'utente primario del sistema. L'umano è al massimo uno spettatore.

- **Tutto comandabile via testo, CLI o API.** Nessuna impostazione raggiungibile solo da interfaccia
  grafica, nessuna procedura guidata, nessuna finestra di conferma.
- **Tutto osservabile in formato strutturato** (JSON dove possibile), schermo compreso: l'agente può
  leggere cosa è aperto e farne uno screenshot.
- **Zero attriti per chi opera:** niente richieste di password, blocco schermo o sospensione.
- **Reti di sicurezza al posto dei blocchi preventivi:** invece di chiedere "sei sicuro?", il sistema
  permette di tornare indietro (snapshot e rollback).
- **Agent-first non vuol dire aperto a chiunque:** le difese verso l'esterno restano. Si toglie
  l'attrito verso l'agente, non verso gli attaccanti.
- **La grafica è un canale dell'agente verso l'umano** (dashboard, riepiloghi delle sessioni, comandi
  mostrati a schermo), non un'interfaccia per far comandare l'umano.

## 2. Sviluppo incrementale

- Si risolve solo ciò che serve al passo successivo, senza progettare tutto in anticipo.
- Ogni intervento si discute prima di farlo.
- Si preferiscono scelte reversibili; quelle difficili da cambiare si decidono quando arrivano.

## 3. Visione: AgentDeck

- **Ogni componente del sistema viene riprogettato per l'uso agentico.** Si prende spunto dalle funzioni
  di un OS come macOS (impostazioni, monitor attività, aggiornamenti, Time Machine, notifiche, …) e le si
  converte in funzioni e gestione adatte a un agente.
- **Doppio ruolo dell'agente:** chi sviluppa le soluzioni è anche l'agente che usa AgentDeck. Problemi e
  bisogni emergono così dall'uso reale, non da ipotesi.
- **Agente interno, più avanti:** solo dopo un insieme minimo di componenti. Basato su API cloud, non su
  un modello locale, così le risorse della Deck restano per server e sviluppo.
- **Obiettivo finale:** una o più sessioni Claude Code dedicate ad AgentDeck, con integrazione completa
  del sistema (tramite configurazione di Claude Code o un fork). AgentDeck diventa un sistema operativo
  nativo per Claude Code.

## 4. Livello di intervento

Non si riscrive Linux: il sistema si modifica **quanto serve, al livello più alto che risolve il
problema** (invariante INV-10). Kernel e componenti di base di Arch restano quelli originali; quello che
rende AgentDeck un sistema operativo per agenti si costruisce sopra.

| Livello | Cosa vuol dire | Esempio in AgentDeck | Quando |
|---|---|---|---|
| 1. Configurazione | Scegliere pacchetti e impostare come si comportano | Btrfs con snapshot, utente `agent`, rete, niente sospensione | Sempre, è il primo strumento |
| 2. Strato agentico nostro | Programmi nostri che usano gli strumenti reali di Linux e li traducono per l'agente | `deck`: dietro chiama snapper, systemctl, iwd e risponde con schermate JSON e istruzioni | Il cuore del progetto |
| 3. Sostituire componenti | Un pezzo nostro al posto di uno standard | La grafica: un nostro ambiente al posto di un desktop classico; servizi nostri sempre attivi | Quando uno standard non va bene |
| 4. Modificare il codice di base | Patch al kernel o a programmi di sistema, pacchetti ricompilati | Driver specifici della Deck per ventola o limite di batteria | Solo per un bisogno reale e con decisione esplicita dell'utente |

Perché salire di livello solo quando serve:

- **Aggiornamenti:** finché il codice di base resta originale, Arch continua ad aggiornare sicurezza,
  driver e kernel. Ogni modifica profonda è una versione nostra da mantenere per sempre.
- **Reversibilità:** configurazione e strato nostro si annullano facilmente; una patch al kernel no.
- **È così anche negli OS conosciuti:** macOS ha sotto un nucleo Unix (Darwin) e sopra gli strati di
  Apple; Android usa il kernel Linux con sopra un mondo tutto suo. AgentDeck: Linux e Arch sotto, sopra lo
  strato agentico (interfaccia a schermate, autoprompting, poi grafica e integrazione con Claude Code).

## Decisioni prese

| Data | Decisione | Motivo |
|---|---|---|
| 2026-10-25 | Si cancella tutto: la Deck serve solo come hardware | Niente da conservare |
| 2026-10-25 | Base: Arch Linux | Velocità, kernel recenti, ottimo supporto alla Deck |
| 2026-10-25 | Interfaccia grafica presente, minimale e comandabile da script | L'agente mostra comandi, dashboard e riepiloghi all'umano |
| 2026-10-25 | Installazione: Arch live da chiavetta, poi installazione via SSH passo per passo | Semplice, ispezionabile, niente cancellazioni alla cieca |
| 2026-10-25 | Filesystem Btrfs con snapshot automatici | Rete di sicurezza per le modifiche dell'agente |
| 2026-10-25 | Utente `agent` con sudo senza password | Niente attriti; alcuni strumenti Arch rifiutano root |
| 2026-10-25 | Niente sospensione né blocco, accesso automatico | Server sempre attivo, nessun gesto umano richiesto |
| 2026-10-25 | Sistema sull'NVMe da 2 TB; la microSD da 1 TB per ora non si tocca | Il suo uso (backup, dati poco usati) si decide più avanti |
| 2026-10-25 | Niente cifratura del disco | Avvio senza password; rischio accettato: chi ruba la Deck legge il disco |
| 2026-10-25 | Interfaccia agentica con interattività e autoprompting | Ogni risposta è una schermata JSON con istruzioni per il contesto |
| 2026-10-25 | Behaviour Governance attiva, versioni MAJOR.MINOR.PATCH | Tappe verificabili e storia leggibile; vedi [docs/sviluppo.md](docs/sviluppo.md) |
| 2026-10-25 | Remote privato `panicDa3m0n/agentdeck`, ogni versione pubblicata | Storia granulare e documentazione progettuale sempre online |
| 2026-10-25 | Documentazione per argomento in `docs/`, indicizzata e collegata al codice | Il sistema resta comprensibile a ogni agente che ci lavora |
| 2026-10-25 | Si interviene al livello più alto che risolve il problema | Aggiornamenti di Arch preservati, modifiche reversibili |
| 2026-10-25 | IP stabile con `SendRelease=no` | Il router riassegna sempre lo stesso indirizzo (`192.168.1.49`) |

## Direzioni da confermare quando ci arriviamo

- Compositor grafico: Sway (leggero, comandabile via IPC), con interfacce nostre dentro, per esempio
  dashboard web a schermo intero.
- Collegamento di rete via cavo USB-C con il Mac, mettendo la Deck in modalità periferica.
