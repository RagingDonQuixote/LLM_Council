"""Service for unified model management and database operations."""

import sqlite3
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from .provider_adapters import UnifiedModel, provider_registry
from .storage import storage


class UnifiedModelService:
    """Service for managing unified model data."""
    
    def __init__(self):
        self.storage = storage
    
    def save_unified_model(self, model: UnifiedModel) -> bool:
        """Save or update a unified model in the database."""
        conn = self.storage.get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        try:
            # Check if model exists using NULL-safe comparison to prevent duplicates
            # SQLite treats NULLs as distinct in UNIQUE constraints, so we handle it manually
            cursor.execute('''
                SELECT id, created_at FROM unified_models 
                WHERE developer_id = ? 
                AND access_provider_id = ? 
                AND base_model_id = ?
                AND (hosting_provider_id = ? OR (hosting_provider_id IS NULL AND ? IS NULL))
                AND (variant_name = ? OR (variant_name IS NULL AND ? IS NULL))
            ''', (
                model.developer_id,
                model.access_provider_id,
                model.base_model_id,
                model.hosting_provider_id, model.hosting_provider_id,
                model.variant_name, model.variant_name
            ))
            
            existing = cursor.fetchone()
            
            # Special case: If we didn't find an exact match, but we have a specific hosting provider (not OpenRouter),
            # check if a generic "OpenRouter" version exists. If so, we will upgrade it.
            if not existing and model.hosting_provider_id != "OpenRouter" and model.access_provider_id == "OpenRouter":
                cursor.execute('''
                    SELECT id, created_at FROM unified_models 
                    WHERE developer_id = ? 
                    AND access_provider_id = ? 
                    AND base_model_id = ?
                    AND hosting_provider_id = 'OpenRouter'
                    AND (variant_name = ? OR (variant_name IS NULL AND ? IS NULL))
                ''', (
                    model.developer_id,
                    model.access_provider_id,
                    model.base_model_id,
                    model.variant_name, model.variant_name
                ))
                existing = cursor.fetchone()
            
            if existing:
                # Update existing record while preserving ID and created_at
                # Also preserve latency_live if incoming is None
                model_id = existing[0]
                
                cursor.execute('''
                    UPDATE unified_models SET
                        access_provider_short = ?,
                        hosting_provider_id = ?,
                        hosting_provider_short = ?,
                        base_model_name = ?,
                        print_name_1 = ?,
                        print_name_part1 = ?,
                        print_name_part2 = ?,
                        capabilities = ?,
                        cost = ?,
                        technical = ?,
                        latency_ms = ?,
                        last_latency_check = ?,
                        latency_live = COALESCE(?, latency_live),
                        latency_live_timestamp = COALESCE(?, latency_live_timestamp),
                        provider_raw_data = ?,
                        updated_at = ?
                    WHERE id = ?
                ''', (
                    model.access_provider_short,
                    model.hosting_provider_id,
                    model.hosting_provider_short,
                    model.base_model_name,
                    model.print_name_1,
                    model.print_name_part1,
                    model.print_name_part2,
                    json.dumps(model.capabilities),
                    json.dumps(model.cost),
                    json.dumps(model.technical),
                    model.latency_ms,
                    model.last_latency_check,
                    model.latency_live,
                    model.latency_live_timestamp,
                    json.dumps(model.provider_raw_data) if model.provider_raw_data else None,
                    now,
                    model_id
                ))
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO unified_models (
                        developer_id, access_provider_id, access_provider_short,
                        hosting_provider_id, hosting_provider_short,
                        base_model_id, base_model_name, variant_name,
                        print_name_1, print_name_part1, print_name_part2,
                        capabilities, cost, technical,
                        latency_ms, last_latency_check, 
                        latency_live, latency_live_timestamp,
                        provider_raw_data,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    model.developer_id,
                    model.access_provider_id,
                    model.access_provider_short,
                    model.hosting_provider_id,
                    model.hosting_provider_short,
                    model.base_model_id,
                    model.base_model_name,
                    model.variant_name,
                    model.print_name_1,
                    model.print_name_part1,
                    model.print_name_part2,
                    json.dumps(model.capabilities),
                    json.dumps(model.cost),
                    json.dumps(model.technical),
                    model.latency_ms,
                    model.last_latency_check,
                    model.latency_live,
                    model.latency_live_timestamp,
                    json.dumps(model.provider_raw_data) if model.provider_raw_data else None,
                    now,
                    now
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving unified model: {e}")
            return False
        finally:
            conn.close()
    
    def get_all_unified_models(self) -> List[Dict[str, Any]]:
        """Get all unified models from database."""
        conn = self.storage.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM unified_models ORDER BY print_name_1
            ''')
            
            rows = cursor.fetchall()
            models = []
            
            for row in rows:
                model = dict(row)
                # Parse JSON fields
                model['capabilities'] = json.loads(model['capabilities'])
                model['cost'] = json.loads(model['cost'])
                model['technical'] = json.loads(model['technical'])
                if model['provider_raw_data']:
                    model['provider_raw_data'] = json.loads(model['provider_raw_data'])
                models.append(model)
            
            return models
            
        except Exception as e:
            print(f"Error fetching unified models: {e}")
            return []
        finally:
            conn.close()
    
    def get_base_models(self) -> List[Dict[str, Any]]:
        """Get unique base models grouped by base_model_id."""
        conn = self.storage.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # We want unique base_model_ids with their best names
            cursor.execute('''
                SELECT 
                    base_model_id, 
                    base_model_name, 
                    developer_id, 
                    print_name_part1,
                    COUNT(*) as variants_count,
                    MAX(CASE WHEN json_extract(cost, '$.is_free') = 1 THEN 1 ELSE 0 END) as is_free_available
                FROM unified_models 
                GROUP BY base_model_id
                ORDER BY developer_id ASC, base_model_name ASC
            ''')
            
            rows = cursor.fetchall()
            base_models = []
            for row in rows:
                base_models.append(dict(row))
            
            return base_models
            
        except Exception as e:
            print(f"Error fetching base models: {e}")
            return []
        finally:
            conn.close()
    
    def get_variants_for_base_model(self, base_model_id: str) -> List[Dict[str, Any]]:
        """Get all variants for a specific base model."""
        conn = self.storage.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM unified_models 
                WHERE base_model_id = ? 
                ORDER BY latency_ms ASC
            ''', (base_model_id,))
            
            rows = cursor.fetchall()
            variants = []
            
            for row in rows:
                variant = dict(row)
                # Parse JSON fields
                variant['capabilities'] = json.loads(variant['capabilities'])
                variant['cost'] = json.loads(variant['cost'])
                variant['technical'] = json.loads(variant['technical'])
                if variant['provider_raw_data']:
                    variant['provider_raw_data'] = json.loads(variant['provider_raw_data'])
                variants.append(variant)
            
            return variants
            
        except Exception as e:
            print(f"Error fetching variants for base model {base_model_id}: {e}")
            return []
        finally:
            conn.close()
    
    def search_models(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search models by query string."""
        if not query.strip():
            return self.get_all_unified_models()[:limit]
        
        all_models = self.get_all_unified_models()
        query_lower = query.lower()
        
        # Score-based search
        scored_models = []
        for model in all_models:
            score = self._calculate_search_score(query_lower, model)
            if score > 0:
                scored_models.append((score, model))
        
        # Sort by score and limit results
        scored_models.sort(key=lambda x: x[0], reverse=True)
        return [model for _, model in scored_models[:limit]]
    
    def _calculate_search_score(self, query: str, model: Dict[str, Any]) -> float:
        """Calculate search score for a model."""
        score = 0.0
        
        # Search in different fields with different weights
        fields_to_search = [
            (model.get('print_name_1') or '', 10.0),
            (model.get('print_name_part1') or '', 8.0),
            (model.get('base_model_name') or '', 6.0),
            (model.get('developer_id') or '', 4.0),
            (model.get('variant_name') or '', 3.0),
        ]
        
        for field_content, weight in fields_to_search:
            content_lower = field_content.lower()
            
            # Exact match
            if query == content_lower:
                score += weight * 2
            # Starts with query
            elif content_lower.startswith(query):
                score += weight * 1.5
            # Contains query
            elif query in content_lower:
                score += weight
        
        # Search in capabilities
        capabilities = model.get('capabilities', {})
        for capability, has_cap in capabilities.items():
            if has_cap and query in capability.lower():
                score += 2.0
        
        # Boost free models in search
        if model.get('cost', {}).get('is_free', False):
            score += 1.0
        
        return score
    
    def deduplicate_models(self, models: List[UnifiedModel]) -> List[UnifiedModel]:
        """Remove duplicate models based on base model and provider."""
        seen = set()
        deduplicated = []
        
        for model in models:
            # Create a unique key for deduplication
            key = (
                model.developer_id,
                model.access_provider_id,
                model.hosting_provider_id,
                model.base_model_id,
                model.variant_name
            )
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(model)
        
        return deduplicated
    
    async def refresh_all_models(self) -> int:
        """Refresh all models from all providers."""
        print("Starting model refresh from all providers...")
        
        try:
            # Fetch from all providers
            raw_models = await provider_registry.fetch_all_models()
            print(f"Fetched {len(raw_models)} raw models from providers")
            
            # Deduplicate
            deduplicated_models = self.deduplicate_models(raw_models)
            print(f"Deduplicated to {len(deduplicated_models)} unique models")
            
            # Save to database
            saved_count = 0
            for model in deduplicated_models:
                if self.save_unified_model(model):
                    saved_count += 1
            
            print(f"Successfully saved {saved_count} models to database")
            
            # Update latencies
            await self.update_latencies()
            
            return saved_count
            
        except Exception as e:
            print(f"Error refreshing models: {e}")
            return 0
    
    async def update_latencies(self) -> None:
        """
        Update latency data for all models using provider metadata.
        
        Note: This only updates 'static' latency reported by the provider API.
        It does NOT perform live latency checks (which would cost money).
        """
        print("Updating latency data (metadata only)...")
        
        all_models = self.get_all_unified_models()
        if not all_models:
            print("No models found to update latencies for")
            return
        
        try:
            # Convert to UnifiedModel objects for the registry
            unified_objects = []
            for model_data in all_models:
                if model_data.get('provider_raw_data'):
                    unified_obj = UnifiedModel(
                        developer_id=model_data['developer_id'],
                        access_provider_id=model_data['access_provider_id'],
                        access_provider_short=model_data['access_provider_short'],
                        hosting_provider_id=model_data['hosting_provider_id'],
                        hosting_provider_short=model_data['hosting_provider_short'],
                        base_model_id=model_data['base_model_id'],
                        base_model_name=model_data['base_model_name'],
                        variant_name=model_data['variant_name'],
                        print_name_1=model_data['print_name_1'],
                        print_name_part1=model_data['print_name_part1'],
                        print_name_part2=model_data['print_name_part2'],
                        capabilities=model_data['capabilities'],
                        cost=model_data['cost'],
                        technical=model_data['technical'],
                        latency_ms=model_data.get('latency_ms'),
                        last_latency_check=model_data.get('last_latency_check'),
                        latency_live=model_data.get('latency_live'),
                        latency_live_timestamp=model_data.get('latency_live_timestamp'),
                        provider_raw_data=model_data['provider_raw_data']
                    )
                    unified_objects.append(unified_obj)
            
            # Update latencies through registry
            await provider_registry.update_latencies(unified_objects)
            
            # Update latencies back to database
            updated_count = 0
            for unified_obj in unified_objects:
                # Find matching model in all_models by its unique key
                original_model = next((m for m in all_models if 
                    m['developer_id'] == unified_obj.developer_id and
                    m['access_provider_id'] == unified_obj.access_provider_id and
                    m['hosting_provider_id'] == unified_obj.hosting_provider_id and
                    m['base_model_id'] == unified_obj.base_model_id and
                    m['variant_name'] == unified_obj.variant_name
                ), None)
                
                if original_model and unified_obj.latency_ms != original_model.get('latency_ms'):
                    if self.save_unified_model(unified_obj):
                        updated_count += 1
            
            print(f"Updated latency data for {updated_count} models")
            
        except Exception as e:
            print(f"Error updating latencies: {e}")
    
    def get_model_statistics(self) -> Dict[str, Any]:
        """Get statistics about the unified model database."""
        all_models = self.get_all_unified_models()
        base_models = self.get_base_models()
        
        if not all_models:
            return {
                "total_models": 0,
                "total_base_models": 0,
                "providers": [],
                "free_models": 0,
                "capabilities": {},
                "average_latency": None
            }
        
        # Count by provider
        provider_counts = {}
        for model in all_models:
            provider = model['access_provider_id']
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        
        # Count free models
        free_count = sum(1 for model in all_models if model['cost'].get('is_free', False))
        
        # Capabilities summary
        capabilities_summary = {}
        all_capabilities = set()
        for model in all_models:
            all_capabilities.update(model['capabilities'].keys())
        
        for capability in all_capabilities:
            count = sum(1 for model in all_models if model['capabilities'].get(capability, False))
            capabilities_summary[capability] = count
        
        # Average latency
        latencies = [model['latency_ms'] for model in all_models if model.get('latency_ms')]
        avg_latency = sum(latencies) / len(latencies) if latencies else None
        
        return {
            "total_models": len(all_models),
            "total_base_models": len(base_models),
            "providers": list(provider_counts.keys()),
            "provider_counts": provider_counts,
            "free_models": free_count,
            "capabilities": capabilities_summary,
            "average_latency": avg_latency,
            "last_updated": datetime.utcnow().isoformat()
        }


# Global service instance
unified_model_service = UnifiedModelService()
