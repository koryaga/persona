# Web Search Methods Reference

This skill supports multiple web search methods with automatic selection based on environment configuration.

## DuckDuckGo API (Default)

**When used:** No `TRAVILY_TOKEN` environment variable set

**Endpoint:** `https://api.duckduckgo.com/?q=<QUERY>&format=json`

**Implementation:**
```python
import urllib.request
import json

def search_duckduckgo_api(query, max_results=10):
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json"
    
    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.loads(response.read().decode())
    
    results = []
    if 'RelatedTopics' in data:
        for item in data['RelatedTopics']:
            if 'FirstURL' in item and 'Text' in item:
                results.append({
                    'title': item['Text'][:100].strip(),
                    'url': item['FirstURL']
                })
                if len(results) >= max_results:
                    break
    return results
```

**Pros:**
- ✅ Free, no API key required
- ✅ No rate limits for reasonable use
- ✅ Simple JSON response
- ✅ Reliable and fast

**Cons:**
- ⚠️ Limited result count (typically 10-15)
- ⚠️ No content snippets
- ⚠️ Results may be less comprehensive

**Best for:** General searches, quick lookups, URL discovery

## Tavily API (Premium)

**When used:** `TRAVILY_TOKEN` environment variable is set

**Endpoint:** `https://api.tavily.com/search`

**Request format:**
```bash
curl -X POST https://api.tavily.com/search \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <TOKEN>' \
  -d '{
    "query": "<QUERY>",
    "include_answer": "advanced"
  }'
```

**Implementation:**
```python
import subprocess
import json

def search_tavily(query, token, max_results=10):
    curl_cmd = [
        'curl', '-X', 'POST', 'https://api.tavily.com/search',
        '-H', 'Content-Type: application/json',
        '-H', f'Authorization: Bearer {token}',
        '-d', json.dumps({
            "query": query,
            "include_answer": "advanced"
        })
    ]
    
    result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
    data = json.loads(result.stdout)
    
    results = []
    if 'answer' in data:
        results.append({
            'title': 'Direct Answer',
            'url': 'N/A',
            'content': data['answer']
        })
    
    for item in data['results'][:max_results]:
        results.append({
            'title': item.get('title', ''),
            'url': item.get('url', ''),
            'content': item.get('content', '')
        })
    
    return results
```

**Pros:**
- ✅ High-quality, relevant results
- ✅ Includes direct answers
- ✅ Content snippets for context
- ✅ More comprehensive search
- ✅ Better for research

**Cons:**
- ⚠️ Requires API token
- ⚠️ Paid service (with free tier)
- ⚠️ More complex setup

**Best for:** Research, complex queries, fact-checking, detailed analysis

## Environment Setup

### DuckDuckGo (Default)
No setup required. Works immediately.

### Tavily
1. Get API token from [Tavily](https://tavily.com)
2. Set environment variable:
   ```bash
   export TRAVILY_TOKEN="tvly-abc123..."
   ```
3. Verify:
   ```bash
   echo $TRAVILY_TOKEN
   ```

## Usage Examples

### Basic Search
```bash
# Using DuckDuckGo
python3 web_search.py "python programming tutorial"

# Using Tavily (when TRAVILY_TOKEN is set)
export TRAVILY_TOKEN="your-token"
python3 web_search.py "machine learning research papers"
```

### With Result Limit
```bash
python3 web_search.py "web development frameworks" 10
```

### In Python Scripts
```python
import subprocess
import json

def web_search(query, max_results=5):
    """Search the web and return results."""
    result = subprocess.run(
        ['python3', 'web_search.py', query, str(max_results)],
        capture_output=True,
        text=True,
        cwd='/skills/web-search/scripts'
    )
    return json.loads(result.stdout)

# Usage
results = web_search("AI news", 3)
for r in results:
    print(f"{r['title']}: {r['url']}")
```

## Error Handling

Both methods include error handling:

- **DuckDuckGo:** Returns empty list on network errors or parsing failures
- **Tavily:** Returns empty list on API errors or invalid responses

Check stderr for error messages:
```bash
python3 web_search.py "query" 2>&1 | grep -i error
```

## Performance Tips

1. **Query specificity:** More specific queries yield better results
2. **Result limits:** Use appropriate limits (5-10 for most cases)
3. **Timeout handling:** Both methods have 30-second timeouts
4. **Caching:** Consider caching results for repeated queries

## Troubleshooting

### DuckDuckGo returns no results
- Check internet connectivity
- Verify query is not too broad
- Try a simpler query

### Tavily authentication fails
- Verify token is set: `echo $TRAVILY_TOKEN`
- Check token is valid and not expired
- Ensure proper formatting (no extra spaces)

### General issues
- Check stderr output for specific errors
- Verify curl is installed: `which curl`
- Test with simple query first
