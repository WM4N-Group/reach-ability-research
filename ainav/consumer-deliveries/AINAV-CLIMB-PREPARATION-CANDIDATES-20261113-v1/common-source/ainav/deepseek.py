"""DeepSeek vision API backend. Credentials stay in process memory, never logs.

Official /models metadata is checked rather than assuming every DeepSeek model
accepts images. The selected alias and each actual returned model/usage are logged.
"""
from __future__ import annotations
import base64
import json
import mimetypes
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
from .contracts import canonical, file_sha, sha


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward Authorization to another endpoint.


class DeepSeekBackend:
    kind = 'deepseek_vision_api'
    BASE = 'https://api.deepseek.com'

    def __init__(self, *, api_key=None, model='deepseek-flash', max_tokens=4096,
                 max_calls=24, max_total_tokens=200000, expected_response_model=None,
                 opener=None, verify_models=True):
        key = api_key if api_key is not None else os.environ.get('DEEPSEEK_API_KEY')
        if not isinstance(key, str) or not key.strip():
            raise ValueError('DEEPSEEK_API_KEY must be supplied in process memory')
        if model != 'deepseek-flash':
            raise ValueError('This approved backend requires the verified image-capable deepseek-flash alias')
        if (type(max_tokens) is not int or not 64 <= max_tokens <= 8192
                or type(max_calls) is not int or not 1 <= max_calls <= 100
                or type(max_total_tokens) is not int or not 1 <= max_total_tokens <= 1000000):
            raise ValueError('Explicit bounded API call/token budgets required')
        if verify_models is not True:
            raise ValueError('Production cannot bypass current model capability verification')
        self._key = key
        self._opener = opener or urllib.request.build_opener(_NoRedirect())
        self.model, self.max_tokens = model, max_tokens
        self.max_calls, self.max_total_tokens = max_calls, max_total_tokens
        self.expected_response_model = expected_response_model
        self.calls = self.total_tokens = 0
        self.last_response_metadata = None
        models, _ = self._http('/models', None, timeout_s=30.)
        candidates = [x for x in models.get('data', []) if isinstance(x, dict) and x.get('id') == model]
        if len(candidates) != 1 or not {'text', 'image'} <= set(candidates[0].get('input_modalities', [])):
            raise ValueError('Current authenticated model list does not certify image input')
        self.identity = dict(provider='DeepSeek', endpoint=self.BASE+'/chat/completions',
                             requested_model=model, model_capability=candidates[0],
                             model_list_sha256=sha(models), thinking='disabled',
                             max_tokens=max_tokens, max_calls=max_calls,
                             max_total_tokens=max_total_tokens, pretrained_inference_only=True)

    def _http(self, endpoint, payload, *, timeout_s):
        data = None if payload is None else canonical(payload).encode()
        request = urllib.request.Request(self.BASE+endpoint, data=data,
            headers={'Authorization': 'Bearer '+self._key, 'Content-Type': 'application/json'},
            method='GET' if payload is None else 'POST')
        try:
            with self._opener.open(request, timeout=timeout_s) as response:
                raw = response.read(4*1024*1024+1)
                if len(raw) > 4*1024*1024:
                    raise ValueError('API response exceeds the bounded evidence size')
                result = json.loads(raw)
                return result, dict(request_id=response.headers.get('x-request-id'))
        except urllib.error.HTTPError as error:
            # No header dump, no raw request, no token in exceptions/journal.
            body = error.read(16384).decode('utf-8', errors='replace').replace(self._key, '[REDACTED]')
            raise RuntimeError('DeepSeek HTTP '+str(error.code)+': '+body[:2048]) from None
        except (urllib.error.URLError, TimeoutError) as error:
            message = str(error).replace(self._key, '[REDACTED]')
            raise RuntimeError('DeepSeek transport failure; no automatic retry: '+message) from None

    def generate(self, request, *, timeout_s):
        if self.calls >= self.max_calls or self.total_tokens >= self.max_total_tokens:
            raise RuntimeError('Experiment API budget exhausted; no further calls/fallback')
        image = request.get('image')
        if not isinstance(image, dict):
            raise ValueError('Real image metadata required for the vision backend')
        path = Path(image['path'])
        if not path.is_absolute() or file_sha(path) != image['sha256']:
            raise ValueError('Real image bytes must match the observed query')
        if path.stat().st_size > 8*1024*1024:
            raise ValueError('Image exceeds configured API upload budget')
        mime = mimetypes.guess_type(str(path))[0]
        if mime not in ('image/jpeg', 'image/png', 'image/gif', 'image/webp'):
            raise ValueError('Only documented DeepSeek image formats allowed')
        encoded = base64.b64encode(path.read_bytes()).decode('ascii')
        payload = dict(model=self.model,
            messages=[dict(role='system', content=request['system']+'\n'+request['instruction']),
                      dict(role='user', content=[dict(type='text', text=canonical(request['payload'])),
                           dict(type='image_url', image_url=dict(url='data:'+mime+';base64,'+encoded, detail='original'))])],
            response_format=dict(type='json_object'), thinking=dict(type='disabled'),
            max_tokens=self.max_tokens, stream=False)
        # Attempt is spent even on 429/HTTP failure; no invisible API retries.
        self.calls += 1
        started = time.monotonic()
        result, transport = self._http('/chat/completions', payload, timeout_s=timeout_s)
        elapsed = time.monotonic()-started
        choices = result.get('choices')
        usage = result.get('usage')
        if (not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict)
                or choices[0].get('finish_reason') != 'stop' or not isinstance(usage, dict)
                or type(usage.get('total_tokens')) is not int or usage['total_tokens'] < 0):
            raise ValueError('Complete stopped response and actual API usage required')
        content = choices[0].get('message', {}).get('content')
        if not isinstance(content, str) or not content.strip():
            raise ValueError('Empty/truncated API content rejected without repair')
        served = result.get('model')
        if not isinstance(served, str) or not served:
            raise ValueError('Actual served model identity required')
        if self.expected_response_model is None:
            self.expected_response_model = served
        elif served != self.expected_response_model:
            raise ValueError('Served model changed inside a frozen experiment')
        self.total_tokens += usage['total_tokens']
        self.last_response_metadata = dict(provider='DeepSeek', requested_model=self.model,
            response_model=served, response_id=result.get('id'),
            system_fingerprint=result.get('system_fingerprint'), **transport,
            usage=usage, cumulative_api_calls=self.calls, cumulative_total_tokens=self.total_tokens,
            elapsed_wall_s=elapsed, image_sha256=image['sha256'], image_uploaded=True,
            thinking='disabled', credential_persisted=False)
        if self.total_tokens > self.max_total_tokens:
            raise RuntimeError('Observed API usage exceeded experiment budget; dispatch refused')
        if file_sha(path) != image['sha256']:
            raise ValueError('Observed image changed during API inference')
        return content
