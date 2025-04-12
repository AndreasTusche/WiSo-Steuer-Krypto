#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scriptname: csv-bsdex-to-wiso.py
Author: Andreas Tusche
Date Created: 2025-04-12
Last Modified: 2025-04-12
Description: Dieses Skript verarbeitet Realized Capital Gains von BINANCE,
             berechnet realisierte Gewinne/Verluste pro Kryptowährung
             und generiert eine CSV-Datei, die für das WISO
             Steuerprogramm geeignet ist.
Version: 1.1
"""

import csv
import sys
from datetime import datetime

# Hilfsfunktion zur Ausgabe des Datums
def format_date(date):
    return date.strftime("%d.%m.%Y")

# Hilfsfunktion zur Konvertierung des eingelesenen Datums
def parse_date(date_str):
    if date_str == "N/A":
        return datetime(tax_year-2, 12, 31)
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M")

# Hilfsfunktion zum Parsen von Zahlenwerten mit Tausender-komma und Dezimalpunkt
def parse_number(value):
    if not value:
        return 0.0, ""
    return float(value.replace(",", ""))

def process_capital_gains(input_file, output_file, tax_year):
    """Verarbeitung der Transaktionshistorie"""

    results = []
    total_fees = 0
    total_gain = 0
    taxed_gain = 0

    # CSV-Datei einlesen und Transaktionen merken
    with open(input_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:

            if row["Transaction type"] in ("Sell", "Trade"):
                coin        = row["Currency name"]
                sold_amount = parse_number(row["Currency amount"])
                date_buy    = parse_date(row["Acquired"])
                date_sell   = parse_date(row["Sold"])
                proceeds    = parse_number(row["Proceeds (EUR)"])   # Verkaufspreis
                cost_basis  = parse_number(row["Cost basis (EUR)"]) # Einkaufpreis
                gain_loss   = parse_number(row["Gains (EUR)"])

                short_long  = "Short" if (date_sell - date_buy).days < 365 else "Long"

                if tax_year == date_sell.year:
                    results.append([
                        f"{sold_amount:.8f}", coin,
                        format_date(date_sell), format_date(date_buy),
                        short_long, "Binance", "Binance",
                        f"{proceeds:.3f}", f"{cost_basis:.3f}", f"{gain_loss:.3f}"
                    ])

                    total_gain += gain_loss
                    if short_long == "Short":
                        taxed_gain += gain_loss

            elif row["Transaction type"] == "Fee":
                date_sell   = parse_date(row["Sold"])
                fee         = parse_number(row["Gains (EUR)"])

                if tax_year == date_sell.year:       
                    total_fees += fee
            else:
                print(f"(!) Unbekannter Transaction type {row["Transaction type"]}.")

    
    # Ergebnisse nach Verkaufs- und Kaufdatum sortieren
    results.sort(key=lambda x: (datetime.strptime(x[2], '%d.%m.%Y'), datetime.strptime(x[3], '%d.%m.%Y')))
    
    # Schreiben der Ergebnisse
    with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_NONE)
        writer.writerow(["Identifier:Capital_Gains", "Method:FIFO", f"Tax_Year:{tax_year}", "Base_Currency:EUR"])
        writer.writerow(["Amount", "Currency", "Date Sold", "Date Acquired", "Short/Long", "Buy/Input at", "Sell/Output at", "Proceeds", "Cost Basis", "Gain/Loss"])
        writer.writerows(results)

    profit = "Gewinn" if taxed_gain > 0 else "Verlust"
    output_txt_file = output_file.replace(".csv", ".txt")
    with open(output_txt_file, "w") as txtfile:
        print(f"--> Im Jahr {tax_year} wurden {total_gain:.2f} EUR erwirtschaftet.", file=txtfile)
        print(f"    Davon sind {taxed_gain:.2f} als {profit}e steuerrelevant.", file=txtfile) 
        print(f"    Die Summe aller Gebühren beträgt {total_fees:.2f} EUR.", file=txtfile)
    with open(output_txt_file, "r") as txtfile:
        print(txtfile.read())

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print("Usage: python3 csv-binance-to-wiso.py <Realized_Capital_Gains.csv> [<output_file.csv> [<tax year>]]")
        sys.exit(1)

    input_file  = sys.argv[1]
    tax_year    = datetime.today().year - 1
    output_file = f"WiSo_Binance_{tax_year}.csv" 

    if len(sys.argv) >2:
        output_file = sys.argv[2]

    if len(sys.argv) == 4:
        tax_year    = int(sys.argv[3])

    process_capital_gains(input_file, output_file, tax_year)
