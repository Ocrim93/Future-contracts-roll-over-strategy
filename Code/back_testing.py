from loguru import logger
from . import utilities
import numpy as np
import pandas as pd
import datetime as dt
from .Bloomberg_formatting import get_expiration_date_from_futures
from . import plotting_lib
from collections import defaultdict 
from functools import reduce	
from settings import PARAMETER, COLUMN, FILENAME

class BackTest():


	@staticmethod
	def get_market_out_dates(database_path : str, commodity : str):
		database = utilities.load_database(database_path, commodity)
		market_out_map = {}
		for future, df in database.items():
			if 	'MarketOut'  in list(df.columns) :
				market_out_df = df[df['MarketOut'].isin([1,-1])]
				if not market_out_df.empty:
					market_out_map[future] = market_out_df[COLUMN.Date.value].to_list()
		return 	market_out_map		

	def __init__(self, commodity : str, 
					   contract_number : int = 5,
					   start_date_PnL : dt.datetime = dt.datetime(2010,1,1),
					   end_date_PnL : dt.datetime = None,
					   specific_run : list = None):

		self.commodity = commodity
		self.database_path = utilities.get_database_path()
		self.output_path = utilities.get_output_path(commodity)

		self.contract_number = contract_number 
		self.lot_size,self.unit, self.liquidity = utilities.lot_size_and_unit_liquidity(commodity)
		self.contract_value = self.lot_size*self.unit*(contract_number/5)*(self.liquidity/5)
		self.configuration = self.find_configuration()
		self.expiration_date_df = pd.DataFrame()
		self.data = pd.DataFrame()

		self.start_date_PnL = start_date_PnL
		self.end_date_PnL = end_date_PnL
		self.performance_ratio_df = pd.DataFrame()

		self.specific_run = specific_run

	def compute_performance_ratio(self,distance : int,due_shift : int ):
		pnl = self.PnL[COLUMN.PnL.value]
		cum_pnl = self.PnL[COLUMN.Cuml_PnL.value]  
		std = pnl.std()

		annualized_std = std*np.sqrt(PARAMETER.TRADING_DAYS.value)
		annualized_cum_pnl = (cum_pnl.iloc[-1] - cum_pnl.iloc[0])*PARAMETER.TRADING_DAYS.value/cum_pnl.shape[0]
		performance_ratio = annualized_cum_pnl/annualized_std
		logger.info(f'{self.commodity} {COLUMN.Cuml_PnL_annualized.value} : {annualized_cum_pnl:.2f}, {COLUMN.STD_annualized.value} : {annualized_std:.2f}, {COLUMN.Performance_Ratio.value} : {performance_ratio:.2f}')
		performance_ratio_df = pd.DataFrame(data = { COLUMN.Distance.value : [distance],
													 COLUMN.Due_Shift.value : [due_shift],
													 COLUMN.STD_annualized.value: [annualized_std],
													 COLUMN.Cuml_PnL_annualized.value : [annualized_cum_pnl],
													 COLUMN.Performance_Ratio.value : [performance_ratio] })
		if not performance_ratio_df.empty:
			self.performance_ratio_df = pd.concat([self.performance_ratio_df,performance_ratio_df])

	def find_configuration(self):
		'''
			Compute the futures pairing with regard to 
			different number of futures apart among long and short legs
			i.e. G,J,M,Q -> 1: (G,J) (J,M)
						  2: (G,M) (J,Q) ... 
		'''
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

	def available_futures(self,database : pd.DataFrame ):
		futures = []
		exp_dates = []
		real_exp_dates = []
		
		for future,df in database.items():
			futures.append(future)
			real_exp_dates.append(df[COLUMN.Date.value].iloc[-1])
		
		expiration_date_df = pd.DataFrame({COLUMN.Due.value : real_exp_dates , COLUMN.Futures.value : futures} )
		# Month symbol column 
		expiration_date_df[COLUMN.Month_Symbol.value] = expiration_date_df[COLUMN.Futures.value].apply(lambda x : x[2])
		expiration_date_df.sort_values(COLUMN.Due.value,ascending = True,ignore_index = True,inplace = True)
		utilities.save_csv(expiration_date_df,self.output_path,FILENAME.Available_Futures.value,  self.commodity)
		self.expiration_date_df = expiration_date_df[expiration_date_df[COLUMN.Due.value] >= self.start_date_PnL]

	def futures_pairing(self, distance : int, due_shift : int):
		'''
			Finding the futures pairing with the respect to configuration of the month and due_date > expiring date 
			(in case the pairing is 12 month apart,	it would be GG and without the date condition it would select the same futures) 
		'''
		expiration_date_df = self.expiration_date_df.copy()
		futures_list = expiration_date_df[COLUMN.Futures.value].to_list()
		configuration = self.configuration[distance]
		
		for futures in futures_list:
			month_symbol = futures[2]		
			exp_date = expiration_date_df[expiration_date_df[COLUMN.Futures.value] == futures][COLUMN.Due.value].values[0]
			mask =  (expiration_date_df[COLUMN.Month_Symbol.value] ==  configuration[month_symbol]) & (expiration_date_df[COLUMN.Due.value] > exp_date)
			if not expiration_date_df.loc[mask, COLUMN.Futures.value].empty:
				pair =  expiration_date_df.loc[mask, COLUMN.Futures.value].values[0]
				expiration_date_df.loc[(expiration_date_df[COLUMN.Futures.value] == futures),COLUMN.Pair.value] = pair
			#else:
			#	expiration_date_df.loc[(expiration_date_df[COLUMN.Futures.value] == futures),COLUMN.Pair.value] = np.nan
		expiration_date_df = expiration_date_df[(expiration_date_df[COLUMN.Pair.value] != 'nan')]
		#expiration_date_df = expiration_date_df.iloc[::due_shift+1]
		expiration_date_df[COLUMN.Due.value] = expiration_date_df[COLUMN.Due.value].shift(due_shift)
		expiration_date_df.dropna(inplace=True)
		expiration_date_df.reset_index(inplace = True, drop = True)
		utilities.save_csv(expiration_date_df, self.configuration_path, FILENAME.Futures_Pairing.value,self.commodity)
		return expiration_date_df
	
	def merging_futures_data(self,database : pd.DataFrame):
		'''
			database is A map <key,value> := <futures_symbol,dataframe(Date,Price)>
			after merging change column name: Price -> Futures_symbol
		'''
		db_data= pd.DataFrame({COLUMN.Date.value : []})
		for futures,df in database.items():
			df = df[[COLUMN.Date.value,COLUMN.Price.value]]
			df = df.rename(columns = { COLUMN.Price.value : futures })
			db_data = db_data.merge(df, on = COLUMN.Date.value, how = 'outer')
		if db_data[COLUMN.Date.value].shape[0] != db_data[COLUMN.Date.value].drop_duplicates().shape[0]:
			print('WARNING duplicate dates')
		end_date = list(db_data[COLUMN.Date.value])[-1] if self.end_date_PnL == None else self.end_date_PnL 
		start_date = self.start_date_PnL
		date_range = pd.date_range(start=start_date, end=end_date, freq = 'B')
		date_range_df = pd.DataFrame(data = { COLUMN.Date.value : date_range})
		dataset = date_range_df.merge(db_data, on = COLUMN.Date.value, how ='left')
		dataset.sort_values(by = COLUMN.Date.value, inplace = True, ignore_index= True, ascending = True)	
		return dataset


	def compute_PnL_per_futures(self, long_short_map, rolling_over_df ):
		dfs = []
		
		for future in long_short_map:
			future_df = pd.DataFrame(long_short_map[future])
			future_df = future_df.merge(rolling_over_df, how = 'left', on = COLUMN.Date.value)
			if future_df[future_df[COLUMN.Price.value].isna()].shape[0] == len(future_df):
				future_df[COLUMN.Price.value] = np.full(len(future_df), np.nan)
			future_df.loc[pd.isnull(future_df[COLUMN.Price.value]),COLUMN.Price.value] =  np.nan
			future_df[COLUMN.Price.value] = future_df[COLUMN.Price.value].astype('float')
			for position in [PARAMETER.Long.value,PARAMETER.Short.value]:
				mult = 1 if position == PARAMETER.Long.value else -1 
				position_df =   future_df[ (future_df[COLUMN.Long_Short.value] == position)]
				quant_adj = position_df[COLUMN.Contract_Quantity.value].shift(1)
				quant_adj = quant_adj.fillna(0)
				price = future_df.loc[ (future_df[COLUMN.Long_Short.value] == position),COLUMN.Price.value].ffill()
				if not future_df[COLUMN.Long_Short.value].isin([position]).empty:
					future_df.loc[ (future_df[COLUMN.Long_Short.value] == position),COLUMN.PnL.value] = mult*(price - price.shift(1))*quant_adj
					# to avoid warning to setting up column previously float64 and then object due to the presence of NaN or NaT
					future_df = future_df.astype({COLUMN.PnL.value : 'object'})

			#future_df[COLUMN.Cuml_PnL.value] = future_df[COLUMN.PnL.value].cumsum()
			utilities.save_data_per_future(self.configuration_path,future_df,future)
			future_df = future_df.rename(columns = {COLUMN.PnL.value : future})
			future_df = future_df[[COLUMN.Date.value, future]]
			# when we short and long the same futures at the same time 
			# we find tow rows with the same date but 2 PnLs: one short and one long 
			# we need to group by 
			future_df= future_df.groupby(COLUMN.Date.value).sum()
			future_df.reset_index(inplace=True)
			dfs.append(future_df)
		return dfs
	
	def compute_PnL(self,long_short_map,rolling_over_df):

		result = False
		dfs = self.compute_PnL_per_futures(long_short_map,rolling_over_df)
		if len(dfs) > 0 :
			#merge all DataFrames into one
			final_df = reduce(lambda  left,right: pd.merge(left,right,on=[COLUMN.Date.value], how='outer'), dfs)
			final_df.sort_values(by = COLUMN.Date.value, inplace = True, ignore_index= True, ascending = True)

			final_df[COLUMN.PnL.value] = final_df[[col  for col in final_df.columns if col != COLUMN.Date.value]].sum(axis=1)
			final_df[COLUMN.PnL.value] = final_df[COLUMN.PnL.value]*self.contract_value
			final_df[COLUMN.Cuml_PnL.value] = final_df[COLUMN.PnL.value].cumsum()
			
			# merging with rolling over period
			final_df = final_df.merge(rolling_over_df, how = 'left', on = COLUMN.Date.value)
			logger.info('Saving PnL outcome')
			utilities.save_csv(final_df,self.configuration_path, FILENAME.PnL.value,self.commodity)
			self.PnL = final_df
			result = True
		else:
			logger.warning(f'{self.commodity} Zero data to compute the PnL ')
		return result
	def handle_missing_price(self,long_short_map,futures,prices,counting_rolling,previous_future_flag = False):
		for _, future in futures.items():
			if pd.isna(prices[future]) and counting_rolling > 1 :
				long_short_map[future][COLUMN.Contract_Quantity.value].append(long_short_map[future][COLUMN.Contract_Quantity.value][-1])
			elif pd.isna(prices[future]):
				if  previous_future_flag:
					long_short_map[future][COLUMN.Contract_Quantity.value].append(5)
				else:
					long_short_map[future][COLUMN.Contract_Quantity.value].append(0)
			else:
				if  previous_future_flag:
					long_short_map[future][COLUMN.Contract_Quantity.value].append(5 - counting_rolling)
				else:
					long_short_map[future][COLUMN.Contract_Quantity.value].append(counting_rolling)

		return long_short_map
						

	def rolling_period(self,long_short_map,futures,previous_futures,prices,counting_rolling):
		for future_map in [futures,previous_futures]:
			for position, future in future_map.items():
				long_short_map[future][COLUMN.Date.value].append(prices.Date)
				long_short_map[future][COLUMN.Price.value].append(prices[future])
				long_short_map[future][COLUMN.Long_Short.value].append(position)
		
		long_short_map = self.handle_missing_price(long_short_map,futures,prices,counting_rolling)
		long_short_map = self.handle_missing_price(long_short_map,previous_futures,prices,counting_rolling,True)
		
		return long_short_map
	
	def base_period(self,long_short_map,futures,prices ):
		for position, future in futures.items():
			long_short_map[future][COLUMN.Date.value].append(prices.Date)
			long_short_map[future][COLUMN.Price.value].append(prices[future])
			long_short_map[future][COLUMN.Contract_Quantity.value].append(5)
			long_short_map[future][COLUMN.Long_Short.value].append(position)
		return long_short_map

	def single_run(self, distance, due_shift):
		self.configuration_path = utilities.get_output_path(self.commodity,distance,due_shift)
		logger.info(f'For the commodity {self.commodity} discovering future pairing ') 
		expiration_date_df = self.futures_pairing(distance, due_shift)
		if expiration_date_df.empty:
			logger.info(f'{self.commodity} no pairings found ')
			return 
		data = self.data.copy()
		
		long_short_map = defaultdict(lambda : defaultdict(list))
		rolling_over = []

		starting_date = self.start_date_PnL #dt.datetime(1789,1,1)
		is_rolling = False
		counting_rolling = 0
		previous_futures = {}
		#market_out_flag = False
		#---------------- settings --------------------
		logger.info('Starting back test')
		for _,exp_row in expiration_date_df.iterrows():
			#print(expiration_date_df[expiration_date_df['Due'] >= dt.datetime(2022,6,6)])
			#if exp_row.Due >= dt.datetime(2022,6,6):
			#	print(exp_row)
			#	print(is_rolling,counting_rolling)
			futures = {PARAMETER.Long.value : exp_row[COLUMN.Pair.value], PARAMETER.Short.value : exp_row[COLUMN.Futures.value]}
			starting_rolling = utilities.get_starting_rolling_date(exp_row.Due)
			for idx,row in data[data[COLUMN.Date.value] >= starting_date ].iterrows():
				if long_short_map == {} and (pd.isna(row[futures[PARAMETER.Short.value]]) or pd.isna(row[futures[PARAMETER.Long.value]]) ) :
					#logger.info(f'the first pairing {futures[PARAMETER.Short.value]}-{futures[PARAMETER.Long.value]} does not have available prices in common date {row[COLUMN.Date.value]}')
					continue
				if row[COLUMN.Date.value] > starting_rolling :
					#logger.info(f'current date {row[COLUMN.Date.value]} > starting rolling {starting_rolling} -> Skip pairing')
					'''
							it means that the current time is later than starting rolling period. Hence
					 		it is reasonable to skip this pairing
					'''
					starting_date = row[COLUMN.Date.value]
					break
				if (row[COLUMN.Date.value] == starting_rolling):
					#print(starting_rolling)
					is_rolling = True
					previous_futures = {PARAMETER.Long.value : futures[PARAMETER.Long.value], PARAMETER.Short.value : futures[PARAMETER.Short.value]}
					starting_date = row[COLUMN.Date.value]
					break

				#------------------- START ROLLING PERIOD ---------------------------------------------------------	
				if is_rolling :
					counting_rolling += 1
					rolling_over.append((is_rolling, row[COLUMN.Date.value],counting_rolling))

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
			logger.warning('Exit from loop not in not-rolling period')
		
		logger.info('Closing ALL positions')
		closing_position = data[data[COLUMN.Date.value] == row[COLUMN.Date.value] ].iloc[0]
		long_short_map = self.base_period(long_short_map,previous_futures,closing_position)
		rolling_over_df = pd.DataFrame(rolling_over,columns = [COLUMN.IS_ROLLING.value,COLUMN.Date.value, COLUMN.Rolling_Day.value])
		#rolling_over_df = rolling_over_df.astype({COLUMN.IS_ROLLING.value: bool})
		if self.compute_PnL(long_short_map,rolling_over_df):
			self.compute_performance_ratio(distance,due_shift)
			self.save_plot(distance,due_shift)

	def save_plot(self, distance : int, due_shift : int):
		fig = plotting_lib.create_figure(self.PnL,f'{self.commodity}_{distance}_{due_shift}_PnL',COLUMN.Date.value,COLUMN.Cuml_PnL.value,self.commodity)
		self.figure = fig
		logger.info(f'Save Image plot {self.commodity}')
		plotting_lib.plot(fig,self.configuration_path,SAVE = True)

	def plot(self):
		plotting_lib.plot(self.figure,self.output_path, PLOT=True)

	def run(self):
		logger.info('Loading database')
		database = utilities.load_database(self.database_path,self.commodity)
		self.available_futures(database)
		self.data = self.merging_futures_data(database)
		self.market_out_map = BackTest.get_market_out_dates(self.database_path,self.commodity)
		# in case specific run is enabled 
		if self.specific_run != None :
			logger.info(f'Starting configuration distance {self.specific_run[0]} with due shift {self.specific_run[1]}: {self.configuration[self.specific_run[0]]}' )	
			self.single_run(6,3)
		else:
			for conf in self.configuration :
				for due_shift in range(len(self.configuration.keys())):
					logger.info(f'Starting configuration distance {conf} with due shift {due_shift} : {self.configuration[conf]}' )
					#utilities.log_inizialization(self.configuration_path)
					self.single_run(conf,due_shift)
		if self.performance_ratio_df.empty:
			logger.info('NOT Saving sharp ratios, empty performance ratio dataset')
		else:
			logger.info('Saving sharp ratios')
			self.performance_ratio_df.reset_index(drop=True,inplace= True)
			self.performance_ratio_df.sort_values(by = COLUMN.Performance_Ratio.value, inplace = True, ignore_index= True, ascending = False)
			utilities.save_csv(self.performance_ratio_df,self.output_path, FILENAME.Sharp_Ratio.value, self.commodity)


