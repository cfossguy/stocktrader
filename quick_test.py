import unittest
import llm
import market_analytics 

class QuickTestClient(unittest.TestCase):
    
    # def test_generate_top_tickers(self):
    #     formatted_date = datetime.now().strftime("%m-%d-%Y")
    #     result = llm.generate_top_tickers(top_n=2, timestamp=formatted_date)
    #     print(result)
    #     with open('./result.json', 'w') as f:
    #         f.write(str(result))

    def test_generate_news_summary(self):
        # Mock news data for testing
        # mock_news = "Company T announced a 10% increase in quarterly revenue. Analysts are optimistic about future growth."
        news = market_analytics.get_news(ticker='TQQQ')
        # Call the function with mock data
        result = llm.generate_news_summary_and_rank(ticker='TQQQ', news=news)

        # Log the result for debugging
        print("News Test Result:", result)
        
        # Assert that the result contains expected keys
        self.assertIn("summary", result)
        self.assertIn("rank", result)

    def test_generate_financials(self):
        financials = market_analytics.get_financials(ticker='TQQQ')
        result = llm.generate_fundamentals_summary_and_rank(ticker='TQQQ', financials=financials)
        # Log the result for debugging
        print("Financials Test Result:", result)

        # Assert that the result contains expected keys
        self.assertIn("summary", result)
        self.assertIn("rank", result)

if __name__ == '__main__':
    unittest.main()