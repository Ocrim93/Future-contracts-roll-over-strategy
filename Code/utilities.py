import datetime as dt

def last_business_date(date : dt.datetime):
	bday = BDay()
	is_business_date = bday.is_on_offset(date)
	if is_business_date:
		return date
	else:
		return 	last_business_date(date- dt.timedelta(days=1))