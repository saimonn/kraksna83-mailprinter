# mailprinter
Script which connects to an IMAP mailbox and prints whatever arrives as PDF using given printer. 

How to use :

1)  set your params in config.ini 

## IMAP parameters should be clear. 
"keyword" is a word, that must be included in the subject, if the script is supposed to do anything to prevent printing spam mails. 
"AuThEnTICAtiOn"
delete_mail = True

## For Printer: 

If using remote host, make sure the CUPS accepts remote print jobs 
cupsctl --share-printers 
which accepts them on local subnet. If it's on remote subnet, do 
cupsctl --share-printers --remote-any

then set a particular printer to shared. 
Check the printer names : 
```
root@jelito ~ $ lpstat
Xerox_WorkCentre_3025-34 root              1024   Sun 07 Jan 2024 01:31:51 PM CET
Basement_Brother_Printer       root                 0   Fri 03 Jan 2025 12:50:11 PM CET
```

set a particular printer to shared :

lpadmin -p Basement_Brother_Printer -o printer-is-shared=true

use this CUPS printer name in "printer" ini section


2) launch on background. or via "screen". or define a systemd service. 

