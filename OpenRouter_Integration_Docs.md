# OpenRouter Integration & Unified Model Table (UMT) Documentation

## Overview
This document describes how the LLM Council application integrates with the OpenRouter API to fetch, store, and merge model data into a **Unified Model Table (UMT)**. The goal is to create a reliable "Source of Truth" for model capabilities, pricing, and technical specifications, addressing discrepancies between OpenRouter's general model metadata and specific provider endpoint data.

## 1. Data Acquisition Strategy
We use a **Dual-Fetch Strategy** to gather comprehensive data, as OpenRouter distributes information across two endpoints.

### Source 1: Base Models API (`/models`)
- **Endpoint:** `https://openrouter.ai/api/v1/models`
- **Purpose:** Provides high-level metadata for "Base Models" (e.g., `openai/gpt-4o`, `anthropic/claude-3-opus`).
- **Key Data:** Description, architecture (modality), general context length.
- **Storage:** Saved raw into SQLite table `raw_openrouter_models`.

### Source 2: Endpoints API (`/models/{model_id}/endpoints`)
- **Endpoint:** `https://openrouter.ai/api/v1/models/{model_id}/endpoints`
- **Purpose:** Provides specific details for each **Hosting Provider** offering a model. A single base model (e.g., `gpt-oss-120b`) can have dozens of endpoints (e.g., DeepInfra, Chutes, Novita).
- **Key Data:** **Real** pricing (per provider), **Real** context length (provider limit), Quantization, specific capabilities (Tools, JSON mode).
- **Storage:** Saved raw into SQLite table `raw_openrouter_endpoints`.

### Automated Script
- **Script:** `backend/fetch_raw_openrouter.py`
- **Function:** Fetches data from both APIs and updates the raw tables. It also manages `_raw.json` and `_raw_old.json` file dumps for version comparison.

## 2. Database Schema

### Raw Tables
These tables serve as a permanent record of the API responses, allowing for debugging and re-processing without new API calls.

**`raw_openrouter_models`**
- `id` (TEXT): Base model ID (e.g., `openai/gpt-oss-120b`)
- `name` (TEXT): Human-readable name
- `raw_json` (TEXT): Full JSON response from `/models`

**`raw_openrouter_endpoints`**
- `model_id` (TEXT): Foreign key to base model
- `endpoints_count` (INTEGER): Number of providers found
- `raw_json` (TEXT): Full JSON response from `/endpoints` containing the list of providers.

### Unified Models Table (`unified_models`)
This is the application's main working table. It contains the merged and normalized data.

**Key Columns:**
- `id` (PK): Composite ID: `{base_model_id}:{normalized_provider_name}` (e.g., `openai/gpt-oss-120b:DeepInfra`)
- `base_model_id`: The OpenRouter ID.
- `hosting_provider_id`: The specific provider (e.g., `DeepInfra`).
- `capabilities`: JSON-encoded flags (Vision, Tools, Reasoning).
- `cost`: JSON-encoded pricing (USD/million tokens).
- `technical`: JSON-encoded context window, quantization, max output.
- `raw_base_model_data`: **Copy of the raw base JSON used for this record.**
- `raw_endpoint_data`: **Copy of the raw endpoint JSON used for this record.**

## 3. Merge Logic ("Endpoint-First")
The core logic resides in `backend/merger.py`. It enforces the rule that **Provider Endpoint Data overrides Base Model Data**.

**Logic Flow:**
1.  **Identification:** A unique ID is generated combining the Base ID and the Provider Name.
2.  **Capabilities:**
    *   `tools`: Derived from `supported_parameters` (endpoint > base).
    *   `vision`: Derived from architecture (base) or pricing for image (endpoint).
3.  **Pricing:** Endpoint pricing is used. If missing (rare), falls back to base.
4.  **Context Window:** Endpoint `context_length` is authoritative. If missing, base `context_length` is used.
5.  **Quantization:** Extracted from endpoint data.

**Script:** `backend/process_raw_to_umt.py`
- Reads from `raw_openrouter_models` and `raw_openrouter_endpoints`.
- Applies `merger.merge_endpoint_strategy`.
- Populates `unified_models`.

## 4. Frontend Visualization (DB Browser)
The Frontend (`frontend/src/components/DbBrowser.jsx`) provides a specialized **Origin Trace View** to visualize the merge process.

- **Trace Analysis:** When viewing a record, the system compares `raw_base_model_data`, `raw_endpoint_data`, and the final UMT columns.
- **Color Coding:**
    - **Green:** Value matches the Endpoint source (Preferred).
    - **Grey:** Value matches the Base source (Fallback).
    - **Red/No Match:** Value was transformed or is unique.
- **Goal:** This allows the user to verify exactly *why* a model has a specific price or context length, ensuring transparency.

## 5. Maintenance & Updates
To update the model database:
1.  Run `backend/fetch_raw_openrouter.py` to get fresh data.
2.  Run `backend/process_raw_to_umt.py` to regenerate the UMT.
