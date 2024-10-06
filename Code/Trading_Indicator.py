from loguru import logger
from . import utilities
from settings import COLUMN,FILENAME, PATH
from . import plotting_lib
import pandas as pd
import yaml
import numpy as np

class Trading_Indicator():
	def __init__(self, 
				 commodity : str
				,pairing_distance : int
				,due_shift :int):
		
		self.commodity = commodity
		self.pairing_distance = pairing_distance
		self.due_shift = due_shift
		self.configuration_path = utilities.get_output_path(self.commodity, pairing_distance = pairing_distance, due_shift = due_shift)
		self.data = pd.read_csv(f'{self.configuration_path}/{self.commodity}_{FILENAME.PnL.value}.csv', sep = '\t')
		settings = yaml.safe_load(open(PATH.Trading_settings.value))
		self.filename = f'{self.commodity}_{self.pairing_distance}_{self.due_shift}_Trading_Indicator'

		for ind in settings['active']:
			match ind:
				case  COLUMN.Volume.value:
					self.volumne_open_interest(ind)
				case  COLUMN.Open_Interest.value:
					self.volumne_open_interest(ind)
				case  COLUMN.Volatility.value:
					self.volatility(settings[ind]['window'])
				case _:
					logger.warning(f'{ind} Not a Trading Indicator')

		self.save_plot(settings['active'])

	def volumne_open_interest(self, name : str):
		self.data.loc[self.data[name] == 0, name] = np.nan
		self.data[name] = self.data[name].ffill()

	def volatility(self, window : int ):
		self.data[COLUMN.Volatility.value] = self.data[COLUMN.PnL.value].rolling(window).std()
	
	def save_plot(self, indicators: list):
		title = f'{self.commodity} PnL ( futures apart : {self.pairing_distance} month shift : {self.due_shift}) Trading Indicators'
		fig = plotting_lib.create_multiple_axes_figure(self.data,title,COLUMN.Date.value,indicators, COLUMN.Cuml_PnL.value)
		self.figure = fig
		logger.info(f'Save Image plot {self.commodity} Trading Indicator')
		plotting_lib.plot(fig,self.configuration_path,self.filename, SAVE = True)