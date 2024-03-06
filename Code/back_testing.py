from loguru import logger
from . import utilities
import numpy as np
import pandas as pd
import datetime as dt
from .Bloomberg_formatting import get_expiration_date_from_futures
from . import plotting_lib

class BackTest():

	
	@staticmethod
	def compute_value(data,long ,short, pre_long = None , pre_short = None , counting_rolling = 0):
		if counting_rolling == 0 :
			value =  5*(data[long] - data[short])
		else:
			value = counting_rolling*(BackTest.compute_value(data,long,short )) + (5-counting_rolling)*(BackTest.compute_value(data,pre_long,pre_short))
			value = value/5
		return value	


	def __init__(self, commodity : str, 
					   database_path : str ,
					   output_path : str,
					   contract_number : int = 5,
					   lot_size : int = 1):

		self.commodity = commodity
		self.database_path = database_path
		self.output_path = output_path
		self.contract_number = contract_number 
		self.lot_size = lot_size
		self.contract_value = lot_size*contract_number
		self.output_path = utilities.create_folder(commodity) 

	def compute_futures_pairing(self, database : pd.DataFrame):
		futures = []
		exp_dates = []
		real_exp_dates = []

		for future,df in database.items():
			futures.append(future)
			exp_dates.append(get_expiration_date_from_futures(future))
			real_exp_dates.append(df['Date'].iloc[-1])
		day = np.timedelta64(1, 'D')
		
		expiration_date_df = pd.DataFrame({'Real_Due' : real_exp_dates ,'Due' : exp_dates, 'Future' : futures})
		expiration_date_df.sort_values('Due',ascending = True,ignore_index = True,inplace = True)
		for future in futures:
			exp_date = expiration_date_df[expiration_date_df['Future'] == future]['Due'].values[0]
			mask = expiration_date_df['Due'].isin([exp_date+365*day, exp_date+366*day])
			if not expiration_date_df[mask].empty : 
				pair = expiration_date_df[mask]['Future'].values[0]
				expiration_date_df.loc[(expiration_date_df['Future'] == future),'Pair'] = pair
			else :
				expiration_date_df.loc[(expiration_date_df['Future'] == future),'Pair'] = np.nan
			 	
		logger.info('Drop NaN values')
		expiration_date_df = expiration_date_df.dropna()

		print(expiration_date_df)
		return expiration_date_df
	
	def merging_futures_data(self,database : pd.DataFrame):

		data = pd.DataFrame({'Date' : []})
		for future,df in database.items():
			df = df[['Date','Price']]
			df = df.rename(columns = {'Price' : future })
			data = data.merge(df, on = 'Date', how = 'outer')
		if data['Date'].shape[0] != data['Date'].drop_duplicates().shape[0]:
			print('WARNING duplicate dates')
		end_date = list(data['Date'])[-1]
		start_date = list(data['Date'])[0]

		date_range = pd.date_range(start=start_date, end=end_date, freq = 'B')
		date_range_df = pd.DataFrame(data = { 'Date' : date_range})

		dataset = date_range_df.merge(data, on = 'Date', how ='left')
		dataset.sort_values(by = 'Date', inplace = True, ignore_index= True, ascending = True)	
		return dataset
	
	def compute_PnL(self, data : pd.DataFrame):
		data['Value'] = data['Value'].ffill()
		data['Daily_Gain'] = self.contract_value*(data['Value'] - data['Value'].shift(1))

		data['Missing_Price'] = np.where(data['Payload'].apply(lambda x : x['tradable_day']) > 0 , True, False )
		data['No_Tradable_Day'] = np.where(data['Payload'].apply(lambda x : ( (x['tradable_day'] == 0) and (x['missing_price_flag']))) , True, False )

		data['Change (%)'] = data['Daily_Gain'].pct_change()
		data['Cum_Gain'] = data['Daily_Gain'].cumsum()
		
		logger.info('Saving PnL outcome')
		data.to_csv(f'{self.output_path}/{self.commodity}_PnL.csv')
		self.PnL = data
		return data

	def check_available_price(self,row):
		temp_price = 0
		row = row.drop('Date')
		if  not row[~pd.isna(row)].empty:
			temp_price = row[~pd.isna(row)].mean()
		return 	temp_price

	def check_missing_price(self, row , list_futures : list[str], is_rolling : bool ):
		'''
		Both of long and short futures have nan values
			 check if it is a missing price or no tradable day
				if missing price, take the mean of the available prices
				if not missing price, fill forward the value
		'''
		if not is_rolling:
			list_futures = list_futures[0:2]
		missing_price_flag = False
		temp_price = 0
		for future in list_futures:
			if pd.isna(row[future]):
				missing_price_flag = True
				temp_price = self.check_available_price(row)
				break
		return 	missing_price_flag,temp_price	

	def run(self):
		logger.info('Loading database')
		database = utilities.load_database(self.database_path,self.commodity)
		logger.info(f'For the commodity {self.commodity} discovering expiration dates with future paring ') 
		expiration_date_df = self.compute_futures_pairing(database)
		data = self.merging_futures_data(database)
		#---------------- settings --------------------
		starting_date = dt.datetime(1789,1,1)
		is_rolling = False
		counting_rolling = 0
		Date = [] 
		Value = []
		Payload = []
		previous_long_future = ''
		previous_short_future = ''
		#---------------- settings --------------------
		logger.info('Starting back test')
		for exp_row in expiration_date_df.itertuples():
			long_future = exp_row.Future
			short_future = exp_row.Pair
			starting_rolling = utilities.get_starting_rolling_date(exp_row.Real_Due)
			for idx,row in data[data['Date'] >= starting_date ].iterrows():
				t = row.Date
				if len(Date) == 0 and pd.isna(row[short_future]):
					'''
						the first pairing does not have prices in common
					'''
					continue
				if t > starting_rolling :
					'''it means that the current time is later than starting rolling so
					 it is reasonable to skip this pairing'''
					starting_date = t
					break
				if (t == starting_rolling):
					is_rolling= True
					previous_long_future = long_future
					previous_short_future = short_future
					starting_date = t
					break
				#check missing price
				missing_price_flag,temp_price = self.check_missing_price(row,[long_future,short_future,previous_long_future,previous_short_future],is_rolling)
				if  missing_price_flag and temp_price != 0 :
					'''
						Missing price
					'''
					row = row.fillna(temp_price)
				if is_rolling :
					counting_rolling += 1
					value = BackTest.compute_value(row,long_future,short_future,previous_long_future,previous_short_future,counting_rolling)
					occurence = {'long_future' : long_future,
								 'short_future' : short_future, 
								 'previous_long_future' : previous_long_future,
								 'previous_short_future' : previous_short_future,
								 'event' : {'rolling_over' : counting_rolling},
								 'missing_price_flag' :  missing_price_flag,
								  'tradable_day' : temp_price }
					if counting_rolling == 5 :
						is_rolling = False 
						counting_rolling = 0
				else:
					value = BackTest.compute_value(row,long_future,short_future)
					occurence = {'long_future' : long_future,
								 'short_future' : short_future, 
								 'event' : 'base',
								 'missing_price_flag' : missing_price_flag,
								 'tradable_day' : temp_price}


				Payload.append(occurence)
				Date.append(t)
				Value.append(value)

		logger.info('Closing positions')
		closing_position = data[data['Date'] == t ].iloc[0]
		missing_price_flag,temp_price = self.check_missing_price(closing_position,[long_future,short_future,previous_long_future,previous_short_future],is_rolling)
		
		if  missing_price_flag and temp_price != 0 :
			closing_position = closing_position.fillna(temp_price)
		value = BackTest.compute_value(closing_position,long_future,short_future,previous_long_future,previous_short_future ,counting_rolling)
		occurence = {'long_future' : long_future,
					'short_future' : short_future, 
					'previous_long_future' : previous_long_future,
					'previous_short_future' : previous_short_future,
		 			'event' : 'Closing positions',
					 'is_rolling' : is_rolling,
					 'missing_price_flag' : missing_price_flag,
					 'tradable_day' : temp_price}
		Payload.append(occurence)				 
		Date.append(starting_date)
		Value.append(value)

		result = pd.DataFrame({'Date': Date, 'Value' : Value, 'Payload' : Payload})
		PnL_df = self.compute_PnL(result)

	 
	def plot(self):
		fig = plotting_lib.create_figure(self.PnL,f'{self.commodity}_PnL','Date','Cum_Gain')
		plotting_lib.plot(fig,self.output_path)




