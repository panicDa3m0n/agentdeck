# Principi del progetto

Steam Deck trasformata in un server domestico gestito interamente da un agente AI.
Ogni scelta tecnica si verifica contro questi principi.

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

## Direzioni da confermare quando ci arriviamo

- Compositor grafico: Sway (leggero, comandabile via IPC), con interfacce nostre dentro, per esempio
  dashboard web a schermo intero.
- Collegamento di rete via cavo USB-C con il Mac, mettendo la Deck in modalità periferica.
