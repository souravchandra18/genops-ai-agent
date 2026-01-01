#Author: Sourav Chandra
import os
import requests
import json

def call_llm(provider, prompt):
    if provider == 'openai':
        key = os.getenv('OPENAI_API_KEY')
        if not key:
            return {'error': 'OPENAI_API_KEY missing'}
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={
                'model': 'gpt-4.1-mini', 
                'messages': [{'role': 'user', 'content': prompt}], 
                'max_tokens': 2000,
                'temperature': 0.1,
                'response_format': {'type': 'json_object'}
            }
        )
        data = response.json()

        print("LLM response:", data) 
        
        if 'error' in data:
            return {'error': f"OpenAI API Error: {data['error']['message']}"}
            
        text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        try:
            # Try to parse as JSON first
            parsed_json = json.loads(text)
            return {
                'summary': parsed_json.get('executive_summary', 'No summary available'),
                'full': text,
                'structured': parsed_json
            }
        except json.JSONDecodeError:
            # Fallback to text parsing
            return {
                'summary': '\n'.join(text.splitlines()[:8]), 
                'full': text,
                'structured': None
            }

    if provider == 'bedrock':
        return {'error': 'Bedrock adapter not implemented yet'}

    if provider == 'custom':
        url = os.getenv('CUSTOM_LLM_ENDPOINT')
        if not url:
            return {'error': 'CUSTOM_LLM_ENDPOINT missing'}
        response = requests.post(url, json={'prompt': prompt})
        data = response.json()
        return {'summary': data.get('summary', ''), 'full': str(data)}

    return {'error': 'Unknown provider'}
