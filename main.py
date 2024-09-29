from Code.back_testing import BackTest
from Code.utilities import load_database
from settings import PATH
import os

database = load_database(PATH.database.value)

for comm in database:
	#if comm in os.listdir(PATH.Output.value):
	#	continue
	if comm !='LC':
		continue
	b = BackTest(comm, specific_run = [6,3]	)	
	b.run()
	
	