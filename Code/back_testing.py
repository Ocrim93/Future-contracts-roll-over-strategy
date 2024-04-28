from loguru import logger
from . import utilities
import numpy as np
import pandas as pd
import datetime as dt
from .Bloomberg_formatting import get_expiration_date_from_futures
from . import plotting_lib
from collections import defaultdict 
from functools import reduce	

class BackTest():


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
					   contract_number : int = 5):

		self.commodity = commodity
		self.database_path = utilities.get_database_path()
		self.output_path = utilities.get_output_path(commodity)

		self.contract_number = contract_number 
		self.lot_size,self.unit = utilities.lot_size_and_unit(commodity)
		self.contract_value = self.lot_size*self.unit*(contract_number/5)
		self.configuration = self.find_configuration()
		self.expiration_date_df = pd.DataFrame()
		self.data = pd.DataFrame()

		self.sharp_ratio = pd.DataFrame()

	def compute_sharp_ratio(self,distance : int,due_shift : int ):
		TRADING_DAYS = 252
		pnl = self.PnL['PNL'] 
		std = pnl.std()

		annualized_std = std*np.sqrt(TRADING_DAYS)
		annualized_cum_pnl = (pnl.iloc[-1] - pnl.iloc[0])*TRADING_DAYS/pnl.shape[0]
		sharp_ratio = (pnl.iloc[-1] - pnl.iloc[0])/(annualized_std)
		logger.info(f'{self.commodity} std : {std} annualized_std : {annualized_std} sharp_ratio : {sharp_ratio}')
		sharp_df = pd.DataFrame(data = { 'Distance' : [distance],
										 'Due_Shift' : [due_shift],
										  'STD': [annualized_std],
										   'Cuml_PnL' : [annualized_cum_pnl],
										   'Sharp_Ratio' : [sharp_ratio] })

		self.sharp_ratio = pd.concat([self.sharp_ratio,sharp_df])
		
		return sharp_ratio

	def find_configuration(self):
		configuration  = defaultdict(lambda  : defaultdict() )
		database = utilities.load_database(self.database_path,self.commodity)

		months = [ symbol[2] for symbol in database.keys() ]
		
		sequence = utilities.find_sequence(months)
		sequence_map  = { f:idx+1  for idx, f in enumerate(sequence)}
		sequence_reverse_map  = { value: key for key,value in sequence_map.items()}
		for i in range(1,1+len(sequence)):
			for future in sequence:
				idx = sequence_map[future]
				if (i+idx) % len(sequence) != 0 :
					number = (i+idx) % len(sequence) 
				else:
					number = len(sequence)
				pair = sequence_reverse_map[number]
				configuration[i][future]= pair
		logger.info('Setting configuration map')
		return configuration

	def available_future(self,database : pd.DataFrame):
		futures = []
		exp_dates = []
		real_exp_dates = []
		
		for future,df in database.items():
			futures.append(future)
			real_exp_dates.append(df['Date'].iloc[-1])
		
		expiration_date_df = pd.DataFrame({'Due' : real_exp_dates , 'Future' : futures} )
		expiration_date_df['Month'] = expiration_date_df['Future'].apply(lambda x : x[2])
		expiration_date_df.sort_values('Due',ascending = True,ignore_index = True,inplace = True)
		expiration_date_df.to_csv(f'{self.output_path}/{self.commodity}_future_list.csv')

		self.expiration_date_df = expiration_date_df

	def futures_pairing(self,distance : int, due_shift : int):
		expiration_date_df = self.expiration_date_df
		futures = expiration_date_df['Future'].to_list()
		configuration = self.configuration[distance]
		
		for future in futures:
			month = future[2]		
			exp_date = expiration_date_df[expiration_date_df['Future'] == future]['Due'].values[0]
			mask =  (expiration_date_df['Month'] ==  configuration[month]) & (expiration_date_df['Due'] > exp_date)
			if not expiration_date_df.loc[mask, 'Future'].empty:
				pair =  expiration_date_df.loc[mask, 'Future'].values[0]
				expiration_date_df.loc[(expiration_date_df['Future'] == future),'Pair'] = pair
		expiration_date_df = expiration_date_df[(expiration_date_df['Pair'] != 'nan')]
		expiration_date_df['Due'] = expiration_date_df['Due'].shift(due_shift)
		expiration_date_df.dropna(inplace=True)
		expiration_date_df.reset_index(inplace = True, drop = True)
		expiration_date_df.to_csv(f'{self.configuration_path}/{self.commodity}_pairing.csv')
		
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
	
	
	def compute_PnL_per_future(self,long_short_map, rolling_over_df ):
		dfs = []
		
		for future in long_short_map:
			future_df = pd.DataFrame(long_short_map[future])
			future_df = future_df.merge(rolling_over_df,how = 'left', on = 'Date')
			for position in ['long','short']:
				mult = 1 if position == 'long' else -1 
				position_df =   future_df[ (future_df['long_short'] == position)]
				quant_adj = position_df['Quantity'].shift(1)
				quant_adj = quant_adj.fillna(0)
				price = future_df.loc[ (future_df['long_short'] == position),'Price'] .ffill()
				if not future_df['long_short'].isin([position]).empty:
					future_df.loc[ (future_df['long_short'] == position),'Pnl'] = mult*(price - price.shift(1))*quant_adj
					# to avoid warning to setting up column previously float64 and then object due to the presence of NaN or NaT
					future_df = future_df.astype({'Pnl' : 'object'})

			future_df['cum_PnL'] = future_df['Pnl'].cumsum()
			utilities.save_data_per_future(self.configuration_path,future_df,future)
			future_df = future_df.rename(columns = {'cum_PnL' : future})
			dfs.append(future_df[['Date', future]])
		return dfs
	
	def compute_PnL(self,long_short_map,rolling_over_df):

		dfs = self.compute_PnL_per_future(long_short_map,rolling_over_df)
		
		#merge all DataFrames into one
		final_df = reduce(lambda  left,right: pd.merge(left,right,on=['Date'], how='outer'), dfs)
		final_df.sort_values(by = 'Date', inplace = True, ignore_index= True, ascending = True)

		final_df['PnL'] = final_df[[col  for col in final_df.columns if col != 'Date']].sum(axis=1)
		final_df['PNL'] = final_df['PnL']*self.contract_value
		
		# merging with rolling over period
		final_df = final_df.merge(rolling_over_df, how = 'left', on = 'Date')
		logger.info('Saving PnL outcome')
		final_df.to_csv(f'{self.configuration_path}/{self.commodity}_PnL.csv')
		self.PnL = final_df

	def handle_missing_price(self,long_short_map,futures,prices,counting_rolling,previous_future_flag = False):
		for _, future in futures.items():
			if pd.isna(prices[future]) and counting_rolling > 1 :
				long_short_map[future]['Quantity'].append(long_short_map[future]['Quantity'][-1])
			elif pd.isna(prices[future]):
				if  previous_future_flag:
					long_short_map[future]['Quantity'].append(5)
				else:
					long_short_map[future]['Quantity'].append(0)
			else:
				if  previous_future_flag:
					long_short_map[future]['Quantity'].append(5 - counting_rolling)
				else:
					long_short_map[future]['Quantity'].append(counting_rolling)

		return long_short_map
						

	def rolling_period(self,long_short_map,futures,previous_futures,prices,counting_rolling):
		for future_map in [futures,previous_futures]:
			for position, future in future_map.items():
				long_short_map[future]['Date'].append(prices.Date)
				long_short_map[future]['Price'].append(prices[future])
				long_short_map[future]['long_short'].append(position)
		
		long_short_map = self.handle_missing_price(long_short_map,futures,prices,counting_rolling)
		long_short_map = self.handle_missing_price(long_short_map,previous_futures,prices,counting_rolling,True)
		
		return long_short_map
	
	def base_period(self,long_short_map,futures,prices ):
		for position, future in futures.items():
			long_short_map[future]['Date'].append(prices.Date)
			long_short_map[future]['Price'].append(prices[future])
			long_short_map[future]['Quantity'].append(5)
			long_short_map[future]['long_short'].append(position)
		return long_short_map

	def single_run(self, distance, due_shift):
		logger.info(f'For the commodity {self.commodity} discovering future pairing ') 
		expiration_date_df = self.futures_pairing(distance, due_shift)
		if expiration_date_df.empty:
			logger.info(f'{self.commodity} no pairings found ')
			return 
		data = self.data
		
		long_short_map = defaultdict(lambda : defaultdict(list))
		rolling_over = []

		starting_date = dt.datetime(1789,1,1)
		is_rolling = False
		counting_rolling = 0
		previous_future = {}

		#market_out_flag = False
		#---------------- settings --------------------
		logger.info('Starting back test')
		for exp_row in expiration_date_df.itertuples():
			futures = {'long' : exp_row.Pair, 'short' : exp_row.Future}
			starting_rolling = utilities.get_starting_rolling_date(exp_row.Due)
			for idx,row in data[data['Date'] >= starting_date ].iterrows():
				if long_short_map == {} and (pd.isna(row[futures['short']]) or pd.isna(row[futures['long']]) ) :
					logger.info(f'the first pairing {futures["short"]}-{futures["long"]} does not have available prices in common date {row.Date}')
					continue
				if row.Date > starting_rolling :
					logger.info(f'current date {row.Date} > starting rolling {starting_rolling} -> Skip pairing')
					'''it means that the current time is later than starting rolling so
					 it is reasonable to skip this pairing'''
					starting_date = row.Date
					break
				if (row.Date == starting_rolling):
					is_rolling = True
					previous_futures = {'long' : futures['long'], 'short' : futures['short']}
					starting_date = row.Date
					break

				#------------------- START ROLLING PERIOD ---------------------------------------------------------	
				if is_rolling :
					counting_rolling += 1
					rolling_over.append((is_rolling, row.Date,counting_rolling))

					long_short_map = self.rolling_period(long_short_map,
													     futures,
													     previous_futures,
													     row,
													     counting_rolling)

				#------------------- END ROLLING PERIOD ---------------------------------------------------------

				#------------------- BASE PERIOD ----------------------------------------------------------------	
		
				else:
					long_short_map = self.base_period(long_short_map,futures,row)

				if counting_rolling == 5 :
						is_rolling = False
						counting_rolling = 0
				#------------------- BASE PERIOD ----------------------------------------------------------------	
		if not is_rolling:
			logger.warning('Exit from loop not in pre rolling period')
		
		logger.info('Closing ALL positions')
		closing_position = data[data['Date'] == row.Date ].iloc[0]
		long_short_map = self.base_period(long_short_map,previous_futures,closing_position)
		rolling_over_df = pd.DataFrame(rolling_over,columns = ['IS_ROLLING','Date', 'Day'])
		#rolling_over_df = rolling_over_df.astype({'IS_ROLLING': bool})
		self.compute_PnL(long_short_map,rolling_over_df)
		self.compute_sharp_ratio(distance,due_shift)
		self.save_plot(distance,due_shift)

	def save_plot(self, distance : int, due_shift : int):
		fig = plotting_lib.create_figure(self.PnL,f'{self.commodity}_{distance}_{due_shift}_PnL','Date','PNL',self.commodity)
		self.figure = fig
		logger.info(f'Save Image plot {self.commodity}')
		plotting_lib.plot(fig,self.configuration_path,SAVE = True)

	def plot(self):
		plotting_lib.plot(self.figure,self.output_path, PLOT=True)

	def run(self):
		logger.info('Loading database')
		database = utilities.load_database(self.database_path,self.commodity)
		self.available_future(database)
		self.data = self.merging_futures_data(database,'Price')
		self.market_out_map = BackTest.get_market_out_dates(self.database_path,self.commodity)

		for conf in self.configuration :
			for due_shift in range(len(self.configuration.keys())):
				self.configuration_path = utilities.get_output_path(self.commodity,conf,due_shift)
				logger.info(f'Starting configuration {self.configuration[conf]} with due shift {due_shift}' )
				self.single_run(conf,due_shift)
		logger.info('Saving sharp ratios')
		self.sharp_ratio.reset_index(drop=True,inplace= True)
		self.sharp_ratio.sort_values(by = 'Sharp_Ratio', inplace = True, ignore_index= True, ascending = False)

		self.sharp_ratio.to_csv(f'{self.output_path}/{self.commodity}_sharp_ratio.csv')


