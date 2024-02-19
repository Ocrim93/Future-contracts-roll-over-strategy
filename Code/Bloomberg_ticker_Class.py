from pandas.tseries.offsets import BDay
from pandas.tseries.offsets import BMonthEnd
from . import utilities


def get_map_month_symbol(reverse = False ):
	
	list_symbol = ['F','G','H','J','K','M','N','Q','U','V','X','Z']
	if reverse:
		map_month_symbol = {  symbol : idx+1  for idx,symbol in  enumerate(list_symbol)}
	else:
		map_month_symbol = { idx+1 : symbol for idx,symbol in  enumerate(list_symbol)}
	return map_month_symbol

def get_year_symbol(year):
	if year == 2024:
		return '4'
	year_symbol = year - 2000 if year > 1999 else  year - 1900	
	if year_symbol < 10 :
		year_symbol = '0' + str(year_symbol)
	else :
		year_symbol = str(year_symbol)
	return year_symbol

				

def get_future_symbol(commodity,year,month):
	future_name = commodity +  get_map_month_symbol()[month]+ get_year_symbol(year)
	return future_name	

def get_expiration_date_from_futures(future_symbol):
	future = future_symbol[2:]
	month = int(get_map_month_symbol(reverse=True)[future[0]])
	if len(future) == 2 :
		if future[-1] == '4':
			year = 2024
		else:
			print('ERROR ',future_symbol)
	elif len(future) ==3 :
		year_symbol = int(future[1:])
		if year_symbol < 24:
			year = 2000 + year_symbol
		else:
			print('ERROR ',future_symbol)
	else:
		print('ERROR ',future_symbol)
	date = BMonthEnd().rollforward(dt.datetime(year,month,1))
	return utilities.last_business_date(date)			


