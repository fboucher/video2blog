"""
AI editing service — routes to Anthropic or OpenAI for text editing — Issue #16.

Functions:
  is_configured() → bool
  get_provider() → "anthropic" | "openai"
  stream_edit(system_prompt, draft, transcript, messages) → SSE generator
"""

import os
import json


def is_configured():
    """Return True when EDITING_API_KEY is set, False otherwise."""
    return bool(os.environ.get('EDITING_API_KEY'))


def get_provider():
    """Return the configured provider: 'anthropic' (default) or 'openai'."""
    return os.environ.get('EDITING_PROVIDER', 'anthropic').lower()


def stream_edit(system_prompt, draft, transcript=None, messages=None):
    """
    Generator yielding SSE-formatted JSON strings.
    
    Args:
        system_prompt: The skill prompt body
        draft: The current draft content
        transcript: Optional video transcript
        messages: Optional conversation history (reserved for future multi-turn)
    
    Yields:
        SSE data lines: 'data: {"delta": "...", "done": false}\n\n'
        Final chunk: 'data: {"done": true}\n\n'
    """
    provider = get_provider()
    api_key = os.environ.get('EDITING_API_KEY')
    model = os.environ.get(
        'EDITING_MODEL',
        'claude-sonnet-4-6' if provider == 'anthropic' else 'gpt-4o-mini'
    )
    base_url = os.environ.get('EDITING_BASE_URL')

    # Build the user message
    user_content = f"Draft:\n\n{draft}"
    if transcript:
        user_content += f"\n\nTranscript:\n\n{transcript}"

    if provider == 'anthropic':
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'delta': text, 'done': False})}\n\n"
        
        yield f"data: {json.dumps({'done': True})}\n\n"

    elif provider == 'openai':
        from openai import OpenAI
        
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        
        client = OpenAI(**kwargs)
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            stream=True,
        )
        
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield f"data: {json.dumps({'delta': delta, 'done': False})}\n\n"
        
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    else:
        yield f"data: {json.dumps({'error': f'Unknown provider: {provider}', 'done': True})}\n\n"
