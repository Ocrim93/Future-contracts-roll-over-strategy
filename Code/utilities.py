import datetime as dt
import pickle 


def load_database(file_path):
	pkl_file = open(file_path, 'rb')
	data = pickle.load(pkl_file)
	pkl_file.close()

	return data

def last_business_date(date : dt.datetime):
	bday = BDay()
	is_business_date = bday.is_on_offset(date)
	if is_business_date:
		return date
	else:
		return 	last_business_date(date- dt.timedelta(days=1))