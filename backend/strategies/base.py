from typing import List, Dict, Any, Protocol

class ConsensusStrategy(Protocol):
    name: str
    description: str
    
    def calculate(self, rankings: List[Dict[str, Any]], model_labels: Dict[str, str]) -> List[Dict[str, Any]]:
        """Calculate the consensus ranking."""
        ...

class BordaCountStrategy:
    name = "Borda-Count"
    description = "Punktesystem für Rankings (n-1 Punkte für Platz 1, n-2 für Platz 2, etc.)"
    
    def calculate(self, rankings: List[Dict[str, Any]], model_labels: Dict[str, str]) -> List[Dict[str, Any]]:
        # Implementation of Borda Count
        scores = {model_id: 0 for model_id in model_labels.values()}
        n_models = len(model_labels)
        vote_counts = {model_id: 0 for model_id in model_labels.values()}
        
        for rank_entry in rankings:
            parsed = rank_entry.get("parsed_ranking", [])
            for i, label in enumerate(parsed):
                if label in model_labels:
                    model_id = model_labels[label]
                    # Borda score: n-1 for first, n-2 for second... 0 for last
                    scores[model_id] += (n_models - 1 - i)
                    vote_counts[model_id] += 1
        
        # Calculate average position as well (for backward compatibility)
        positions = {model_id: [] for model_id in model_labels.values()}
        for rank_entry in rankings:
            parsed = rank_entry.get("parsed_ranking", [])
            for i, label in enumerate(parsed):
                if label in model_labels:
                    model_id = model_labels[label]
                    positions[model_id].append(i + 1)
        
        results = []
        for model_id, score in scores.items():
            avg_pos = sum(positions[model_id]) / len(positions[model_id]) if positions[model_id] else 0
            results.append({
                "model_id": model_id,
                "score": score,
                "average_position": avg_pos,
                "votes": vote_counts[model_id]
            })
            
        return sorted(results, key=lambda x: x["score"], reverse=True)

class ChairmanCutStrategy:
    name = "Chairman Cut"
    description = "Berücksichtigt nur die Top-Ergebnisse der Ratsmitglieder für die finale Entscheidung des Chairmans."
    
    def calculate(self, rankings: List[Dict[str, Any]], model_labels: Dict[str, str]) -> List[Dict[str, Any]]:
        # In Chairman Cut, we still show Borda-like scores for UI transparency,
        # but we might flag that it's a 'Chairman Choice' in the future.
        # For now, let's implement a robust ranking based on Borda but with a 'Chairman' bias if we had the chairman's vote here.
        # Since we only have peer votes in stage 2, we use Borda as a baseline.
        
        borda = BordaCountStrategy()
        results = borda.calculate(rankings, model_labels)
        
        # Add a flag to indicate this was processed via Chairman Cut logic
        for res in results:
            res["strategy_applied"] = "chairman_cut"
            
        return results
