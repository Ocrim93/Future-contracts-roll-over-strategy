from Code.back_testing import BackTest
from Code.utilities import load_database
from settings import PATH


database = load_database(PATH.database.value)

for comm in database:
	b = BackTest(comm)	
	b.run()
