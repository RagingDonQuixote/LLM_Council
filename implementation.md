# UnifiedModelTable Implementation Plan

## Overview
Implementation of a multi-provider LLM model abstraction layer with search-enabled selection and real-time latency tracking.

## Effort Estimate: 2-3 Weeks Development Time

### Phase Breakdown:
- **Phase 1 (Backend)**: 1-1.5 weeks
- **Phase 2 (Frontend)**: 0.5-1 week  
- **Phase 3 (Integration)**: 0.5 week

---

## Phase 1: Backend Infrastructure (1-1.5 weeks)

### 1.1 Database Schema (3-4 days)

**UnifiedModelTable Structure:**
```sql
CREATE TABLE unified_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    developer_id TEXT NOT NULL,
    access_provider_id TEXT NOT NULL,
    access_provider_short TEXT NOT NULL,
    hosting_provider_id TEXT,
    hosting_provider_short TEXT,
    base_model_id TEXT NOT NULL,
    base_model_name TEXT NOT NULL,
    variant_name TEXT,
    print_name_1 TEXT NOT NULL,
    print_name_part1 TEXT NOT NULL,
    print_name_part2 TEXT NOT NULL,
    capabilities JSON NOT NULL,
    cost JSON NOT NULL,
    technical JSON NOT NULL,
    latency_ms REAL,
    last_latency_check TIMESTAMP,
    provider_raw_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(developer_id, access_provider_id, hosting_provider_id, base_model_id, variant_name)
);

CREATE INDEX idx_unified_models_search ON unified_models(print_name_1, base_model_name);
CREATE INDEX idx_unified_models_capabilities ON unified_models(capabilities);
```

### 1.2 Provider Adapter System (4-5 days)

**Base Adapter Interface:**
```python
class BaseProviderAdapter:
    async def fetch_models(self) -> List[Dict]:
        """Fetch raw model data from provider"""
        pass
    
    async def fetch_latencies(self, model_ids: List[str]) -> Dict[str, float]:
        """Fetch latency data for models"""
        pass
    
    def normalize_model(self, raw_model: Dict) -> UnifiedModel:
        """Transform provider data to unified format"""
        pass

class OpenRouterAdapter(BaseProviderAdapter):
    async def fetch_latencies(self, model_ids: List[str]) -> Dict[str, float]:
        # Use OpenRouter's free latency API
        # Transform to unified format
        pass
```

**Provider Registry:**
```python
class ProviderRegistry:
    def __init__(self):
        self.adapters = {
            'openrouter': OpenRouterAdapter(),
            'openai': OpenAIAdapter(),  # Future
            'anthropic': AnthropicAdapter(),  # Future
        }
    
    async def refresh_all_providers(self):
        """Update all provider data"""
        pass
```

### 1.3 Data Normalization & Deduplication (2-3 days)

**Model Matching Logic:**
```python
class ModelMatcher:
    def find_base_model(self, provider_models: List[Dict]) -> str:
        """Group variants of same base model across providers"""
        # Use model name similarity, parameter counts, capabilities
        pass
    
    def generate_hierarchical_id(self, model_data: Dict) -> str:
        """Generate D.A.H.BN002 format IDs"""
        pass
```

---

## Status Update (2026-03-01) - Implementation Reality

The actual implementation has evolved to focus on a **Dual-Fetch Strategy** specifically for OpenRouter to handle the complexity of their provider ecosystem.

### Key Components Implemented:
1.  **Raw Data Storage**:
    *   `fetch_raw_openrouter.py`: Fetches from `/models` and `/endpoints` APIs.
    *   Tables: `raw_openrouter_models` and `raw_openrouter_endpoints`.

2.  **Merge Logic ("Endpoint-First")**:
    *   `merger.py`: Implements the `merge_endpoint_strategy` where specific endpoint data overrides base model defaults.
    *   `process_raw_to_umt.py`: Batch processor that populates `unified_models`.

3.  **Schema Evolution**:
    *   `unified_models` now includes `raw_base_model_data` and `raw_endpoint_data` columns for full traceability.
    *   Primary Key is now a composite string: `{base_id}:{provider_name}`.

4.  **Frontend Visualization**:
    *   **DB Browser** includes an "Origin Trace View" to visually audit the merge logic.
    *   Filtering and Pagination added to table views.
