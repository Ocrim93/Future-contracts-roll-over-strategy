from enum import Enum

class PATH(Enum):
	Input = './Input'
	Output = './Output'
	database = f'{Input}/new_database'
	fututes_info = f'{Input}/futures_info.csv'

class GRAPH(Enum):
	font_family="Courier New"
	font_color="blue"
	title_font_family="Times New Roman"
	title_font_color="blue"
	title_font_size = 20
	legend_title_font_color="green"

class PARAMETER(Enum):
	TRADING_DAYS = 252

class COLUMN(Enum):
	Futures = 'Futures'
	Pair = 'Futures Pair'
	Price = 'Price'
	Due = 'Due'
	Month_Symbol = 'Month Symbol'
	#Distance between futures, F and G has 1 future apart
	Distance = 'Distance'
	# Shift in rolling over dates
	Due_Shift = 'Due Shift'
	STD_annualized = 'STD nnualized'
	Cuml_PnL = 'Cumulative P&L annualized'
	Performance_Ratio = 'Performance Ratio'