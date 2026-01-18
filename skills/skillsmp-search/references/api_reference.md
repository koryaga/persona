# SkillsMP API Reference

## Overview

The SkillsMP API provides programmatic access to the SkillsMP skills marketplace, allowing you to search and discover AI skills built by the community.

## Base URL

```
https://skillsmp.com/api/v1
```

## Authentication

All API requests require authentication using a Bearer token in the Authorization header:

```
Authorization: Bearer <your-api-key>
```

### Getting Your API Key

1. Visit https://skillsmp.com/docs/api
2. Generate a new API key
3. Store it securely using environment variables:
   ```bash
   export SKILLSMP_API_KEY="your-api-key-here"
   ```

## Endpoints

### GET /api/v1/skills/search

Search skills using keywords.

**Parameters:**

| Parameter | Type   | Required | Default | Description |
|-----------|--------|----------|---------|-------------|
| q         | string | Yes      | -       | Search query |
| page      | number | No       | 1       | Page number |
| limit     | number | No       | 20      | Items per page (max: 100) |
| sortBy    | string | No       | -       | Sort by 'stars' or 'recent' |

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "skill-id",
      "name": "Skill Name",
      "description": "Skill description",
      "stars": 123,
      "created": "2026-01-17T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

### GET /api/v1/skills/ai-search

AI semantic search powered by Cloudflare AI.

**Parameters:**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| q         | string | Yes      | Natural language search query |

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "skill-id",
      "name": "Skill Name",
      "description": "Skill description",
      "stars": 123,
      "created": "2026-01-17T10:00:00Z",
      "relevance_score": 0.95
    }
  ]
}
```

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| MISSING_API_KEY | 401 | API key not provided in Authorization header |
| INVALID_API_KEY | 401 | The provided API key is invalid |
| MISSING_QUERY | 400 | Required query parameter 'q' is missing |
| INTERNAL_ERROR | 500 | Internal server error |

## Rate Limits

- Standard rate limits apply (documented in API response headers)
- Use pagination for large result sets
- Respect the max limit of 100 items per request

## Best Practices

1. **Always use environment variables** for API keys
2. **Handle errors gracefully** - check the `success` field in responses
3. **Use appropriate search type**:
   - Keyword search for specific terms
   - AI search for natural language questions
4. **Implement retry logic** for transient errors
5. **Cache results** when appropriate to reduce API calls

## Examples

### Search for SEO skills
```bash
curl -X GET "https://skillsmp.com/api/v1/skills/search?q=SEO&sortBy=stars" \
-H "Authorization: Bearer $SKILLSMP_API_KEY"
```

### Find skills for web scraping
```bash
curl -X GET "https://skillsmp.com/api/v1/skills/ai-search?q=How+to+scrape+websites+efficiently" \
-H "Authorization: Bearer $SKILLSMP_API_KEY"
```

### Get recently added skills
```bash
curl -X GET "https://skillsmp.com/api/v1/skills/search?sortBy=recent" \
-H "Authorization: Bearer $SKILLSMP_API_KEY"
```

## Additional Resources

- **API Documentation**: https://skillsmp.com/docs/api
- **Skills Marketplace**: https://skillsmp.com
- **Support**: Contact via the SkillsMP website

## Notes

- SkillsMP is not affiliated with Anthropic
- API keys are created on January 17, 2026
- The API is currently in beta
