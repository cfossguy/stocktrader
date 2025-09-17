import unittest
from venv import logger
import llm
import market_analytics 
import logging
import sys
import time

class QuickTestClient(unittest.TestCase):
    
    # def test_generate_top_tickers(self):
    #     formatted_date = datetime.now().strftime("%m-%d-%Y")
    #     result = llm.generate_top_tickers(top_n=2, timestamp=formatted_date)
    #     print(result)
    #     with open('./result.json', 'w') as f:
    #         f.write(str(result))

    def test_generate_news_summary(self):
        start = time.time()
        news = market_analytics.get_news(ticker='T')
        result = llm.generate_news_summary_and_rank(ticker='T', news=news)
        duration = time.time() - start
        print(f"News Test Result: {result}\nDuration: {duration:.3f} seconds")

    def test_generate_financials(self):
        start = time.time()
        financials = market_analytics.get_financials(ticker='T')
        result = llm.generate_fundamentals_summary_and_rank(ticker='T', financials=financials)
        duration = time.time() - start
        print(f"Financials Test Result: {result}\nDuration: {duration:.3f} seconds")

if __name__ == '__main__':
    unittest.main()