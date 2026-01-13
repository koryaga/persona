#!/usr/bin/env python3
"""
Web search script that uses DuckDuckGo by default, with Tavily fallback when TRAVILY_TOKEN is provided.
"""

import os
import sys
import json
import subprocess
import urllib.parse
import urllib.request


def search_duckduckgo_api(query, max_results=10):
    """
    Search using DuckDuckGo Instant Answer API.
    Returns list of results with 'title' and 'url' keys.
    """
    try:
        # Use DuckDuckGo's Instant Answer API
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json"
        
        # Make the request
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        results = []
        
        # Extract results from RelatedTopics
        if 'RelatedTopics' in data:
            for item in data['RelatedTopics']:
                if 'FirstURL' in item and 'Text' in item:
                    # Extract title from text or URL
                    text = item['Text']
                    url = item['FirstURL']
                    
                    # Clean up the title
                    title = text.split(' - ')[0] if ' - ' in text else text.split('. ')[0] if '. ' in text else text[:100]
                    
                    results.append({
                        'title': title.strip(),
                        'url': url
                    })
                    
                    if len(results) >= max_results:
                        break
        
        # If no results from RelatedTopics, try the main result
        if not results and 'Results' in data and data['Results']:
            for item in data['Results'][:max_results]:
                if 'FirstURL' in item and 'Text' in item:
                    results.append({
                        'title': item['Text'][:100].strip(),
                        'url': item['FirstURL']
                    })
        
        return results
        
    except Exception as e:
        print(f"DuckDuckGo API error: {e}", file=sys.stderr)
        return []


def search_tavily(query, token, max_results=10):
    """
    Search using Tavily API when token is provided.
    Returns list of results with 'title' and 'url' keys.
    """
    try:
        # Build the curl command
        curl_cmd = [
            'curl', '-X', 'POST', 'https://api.tavily.com/search',
            '-H', 'Content-Type: application/json',
            '-H', f'Authorization: Bearer {token}',
            '-d', json.dumps({
                "query": query,
                "include_answer": "advanced"
            })
        ]
        
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"Tavily curl error: {result.stderr}", file=sys.stderr)
            return []
        
        # Parse JSON response
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            print(f"Tavily response not valid JSON: {e}", file=sys.stderr)
            return []
        
        # Extract results
        results = []
        
        # Include direct answer if available
        if 'answer' in data and data['answer']:
            results.append({
                'title': 'Direct Answer',
                'url': 'N/A',
                'content': data['answer']
            })
        
        # Add search results
        if 'results' in data:
            for item in data['results'][:max_results]:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'content': item.get('content', '')
                })
        
        return results
        
    except Exception as e:
        print(f"Tavily search error: {e}", file=sys.stderr)
        return []


def search_web(query, max_results=10):
    """
    Main search function that chooses between DuckDuckGo and Tavily.
    """
    token = os.environ.get('TRAVILY_TOKEN')
    
    if token:
        print(f"Using Tavily API for search...", file=sys.stderr)
        results = search_tavily(query, token, max_results)
    else:
        print(f"Using DuckDuckGo API for search...", file=sys.stderr)
        results = search_duckduckgo_api(query, max_results)
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: web_search.py <query> [max_results]")
        print("Set TRAVILY_TOKEN environment variable to use Tavily API")
        sys.exit(1)
    
    query = sys.argv[1]
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    results = search_web(query, max_results)
    
    # Output as JSON for easy parsing
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
