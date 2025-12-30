"""Test script to check current model pricing behavior."""

import asyncio
import os
from backend.openrouter import get_available_models

async def main():
    print("Fetching available models from OpenRouter...")
    models = await get_available_models()
    
    print(f"\nFound {len(models)} models:")
    print("=" * 80)
    
    # Group by free/paid
    free_models = []
    paid_models = []
    
    for model in models:
        if model['free']:
            free_models.append(model)
        else:
            paid_models.append(model)
    
    print(f"FREE MODELS ({len(free_models)}):")
    print("-" * 80)
    for model in sorted(free_models, key=lambda x: x['id'])[:10]:  # Show first 10
        print(f"  {model['name']}")
    
    print(f"\nPAID MODELS - Sample ({min(20, len(paid_models))}):")
    print("-" * 80)
    for model in sorted(paid_models, key=lambda x: x['pricing']['prompt'])[:20]:
        print(f"  {model['name']}")
    
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS:")
    print("-" * 80)
    
    # Check for models with very low prices that might be problematic
    print("Models with extremely low prices:")
    for model in models:
        pricing = model['pricing']
        if 0 < pricing['prompt'] < 0.000001 or 0 < pricing['completion'] < 0.000001:
            status = "FREE" if model['free'] else "PAID"
            print(f"  {model['id']:<50} | Status: {status:<6} | Prompt: ${pricing['prompt']:<12.9f} | Display: {model['name']}")
    
    # Check for negative prices (which would be wrong)
    print("\nModels with negative prices (should not exist):")
    negative_found = False
    for model in models:
        pricing = model['pricing']
        if pricing['prompt'] < 0 or pricing['completion'] < 0:
            negative_found = True
            print(f"  {model['id']:<50} | Prompt: ${pricing['prompt']:<12.9f} | Completion: ${pricing['completion']:<12.9f}")
    
    if not negative_found:
        print("  No negative prices found - GOOD!")
    
    # Summary of pricing ranges
    print("\nPRICING SUMMARY:")
    print("-" * 80)
    
    # Count models by price ranges
    price_ranges = {
        "Free": 0,
        "Very cheap (<$0.0001/mT)": 0,
        "Cheap ($0.0001-$0.001/mT)": 0,
        "Medium ($0.001-$0.01/mT)": 0,
        "Expensive (>$0.01/mT)": 0
    }
    
    for model in models:
        if model['free']:
            price_ranges["Free"] += 1
        else:
            prompt_price = model['pricing']['prompt']
            cost_per_million = prompt_price * 1000000
            
            if cost_per_million < 0.0001:
                price_ranges["Very cheap (<$0.0001/mT)"] += 1
            elif cost_per_million < 0.001:
                price_ranges["Cheap ($0.0001-$0.001/mT)"] += 1
            elif cost_per_million < 0.01:
                price_ranges["Medium ($0.001-$0.01/mT)"] += 1
            else:
                price_ranges["Expensive (>$0.01/mT)"] += 1
    
    for range_name, count in price_ranges.items():
        print(f"  {range_name:<30}: {count:3d} models")

if __name__ == "__main__":
    asyncio.run(main())