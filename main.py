from Code.back_testing import BackTest
from Code.utilities import load_database
from settings import PATH
import os
from Code.Trading_Indicator import Trading_Indicator

database = load_database(PATH.database.value)

for comm in database:
	b = BackTest(comm, specific_run= [1,1])		
	b.run()
Trading_Indicator('CL', 1,1)