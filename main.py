#!env/bin/python3
import requests
import json
import pandas as pd
import matplotlib.pyplot as plt 



stocks = ('CVX', 'MPC')



with open('key.txt', 'r') as f:  #requires Alpha Vantage API key
    KEY = f.readlines()[0]



#gets historical data
def get_historical_data(ticker):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={ticker}&apikey={KEY}&datatype=json"
    response = requests.get(url).json()
    print(response)
    response = response['Time Series (Daily)']
    df = pd.DataFrame.from_dict(response)
    df = df.transpose()
    df = df.drop(columns=df.columns[4:])

    return df


#data cleaning

#df1 = get_historical_data(stocks[0])
#df2 = get_historical_data(stocks[1])
df1 = pd.read_csv(f"{stocks[0]}_data.csv")
df2 = pd.read_csv(f"{stocks[1]}_data.csv")

df1['4. close'] = pd.to_numeric(df1['4. close'])
df2['4. close'] = pd.to_numeric(df2['4. close'])

df1.to_csv(f"{stocks[0]}_data.csv")
df2.to_csv(f"{stocks[1]}_data.csv")


corr = df1['4. close'].corr(df2['4. close'])

df = pd.DataFrame()
df[f"{stocks[0]}"] = df1['4. close']
df[f"{stocks[1]}"] = df2['4. close']
df["correlation"] = df[f"{stocks[0]}"].rolling(20).corr(df[f"{stocks[1]}"])
df[f"{stocks[0]}_change"] = df1['4. close'].pct_change()
df[f"{stocks[1]}_change"] = df2['4. close'].pct_change()

df = df.dropna()

class Bot:
    def __init__(self, corr: float, test: bool = True):
        self.corr = corr
        self.test = test
        self.trades = []
    
    def next(self, df: pd.DataFrame, index: int) -> list:
        row = df.iloc[-1]
        corr = row['correlation'] 
        s = [0, 0]
        if corr > self.corr:
            if row[f"{stocks[0]}_change"] > row[f"{stocks[1]}_change"]:
                if self.test: 
                    print(f"[BUY] Going long on {stocks[1]}")
                self.trades.append([1, index, row[stocks[1]]])
                s[1] = 1
            else:
                if self.test: 
                    print(f"[BUY] Going short on {stocks[1]}")
                self.trades.append([-1, index, row[stocks[1]]])
                s[1] = -1

        
        return s

b = Bot(0.8, test=False)


#trades
for index, row in df.iterrows():
    s_df = df.loc[0:index]
    b.next(s_df, index)


#buy and sell lists
buys = [i[1:] for i in b.trades if i[0] == 1]
sells = [i[1:] for i in b.trades if i[0] == -1]

#plotting 
plt.plot(df[stocks[1]])
plt.scatter([i[0] for i in buys],[i[1] for i in buys] , color='g')
plt.scatter([i[0] for i in sells],[i[1] for i in sells], color='r')
plt.show()



