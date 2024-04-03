'''
import ondemand

od = ondemand.OnDemandClient(api_key='CHANGE_ME')

# or if you are using a free sandbox API

od = ondemand.OnDemandClient(api_key='CHANGE_ME', end_point='https://marketdata.websol.barchart.com/')

# if you want data in a format other than json. xml also supported

od = ondemand.OnDemandClient(api_key='CHANGE_ME', format='csv')

# get quote data for Apple and Microsoft
quotes = od.quote('AAPL,MSFT')['results']

for q in quotes:
    print('Symbol: %s, Last Price: %s' % (q['symbol'], q['lastPrice']))

# get 1 minutes bars for Apple
resp = od.history('AAPL', 'minutes', maxRecords=50, interval=1)

# generic request by API name
resp = od.get('getQuote', symbols='AAPL,EXC', fields='bid,ask')

# or, get the crypto
resp = od.crypto('^BTCUSD,^LTCUSD')
'''

import pandas as pd

class Extract():
    def __init__(self,path):
        self.path = path
        

    def from_excel(self):
        xls = pd.ExcelFile(self.path)
        sheets = xls.sheet_names
        
        df = pd.read_excel(io=self.path,sheet_name = '2023', header =1 )
        futures = []
        number_of_futures = int((df.shape[1] -1)/6)  
        for i in range(number_of_futures):
            if i == 0 :
                col = 'Symbol'
            else:
                col = f'Symbol.{i}'
            futures.append(df[col].dropna().values[0])      
        print(futures)

            