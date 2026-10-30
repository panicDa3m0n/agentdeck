# 05 Adattatore dei programmi interattivi: le mani

**Stato:** attivo. Indice: [README.md](README.md).

## Scopo

Far usare all'agente i programmi che fanno domande (pacman, `gh`, `ssh-keygen`…) senza restare bloccato: il
programma gira in un terminale che vede solo l'agente, e domanda, opzioni e dati tornano come schermata (INV-2).

## Come funziona oggi

- **`deck term`** ([../adattatore.md](../adattatore.md),
  [../../deck/agentdeck/term.py](../../deck/agentdeck/term.py)): sessioni tmux con `start`, `show`, `answer`,
  `choose`, `key`, `wait`, `interrupt` e `close`. Lo stato del processo si legge da `/proc` (trappole P21 e P23).
  Riconosce le domande sì/no, le scelte, il testo, i segreti, i menu e i pager.
- **Profili:** quello di `pacman` integrato ([../../deck/profiles/pacman.json](../../deck/profiles/pacman.json)) e
  tre scritti dagli agenti in `~/.local/share/agentdeck/profiles` (`ssh-keygen`, `gh`, `adb`). Si scrivono con
  `profile_save` e si provano con `profile_test`.
- **Segreti:** l'adattatore rifiuta di digitare password; i segreti passano da `deck secret` (componente 12).
- **Obblighi** ([../obblighi.md](../obblighi.md)): un hook di pacman apre `PROFILE_NEEDED` per i programmi nuovi
  senza profilo. Gli obblighi viaggiano in ogni schermata di `deck` e negli hook; si chiudono con `done` o `dismiss`.

## Comandi collegati

`deck term` (`start`, `choose`, `answer`, `wait`, `close`, `profile_save`, `profile_test`), `deck obligations`
(`show`, `done`, `dismiss`).

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Adattatore con schermate JSON e profili | O10.T7 | ✔ |
| Obblighi del sistema, primo obbligo: profilo dei programmi nuovi | O10.T8 | ✔ (usato il 30/10 per `cloudflared`) |
| Programmi Go (`gh`) riconosciuti in attesa | O14.T2 (P23) | ✔ |
| Profili scritti dagli agenti sincronizzati nel repository | piano punto 5, O22.T4 | ✖ |
| Menu a frecce: opzioni sotto il cursore in `question.options` | N61 | ✖ |
| Obblighi solo per i programmi davvero nuovi (non per le librerie trascinate) | N65 | ✖ |
| Altri obblighi (`.pacnew`, servizi nuovi…) | [../obblighi.md](../obblighi.md), A4.4 | ✖ previsto |

## Issue aperte

- N61: nei menu a frecce (per esempio `gh auth login`) le opzioni sotto la riga del cursore non arrivano.
- N65: l'installazione di cage e chromium ha aperto 47 obblighi, uno per ogni pacchetto trascinato.
- I profili degli agenti vivono solo sulla Deck: una reinstallazione li perde.

## Obiettivi tecnici

1. Sincronizzazione dei profili nel repository, dentro la manutenzione ciclica (componenti 11 e 13).
2. N65: obblighi solo per i pacchetti installati esplicitamente.
