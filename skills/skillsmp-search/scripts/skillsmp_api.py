#!/usr/bin/env python3
"""
SkillsMP API Client
A Python client for the SkillsMP API for searching and discovering AI skills.
"""

import os
import requests
import json
from typing import Optional, Dict, Any, List


class SkillsMPAPI:
    """Client for the SkillsMP API."""
    
    BASE_URL = "https://skillsmp.com/api/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the SkillsMP API client.
        
        Args:
            api_key: SkillsMP API key. If None, reads from SKILLSMP_API_KEY env var.
        
        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.environ.get('SKILLSMP_API_KEY')
        if not self.api_key:
            raise ValueError(
                "API key must be provided or set in SKILLSMP_API_KEY environment variable"
            )
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
    
    def search(
        self,
        query: str,
        page: int = 1,
        limit: int = 20,
        sort_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search skills using keywords.
        
        Args:
            query: Search query string
            page: Page number (default: 1)
            limit: Items per page (default: 20, max: 100)
            sort_by: Sort by 'stars' or 'recent'
        
        Returns:
            API response as dictionary
        """
        url = f"{self.BASE_URL}/skills/search"
        params = {"q": query, "page": page, "limit": limit}
        if sort_by:
            params["sort_by"] = sort_by
        
        response = requests.get(url, params=params, headers=self.headers)
        return response.json()
    
    def ai_search(self, query: str) -> Dict[str, Any]:
        """
        AI semantic search powered by Cloudflare AI.
        
        Args:
            query: Natural language search query
        
        Returns:
            API response as dictionary
        """
        url = f"{self.BASE_URL}/skills/ai-search"
        params = {"q": query}
        
        response = requests.get(url, params=params, headers=self.headers)
        return response.json()


def search_skills(query: str, page: int = 1, limit: int = 20, sort_by: Optional[str] = None) -> None:
    """Search for skills using keywords and print results."""
    try:
        client = SkillsMPAPI()
        results = client.search(query, page, limit, sort_by)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error: {e}")


def ai_search_skills(query: str) -> None:
    """Search for skills using AI semantic search and print results."""
    try:
        client = SkillsMPAPI()
        results = client.ai_search(query)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python skillsmp_api.py search <query> [page] [limit] [sort_by]")
        print("  python skillsmp_api.py ai-search <query>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "search":
        query = sys.argv[2]
        page = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 20
        sort_by = sys.argv[5] if len(sys.argv) > 5 else None
        search_skills(query, page, limit, sort_by)
    elif command == "ai-search":
        query = sys.argv[2]
        ai_search_skills(query)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
