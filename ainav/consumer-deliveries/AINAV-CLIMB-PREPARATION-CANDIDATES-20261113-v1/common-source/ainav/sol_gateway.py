"""User-configured OpenAI-compatible vision gateway, exact model + high effort.

Gateway alias/returned metadata are recorded; no claim of upstream model weights
or official OpenAI identity. HTTP is explicit, no redirects/retries/downgrade.
"""
import base64
import json
import mimetypes
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
from .contracts import canonical,file_sha,sha
from .deepseek import _NoRedirect


class SolGatewayBackend:
    kind='openai_compatible_vision_api'
    def __init__(self,*,api_key=None,base_url='http://43.133.198.249:3000/v1',model='gpt-6.1-sol',reasoning_effort='high',
                 max_tokens=8192,max_calls=24,max_total_tokens=200000,opener=None,vision_verification=None):
        key=api_key if api_key is not None else os.environ.get('AINAV_VLM_API_KEY')
        if not isinstance(key,str) or not key.strip():raise ValueError('AINAV_VLM_API_KEY must be supplied in process memory')
        if model!='gpt-6.1-sol' or reasoning_effort!='high':raise ValueError('User-authorized exact gpt-6.1-sol/high required; no downgrade')
        parsed=urllib.parse.urlsplit(base_url)
        if base_url!='http://43.133.198.249:3000/v1' or parsed.username or parsed.password or parsed.query or parsed.fragment:raise ValueError('Only the explicit user-approved gateway endpoint is registered')
        if (type(max_tokens) is not int or not 64<=max_tokens<=8192 or type(max_calls) is not int or not 1<=max_calls<=100
                or type(max_total_tokens) is not int or not 1<=max_total_tokens<=1000000):raise ValueError('Explicit bounded inference budgets required')
        if not isinstance(vision_verification,dict) or vision_verification.get('requested_model')!=model or vision_verification.get('requested_reasoning_effort')!='high' or vision_verification.get('endpoint')!=base_url+'/chat/completions' or not vision_verification.get('vision_high_probe_passed'):
            raise ValueError('Same-endpoint/model/high actual image-probe verification receipt required')
        self._key=key;self.base_url=base_url;self.model=model;self.reasoning_effort=reasoning_effort
        self.max_tokens,self.max_calls,self.max_total_tokens=max_tokens,max_calls,max_total_tokens
        self.calls=self.total_tokens=0;self.last_response_metadata=None;self._served=None
        self._opener=opener or urllib.request.build_opener(_NoRedirect())
        models,_=self._http('/models',None,timeout_s=25.)
        matches=[m for m in models.get('data',[]) if isinstance(m,dict) and m.get('id')==model]
        if len(matches)!=1:raise ValueError('Exact requested model not advertised by authenticated gateway; no fallback')
        self.identity=dict(provider='user_configured_sub2api_gateway',endpoint=base_url+'/chat/completions',requested_model=model,
            reasoning_effort=reasoning_effort,model_capability=matches[0],model_list_sha256=sha(models),
            vision_verification=vision_verification,transport_security='HTTP unencrypted; explicitly configured by user',
            max_tokens=max_tokens,max_calls=max_calls,max_total_tokens=max_total_tokens,pretrained_inference_only=True,
            upstream_model_weights_or_official_identity_verified=False)
    def _http(self,path,payload,*,timeout_s):
        data=None if payload is None else canonical(payload).encode()
        request=urllib.request.Request(self.base_url+path,data=data,method='GET' if data is None else 'POST',
            headers={'Authorization':'Bearer '+self._key,'Content-Type':'application/json'})
        try:
            with self._opener.open(request,timeout=timeout_s) as response:
                raw=response.read(4*1024*1024+1)
                if len(raw)>4*1024*1024:raise ValueError('Gateway response exceeds bounded evidence size')
                return json.loads(raw),dict(request_id=response.headers.get('x-request-id'))
        except urllib.error.HTTPError as e:
            message=e.read(16384).decode(errors='replace').replace(self._key,'[REDACTED]')
            raise RuntimeError('Configured gateway HTTP '+str(e.code)+': '+message[:2048]) from None
        except (urllib.error.URLError,TimeoutError) as e:
            raise RuntimeError('Configured gateway transport failed; no retry: '+str(e).replace(self._key,'[REDACTED]')) from None
    def generate(self,request,*,timeout_s):
        if self.calls>=self.max_calls or self.total_tokens>=self.max_total_tokens:raise RuntimeError('Gateway inference budget exhausted; no fallback')
        image=request.get('image')
        if not isinstance(image,dict):raise ValueError('Real image identity required')
        path=Path(image['path'])
        if not path.is_absolute() or file_sha(path)!=image['sha256']:raise ValueError('Observed image bytes differ')
        mime=mimetypes.guess_type(str(path))[0]
        if mime not in ('image/png','image/jpeg','image/webp','image/gif') or path.stat().st_size>8*1024*1024:raise ValueError('Bounded supported actual image required')
        payload=dict(model=self.model,reasoning_effort=self.reasoning_effort,max_completion_tokens=self.max_tokens,
            messages=[dict(role='system',content=request['system']+'\n'+request['instruction']),
                      dict(role='user',content=[dict(type='text',text=canonical(request['payload'])),dict(type='image_url',image_url=dict(url='data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode(),detail='high'))])],
            response_format={'type':'json_object'},stream=False)
        self.calls+=1;start=time.monotonic();result,transport=self._http('/chat/completions',payload,timeout_s=timeout_s)
        choices=result.get('choices');usage=result.get('usage');served=result.get('model')
        if not isinstance(choices,list) or len(choices)!=1 or choices[0].get('finish_reason')!='stop':raise ValueError('Complete stopped gateway response required; no truncation retry')
        if not isinstance(usage,dict) or type(usage.get('total_tokens')) is not int or usage['total_tokens']<0:raise ValueError('Actual gateway token usage required')
        content=choices[0].get('message',{}).get('content')
        if not isinstance(content,str) or not content.strip():raise ValueError('Nonempty final JSON response required; reasoning text is not a final plan')
        if served!=self.model:raise ValueError('Gateway returned another model alias; no silent substitution')
        returned_effort=result.get('reasoning_effort')
        if returned_effort is not None and returned_effort!=self.reasoning_effort:raise ValueError('Gateway response reports different reasoning effort')
        self.total_tokens+=usage['total_tokens'];self._served=served
        self.last_response_metadata=dict(provider='user_configured_sub2api_gateway',requested_model=self.model,response_model=served,
            requested_reasoning_effort='high',returned_reasoning_effort=returned_effort,reasoning_effort_independently_observable=returned_effort is not None,
            response_id=result.get('id'),system_fingerprint=result.get('system_fingerprint'),**transport,usage=usage,
            cumulative_api_calls=self.calls,cumulative_total_tokens=self.total_tokens,elapsed_wall_s=time.monotonic()-start,
            image_sha256=image['sha256'],image_uploaded=True,credential_persisted=False,transport_TLS=False,upstream_model_identity_verified=False)
        if self.total_tokens>self.max_total_tokens:raise RuntimeError('Actual usage exceeded frozen token budget; refuse dispatch')
        if file_sha(path)!=image['sha256']:raise ValueError('Observed image changed during gateway inference')
        return content
