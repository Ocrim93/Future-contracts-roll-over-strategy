from settings import PATH 
from Code import utilities
from loguru import logger

logger.info('Loading database')
database = utilities.load_database(PATH.database.value)

comm = 'CC'
print(type(database[comm]))
