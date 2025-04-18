# WiSo-Steuer-Krypto

Generiere Krypto Steuer Reports, die in WiSo-Steuer eingelesen werden können

---

(DE) EXPERIMENTELL - VERWENDUNG AUF EIGENE GEFAHR

(EN) EXPERIMENTAL - USE AT YOUR OWN RISK

---

## Unterstützte Kryptobörsen:

### Binance

Usage: `python3 csv-binance-to-wiso.py <Realized_Capital_Gains.csv> [<output_file.csv> [<tax year>]]`

Dieses Skript verarbeitet Realized Capital Gains von BINANCE, berechnet realisierte Gewinne/Verluste pro Kryptowährung und generiert eine CSV-Datei, die für das WISO Steuerprogramm geeignet ist.
Die Eingabedatei ist die von Binance erstellte "Realized Capital Gains" csv Datei. Sie hat derzeit (Stand März 2025) die folgenden Spalten:

``` csv
Currency name,Currency amount,Acquired,Sold,Proceeds (EUR),Cost basis (EUR),Gains (EUR),Holding period (Days),Transaction type,Label
```


### BSDEX

Usage: `python3 csv-bsdex-to-wiso.py <input_file> [<output_file> [<tax year>]]`

Dieses Skript verarbeitet Transaktionsdaten von BSDEX, berechnet realisierte Gewinne/Verluste pro Kryptowährung und generiert eine CSV-Datei, die für das WISO Steuerprogramm geeignet ist.
Die Eingabedatei ist die von BSDEX erstellte "Transactions" csv Datei. Sie hat derzeit (Stand März 2025) die folgenden Spalten:

``` csv
Transaktionstyp,Kryptowährung,Betrag,Seite,Ausgelöster Preis,Gefüllt,Ausgeführter Gesamtbetrag,Ausgeführte Menge,Status,Transaktionsentgelt,Bestellstatus,Erstellt,Finalisiert am,Stop-Preis,Ausgelöst am,Ausgelöster Preis,Transaktionstyp,Storniert,Sendeadresse,Zieladresse,Zieladressen-Tag,Sendeadressen-Tag,IBAN,IBAN
```


## Ausgabeformat

Die generierte csv Ausgabedatei hat einen Header in der ersten Zeile und die Spaltenüberschriften in der zweiten Zeile. Hier für das Steuerjahr 2024:

```csv
Identifier:Capital_Gains,Method:FIFO,Tax_Year:2024,Base_Currency:EUR
Amount,Currency,Date Sold,Date Acquired,Short/Long,Buy/Input at,Sell/Output at,Proceeds,Cost Basis,Gain/Loss
```

Die *-kompakt Skripte erlauben es, jene Zeilen im Bericht zusammenzufassen, bei denen Die Kryptowährung UND Kaufdatum UND Verkaufsdatum identisch sind.


---

(DE) EXPERIMENTELL - VERWENDUNG AUF EIGENE GEFAHR

(EN) EXPERIMENTAL - USE AT YOUR OWN RISK




