from Module.extract_data import Extract
from settings import PATH

extract_obj = Extract(PATH.excel_file.value)
extract_obj.from_excel()