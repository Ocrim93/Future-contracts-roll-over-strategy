from settings import PATH 
from Code.back_testing import BackTest
from Code import utilities,plotting_lib
database = utilities.load_database(PATH.database.value)

fig = None
for comm in database:
	if comm in ['LP','LT','LN','LL','LA','LX']:
		print('@@@@@@@@@@@@@@@@@@@@@@@@ ' ,comm)
	back_test = BackTest(comm,PATH.database.value,PATH.Output.value)

	back_test.run()
	pnl = back_test.PnL
	if fig == None:
		fig = plotting_lib.create_figure(pnl,'PnL','Date','Cum_Gain',comm)
	else:
		fig = plotting_lib.adding_line(fig,pnl,comm,'Date','Cum_Gain')	

plotting_lib.plot(fig,PATH.Output.value, 'Summary')

















