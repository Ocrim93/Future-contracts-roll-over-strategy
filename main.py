from settings import PATH 
from Code.back_testing import BackTest
from Code import utilities,plotting_lib
from plotly.subplots import make_subplots
import plotly.graph_objects as go

database = utilities.load_database(PATH.database.value)
'''
comm = 'LH'



back_test = BackTest(comm,PATH.database.value,PATH.Output.value)

back_test.run()
back_test.plot()





'''

fig = None
for comm in database:
	if comm in ['LP','LT','LN','LL','LA','LX','FC']:
		print('@@@@@@@@@@@@@@@@@@@@@@@@ ' ,comm)
		continue
	back_test = BackTest(comm,PATH.database.value,PATH.Output.value)

	back_test.run()
	back_test.plot()
	pnl = back_test.PnL

	if fig == None:
		#rows = int(len(database.keys())/3) + ( 1 if len(database.keys())%3 != 0 else 0 )  
		#fig = make_subplots(rows=rows,cols=3)
		fig = plotting_lib.create_figure(pnl,'PnL','Date','Cum_Gain',comm)

	else:
		fig = plotting_lib.adding_line(fig,pnl,comm,'Date','Cum_Gain')	
		#fig.add_scatter(plotting_lib.create_figure(pnl,'PnL','Date','Cum_Gain',comm))
		#fig.add_scatter(go.Scatter(x=pnl['Date'], y  = pnl['Cum_Gain']),row=pr, col=pc)

plotting_lib.plot(fig,PATH.Output.value, 'Summary')

















