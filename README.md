# mailprinter

Script which connects to an IMAP mailbox and prints whatever arrives as PDF using a given CUPS printer.

This is a fork of kraksna83/mailprinter adding systemd steps in README and looking config in XDG or .config paths.

## How to use:

    1. Set your parameters in `~/.config/mailprinter.ini` or `/etc/mailprinter.init` for a system-wide installation.
    2. Launch in the background, via `screen`, or define a user systemd service:
       This supposes to save the script in ~/bin/ and make it executable.

```shell
mkdir -p ~/.config/systemd/user
cat <<EOF > ~/.config/systemd/user/mailprinter.service
[Unit]
Description=MailPrinter script at login
After=graphical-session.target

[Service]
Type=simple
ExecStart=%h/bin/mailprinter.py
Restart=on-failure

[Install]
WantedBy=default.target
EOF
```

    3. Start and activate the userland service
systemctl --user daemon-reload
systemctl --user start mailprinter.service
systemctl --user enable mailprinter.service


### IMAP parameters

- `keyword`: A word that must be included in the subject for the script to process the email, preventing spam mails from being printed. AuThEnTICAtiOn yay
- `delete_mail`: Whether the script should delete all emails in the mailbox after processing. 

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


The following will just list out printers on a given host, mailboxes in a given IMAP server and quit. 
```sh
python3 mailprinter.py list
```


