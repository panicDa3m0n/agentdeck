# 15 Sicurezza, identità e privilegi: le difese

**Stato:** parziale. Le difese di base ci sono; identità per agente, broker dei privilegi, segreti cifrati e audit
sono previsti. Indice: [README.md](README.md).

## Scopo

Chi può fare cosa sulla Deck, e con quali prove: l'agente, i suoi sotto-agenti, i servizi e il proprietario.
Segreti custoditi, privilegi limitati, traccia di tutto.

## Come funziona oggi

- **Un solo utente agente**, `agent`, con `sudo` senza password, e una sola chiave SSH senza scadenza
  (componente 02).
- **Protezioni a livello di agente:** la guardia (componente 06) per accesso, cose del proprietario e versioni
  fissate. Le azioni distruttive di `deck` vanno in due passi con anteprima.
- **Segreti:** file con permessi 600 in `~/.config/agentdeck/` e `secrets/`, consegnati con la pagina monouso
  (componente 12). Mai nel repository (INV-6), mai in chat, mai nelle memorie (il Brain li rifiuta). Non sono
  cifrati sul disco.
- **Credenziali del proprietario**: login di Claude, chiavi SSH, login GitHub. L'agente le usa ma non le legge
  (ADR-0001, ADR-0002).

## Previsto e fatto

| Previsto | Da dove | Fatto |
|---|---|---|
| Studio di identità, permessi, isolamento e segreti | O8.T3 | ✔ in [../architettura.md](../architettura.md), sezione 3 |
| Politica ADR-0001 e protezione delle cose del proprietario | O12.T1, O19.T1 | ✔ |
| Segreti consegnati senza chat | O23.T1 | ✔ |
| Identità degli agenti: un nome e una chiave o un certificato per agente e sessione | A3.2, D8 | ✖ |
| Broker dei privilegi al posto di `sudo ALL` | A3.3, D3 | ✖ |
| polkit per il gruppo degli agenti | A3.4 | ✖ |
| Isolamento per default dei lavori (sandbox) | A3.5 | ✖ |
| `deck secrets` cifrati con `systemd-creds` e TPM | A3.6, A6.6 | ✖ (oggi file 600 in chiaro) |
| Secure Boot con chiavi nostre | A3.7 | ✖ più avanti |
| `auditd` con regole sull'agente | A3.8 | ✖ |

## Issue aperte

- L'agente interno ha gli stessi privilegi dell'agente principale: `sudo` senza password e tutto `deck`. Il 30/10
  ha riavviato la Deck da solo (componente 11). È il caso concreto che rende urgenti A3.2 e A3.3.
- I segreti sono in chiaro su disco e leggibili da qualunque processo dell'utente `agent`.

## Obiettivi tecnici

1. Prima, in piccolo, i limiti della guardia per l'agente interno (componente 06). È la forma leggera di A3.2.
2. Poi un utente separato per gli agenti di background, con permessi minimi e un broker per le azioni privilegiate
   (A3.3).
3. Segreti cifrati con `systemd-creds` (A3.6).
