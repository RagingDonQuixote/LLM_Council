import os
import sys
import unittest
import sqlite3
import json

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

from backend.storage import Storage
from backend.strategies.base import BordaCountStrategy, ChairmanCutStrategy
from backend.models_service import ModelsService

class TestLLMCouncilBackend(unittest.TestCase):
    def setUp(self):
        # Use a temporary test database
        self.test_db = "test_council.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.storage = Storage(self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_database_init(self):
        """Test if database and tables are created correctly."""
        self.assertTrue(os.path.exists(self.test_db))
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        self.assertIn('conversations', tables)
        self.assertIn('messages', tables)
        self.assertIn('settings', tables)
        self.assertIn('templates', tables)
        conn.close()

    def test_settings_persistence(self):
        """Test saving and loading configuration."""
        config = {
            "council_models": ["model1", "model2"],
            "chairman_model": "chairman1",
            "consensus_strategy": "chairman_cut",
            "response_timeout": 45,
            "model_personalities": {"model1": "Expert"}
        }
        self.storage.save_config(config)
        
        loaded_config = self.storage.load_config()
        self.assertEqual(loaded_config["chairman_model"], "chairman1")
        self.assertEqual(loaded_config["consensus_strategy"], "chairman_cut")
        self.assertEqual(loaded_config["response_timeout"], 45)
        self.assertEqual(loaded_config["council_models"], ["model1", "model2"])

    def test_templates(self):
        """Test template management."""
        templates = self.storage.list_templates()
        self.assertGreater(len(templates), 0) # Default templates should exist
        
        new_template = {
            "id": "test_t",
            "name": "Test Template",
            "description": "Test",
            "council_models": ["m1"],
            "chairman_model": "c1",
            "consensus_strategy": "borda_count"
        }
        self.storage.save_template(new_template)
        
        updated_templates = self.storage.list_templates()
        names = [t["name"] for t in updated_templates]
        self.assertIn("Test Template", names)

    def test_borda_count_strategy(self):
        """Test Borda Count calculation."""
        strategy = BordaCountStrategy()
        rankings = [
            {"parsed_ranking": ["A", "B", "C"]},
            {"parsed_ranking": ["A", "C", "B"]},
            {"parsed_ranking": ["B", "A", "C"]}
        ]
        model_labels = {"A": "A", "B": "B", "C": "C"}
        
        results = strategy.calculate(rankings, model_labels)
        self.assertEqual(results[0]["model_id"], "A")
        # A scores: (3-1-0) + (3-1-0) + (3-1-1) = 2 + 2 + 1 = 5
        # B scores: (3-1-1) + (3-1-2) + (3-1-0) = 1 + 0 + 2 = 3
        # C scores: (3-1-2) + (3-1-1) + (3-1-2) = 0 + 1 + 0 = 1
        self.assertEqual(results[0]["score"], 5)
        self.assertEqual(results[1]["model_id"], "B")
        self.assertEqual(results[2]["model_id"], "C")

    def test_chairman_cut_strategy(self):
        """Test Chairman Cut strategy logic."""
        strategy = ChairmanCutStrategy()
        rankings = [
            {"parsed_ranking": ["A", "B", "C", "D"]},
            {"parsed_ranking": ["B", "A", "C", "D"]},
        ]
        model_labels = {"A": "A", "B": "B", "C": "C", "D": "D"}
        
        results = strategy.calculate(rankings, model_labels)
        self.assertEqual(len(results), 4)

    def test_conversation_storage(self):
        """Test creating and retrieving conversations."""
        conv = self.storage.create_conversation()
        conv_id = conv["id"]
        
        self.storage.add_message(conv_id, "user", "Hello")
        self.storage.add_message(conv_id, "assistant", "Hi", stage1=[{"model": "m1", "response": "test"}])
        
        retrieved = self.storage.get_conversation(conv_id)
        self.assertEqual(len(retrieved["messages"]), 2)
        self.assertEqual(retrieved["messages"][1]["role"], "assistant")
        self.assertEqual(retrieved["messages"][1]["stage1"][0]["model"], "m1")

if __name__ == "__main__":
    unittest.main()
