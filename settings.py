from enum import Enum

class PATH(Enum):
	Input = './Input'
	Output = './Output'
	excel_file = f'{Input}/BTC 2019 - 2023.xlsx'

class GRAPH(Enum):
	font_family="Courier New"
	font_color="blue"
	title_font_family="Times New Roman"
	title_font_color="blue"
	title_font_size = 20
	legend_title_font_color="green"
