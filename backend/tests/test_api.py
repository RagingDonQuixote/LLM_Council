import os
import sys
import json
import unittest
from fastapi.testclient import TestClient

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

# Set test DB path before importing app
os.environ["DB_PATH"] = "test_api_council.db"

from backend.main import app
from backend.storage import storage

class TestLLMCouncilAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Clear test DB if it exists
        if os.path.exists("test_api_council.db"):
            os.remove("test_api_council.db")
        storage.db_path = "test_api_council.db"
        storage.init_db()

    def tearDown(self):
        # We might not be able to delete on Windows if it's open, but that's okay for tests
        pass

    def test_root_health_check(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_version_endpoint(self):
        response = self.client.get("/api/version")
        self.assertEqual(response.status_code, 200)
        self.assertIn("version", response.json())

    def test_conversation_crud(self):
        # Create
        create_resp = self.client.post("/api/conversations", json={})
        self.assertEqual(create_resp.status_code, 200)
        conv_id = create_resp.json()["id"]
        
        # List
        list_resp = self.client.get("/api/conversations")
        self.assertEqual(list_resp.status_code, 200)
        self.assertTrue(any(c["id"] == conv_id for c in list_resp.json()))
        
        # Get
        get_resp = self.client.get(f"/api/conversations/{conv_id}")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["id"], conv_id)
        
        # Delete
        del_resp = self.client.delete(f"/api/conversations/{conv_id}")
        self.assertEqual(del_resp.status_code, 200)
        
        # Verify deleted
        get_resp_after = self.client.get(f"/api/conversations/{conv_id}")
        self.assertEqual(get_resp_after.status_code, 404)

    def test_config_endpoints(self):
        # Get config
        resp = self.client.get("/api/config")
        self.assertEqual(resp.status_code, 200)
        
        # Update config
        new_config = {
            "council_models": ["model-a", "model-b"],
            "chairman_model": "chairman-1",
            "model_personalities": {"model-a": "Funny"}
        }
        update_resp = self.client.put("/api/config", json=new_config)
        self.assertEqual(update_resp.status_code, 200)
        
        # Verify update
        get_resp = self.client.get("/api/config")
        self.assertEqual(get_resp.json()["chairman_model"], "chairman-1")

    def test_templates_endpoints(self):
        # List
        resp = self.client.get("/api/templates")
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.json()), 0)
        
        # Save new
        template = {
            "id": "new-t",
            "name": "New API Template",
            "models": ["m1"],
            "strategy": "borda"
        }
        save_resp = self.client.post("/api/templates", json=template)
        self.assertEqual(save_resp.status_code, 200)

if __name__ == "__main__":
    unittest.main()
