import os
import sys
import unittest
import json

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

from backend.strategies.base import BordaCountStrategy, ChairmanCutStrategy

class TestConsensusStrategies(unittest.TestCase):
    def test_borda_count_basic(self):
        """Standard Borda Count Test."""
        strategy = BordaCountStrategy()
        rankings = [
            {"parsed_ranking": ["Response A", "Response B", "Response C"]},
            {"parsed_ranking": ["Response A", "Response C", "Response B"]},
        ]
        model_labels = {"Response A": "model_a", "Response B": "model_b", "Response C": "model_c"}
        
        results = strategy.calculate(rankings, model_labels)
        
        # model_a: 2 + 2 = 4
        # model_b: 1 + 0 = 1
        # model_c: 0 + 1 = 1
        self.assertEqual(results[0]["model_id"], "model_a")
        self.assertEqual(results[0]["score"], 4)
        self.assertEqual(results[1]["model_id"], "model_b") # B and C tied, B came first in dict order
        
    def test_borda_count_tie_handling(self):
        """Test how ties are handled in Borda Count."""
        strategy = BordaCountStrategy()
        rankings = [
            {"parsed_ranking": ["Response A", "Response B"]},
            {"parsed_ranking": ["Response B", "Response A"]},
        ]
        model_labels = {"Response A": "model_a", "Response B": "model_b"}
        
        results = strategy.calculate(rankings, model_labels)
        # Both should have score 1
        self.assertEqual(results[0]["score"], 1)
        self.assertEqual(results[1]["score"], 1)

    def test_borda_count_incomplete_votes(self):
        """Test ranking where a model misses some responses."""
        strategy = BordaCountStrategy()
        rankings = [
            {"parsed_ranking": ["Response A"]}, # Missing B and C
            {"parsed_ranking": ["Response B", "Response C", "Response A"]},
        ]
        model_labels = {"Response A": "model_a", "Response B": "model_b", "Response C": "model_c"}
        
        results = strategy.calculate(rankings, model_labels)
        # model_a: (3-1-0) + (3-1-2) = 2 + 0 = 2
        # model_b: 0 + 2 = 2
        # model_c: 0 + 1 = 1
        
        scores = {r["model_id"]: r["score"] for r in results}
        self.assertEqual(scores["model_a"], 2)
        self.assertEqual(scores["model_b"], 2)
        self.assertEqual(scores["model_c"], 1)

    def test_chairman_cut_basic(self):
        """Chairman Cut should return results with the correct strategy flag."""
        strategy = ChairmanCutStrategy()
        rankings = [
            {"parsed_ranking": ["Response A", "Response B"]},
        ]
        model_labels = {"Response A": "model_a", "Response B": "model_b"}
        
        results = strategy.calculate(rankings, model_labels)
        self.assertEqual(results[0]["strategy_applied"], "chairman_cut")
        self.assertEqual(results[0]["model_id"], "model_a")

    def test_empty_rankings(self):
        """Test behavior with no rankings submitted."""
        strategy = BordaCountStrategy()
        rankings = []
        model_labels = {"Response A": "model_a", "Response B": "model_b"}
        
        results = strategy.calculate(rankings, model_labels)
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertEqual(r["score"], 0)
            self.assertEqual(r["votes"], 0)

if __name__ == "__main__":
    unittest.main()
