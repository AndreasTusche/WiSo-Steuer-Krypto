#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scriptname: csv-bsdex-to-wiso.py
Author: Andreas Tusche
Date Created: 2025-03-30
Last Modified: 2025-04-12
Description: Dieses Skript verarbeitet Transaktionsdaten von BSDEX,
             berechnet realisierte Gewinne/Verluste pro Kryptowährung
             und generiert eine CSV-Datei, die für das WISO
             Steuerprogramm geeignet ist.
Version: 1.1
"""

import csv
import sys
from datetime import datetime
from collections import defaultdict, deque

# Hilfsfunktion zur Ausgabe des Datums
def format_date(date):
    return date.strftime("%d.%m.%Y")

# Hilfsfunktion zum Parsen von Währungswerten mit Tausenderpunkten, Dezimalkomma und Währungsangabe.
def parse_currency(value):
    if not value:
        return 0.0, ""
    value = value.replace(".", "").replace(",", ".").replace("\xa0", " ")
    parts = value.split()
    if len(parts) == 2:
        return float(parts[0]), parts[1]
    return float(parts[0]), ""

# Hilfsfunktion zur Konvertierung des eingelesenen Datums
def parse_date(date_str):
    return datetime.strptime(date_str, "%d.%m.%Y, %H:%M")

class Portfolio:
    """Portfolio-Verwaltung mit Käufen und FIFO-Verwaltung für Verkäufe"""

    def __init__(self):
        self.holdings = defaultdict(deque)  # Dictionary mit FIFO-Listen pro Coin

    def add(self, coin, amount, date, cost):
        """Einen Kauf zum Portfolio hinzufügen"""

        price = cost / amount
        self.holdings[coin].append((amount, date, cost, price))

    def remove(self, coin, amount):
        """Verkäufe und Teilverkäufe aus dem Portfolio austragen."""

        sales = []
        to_sell = amount
        while to_sell > 0 and self.holdings[coin]:
            first_amount, first_date, first_cost, first_price = self.holdings[coin].popleft()

            if first_amount <= to_sell:
                sales.append((first_amount, first_date, first_cost))
                to_sell -= first_amount
            else:
                remaining = first_amount - to_sell
                real_cost_remaining = remaining * first_price
                real_cost_of_sold   = to_sell * first_price
                self.holdings[coin].appendleft((remaining, first_date, real_cost_remaining, first_price))
                sales.append((to_sell, first_date, real_cost_of_sold))
                to_sell = 0
        return sales


def process_transactions(input_file, output_file, tax_year):
    """Verarbeitung der Transaktionshistorie"""

    portfolio = Portfolio()
    transactions = []
    results = []
    total_fees = 0
    total_gain = 0
    taxed_gain = 0

    # CSV-Datei einlesen und Transaktionen merken
    with open(input_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["Bestellstatus"] != "Geschlossen":
                continue

            date          = parse_date(row["Erstellt"])
            side          = row["Seite"]
            amount, coin  = parse_currency(row["Ausgeführter Gesamtbetrag"])
            fee, _        = parse_currency(row["Transaktionsentgelt"])
            euro_value, _ = parse_currency(row["Ausgeführte Menge"])
            
            # Korrektur von unvollständigen Angaben
            if euro_value == 0:
                euro_value, _ = parse_currency(row["Gefüllt"])
                if euro_value == 0:
                    euro_value = fee * 285.714285714286
            
            if not amount or not euro_value:
                print(f"WARNUNG: Fehlende Werte für {coin} am {date}")
                continue
            
            transactions.append((date, side, coin, amount, euro_value))
            
            if tax_year == date.year:       
                total_fees += fee
    
    # Schritt: Fehlende Käufe vorab korrigieren
    total_buys  = defaultdict(float)
    total_sells = defaultdict(float)

    for date, side, coin, amount, _ in transactions:
        if side == "Kaufen":
            total_buys[coin] += amount
        elif side == "Verkaufen":
            total_sells[coin] += amount

    for coin in total_sells:
        buy_amount = total_buys.get(coin, 0)
        sell_amount = total_sells[coin]
        if sell_amount > buy_amount:
            missing = sell_amount - buy_amount
            dummy_date = datetime(tax_year-2, 12, 31)
            dummy_cost = 0.0
            portfolio.add(coin, missing, dummy_date, dummy_cost)
            print(f"(!) Fiktiver Kauf über {missing:.8f} {coin} am {format_date(dummy_date)} eingefügt (0 EUR Kostenbasis), um historischen Fehlbestand auszugleichen.")

    # Transaktionen nach Datum sortieren
    transactions.sort()

    # Käufe und Verkäufe verarbeiten
    for date, side, coin, amount, euro_value in transactions:
        if side == "Kaufen":
            portfolio.add(coin, amount, date, euro_value)
        elif side == "Verkaufen":
            sales = portfolio.remove(coin, amount)
            for sold_amount, date_buy, buy_cost_basis in sales:
                proceeds = euro_value * (sold_amount / amount)  # Anteil am Gesamtverkaufserlös
                cost_basis = buy_cost_basis
                gain_loss = proceeds - cost_basis
                short_long = "Short" if (date - date_buy).days < 365 else "Long"

                if tax_year == date.year:
                    results.append([
                        f"{sold_amount:.8f}", coin,
                        format_date(date), format_date(date_buy),
                        short_long, "BSDEX", "BSDEX",
                        f"{proceeds:.3f}", f"{cost_basis:.3f}", f"{gain_loss:.3f}"
                    ])
                    total_gain += gain_loss
                    if short_long == "Short":
                        taxed_gain += gain_loss
    
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
        print("Usage: python3 csv-bsdex-to-wiso.py <input_file> [<output_file> [<tax year>]]")
        sys.exit(1)

    input_file  = sys.argv[1]
    tax_year    = datetime.today().year - 1
    output_file = f"WiSo_BSDEX_{tax_year}.csv" 

    if len(sys.argv) >2:
        output_file = sys.argv[2]

    if len(sys.argv) == 4:
        tax_year    = int(sys.argv[3])
 
    process_transactions(input_file, output_file, tax_year)
