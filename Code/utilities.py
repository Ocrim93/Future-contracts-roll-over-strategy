import datetime as dt
import pickle 
import os 
from pandas.tseries.offsets import BDay
import pandas as pd
from settings import PATH
from loguru import logger


def create_folder(output_folder : str = None):
	# ---------- Create folder -----------
	for folder in  list(PATH):
		if not os.path.exists(folder.value):
			os.mkdir(folder.value)
			logger.info(f'Create folder {folder.value}')
	if output_folder != None:
		if not os.path.exists(f'{PATH.Output.value}/{output_folder}'):
			os.mkdir(f'{PATH.Output.value}/{output_folder}')
			logger.info(f'Create folder {output_folder}')
	return  f'{PATH.Output.value}/{output_folder}'

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
def lot_size_and_unit(commodity : str):
	info = pd.read_csv(PATH.fututes_info.value,sep ='\t')
	comm_info = info[info['Commodity'] == commodity]
	if comm_info.empty:
		print(logger.error(f'{commodity}'))
		return 1,1
	return comm_info['Lot size'].values[0],comm_info['Unit'].values[0]







