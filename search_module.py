import requests
import json
from datetime import datetime
import os
from typing import List
from bs4 import BeautifulSoup
import re 

class SnippetGoogleSearch:
    """Google Search with snippet extraction and Deepseek analysis"""
    
    def __init__(
        self,
        google_api_key: str,
        cx_id: str,
        deepseek_api_key: str,
        k: int = 3,
        max_snippet_length: int = 500,
        enable_extra_snippets: bool = False,
    ):
        self.google_api_key = google_api_key
        self.cx_id = cx_id
        self.deepseek_api_key = deepseek_api_key
        self.k = k
        self.max_snippet_length = max_snippet_length
        self.enable_extra_snippets = enable_extra_snippets

    def _google_search(self, query: str) -> List[dict]:
        """Retrieve search results with snippets"""
        results = []
        start = 1
        
        while len(results) < self.k:
            params = {
                "q": query,
                "key": self.google_api_key,
                "cx": self.cx_id,
                "num": min(10, self.k - len(results)),
                "start": start
            }
            
            response = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
            search_data = response.json()
            
            if 'items' not in search_data:
                break
                
            for item in search_data['items']:
                if len(results) >= self.k:
                    break
                
                result = {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "main_snippet": item.get("snippet", "")[:self.max_snippet_length],
                    "extra_snippets": self._get_extra_snippets(item["link"]) if self.enable_extra_snippets else [],
                    "date": datetime.now().isoformat()
                }
                
                results.append(result)
            
            start += 10
        
        return results

    def _get_extra_snippets(self, url: str) -> List[str]:
        """Optional: Extract additional snippets from page content"""
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
            return [p[:500] for p in paragraphs[:3]]  # Return first 3 paragraphs trimmed
        except:
            return []

    def _deepseek_analysis(self, documents: List[dict], query: str) -> str:
        """Generate analysis with proper citations and validation"""
        references = []
        context = []
        
        for idx, doc in enumerate(documents):
            ref_num = idx + 1
            snippets = [doc["main_snippet"]] + doc["extra_snippets"]
            context.append(f"[Source {ref_num}]\n" + "\n".join(snippets))
            references.append(f"[{ref_num}] {doc['url']}")
        
        prompt = f"""a user searched for "{query}. Based on the search results below, please provide a detailed analysis or a summary of the result in a paragraph or a sentence format."
        Follow these rules:
        1. Only cite sources that are actually used
        2. Use numeric references [1], [2], etc.
        3. Never reference numbers higher than {len(documents)}
        4. The output can include a table or a graph since the output will be in markdown structure if user mentioned a table or graph
            for tables follow these rules:
            When creating tables:
                - Use simple markdown table syntax
                - Include clear column headers
                - Limit to 10 columns max
                - Add table captions when needed
                - Avoid complex merging cells.
                
        Query: {query}
                
        Search results:
        {"\n\n".join(context)}

        Reference URLs:
        {"\n".join(references)}
        """
        
        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5,
            "max_tokens": 1500
        }
        
        response = requests.post("https://api.deepseek.com/v1/chat/completions", 
                            json=payload, headers=headers)
        
        analysis = response.json()['choices'][0]['message']['content']
        
        # Validate citation numbers
        max_valid = len(documents)
        analysis = re.sub(
            r'\[(\d+)\]',
            lambda m: f'[{min(int(m.group(1)), max_valid)}]' if m.group(1).isdigit() else m.group(0),
            analysis
        )
        
        return analysis

    def process_query(self, query: str) -> dict:
        """End-to-end processing pipeline"""
        search_results = self._google_search(query)
        analysis = self._deepseek_analysis(search_results, query)
        
        # Extract cited reference numbers from analysis text
        cited_numbers = list(set(
            int(match) - 1  # Convert to zero-based index
            for match in re.findall(r'\[(\d+)\]', analysis)
            if match.isdigit()
        ))
        
        # Filter sources to only cited ones
        cited_sources = [
            search_results[idx] 
            for idx in cited_numbers 
            if idx < len(search_results)
        ]
        
        # Update analysis numbers to match filtered sources
        for new_idx, original_idx in enumerate(cited_numbers):
            analysis = analysis.replace(
                f'[{original_idx + 1}]', 
                f'[{new_idx + 1}]'
            )
        
        return {
            "query": query,
            "analysis": analysis,
            "sources": [{
                "title": res["title"],
                "url": res["url"],
                "main_snippet": res["main_snippet"]
            } for res in cited_sources]
        }

# Usage example
