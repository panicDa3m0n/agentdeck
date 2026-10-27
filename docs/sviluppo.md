# Sviluppo: repository, versioni, governance

Come è organizzato il lavoro su AgentDeck: dove sta il codice, come si versiona e si pubblica, quali regole
guidano ogni modifica. Indice: [README.md](README.md).

## Repository

- **Locale:** `/Users/snj/linuxai-steamdeck` sul Mac. Struttura in [../README.md](../README.md).
- **Remote:** <https://github.com/panicDa3m0n/agentdeck>, **privato**, account personale `panicDa3m0n`.
- **Identità dei commit:** Davide `<davideditrani94@gmail.com>`, impostata solo per questo repository
  (`git config --local`). L'identità globale del Mac resta quella SNJ.
- **Mai nel repository:** credenziali (`secrets/`) e file scaricati (`cache/`), esclusi da
  [../.gitignore](../.gitignore) (INV-6).

### Pubblicare senza cambiare account GitHub

Sul Mac `gh` ha due account e quello attivo di solito è SNJ (`DavDit94`). Il gestore di credenziali di `gh`
fornisce solo le credenziali dell'account attivo, e un nome utente nell'URL non basta. Per questo il
repository ha un credential helper **locale** che chiede a `gh` il token di `panicDa3m0n` al momento,
senza salvarlo da nessuna parte:

```
git config --local credential.https://github.com.helper ""
git config --local --add credential.https://github.com.helper \
  '!f() { test "$1" = get || exit 0; echo username=panicDa3m0n; echo "password=$(gh auth token --user panicDa3m0n)"; }; f'
```

Così `git push` pubblica sempre come `panicDa3m0n`, qualunque sia l'account attivo in `gh`. Non va rimosso
(trappola P1 della governance).

## GitHub dalla Deck (ADR-0002, O14.T2)

**La decisione dell'utente, 26/10/2026.** I progetti su cui l'agente lavora sulla Deck, come `/home/agent/frugale`,
si pubblicano dalla Deck stessa, senza passare dal Mac. La Deck ha un suo login GitHub con l'account personale
`panicDa3m0n`, mai quello SNJ. I repository sono privati finché l'utente non decide altro.

**Com'è stato fatto, il 26/10/2026:**
1. snapshot 92 "prima di github-cli e del login GitHub", poi `sudo pacman -S --needed --noconfirm github-cli`
   (2.102.1);
2. dalla sessione del Mac, attraverso l'adattatore (`deck term`, sessione `2b6e`):
   `gh auth login --hostname github.com --git-protocol https --web --skip-ssh-key`, rispondendo sì a "usare il
   login anche per git";
3. l'utente ha inserito il codice monouso su <https://github.com/login/device>: né il codice né il token passano
   dalla chat.

**Cosa c'è sulla Deck, per l'utente `agent`:**
- `~/.config/gh/hosts.yml`, permessi 600: il login di `gh` per `github.com` (`gh auth status`: account
  `panicDa3m0n`, protocollo git `https`);
- nella configurazione globale di git `credential.https://github.com.helper` = `!/usr/bin/gh auth git-credential`:
  `git push` verso `https://github.com/...` usa quel login da sé.

**Come lavora l'agente:** crea il repository con `gh repo create panicDa3m0n/<nome> --private`, aggiunge il
remote `https://github.com/panicDa3m0n/<nome>.git` e pubblica senza chiedere. Il login è una credenziale
dell'utente (ADR-0001): l'agente lo usa attraverso git e `gh` ma non lo legge né lo copia. Leggere
`~/.config/gh/hosts.yml`, `gh auth token`, `gh auth status --show-token`, `gh auth login`, `gh auth refresh` e
`gh auth logout` fanno chiedere il permesso all'utente
([../deck/agentdeck/ownership.py](../deck/agentdeck/ownership.py)); la regola per l'agente sta in
[../deck/claude/CLAUDE.template.md](../deck/claude/CLAUDE.template.md).

**Per togliere l'accesso:** `gh auth logout` sulla Deck, oppure si revoca l'applicazione "GitHub CLI" dalle
impostazioni dell'account `panicDa3m0n` su GitHub (Applications, Authorized OAuth Apps).

## Versioni

- Schema **MAJOR.MINOR.PATCH** gestito dalla governance: il terzo numero sale a ogni task completata, il
  secondo a ogni ciclo chiuso, il primo solo con il sì dell'utente.
- Il numero corrente sta in [../VERSION](../VERSION); la storia in [../CHANGELOG.md](../CHANGELOG.md).
- **Ogni versione si pubblica appena chiusa** (INV-8): commit di chiusura, tag `v<versione>`, push di
  commit e tag.

```bash
git tag -a v0.1.3 -m "Versione 0.1.3: …"
git push origin main && git push origin v0.1.3
```

## Governance

Il progetto usa Behaviour Governance: roadmap per cicli, obiettivi e task con un gate verificabile,
invarianti controllate a ogni passo.

- [../PROGETTO.md](../PROGETTO.md): dossier di progetto (descrizione, verifica, dettagli).
- [../ROADMAP.md](../ROADMAP.md): obiettivi e task del ciclo in corso, annotazioni.
- `.claude/workflow/`: stato della governance (invarianti, trappole, registro).

Questi file sono **generati**: si cambiano solo con i comandi `~/claude-rules/bin/wf.sh`, mai a mano.

Le invarianti in vigore riguardano:
- accesso dell'agente sempre garantito;
- tutto utilizzabile da un agente;
- modifiche reversibili con snapshot;
- canale delle istruzioni pulito;
- difese verso l'esterno;
- niente credenziali in git;
- stack imposto;
- pubblicazione di ogni versione;
- documentazione completa;
- intervento al livello più alto.

Il testo completo è in `.claude/workflow/invariants.json`, e i principi da cui nascono sono in
[../PRINCIPI.md](../PRINCIPI.md).

## Documentazione (INV-9)

- Un documento per argomento in `docs/`, elencato nell'indice [README.md](README.md).
- Ogni script ha nell'intestazione il link al suo documento, e ogni documento elenca il codice che descrive.
- Una modifica non è conclusa finché la documentazione non la riflette: codice e documento cambiano nello
  stesso commit.

## Note sugli strumenti del Mac

- `git` in `/usr/local/bin` è la versione 2.13: per esempio `git init -b` non esiste.
- La shell del Mac è zsh, che non divide in parole una variabile con più opzioni (`$OPZIONI`). Per i
  comandi SSH si usa un alias in `~/.ssh/config` oppure le opzioni scritte per esteso.
