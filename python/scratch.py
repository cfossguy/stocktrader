import pandas as pd
def fetch_midcap_list():
    url = "https://www.ssga.com/bin/etf/holdings/download?fileType=csv&fundId=MDY"
    df = pd.read_csv(url, skiprows=4)  # skip header junk
    df = df[['Ticker', 'Name', 'Weight']]

    print(df.head())

def main():
    fetch_midcap_list()