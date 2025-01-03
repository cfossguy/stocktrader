import unittest
import llm
import market_analytics 

class TestLLMClient(unittest.TestCase):
    
    # def test_generate_top_tickers(self):
    #     formatted_date = datetime.now().strftime("%m-%d-%Y")
    #     result = llm.generate_top_tickers(top_n=2, timestamp=formatted_date)
    #     print(result)
    #     with open('./result.json', 'w') as f:
    #         f.write(str(result))

    def test_generate_news_summary(self):
        news = market_analytics.get_news(ticker='AAPL')
        result = llm.generate_news_summary(ticker='AAPL', news=news)
        print(result)
            
if __name__ == '__main__':
    unittest.main()