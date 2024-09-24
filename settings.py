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
	Short = 'S'
	Long = 'L'

class COLUMN(Enum):
	Futures = 'Futures'
	Pair = 'Futures Pair'
	Price = 'Price'
	Date = 'Date'
	Due = 'Due'
	IS_ROLLING = 'IS_ROLLING'
	Rolling_Day = 'Rolling_Day'
	Contract_Quantity = 'Quantity'
	Long_Short = 'L/S'

	_Pnl = '_P&L' # PnL without the contract, unit and liquidity size
	PnL = 'P&L'

	Month_Symbol = 'Month Symbol'
	#Distance between futures, F and G has 1 future apart
	Distance = 'Distance'
	# Shift in rolling over dates
	Due_Shift = 'Due Shift'
	STD_annualized = 'STD nnualized'
	Cuml_PnL = 'Cuml_P&L'	
	Cuml_PnL_annualized = 'Cumulative P&L annualized'
	Performance_Ratio = 'Performance Ratio'