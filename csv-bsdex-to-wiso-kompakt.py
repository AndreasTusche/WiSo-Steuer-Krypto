#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scriptname: csv-bsdex-to-wiso.py
Author: Andreas Tusche
Date Created: 2025-03-30
Last Modified: 2025-04-13
Description: Dieses Skript verarbeitet Transaktionsdaten von BSDEX,
             berechnet realisierte Gewinne/Verluste pro Kryptowährung
             und generiert eine CSV-Datei, die für das WISO
             Steuerprogramm geeignet ist.
             Aggregation optional via --no-aggregate
Version: 1.2
"""

import csv
import sys
from datetime import datetime
from collections import defaultdict, deque

# Hilfsfunktion zur Ausgabe des Datums
def format_date(date):
    return date.strftime("%d.%m.%Y")

# Hilfsfunktion zum Parsen von Währungswerten mit Zahl und Währung
def parse_currency(value):
    if not value:
        return 0.0, ""
    value = value.replace(".", "").replace(",", ".").replace("\xa0", " ")
    parts = value.split()
    if len(parts) == 2:
        return float(parts[0]), parts[1]
    return float(parts[0]), ""

# Hilfsfunktion zur Konvertierung des eingelesenen Datums
def parse_date(date_str, format="%Y-%m-%d %H:%M:%S"):
    if date_str == "N/A":
        return datetime(tax_year - 2, 12, 31)
    return datetime.strptime(date_str, format)

class Portfolio:
    def __init__(self):
        self.holdings = defaultdict(deque)

    def add(self, coin, amount, date, cost):
        price = cost / amount
        self.holdings[coin].append((amount, date, cost, price))

    def remove(self, coin, amount):
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

def process_transactions(input_file, output_file, tax_year, aggregate=True):
    portfolio = Portfolio()
    transactions = []
    results = []
    total_fees = 0
    total_gain = 0
    taxed_gain = 0

    with open(input_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["Bestellstatus"] != "Geschlossen":
                continue
            date          = parse_date(row["Erstellt"], "%d.%m.%Y, %H:%M")
            side          = row["Seite"]
            amount, coin  = parse_currency(row["Ausgeführter Gesamtbetrag"])
            fee, _        = parse_currency(row["Transaktionsentgelt"])
            euro_value, _ = parse_currency(row["Ausgeführte Menge"])

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
            dummy_date = datetime(tax_year - 2, 12, 31)
            dummy_cost = 0.0
            portfolio.add(coin, missing, dummy_date, dummy_cost)
            print(f"(!) Fiktiver Kauf über {missing:.8f} {coin} am {format_date(dummy_date)} eingefügt (0 EUR Kostenbasis), um historischen Fehlbestand auszugleichen.")

    transactions.sort()

    for date, side, coin, amount, euro_value in transactions:
        if side == "Kaufen":
            portfolio.add(coin, amount, date, euro_value)
        elif side == "Verkaufen":
            sales = portfolio.remove(coin, amount)
            for sold_amount, date_buy, buy_cost_basis in sales:
                proceeds = euro_value * (sold_amount / amount)
                cost_basis = buy_cost_basis
                gain_loss = proceeds - cost_basis
                short_long = "Short" if (date - date_buy).days < 365 else "Long"

                if tax_year == date.year:
                    results.append([
                        sold_amount, coin, date, date_buy, short_long,
                        "BSDEX", "BSDEX", proceeds, cost_basis, gain_loss
                    ])
                    total_gain += gain_loss
                    if short_long == "Short":
                        taxed_gain += gain_loss

    if aggregate:
        grouped = defaultdict(lambda: {
            "sold_amount": 0.0,
            "proceeds": 0.0,
            "cost_basis": 0.0,
            "gain_loss": 0.0,
            "short_long": "",
            "buy_platform": "BSDEX",
            "sell_platform": "BSDEX"
        })
        for sold_amount, coin, date_sell, date_buy, short_long, bplatform, splatform, proceeds, cost_basis, gain_loss in results:
            key = (coin, date_sell.strftime("%Y-%m-%d"), date_buy.strftime("%Y-%m-%d"))
            grouped[key]["sold_amount"] += sold_amount
            grouped[key]["proceeds"] += proceeds
            grouped[key]["cost_basis"] += cost_basis
            grouped[key]["gain_loss"] += gain_loss
            grouped[key]["short_long"] = short_long
        final_results = []
        for (coin, date_sell_str, date_buy_str), data in grouped.items():
            final_results.append([
                f"{data['sold_amount']:.8f}", coin,
                datetime.strptime(date_sell_str, "%Y-%m-%d").strftime("%d.%m.%Y"),
                datetime.strptime(date_buy_str, "%Y-%m-%d").strftime("%d.%m.%Y"),
                data["short_long"], data["buy_platform"], data["sell_platform"],
                f"{data['proceeds']:.3f}", f"{data['cost_basis']:.3f}", f"{data['gain_loss']:.3f}"
            ])
    else:
        final_results = [
            [
                f"{x[0]:.8f}", x[1],
                format_date(x[2]), format_date(x[3]),
                x[4], x[5], x[6],
                f"{x[7]:.3f}", f"{x[8]:.3f}", f"{x[9]:.3f}"
            ] for x in results
        ]

    final_results.sort(key=lambda x: (datetime.strptime(x[2], '%d.%m.%Y'), datetime.strptime(x[3], '%d.%m.%Y')))

    with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_NONE)
        writer.writerow(["Identifier:Capital_Gains", "Method:FIFO", f"Tax_Year:{tax_year}", "Base_Currency:EUR"])
        writer.writerow(["Amount", "Currency", "Date Sold", "Date Acquired", "Short/Long", "Buy/Input at", "Sell/Output at", "Proceeds", "Cost Basis", "Gain/Loss"])
        writer.writerows(final_results)

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
        print("Usage: python3 csv-bsdex-to-wiso.py <input_file> [<output_file>] [<tax_year>] [--no-aggregate]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = f"WiSo_BSDEX_{datetime.today().year - 1}_kompakt.csv"
    tax_year = datetime.today().year - 1
    aggregate = True

    for arg in sys.argv[2:]:
        if arg.endswith(".csv"):
            output_file = arg
        elif arg.isdigit():
            tax_year = int(arg)
        elif arg in ("--no-aggregate", "-n"):
            aggregate = False

    process_transactions(input_file, output_file, tax_year, aggregate)
