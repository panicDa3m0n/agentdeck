# Schermo della Deck: l'attività dell'agente

Lo schermo della Deck mostra in tempo reale, come un terminale, ogni comando che l'agente esegue sulla
Deck, la sua risposta e l'esito delle chiamate a `deck`. È un canale verso l'umano (principio agent-first: la grafica serve
all'agente per mostrare cosa fa), quindi i testi sono in italiano. Al posto di questo schermo prima c'era
il login di Linux, che non serviva a nessuno.
Indice: [README.md](README.md).

> **Dal 27/10/2026 lo schermo è grafico**, con le interfacce effimere (ADR-0003): [interfacce.md](interfacce.md).
> Il terminale descritto qui resta installato ma spento, come ripiego che systemd riaccende se lo schermo grafico
> non parte. La registrazione dei comandi nel registro resta com'è.

## Cosa si vede

```
─────────────────────────────────────────────────────────────────────────────
 AgentDeck · agentdeck · 192.168.1.49
 Attività dell'agente: i comandi compaiono qui mentre vengono eseguiti.
─────────────────────────────────────────────────────────────────────────────
17:55:36 agent@agentdeck:~$ df -h /
         Filesystem      Size  Used Avail Use% Mounted on
         /dev/nvme0n1p2  1.9T  2.7G  1.9T   1% /
17:55:36 agent@agentdeck:~$ ls /nonexiste
         ls: cannot access '/nonexiste': No such file or directory
17:55:37 agent@agentdeck:~$ deck status
17:55:37   → deck /status: ok, 3 avvisi
17:55:38 agent@agentdeck:~$ (trasferimento di file)
```

- Ogni comando SSH dell'agente compare con l'ora e un prompt da terminale; i comandi su più righe mostrano
  la prima riga seguita da `…`, quelli troppo lunghi vengono accorciati.
- **Sotto ogni comando compare la sua risposta**: l'output normale e, in rosso, i messaggi di errore. Una
  riga molto lunga va a capo al massimo su 3 righe dello schermo e poi finisce con `…`.
- Per `deck` la risposta JSON non viene mostrata (sarebbe una riga di migliaia di caratteri): al suo posto
  c'è la riga di esito con la freccia.
- I trasferimenti di file (`scp`, `sftp`, `rsync`) compaiono come "(trasferimento di file)".
- Le chiamate a `deck` aggiungono una riga con la freccia: `ok` con il numero di avvisi, `errore` con il
  codice, `anteprima` per le conferme in attesa, `eseguito` per le azioni completate.
- I caratteri di controllo vengono ripuliti (un comando non può pilotare lo schermo) e i valori che
  sembrano segreti (`password`, `token`, `secret`, `api_key`, `Authorization`, `Bearer`) sono oscurati.

## Come funziona

1. **Registrazione dei comandi.** Per l'utente `agent` sshd imposta la variabile `BASH_ENV`
   ([../deck/screen/20-agentdeck-screen.conf](../deck/screen/20-agentdeck-screen.conf)). Prima di eseguire
   un comando SSH, bash legge [../deck/screen/ssh-log.sh](../deck/screen/ssh-log.sh)
   (installato in `/usr/local/lib/agentdeck/`), che scrive il comando nel journal con l'identificatore
   `agentdeck-cmd`. Se quello script avesse un errore, il comando partirebbe comunque: l'accesso non
   dipende da lui (INV-1). Autenticazione e permessi SSH non cambiano.
2. **Registrazione della risposta.** Lo stesso script fa passare stdout e stderr del comando da `tee`: una
   copia arriva invariata a chi ha lanciato il comando, l'altra va nel journal (`agentdeck-out`,
   `agentdeck-err`). Codice di uscita, output ed errori restano identici, anche per dati binari (verificato
   a ogni installazione). Sono esclusi i trasferimenti di file (`scp`, `sftp`, `rsync`), le sessioni con
   terminale (`ssh -t`), dove `tee` cambierebbe il comportamento dei programmi, e il server MCP
   (`ssh agentdeck deck mcp`), il cui flusso JSON-RPC non serve a chi guarda: le sue chiamate arrivano
   comunque sullo schermo come esiti di `deck` (punto 3). `logger` usa `--size 65536`:
   con il limite predefinito di 1 KB spezzerebbe le righe lunghe in frammenti. Questa traccia è separata dai
   log del sistema: `deck logs` la esclude, salvo `include_agent=true` ([deck.md](deck.md)).
