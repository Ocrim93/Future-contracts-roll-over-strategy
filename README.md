# Future-contracts-roll-over-strategy

# Installation 
	-- conda env create -f requirements.yml

# Strategy 

The strategy is based on the following steps:
- Finding a pair of futures on the same commodity whose expiration dates are 1 year apart.
* Long on the future with earliest expiration date and short on future with latest expiration date
* Rolling over new futures pair on the 6th, 7th, 8th, 9th and 10th business dates of the long future expiration month
+ Compute PnL, cumulative gain and plot them 

In case of missing prices because the database might not be fully completed, it follows	
-	if there is no available price in any future of the same commodity at the specific day, it would be high probability it was a non tradable day: the PnL is equal to the day before's PnL
+	if there are available prices in other futures of the same commodity at the specific date, it is a missing price. Two cases:
	- during rolling over period -> the future with missing prices would long/short double it the next business day 
	+ orthrwise, it has assumed that the PnL is equal to the day before's PnL

# Theory

Traders roll over futures contracts to switch from the front month (it refers to the nearest expiration date in future trading)	that is close to expiration to another contract in a further-out-month. Futures contracts have expiration dates as opposed to stocks that trade in perpetuity. They are rolled over to a different month to avoid the costs and obligations assosciated with settlement of the contracts. Futures contracts are most often settled by physical settlement or cash settlement. 

