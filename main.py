#!env/bin/python3
import requests
import json
import pandas as pd
import matplotlib.pyplot as plt 

stocks = ('CVX', 'MPC')

with open('key.txt', 'r') as f:  #requires Alpha Vantage API key
    KEY = f.readlines()[0]

#gets historical data
def get_historical_data(ticker, data_slice: str, interval: str) -> pd.DataFrame:
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={KEY}&outputsize=full&datatype=json"
    #url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY_EXTENDED&symbol={ticker}a&interval={interval}&slice=year1month1&apikey={KEY}"
    response = requests.get(url)
    response = response.json()
    response = response['Time Series (Daily)']
    df = pd.DataFrame.from_dict(response)
    df = df.transpose()
    df = df.drop(columns=df.columns[4:])

    return df

#data cleaning
df1 = get_historical_data(stocks[0], 'year2month11', '1min')
df2 = get_historical_data(stocks[1], 'year2month11', '1min')
df1.reset_index(inplace=True)
df2.reset_index(inplace=True)

df1['4. close'] = pd.to_numeric(df1['4. close'])
df2['4. close'] = pd.to_numeric(df2['4. close'])
df1['2. high'] = pd.to_numeric(df1['2. high'])
df2['2. high'] = pd.to_numeric(df2['2. high'])

df1.to_csv(f"{stocks[0]}_data.csv")
df2.to_csv(f"{stocks[1]}_data.csv")

corr = df1['4. close'].corr(df2['4. close'])

df = pd.DataFrame()
df[f"{stocks[0]}"] = df1['4. close']
df[f"{stocks[1]}"] = df2['4. close']
df["correlation"] = df[f"{stocks[0]}"].rolling(20).corr(df[f"{stocks[1]}"])
df[f"{stocks[0]}_change"] = df1['4. close'].pct_change()
df[f"{stocks[1]}_change"] = df2['4. close'].pct_change()
print(df.head())
df = df.dropna()
df = df.loc[0:800]


class Bot:
    def __init__(self, corr: float, test: bool = True, cash: float = 10000):
        self.corr = corr
        self.test = test
        self.trades = []
        self.cash = cash
        self.initial_cash = cash
        self.holdings = {f"{stocks[0]}": 0}
        self.value = []

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

    def compute_execution_price(self,side: str, order_price: float, 
            high_price: float = None, low_price: float = None, factor: float = .25) -> float: 

        if side == 'BUY':
            return order_price + (high_price - order_price) * factor
        else:
            return order_price - (high_price - order_price) * factor


    def run(self, df: pd.DataFrame, slippage: bool = True) -> dict: 
        for index, row in df.iterrows():
            low_price = df1.iloc[index]['3. low']
            high_price = df1.iloc[index]['2. high']

            s_df = df.loc[0:index]
            
            #calculate signal 
            signal = self.next(s_df, index)[1]
            price = float(row[stocks[0]])
            
            if signal == 1: #buy signal 
                shares = int((.1 * self.cash) / price)
                if slippage: 
                    self.cash -= shares * self.compute_execution_price('BUY', price, high_price=high_price)
                else:
                    self.cash -= shares * price
                self.holdings[stocks[0]] += shares
            
            elif signal == -1 and stocks[0] in self.holdings.keys(): 
                shares = self.holdings[stocks[0]]
                if slippage: 
                    self.cash += shares * self.compute_execution_price('SELL', price, high_price=high_price)
                else: 
                    self.cash += shares * price
                self.holdings[stocks[0]] = 0
            
            
            #calculate final portfolio value 
            current_value = (self.holdings[stocks[0]] * price) + self.cash if stocks[0] in self.holdings.keys() else self.cash             
            self.value.append(current_value)

            #print(current_value, signal, self.holdings, '-----')
    def generate_stats(self, test: bool = True) -> dict: 
        stats = {
            'final_value': self.value[-1],
            'final_equity': self.cash, 
            'final_holdings': self.holdings[stocks[0]],
            'percent_return': round((self.value[-1] - self.initial_cash) / abs(self.initial_cash) * 100, 2),
            'cash_return': self.value[-1] - self.initial_cash
        }
        return stats


b = Bot(0.8, test=False)
b.run(df, slippage=True)

#buy and sell lists
buys = [i[1:] for i in b.trades if i[0] == 1]
sells = [i[1:] for i in b.trades if i[0] == -1]

#plotting 
for key, value in b.generate_stats().items():
    print(f"{key}: {value}")
fig, (ax1, ax2, ax3) = plt.subplots(3, 1)


ax1.plot(df[stocks[1]])
ax1.set_title("Stock Price ($)")
ax1.scatter([i[0] for i in buys],[i[1] for i in buys] , color='g') #buys
ax1.scatter([i[0] for i in sells],[i[1] for i in sells], color='r') #sells

ax2.plot(df[f"{stocks[0]}_change"], color='b')
ax2.plot(df[f"{stocks[1]}_change"], color='r')
ax2.set_title("Pair Discrepancy (%)")

ax3.plot(b.value)
ax3.set_title("Portfolio Value ($)")


plt.show()


