#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scriptname: csv-binance-to-wiso-kompakt.py
Author: Andreas Tusche
Date Created: 2025-04-12
Last Modified: 2025-04-13
Description: Dieses Skript verarbeitet Realized Capital Gains von BINANCE,
             berechnet realisierte Gewinne/Verluste pro Kryptowährung
             und generiert eine CSV-Datei, die für das WISO
             Steuerprogramm geeignet ist. Optional mit Aggregation.
Version: 1.2
"""

import csv
import sys
from datetime import datetime
from collections import defaultdict

# Hilfsfunktion zur Ausgabe des Datums
def format_date(date):
    return date.strftime("%d.%m.%Y")

# Hilfsfunktion zur Konvertierung des eingelesenen Datums
def parse_date(date_str, format="%Y-%m-%d %H:%M:%S"):
    if date_str == "N/A":
        return datetime(tax_year - 2, 12, 31)
    return datetime.strptime(date_str, format)

# Hilfsfunktion zum Parsen von Zahlenwerten mit Tausenderkomma
def parse_number(value):
    if not value:
        return 0.0
    return float(value.replace(",", ""))

def process_capital_gains(input_file, output_file, tax_year, aggregate=True):
    """Verarbeitung der Transaktionshistorie mit optionaler Aggregation"""

    if aggregate:
        grouped = defaultdict(lambda: {
            "sold_amount": 0.0,
            "proceeds": 0.0,
            "cost_basis": 0.0,
            "gain_loss": 0.0,
            "short_long": "",
            "buy_platform": "Binance",
            "sell_platform": "Binance"
        })
    else:
        results = []

    total_fees = 0
    total_gain = 0
    taxed_gain = 0

    with open(input_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["Transaction type"] in ("Sell", "Trade"):
                coin        = row["Currency name"]
                sold_amount = parse_number(row["Currency amount"])
                date_buy    = parse_date(row["Acquired"], "%Y-%m-%d %H:%M")
                date_sell   = parse_date(row["Sold"], "%Y-%m-%d %H:%M")
                proceeds    = parse_number(row["Proceeds (EUR)"])
                cost_basis  = parse_number(row["Cost basis (EUR)"])
                gain_loss   = parse_number(row["Gains (EUR)"])

                short_long  = "Short" if (date_sell - date_buy).days < 365 else "Long"

                if tax_year == date_sell.year:
                    if aggregate:
                        key = (coin, date_sell.strftime("%Y-%m-%d"), date_buy.strftime("%Y-%m-%d"))
                        grouped[key]["sold_amount"] += sold_amount
                        grouped[key]["proceeds"] += proceeds
                        grouped[key]["cost_basis"] += cost_basis
                        grouped[key]["gain_loss"] += gain_loss
                        grouped[key]["short_long"] = short_long
                    else:
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
                date_sell = parse_date(row["Sold"], "%Y-%m-%d %H:%M")
                fee = parse_number(row["Gains (EUR)"])
                if tax_year == date_sell.year:
                    total_fees += fee
            else:
                print(f"(!) Unbekannter Transaction type {row['Transaction type']}.")

    # Ergebnisse zusammenstellen
    if aggregate:
        results = []
        for (coin, date_sell_str, date_buy_str), data in grouped.items():
            date_sell_fmt = datetime.strptime(date_sell_str, "%Y-%m-%d").strftime("%d.%m.%Y")
            date_buy_fmt = datetime.strptime(date_buy_str, "%Y-%m-%d").strftime("%d.%m.%Y")
            results.append([
                f"{data['sold_amount']:.8f}", coin,
                date_sell_fmt, date_buy_fmt,
                data["short_long"], data["buy_platform"], data["sell_platform"],
                f"{data['proceeds']:.3f}", f"{data['cost_basis']:.3f}", f"{data['gain_loss']:.3f}"
            ])

    results.sort(key=lambda x: (datetime.strptime(x[2], '%d.%m.%Y'), datetime.strptime(x[3], '%d.%m.%Y')))

    # CSV schreiben
    with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_NONE)
        writer.writerow(["Identifier:Capital_Gains", "Method:FIFO", f"Tax_Year:{tax_year}", "Base_Currency:EUR"])
        writer.writerow(["Amount", "Currency", "Date Sold", "Date Acquired", "Short/Long", "Buy/Input at", "Sell/Output at", "Proceeds", "Cost Basis", "Gain/Loss"])
        writer.writerows(results)

    # Textausgabe
    profit = "Gewinn" if taxed_gain > 0 else "Verlust"
    output_txt_file = output_file.replace(".csv", ".txt")
    with open(output_txt_file, "w") as txtfile:
        print(f"--> Im Jahr {tax_year} wurden {total_gain:.2f} EUR erwirtschaftet.", file=txtfile)
        print(f"    Davon sind {taxed_gain:.2f} als {profit}e steuerrelevant.", file=txtfile)
        print(f"    Die Summe aller Gebühren beträgt {total_fees:.2f} EUR.", file=txtfile)
    with open(output_txt_file, "r") as txtfile:
        print(txtfile.read())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 csv-binance-to-wiso-kompakt.py <Realized_Capital_Gains.csv> [<output_file.csv>] [<tax year>] [--no-aggregate]")
        sys.exit(1)

    input_file  = sys.argv[1]
    output_file = f"WiSo_Binance_{datetime.today().year - 1}_kompakt.csv"
    tax_year    = datetime.today().year - 1
    aggregate   = True

    for arg in sys.argv[2:]:
        if arg.endswith(".csv"):
            output_file = arg
        elif arg.isdigit():
            tax_year = int(arg)
        elif arg in ("--no-aggregate", "-n"):
            aggregate = False

    process_capital_gains(input_file, output_file, tax_year, aggregate)
