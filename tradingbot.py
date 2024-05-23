import logging
from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime, timedelta
from alpaca_trade_api import REST
from finbert_utils import estimate_sentiment 

API_KEY = "AKT5W81ONCBR6OLFHM2B"
API_SECRET = "G4ZoctCrwki8LScvYPWL9w3HutWbj2y0pvrCbNGn"
BASE_URL = "https://api.alpaca.markets"

APLACA_CREDS = {
	"API_KEY":API_KEY,
	"API_SECRET":API_SECRET,
	"PAPER": False
}

# Setup logging
logging.basicConfig(
    filename=f'tradingbot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MLTrader(Strategy): 
	def initialize(self, symbol:str="PFE", cash_at_risk:float=.5):
		self.set_market('24/7')
		self.symbol = symbol
		self.sleeptime = "1H"
		self.last_trade = None
		self.cash_at_risk = cash_at_risk
		self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

	def position_sizing(self):
		cash = self.get_cash()
		last_price = self.get_last_price(self.symbol)
		quantity = round(cash * self.cash_at_risk / last_price, 0)
		return cash, last_price, quantity

	def get_dates(self):
		today = self.get_datetime()
		three_days_prior = today - timedelta(days=3)
		return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

	def get_sentiment(self):
		today, three_days_prior = self.get_dates()
		news = self.api.get_news(symbol=self.symbol, start=three_days_prior, end=today)
		news = [ev.__dict__["_raw"]["headline"] for ev in news]
		probability, sentiment = estimate_sentiment(news)
		return probability, sentiment

	def on_trading_iteration(self):
		cash, last_price, quantity = self.position_sizing()
		probability, sentiment = self.get_sentiment()
		if cash > last_price:
			print(sentiment)
			if sentiment == "positive" and probability > .999:
				print('positive')
				if self.last_trade == "sell":
					self.sell_all()
				order = self.create_order(
						self.symbol,
						quantity,
						"buy",
						type="bracket", 
						take_profit_price=last_price*1.20,
						stop_loss_price=last_price*.95
					)
				self.submit_order(order)
				self.last_trade = "buy"
			elif sentiment == "negative" and probability > .999:
				print('negative')
				if self.last_trade == "buy":
					self.sell_all()
				order = self.create_order(
						self.symbol,
						quantity,
						"sell",
						type="bracket", 
						take_profit_price=last_price*.8,
						stop_loss_price=last_price*1.05
					)
				self.submit_order(order)
				self.last_trade = "sell"	

# start_date = datetime(2020,1,1)
# end_date = datetime(2023,12,31)

broker = Alpaca(APLACA_CREDS)

strategy = MLTrader(name='mlstrat', broker=broker, parameters={"symbol":"PFE", "cash_at_risk":.5})

# strategy.backtest(
# 	YahooDataBacktesting, 
# 	start_date,
# 	end_date,
# 	parameters={"symbol":"SPY", "cash_at_risk":.5}
# )

trader = Trader()
trader.add_strategy(strategy)
try:
    trader.run_all()
except Exception as e:
    logging.exception("An error occurred while running the trading bot")

