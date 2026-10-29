# Sviluppo: repository, versioni, governance

Come è organizzato il lavoro su AgentDeck: dove sta il codice, come si versiona e si pubblica, quali regole
guidano ogni modifica. Indice: [README.md](README.md).

## Repository

- **Sulla Deck, dal 29/10/2026:** `/home/agent/agentdeck/repo`. Qui gli agenti sviluppano AgentDeck, fanno
  commit e tag e pubblicano, con il login GitHub della Deck (sezione "GitHub dalla Deck"); l'identità dei commit è
  impostata con `git config --local`. Decisione dell'utente del 29/10/2026, piano punto 10 ([piano.md](piano.md)).
  La governance si usa da qui con `~/claude-rules/bin/wf.sh` (clone di `panicDa3m0n/claude-rules`).
- **Sul Mac:** `/Users/snj/linuxai-steamdeck`. Prima di lavorarci va aggiornato con `git pull`: la copia di
  riferimento è quella della Deck. Struttura in [../README.md](../README.md).
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

## Installare dalla Deck: `deck release` (O18.T1)

Il codice di [../deck/agentdeck/release.py](../deck/agentdeck/release.py) e la schermata
[../deck/agentdeck/components/release.py](../deck/agentdeck/components/release.py) installano sulla Deck un commit
del repository, e tornano indietro.

**Come sono tenute le versioni.** Ogni versione è una cartella sua, `/opt/agentdeck-versioni/<versione>-<commit>`,
estratta con `git archive` (solo il lavoro nel commit, mai le modifiche non salvate), con `VERSION`, il
`claude/CLAUDE.md` generato con le invarianti di quel commit e un `RELEASE.json` (versione, commit, quando è stata
installata). `/opt/agentdeck` è un collegamento simbolico alla versione attiva. Si cambia con uno scambio atomico
(`mv -T --exchange`), così guardia e hook delle sessioni, che girano da `/opt/agentdeck`, non vedono mai una
cartella a metà. La prima installazione sposta la vecchia cartella `/opt/agentdeck` in
`/opt/agentdeck-versioni/<versione>-prima`, che resta disponibile per tornare indietro. Si tengono le 5 versioni
installate più di recente, sempre l'attiva e la precedente.

**`deck release install [commit=<ref>]`**, di norma `HEAD`, con anteprima e codice di conferma:
1. estrae il commit e lancia i test nella copia; se falliscono non cambia nulla;
2. rifiuta se cambiano `screen/` o `ui/`: `install-screen.sh` tocca la configurazione SSH e serve una procedura
   con verifica dell'accesso (INV-1), per ora con `deck/install.sh` dal Mac;
3. snapshot del sistema, poi scambio del collegamento;
4. passi di sistema: comando `deck`, hook di pacman degli obblighi, unità `agentdeck-sessione@`, configurazione di
   Claude Code (`/etc/claude-code/CLAUDE.md` e `managed-settings.json`, stile di output, impostazioni utente con
   `outputStyle`, `defaultMode: bypassPermissions` e `skipDangerousModePermissionPrompt`, skill, server MCP se
   manca, versione di Claude Code fissata se non lo è, [claude-code.md](claude-code.md#aggiornamenti-versione-fissa-o18t2)).
   I passi li esegue il codice della versione nuova, così un passo aggiunto vale già alla sua prima installazione
   (la cartella di prima di O18.T1, che non ha `release.py`, usa quelli di chi chiama). `agentdeck-claude` non si
   riavvia: la configurazione nuova vale per le sessioni aperte dopo;
5. verifica: `deck status` risponde, `deck mcp` parte, la guardia rifiuta ancora un comando che taglia l'accesso,
   `sshd` è attivo. Se una verifica fallisce, torna da solo alla versione di prima e rifà i suoi passi di sistema.

**`deck release revert [id=<versione>]`**, di norma la precedente: snapshot, scambio, passi di sistema e verifica,
con lo stesso ritorno automatico. Un revert fatto due volte torna avanti.

**Il giro di lavoro:** modifica in `~/agentdeck/repo`, test, commit, `deck release install`, verifica, poi versione
e tag nella governance e `git push` (INV-8).

Test: [../deck/tests/test_release.py](../deck/tests/test_release.py), su un repository git e cartelle temporanee
veri, senza `sudo` e con passi di sistema finti.

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
