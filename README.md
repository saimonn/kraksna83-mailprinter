# mailprinter

Script which connects to an IMAP mailbox and prints whatever arrives as PDF using a given printer.

## How to use:

1. Set your parameters in `config.ini`.

### IMAP parameters

- `keyword`: A word that must be included in the subject for the script to process the email, preventing spam mails from being printed.
- `AuThEnTICAtiOn`
- `delete_mail = True`

### Printer setup

If using a remote host, ensure that CUPS accepts remote print jobs:

```sh
cupsctl --share-printers
```

This command allows printing on the local subnet. If it's on a remote subnet, use:

```sh
cupsctl --share-printers --remote-any
```

Then, set a particular printer to shared. Check the printer names:

```sh
root@jelito ~ $ lpstat
Xerox_WorkCentre_3025-34 root              1024   Sun 07 Jan 2024 01:31:51 PM CET
Basement_Brother_Printer       root                 0   Fri 03 Jan 2025 12:50:11 PM CET
```

Set a particular printer to shared:

```sh
lpadmin -p Basement_Brother_Printer -o printer-is-shared=true
```

Use this CUPS printer name in the `printer` section of the `config.ini`.

2. Launch in the background, via `screen`, or define a systemd service.
