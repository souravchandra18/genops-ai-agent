import os
import requests

def call_llm(provider, prompt):
    if provider == 'openai':
        key = os.getenv('OPENAI_API_KEY')
        if not key:
            return {'error': 'OPENAI_API_KEY missing'}
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 1200}
        )
        data = response.json()
        text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        return {'summary': '\n'.join(text.splitlines()[:8]), 'full': text}

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
