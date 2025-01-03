import unittest
import market_analytics 


class Tests(unittest.TestCase):

    def test_custom_metric(self):
        print("nice")

    def test_get_market_cap(self):
        ticker = 'AAPL'
        result = market_analytics.get_market_cap(ticker)
        print(f'market cap for {ticker} is: {result}')

    def test_get_beta(self):
        ticker = 'AAPL'
        result = market_analytics.get_beta(ticker)
        print(f'beta for {ticker} is: {result}')

    def test_get_dividend_yield(self):
        ticker = 'AAPL'
        result = market_analytics.get_dividend_yield(ticker)
        print(f'dividend for {ticker} is: {result}')
       
    # def test_get_triple_screen_median(self):
    #     ticker = 'AAPL'
    #     indicator = 'rsi'
    #     result_hour = market_analytics.get_triple_screen_median(ticker, timespan="hour", indicator=indicator)
    #     result_day = market_analytics.get_triple_screen_median(ticker, timespan="day", indicator=indicator)
    #     result_week = market_analytics.get_triple_screen_median(ticker, timespan="week", indicator=indicator)

    #     print(f'{indicator}: hour is {result_hour} for ticker {ticker}')
    #     print(f'{indicator}: day is {result_day} for ticker {ticker}')
    #     print(f'{indicator}: week is {result_week} for ticker {ticker}')

    #     indicator = 'macd'
    #     result_hour = market_analytics.get_triple_screen_median(ticker, timespan="hour", indicator=indicator)
    #     result_day = market_analytics.get_triple_screen_median(ticker, timespan="day", indicator=indicator)
    #     result_week = market_analytics.get_triple_screen_median(ticker, timespan="week", indicator=indicator)

    #     print(f'{indicator}: hour is {result_hour} for ticker {ticker}')
    #     print(f'{indicator}: day is {result_day} for ticker {ticker}')
    #     print(f'{indicator}: week is {result_week} for ticker {ticker}')

    #     indicator = 'sma'
    #     result_hour = market_analytics.get_triple_screen_median(ticker, timespan="hour", indicator=indicator)
    #     result_day = market_analytics.get_triple_screen_median(ticker, timespan="day", indicator=indicator)
    #     result_week = market_analytics.get_triple_screen_median(ticker, timespan="week", indicator=indicator)

    #     print(f'{indicator}: hour is {result_hour} for ticker {ticker}')
    #     print(f'{indicator}: day is {result_day} for ticker {ticker}')
    #     print(f'{indicator}: week is {result_week} for ticker {ticker}')

if __name__ == '__main__':
    unittest.main()