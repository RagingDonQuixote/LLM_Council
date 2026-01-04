# OpenRouter API Variables Reference

This document describes all available variables and data structures in the OpenRouter API.

## API Endpoints

### 1. Models List Endpoint
**URL**: `GET https://openrouter.ai/api/v1/models`

**Response Structure**:
```json
{
  "data": [
    {
      "id": "string",           // Model identifier (e.g., "openai/gpt-4o:free")
      "name": "string",         // Human-readable model name
      "description": "string",  // Model description
      "context_length": number, // Maximum token limit
      "pricing": {              // Cost structure
        "prompt": "string|number",     // Cost per prompt token
        "completion": "string|number"  // Cost per completion token
      },
      "top_provider": {         // Provider information
        "context_length": number,
        "max_completion_tokens": number
      },
      "per_request_limits": {   // Rate limits
        "prompt_tokens": "string",
        "completion_tokens": "string"
      }
    }
  ]
}
```

### 2. Chat Completion Endpoint
**URL**: `POST https://openrouter.ai/api/v1/chat/completions`

**Request Variables**:
```json
{
  "model": "string",           // Model ID to use
  "messages": [                // Array of message objects
    {
      "role": "string",        // "system", "user", or "assistant"
      "content": "string"      // Message content
    }
  ],
  "max_tokens": "number",      // Optional: Max completion tokens
  "temperature": "number",     // Optional: Randomness (0-2)
  "top_p": "number",          // Optional: Nucleus sampling
  "stream": "boolean"         // Optional: Streaming response
}
```

**Response Variables**:
```json
{
  "id": "string",              // Request ID
  "object": "string",          // Always "chat.completion"
  "created": number,           // Unix timestamp
  "model": "string",           // Model used
  "choices": [                 // Array of completion choices
    {
      "index": number,         // Choice index
      "message": {             // The assistant's message
        "role": "string",      // Always "assistant"
        "content": "string",   // Generated text
        "reasoning_details": "string" // Optional: Chain of thought
      },
      "finish_reason": "string" // "stop", "length", "content_filter", etc.
    }
  ],
  "usage": {                   // Token usage statistics
    "prompt_tokens": number,   // Tokens in prompt
    "completion_tokens": number, // Tokens in completion
    "total_tokens": number     // Total tokens used
  }
}
```

---

## Available Variables by Category

### Model Identification
| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `id` | string | Unique model identifier | `"openai/gpt-4o:free"` |
| `name` | string | Human-readable model name | `"OpenAI GPT-4o"` |
| `description` | string | Detailed model description | `"Advanced multimodal model..."` |

### Model Capabilities
| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `context_length` | number | Maximum input token limit | `128000` |
| `max_completion_tokens` | number | Maximum output token limit | `4096` |
| `top_provider.context_length` | number | Provider-specific token limit | `128000` |

### Pricing Variables
| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `pricing.prompt` | string\|number | Cost per input token | `"0.00001"` or `0` |
| `pricing.completion` | string\|number | Cost per output token | `"0.00003"` or `0` |
| `per_request_limits.prompt_tokens` | string | Rate limit for prompt tokens | `"1e6"` |
| `per_request_limits.completion_tokens` | string | Rate limit for completion tokens | `"5e5"` |

### Chat Message Variables
| Variable | Type | Description | Values |
|----------|------|-------------|--------|
| `role` | string | Message sender type | `"system"`, `"user"`, `"assistant"` |
| `content` | string | Message text content | Any text string |

### Response Variables
| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `usage.prompt_tokens` | number | Input tokens consumed | `1250` |
| `usage.completion_tokens` | number | Output tokens generated | `850` |
| `usage.total_tokens` | number | Total tokens used | `2100` |
| `choices[].finish_reason` | string | Why generation stopped | `"stop"`, `"length"` |

### Capability Detection Variables
| Variable | Type | Description | Detection Logic |
|----------|------|-------------|----------------|
| `capabilities.thinking` | boolean | Reasoning capability | `"reasoning"` in description OR `"think"` in name OR `"r1"` in id |
| `capabilities.tools` | boolean | Function calling support | `"tool"` in description OR `"function calling"` in description |
| `capabilities.vision` | boolean | Visual processing | `"vision"` in description OR `"vl"` in id OR `"multimodal"` in description |

### Free Model Detection
| Variable | Type | Description | Logic |
|----------|------|-------------|-------|
| `free` | boolean | Is model completely free | `pricing.prompt == "0"` OR `pricing.prompt == 0` OR `":free"` in id |

---

## Data Type Specifications

### String Variables
- **Model IDs**: Format `provider/model-name:variant`
- **Pricing**: Decimal numbers as strings (`"0.00001"`)
- **Token Limits**: Scientific notation as strings (`"1e6"`)

### Number Variables
- **Token Counts**: Integer values
- **Context Length**: Integer values
- **Timestamps**: Unix epoch seconds

### Boolean Variables
- **Capabilities**: Derived from text analysis
- **Free Status**: Calculated from pricing
- **Stream**: User preference

### Object Variables
- **Pricing**: Contains `prompt` and `completion` fields
- **Usage**: Contains token count statistics
- **Top Provider**: Contains provider-specific limits

---

## Error Handling Variables

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (invalid API key)
- `429`: Rate Limited (too many requests)
- `500`: Internal Server Error

### Error Response Structure
```json
{
  "error": {
    "message": "string",     // Error description
    "type": "string",        // Error type
    "code": "string"         // Error code
  }
}
```

---

## Rate Limiting Variables

### Headers
- `X-RateLimit-Limit`: Request limit per window
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

### Response Headers
- `Retry-After`: Seconds to wait (for 429 responses)

---

## Streaming Variables

### Stream Response Format
```json
data: {"id":"...","object":"chat.completion.chunk","created":...,"model":"...","choices":[{"index":0,"delta":{"content":"..."},"finish_reason":null}]}

data: {"id":"...","object":"chat.completion.chunk","created":...,"model":"...","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### Stream Event Types
- `delta`: Partial content update
- `finish_reason`: Completion reason
- `[DONE]`: End of stream

---

## Usage Examples

### Model Selection by Capability
```python
# Filter models by capability
models = await fetch_model_metadata()
reasoning_models = [m for m in models if m.get("capabilities", {}).get("thinking")]
vision_models = [m for m in models if m.get("capabilities", {}).get("vision")]
free_models = [m for m in models if m.get("free")]
```

### Cost Calculation
```python
# Calculate total cost
prompt_cost = float(pricing["prompt"]) * prompt_tokens
completion_cost = float(pricing["completion"]) * completion_tokens
total_cost = prompt_cost + completion_cost
```

### Model Usage
```python
# Use model ID in chat completion
payload = {
    "model": "openai/gpt-4o:free",
    "messages": [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"}
    ]
}
```

---

*Last Updated: 2026-01-03*
*OpenRouter API v1 Documentation*