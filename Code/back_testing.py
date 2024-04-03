from loguru import logger
from . import utilities
import numpy as np
import pandas as pd
import datetime as dt
from .Bloomberg_formatting import get_expiration_date_from_futures
from . import plotting_lib

class BackTest():

	
	@staticmethod
	def compute_value(data : pd.DataFrame):
		data['Value'] = np.where(data['IS_ROLLING'],  
							data['Long'].ffill()*data['Q_Long'].ffill() - data['Short'].ffill()*data['Q_Short'].ffill() + 
							data['Pre_Long'].ffill()*data['Q_Pre_Long'].ffill() - data['Pre_Short'].ffill()*data['Q_Pre_Short'].ffill(),
							data['Long'].ffill()*data['Q_Long'].ffill() - data['Short'].ffill()*data['Q_Short'].ffill() )
		return data	

	@staticmethod
	def get_market_out_dates(database_path : str, commodity : str):
		database = utilities.load_database(database_path, commodity)
		market_out_map = {}
		for future, df in database.items():
			if 	'MarketOut'  in list(df.columns) :
				market_out_df = df[df['MarketOut'].isin([1,-1])]
				if not market_out_df.empty:
					market_out_map[future] = market_out_df['Date'].to_list()
		return 	market_out_map		

	def __init__(self, commodity : str, 
					   database_path : str ,
					   output_path : str,
					   contract_number : int = 5):

		self.commodity = commodity
		self.database_path = database_path
		self.output_path = output_path
		self.contract_number = contract_number 
		self.lot_size,self.unit = utilities.lot_size_and_unit(commodity)
		self.contract_value = self.lot_size*self.unit*(contract_number/5)
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
	
	def merging_futures_data(self,database : pd.DataFrame, column : str ):

		data = pd.DataFrame({'Date' : []})
		for future,df in database.items():
			df = df[['Date','Price']]
			df = df.rename(columns = { column : future })
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
		data = 	BackTest.compute_value(data)
		data['Daily_Gain'] = self.contract_value*(data['Value'] - data['Value'].shift(1))
		data['Daily_Gain'].iloc[0] = 0.0
		data['Change (%)'] = data['Daily_Gain'].pct_change()
		data['Cum_Gain'] = data['Daily_Gain'].cumsum()
		
		logger.info('Saving PnL outcome')
		data.to_csv(f'{self.output_path}/{self.commodity}_PnL.csv')
		self.PnL = data
		return data

	def check_missing_price(self, row , list_futures : list[str], is_rolling : bool ):
		'''
		Both of long and short futures have nan values
			 check if it is a missing price 
		'''
		if not is_rolling:
			list_futures = list_futures[0:2]
		missing_price_future = []
		for future in list_futures:
			if pd.isna(row[future]):
				missing_price_future.append(future)
		return 	missing_price_future	

	def run(self):
		logger.info('Loading database')
		database = utilities.load_database(self.database_path,self.commodity)
		logger.info(f'For the commodity {self.commodity} discovering expiration dates with future paring ') 
		expiration_date_df = self.compute_futures_pairing(database)
		data = self.merging_futures_data(database,'Price')
		market_out_map = BackTest.get_market_out_dates(self.database_path,self.commodity)
		#---------------- settings --------------------
		Date = [] 
		Long = []
		Short = []
		Pre_Long = []
		Pre_Short = []
		Q_Long = []
		Q_Short = []
		Q_Pre_Long= []
		Q_Pre_Short = []
		
		Closing_Long = []
		Closing_Short = []
		Closing_Pre_Long= []
		Closing_Pre_Short = []
		
		Rolling_over = [] 
		Payload = []
		starting_date = dt.datetime(1789,1,1)
		is_rolling = False
		counting_rolling = 0
		previous_long_future = ''
		previous_short_future = ''
		#market_out_flag = False
		#---------------- settings --------------------
		logger.info('Starting back test')
		for exp_row in expiration_date_df.itertuples():
			long_future = exp_row.Future
			short_future = exp_row.Pair
			starting_rolling = utilities.get_starting_rolling_date(exp_row.Real_Due)
			for idx,row in data[data['Date'] >= starting_date ].iterrows():
				t = row.Date
				interested_futures = [long_future,short_future,previous_long_future,previous_short_future]
				if len(Date) == 0 and (pd.isna(row[short_future])) :
					logger.warning(f'the first pairing {long_future}-{short_future} does not have available prices in common date {t}')
					continue
				if t > starting_rolling :
					logger.warning(f'current date {t} > starting rolling {starting_rolling} -> Skip pairing')
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
				
				'''
				# check market out
				for f in interested_futures:
					if f in market_out_map:
						if t in market_out_map[f]:
							market_out_flag = True
							occurence = {'long_future' : long_future,
										 'short_future' : short_future, 
										 'previous_long_future' : previous_long_future,
										 'previous_short_future' : previous_short_future,
										 'event' : 'Market_Out',
										 'missing_price_flag' :  np.nan,
										  'tradable_day' : np.nan }
							break			  
						else : 
							market_out_flag = False
					else:
						market_out_flag = False		

				'''
				#check missing price
				missing_price_future = self.check_missing_price(row,interested_futures,is_rolling) 
				if len(missing_price_future) > 0 :
					#logger.warning(f'Missing Price {missing_price_future}')
					missing_price_flag = True
				else:
					missing_price_flag = False	
				if missing_price_flag and is_rolling :
					logger.warning(f'Missing price during rolling-over period {t} {missing_price_future}')
				#------------------- ROLLING PERIOD ---------------------------------------------------------	
				if is_rolling :
					counting_rolling += 1
					if pd.isna(row[long_future]):
						if counting_rolling > 1 :
							Q_Long.append(Q_Long[-1])
						else:
							Q_Long.append(0)
					else:
						Q_Long.append(counting_rolling)
					
					if pd.isna(row[short_future]):
						if counting_rolling > 1 :
							Q_Short.append(Q_Short[-1])
						else:
							Q_Short.append(0)
					else:
						Q_Short.append( counting_rolling)
					
					if pd.isna(row[previous_long_future]):
						Closing_Pre_Long.append(0)
						if counting_rolling > 1 :
							Q_Pre_Long.append(Q_Pre_Long[-1])
						else:
							Q_Pre_Long.append(5)
					else:
						Closing_Pre_Long.append(counting_rolling)
						Q_Pre_Long.append(5 - counting_rolling)
					
					if pd.isna(row[previous_short_future]):
						Closing_Pre_Short.append(0)
						if counting_rolling > 1 :
							Q_Pre_Short.append(Q_Pre_Short[-1])
						else:
							Q_Pre_Short.append(5)
					else:
						Closing_Pre_Short.append(counting_rolling)
						Q_Pre_Short.append( 5 - counting_rolling)
					
					Closing_Long.append(0)
					Closing_Short.append(0)

					occurence = {'long_future' : long_future,
								 'short_future' : short_future, 
								 'previous_long_future' : previous_long_future,
								 'previous_short_future' : previous_short_future,
								 'event' : {'rolling_over' : counting_rolling}
								 }
				#------------------- ROLLING PERIOD ---------------------------------------------------------		
				else:
					
					Q_Long.append(5)
					Q_Short.append(5)
					Q_Pre_Long.append(0)
					Q_Pre_Short.append(0)
					Closing_Long.append(0)
					Closing_Short.append(0)
					Closing_Pre_Long.append(0)
					Closing_Pre_Short.append(0)
					occurence = {'long_future' : long_future,
								 'short_future' : short_future, 
								 'event' : 'base',
								 'missing_price_flag' : missing_price_flag}
				Long.append(row[long_future])
				Short.append(row[short_future])
				Pre_Long.append(row[previous_long_future] if previous_long_future != '' else np.nan)
				Pre_Short.append(row[previous_short_future] if previous_short_future != '' else np.nan)
				Rolling_over.append(is_rolling)
				Date.append(t)
				Payload.append(occurence)
				if counting_rolling == 5 :
						is_rolling = False 
						counting_rolling = 0

		logger.info('Closing ALL positions')
		closing_position = data[data['Date'] == t ].iloc[0]
		occurence = {'long_future' : long_future,
					'short_future' : short_future, 
					'previous_long_future' : previous_long_future,
					'previous_short_future' : previous_short_future,
		 			'event' : 'Closing positions'
		 			}
		Long.append(row[long_future])
		Short.append(row[short_future])
		Pre_Long.append(row[previous_long_future])
		Pre_Short.append(row[previous_short_future])
		Date.append(t)
		Payload.append(occurence)
		
		Closing_Long.append(Q_Long[-1])
		Closing_Short.append(Q_Short[-1])
		Closing_Pre_Long.append(Q_Pre_Long[-1])
		Closing_Pre_Short.append(Q_Pre_Short[-1])

		Q_Long.append(0)
		Q_Short.append(0)
		Q_Pre_Long.append(0)
		Q_Pre_Short.append(0)

		Rolling_over.append(False)


		result = pd.DataFrame({'Date': Date, 
							   'Long' : Long, 
							   'Short' : Short,
							   'Pre_Long' : Pre_Long,
							   'Pre_Short' : Pre_Short,
							   'Q_Long' : Q_Long,
							   'Q_Short' : Q_Short,
							   'Q_Pre_Long' : Q_Pre_Long,
							   'Q_Pre_Short' : Q_Pre_Short,
							   'IS_ROLLING' : Rolling_over,
							   'Payload' : Payload})

		PnL_df = self.compute_PnL(result)

	 
	def plot(self):
		fig = plotting_lib.create_figure(self.PnL,f'{self.commodity}_PnL','Date','Cum_Gain',self.commodity)
		plotting_lib.plot(fig,self.output_path)