3. **Esiti di `deck`.** Ogni chiamata scrive nel journal, con identificatore `agentdeck`, una riga
   `indirizzo|azione|stato|codice|avvisi` (funzione `call_summary` in
   [../deck/agentdeck/cli.py](../deck/agentdeck/cli.py)). Non succede durante i test (`AGENTDECK_NO_LOG`).
   Le chiamate di `brain` scrivono la stessa riga con il comando davanti all'indirizzo, `brain /memory|search|…`,
   senza parametri: i testi delle memorie non finiscono nel journal ([brain.md](brain.md)).
4. **Lo schermo.** Il servizio [../deck/screen/agentdeck-screen.service](../deck/screen/agentdeck-screen.service)
   prende il posto del login su `tty1` (`getty@tty1` è mascherato) e avvia
   [../deck/screen/agentdeck_screen.py](../deck/screen/agentdeck_screen.py), che segue il journal e stampa le
   righe. Il servizio legge solo il journal e scrive sul terminale (`ProtectSystem=strict`,
   `NoNewPrivileges`); se si ferma, systemd lo riavvia dopo 2 secondi.

## Installazione

È una fase di [../deck/install.sh](../deck/install.sh), che lancia sulla Deck, da root,
[../deck/screen/install-screen.sh](../deck/screen/install-screen.sh). Lo script è ripetibile e cambia solo
ciò che è diverso:

- se cambiano la configurazione SSH, lo script di registrazione o il servizio, prima crea uno snapshot
  (INV-3);
- **rete di sicurezza SSH:** se cambiano la configurazione SSH o lo script di registrazione (che tocca
  l'input/output di ogni comando), salva le versioni precedenti in `/usr/local/lib/agentdeck/previous/` e
  programma il loro ripristino automatico dopo 3 minuti (unità `agentdeck-ssh-revert`). `deck/install.sh`
  prova `ssh` con stdout, stderr e codice di uscita, `scp` e `rsync` con 64 KB di dati casuali, la lettura
  degli stessi dati con `cat`, e solo se tutto coincide annulla il ripristino;
- installa il servizio, maschera `getty@tty1` e riavvia lo schermo.

## Verificare cosa c'è sullo schermo

L'agente può leggere lo schermo senza guardarlo, dal contenuto della console in Unicode:

```bash
ssh agentdeck 'cols=$(sudo stty -F /dev/tty1 size | cut -d" " -f2); sudo cat /dev/vcsu1 | python -c "
import sys; t = sys.stdin.buffer.read().decode(\"utf-32-le\"); c = int(sys.argv[1])
print(\"\n\".join(t[i:i+c].rstrip() for i in range(0, len(t), c) if t[i:i+c].strip()))" "$cols"'
```

`/dev/vcs1` invece contiene i codici dei glifi del font, non testo: i caratteri accentati e i simboli
escono sbagliati.

## Attenzioni

- Un segreto passato sulla riga di comando **o stampato da un comando** (per esempio leggendo un file di
  credenziali con `cat`) è oscurato sullo schermo solo se ha la forma `password=…`, `token=…`, `Bearer …` e
  simili, e resta comunque in chiaro nel journal, leggibile solo da root e dagli amministratori. I segreti
  vanno passati e letti senza stamparli.
- Un output binario (per esempio `ssh agentdeck 'cat archivio.tar'`) arriva intatto a chi lo chiede; sullo
  schermo non compare, ma nel journal resta come dato binario.
- I comandi lanciati con `ssh agentdeck 'bash -s' < script` mostrano solo `bash -s`: il contenuto dello
  script arriva su stdin e non viene registrato.
- Per tornare al login classico: `sudo systemctl disable --now agentdeck-screen` e
  `sudo systemctl unmask getty@tty1 && sudo systemctl start getty@tty1`.
