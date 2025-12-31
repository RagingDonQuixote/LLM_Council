import os
import sys
import unittest
import asyncio
from unittest.mock import patch, MagicMock

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

from backend.council import run_full_council
from backend.storage import Storage

class TestE2EFlow(unittest.TestCase):
    def setUp(self):
        # Use a temporary test database
        self.test_db = "test_e2e.db"
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except:
                pass
        self.storage = Storage(self.test_db)
        
        # Mock storage for the council.py imports
        self.storage_patcher = patch('backend.council.config.get_config')
        self.mock_get_config = self.storage_patcher.start()
        self.mock_get_config.return_value = {
            "council_models": ["model1", "model2"],
            "chairman_model": "chairman1",
            "model_personalities": {"model1": "P1", "model2": "P2"},
            "response_timeout": 1
        }

    def tearDown(self):
        self.storage_patcher.stop()
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except:
                pass

    @patch('backend.council.query_model')
    def test_full_council_cycle_chairman_cut(self, mock_query):
        """Simulate a full council cycle with Chairman Cut strategy."""
        self.mock_get_config.return_value["consensus_strategy"] = "chairman"
        
        def mock_query_side_effect(model, messages, timeout=None):
            system_prompt = messages[0]['content']
            if "Strategic Planner" in system_prompt:
                return {"content": '{"strategy": "DIRECT_EXECUTION", "reasoning": "Test", "current_goal": "Goal", "requires_consensus": false}'}
            if "personality" in system_prompt:
                return {"content": f"Response from {model}"}
            if "critical judge" in system_prompt:
                return {"content": "Ranking: Response A > Response B"}
            if "Chairman of the LLM Council" in system_prompt:
                return {"content": '{"action": "FINAL_ANSWER", "content": "Final", "reasoning": "Reason"}'}
            return {"content": "Unknown"}

        mock_query.side_effect = mock_query_side_effect
        loop = asyncio.get_event_loop()
        s1, s2, s3, meta = loop.run_until_complete(run_full_council("Test Query"))

        self.assertIn("aggregate_rankings", meta)
        self.assertEqual(meta["aggregate_rankings"][0]["strategy_applied"], "chairman_cut")

    @patch('backend.council.query_model')
    def test_full_council_cycle_borda(self, mock_query):
        """Simulate a full council cycle with Borda strategy."""
        self.mock_get_config.return_value["consensus_strategy"] = "borda"
        
        def mock_query_side_effect(model, messages, timeout=None):
            system_prompt = messages[0]['content']
            if "Strategic Planner" in system_prompt:
                return {"content": '{"strategy": "DIRECT_EXECUTION", "reasoning": "Test", "current_goal": "Goal", "requires_consensus": false}'}
            if "personality" in system_prompt:
                return {"content": f"Response from {model}"}
            if "critical judge" in system_prompt:
                return {"content": "Ranking: Response B > Response A"}
            if "Chairman of the LLM Council" in system_prompt:
                return {"content": '{"action": "FINAL_ANSWER", "content": "Final", "reasoning": "Reason"}'}
            return {"content": "Unknown"}

        mock_query.side_effect = mock_query_side_effect
        loop = asyncio.get_event_loop()
        s1, s2, s3, meta = loop.run_until_complete(run_full_council("Test Query"))

        self.assertIn("aggregate_rankings", meta)
        # Borda results shouldn't have the flag
        self.assertNotIn("strategy_applied", meta["aggregate_rankings"][0])
        # In this mock, Response B (model2) should be #1
        self.assertEqual(meta["aggregate_rankings"][0]["model_id"], "model2")

if __name__ == "__main__":
    unittest.main()
