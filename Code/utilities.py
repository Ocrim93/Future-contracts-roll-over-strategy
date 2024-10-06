import datetime as dt
import pickle 
import os 
from pandas.tseries.offsets import BDay
import pandas as pd
from settings import PATH
from Code.Bloomberg_formatting import LIST_SYMBOL 
from loguru import logger
import datetime as dt
import numpy as np
from functools import reduce
from settings import COLUMN


def create_folder(path : str = PATH.Output.value, output_folder : str = None):
	# ---------- Create folder -----------
	for folder in  list(PATH):
		if not os.path.exists(folder.value):
			os.mkdir(folder.value)
			logger.info(f'Create folder {folder.value}')
	creation_path = f'{path}/{output_folder}' if output_folder != None else path 
	if not os.path.exists(creation_path):
		os.makedirs(creation_path)
		logger.info(f'Create folder {creation_path}')
	
	return  creation_path

def retrieve_value(df : pd.DataFrame, field : str, condition : dict = {}, fallback_value : float = 0):
	data = df.copy()[field]
	value = fallback_value
	if condition != {}:
		for key, value in condition.items:
			data = data[data[key] == value]
	if not data.empty or data.notna():
		#check to obtain only one values 
		if len(data) != 1:
			logger.error(f'Finding more than one value {field} for {condition}')
		value = data.values[0]
	return value

def handling_missing_column(data : pd.DataFrame, columns : list):
	for col in columns:
		if col not in data.columns:
			data[col] = np.full(len(data), np.nan)
	return data

def stream_and_rename(data : pd.DataFrame, stream_list : list, rename_map : dict ):
	data = data.copy()
	data = handling_missing_column(data, stream_list)
	data = data[stream_list]
	data = data.rename(columns = rename_map)
	return data

def formatting_futures_data_before_aggregation(data : pd.DataFrame, futures : str, column : str):
	df = data.copy().rename(columns = {column : futures})
	df = df[[COLUMN.Date.value, futures]]
	if column == COLUMN.PnL.value:
		'''
		 when we short and long the same futures at the same time 
		 we find two rows with the same date but 2 PnLs: one short and one long 
		 we need to group by and sum them 
		'''
		df= df.groupby(COLUMN.Date.value).sum()
	else:
		df= df.groupby(COLUMN.Date.value).mean()
	df.reset_index(inplace=True)
	return df

def merging_all_dataframes(dfs : list, column : str ):
	df = reduce(lambda  left,right: pd.merge(left,right,on=[COLUMN.Date.value], how='outer'), dfs)
	df.sort_values(by = COLUMN.Date.value, inplace = True, ignore_index= True, ascending = True)
	df[column] = df[[col  for col in df.columns if col != COLUMN.Date.value]].sum(axis=1)
	df = df.drop([col  for col in df.columns if col not in [column, COLUMN.Date.value]], axis =1 )
	return df

def log_inizialization(path :  str):
	today = dt.datetime.now().strftime('%d%b%Y')
	logger.add(f"{path}/log",enqueue=False, mode = 'w')

def load_database(file_path : str, commodity : str = None):
	pkl_file = open(file_path, 'rb')
	data = pickle.load(pkl_file)
	pkl_file.close()
	if commodity != None:
		data = data[commodity]
	return data

def last_business_date(date : dt.datetime):
	bday = BDay()
	is_business_date = bday.is_on_offset(date)
	if is_business_date:
		return date
	else:
		return 	last_business_date(date +  dt.timedelta(days=1))

def get_starting_rolling_date(date : dt.datetime):
	date = dt.datetime.strftime(date,'%Y/%m/%d')
	year,month,day = date.split('/')
	start = pd.to_datetime(f'{year}/{month}/1')
	end = pd.to_datetime(f'{year}/{month}/15')
	b_dates  = pd.date_range(start = start, end = end, freq = 'B')
	sixth_day = b_dates[5]
	return sixth_day

def lot_size_and_unit_liquidity(commodity : str):
	info = pd.read_csv(PATH.fututes_info.value,sep ='\t')
	comm_info = info[info['Commodity'] == commodity]
	if comm_info.empty:
		logger.error(f'{commodity} Nan Lot Size Nan unit tick ')
		return 1,1,1
	return comm_info['Lot size'].values[0],comm_info['Unit'].values[0], comm_info['Liquidity'].values[0]

def find_sequence(months : list):
	squence = []
	for m in LIST_SYMBOL:
		if m in months:
			squence.append(m)
	return squence		


def get_database_path():
	return PATH.database.value

def get_output_path(commodity :str, data_folder : str = None ,pairing_distance : int  = None, due_shift : int  = None):
	if pairing_distance == None:
		path = create_folder(output_folder = f'{commodity}')
	else:
		path = create_folder(output_folder = f'{commodity}/{pairing_distance}/{due_shift}')
		if data_folder != None:
			data_path = create_folder(output_folder = f'{commodity}/{pairing_distance}/{due_shift}/{data_folder}')
			return path, data_path
	return path

def save_csv(data : pd.DataFrame ,path : str, filename : str, commodity : str = None):
	io_name = f'{commodity}_{filename}' if commodity != None else filename
	if data.empty:
		logger.warning(f'File : {io_name} Not Saved, empty dataframe')
	else:
		data.to_csv(f'{path}/{io_name}.csv', sep = '\t')
		logger.info(f'File : {io_name} Saved')








