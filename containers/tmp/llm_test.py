import unittest
import llm
from datetime import datetime

class TestLLMClient(unittest.TestCase):
    
    def test_generate_top_tickers(self):
        formatted_date = datetime.now().strftime("%m-%d-%Y")
        result = llm.generate_top_tickers(top_n=2, timestamp=formatted_date)
        print(result)
        with open('./result.json', 'w') as f:
            f.write(str(result))
            
if __name__ == '__main__':
    unittest.main()