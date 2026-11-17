"""Passive original-transport accounting and finite C/D method/role policy.

No key/header/opener/response inspection or API call here. Only the ORIGINAL
DeepSeekBackend reads response bytes; this layer retains original safe metadata.
"""
import time
from types import MethodType


class CDAPILedger:
    def __init__(self, journal, *, expected_served_model=None):
        if not callable(journal) or (expected_served_model is not None and
                (type(expected_served_model) is not str or not expected_served_model)):
            raise ValueError('Durable journal and explicit previous C served-model or None')
        self.journal = journal
        self.expected = expected_served_model
        self.served = None
        self.queries = self.role_attempts = self.role_responses = 0
        self.roles_in_query = 0
        self.query = None
        self.failed = False
        self.transport = {'models_attempts': 0, 'completion_attempts': 0,
                          'models_headers_returned': 0, 'completion_headers_returned': 0}
        self.transport_errors = []
        self.responses = []
        self.constructor_attempts = self.constructor_completed = 0
        self.constructor_wall_s = None
        self._installed = False

    def _check(self):
        if self.failed:
            raise RuntimeError('C/D API ledger failed; no retry/resume')

    def __call__(self, row):
        if type(row) is not dict:
            raise ValueError('Original structured journal row')
        event = row.get('event')
        if event == 'vlm_request':
            self._check()
            if self.query is None or self.roles_in_query >= 8:
                self.failed = True
                raise RuntimeError('No active method query or eight-role cap exhausted')
            self.roles_in_query += 1
            self.role_attempts += 1
            row = dict(row)
            identity = row.get('backend', {})
            row['backend'] = {k: identity[k] for k in ('provider','requested_model','endpoint',
                'thinking','model_list_sha256','max_tokens','max_calls','max_total_tokens') if k in identity}
        elif event == 'vlm_response':
            metadata = row.get('provider_metadata')
            if self.query is None or self.role_responses >= self.role_attempts or type(metadata) is not dict:
                self.failed = True
                raise RuntimeError('Missing actual same-query provider metadata')
            served = metadata.get('response_model')
            usage = metadata.get('usage')
            if (type(served) is not str or not 0 < len(served) <= 256 or
                    type(usage) is not dict or type(usage.get('total_tokens')) is not int or
                    usage['total_tokens'] < 0):
                self.failed = True
                raise ValueError('Actual served-model/usage required, never requested alias')
            safe_usage = {k:v for k,v in usage.items() if k in ('prompt_tokens','completion_tokens','total_tokens',
                'prompt_cache_hit_tokens','prompt_cache_miss_tokens') and type(v) is int and v >= 0}
            safe = dict(response_model=served, usage=safe_usage,
                        requested_model=metadata.get('requested_model'),
                        elapsed_wall_s=metadata.get('elapsed_wall_s'),
                        cumulative_api_calls=metadata.get('cumulative_api_calls'),
                        cumulative_total_tokens=metadata.get('cumulative_total_tokens'),
                        image_sha256=metadata.get('image_sha256'), image_uploaded=metadata.get('image_uploaded'),
                        provider='DeepSeek', thinking='disabled', credential_persisted=False)
            row = dict(row, provider_metadata=safe)
            try:
                ref = self.journal(row)  # Persist actual cost BEFORE fair-model refusal.
            except BaseException:
                self.failed = True
                raise
            self.role_responses += 1
            self.responses.append(dict(query_sha256=self.query, role=row.get('role'),
                                       evidence_ref=ref, **safe))
            if (self.served is not None and served != self.served or
                    self.expected is not None and served != self.expected):
                self.failed = True
                raise RuntimeError('Actual served-model mismatch; response cost kept, no native dispatch')
            self.served = served
            return ref
        elif event == 'vlm_role_failed':
            self.failed = True
            row = dict(row)
            error = row.pop('error', '')
            kind = error.split(':',1)[0] if type(error) is str else ''
            row['error_type'] = kind if kind.isidentifier() and len(kind) <= 80 else 'UNKNOWN'
        try:
            return self.journal(row)
        except BaseException:
            self.failed = True
            raise

    def install_method_limit(self, driver):
        self._check()
        if self._installed or driver.r.step_count != 0 or driver.coordinator is not None:
            raise ValueError('Once at task0 after original D seam/task installation, before capture')
        self._installed = True
        original = driver.planner.select
        ledger = self
        def select(planner, batch):
            ledger._check()
            if planner is not driver.planner or ledger.query is not None or ledger.queries >= 6:
                ledger.failed = True
                raise RuntimeError('Six-query cap or method identity refused')
            ledger.queries += 1
            ledger.query, ledger.roles_in_query = batch.sha256, 0
            try:
                return original(batch)  # Exactly the current original C or v3-bound D select.
            except BaseException:
                ledger.failed = True
                raise
            finally:
                ledger.query = None
        driver.planner.select = MethodType(select, driver.planner)

    def snapshot(self, backend=None):
        calls = getattr(backend, 'calls', None)
        tokens = getattr(backend, 'total_tokens', None)
        # Original RoleRunner may reject parse/deadline BEFORE its response event.
        # Preserve safe last-backend usage too, without claiming role acceptance.
        last = getattr(backend, 'last_response_metadata', None)
        last_safe = None
        if type(last) is dict:
            usage=last.get('usage',{})
            last_safe={k:last[k] for k in ('response_model','requested_model','elapsed_wall_s',
                'cumulative_api_calls','cumulative_total_tokens','image_sha256','image_uploaded') if k in last}
            last_safe['usage']={k:v for k,v in usage.items() if k in ('total_tokens','prompt_tokens','completion_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens') and type(v)is int and v>=0} if type(usage)is dict else None
        return dict(method_queries=self.queries, role_attempts=self.role_attempts,
                    role_responses=self.role_responses, expected_previous_C_served_model=self.expected,
                    actual_served_model=self.served, transport=dict(self.transport),
                    transport_error_types=list(self.transport_errors),
                    constructor_attempts=self.constructor_attempts,
                    constructor_completed=self.constructor_completed,
                    constructor_wall_s=self.constructor_wall_s,
                    backend_completion_attempts=calls, backend_known_tokens_lower_bound=tokens,
                    all_attempt_role_usage_known=(self.role_attempts == self.role_responses and not self.failed),
                    money_amount=None, responses=list(self.responses), last_backend_response_metadata=last_safe,
                    last_backend_metadata_not_role_acceptance=True, failed=self.failed)

    def close(self):
        return self.journal.close()


class AuditedOpener:
    """Delegate original NoRedirect opener; never read headers/data or retain requests."""
    def __init__(self, inner, ledger, base_url):
        self.inner, self.ledger, self.base_url = inner, ledger, base_url

    def open(self, request, *, timeout):
        method, url = request.get_method(), request.full_url
        if method == 'GET' and url == self.base_url + '/models':
            kind = 'models'
        elif method == 'POST' and url == self.base_url + '/chat/completions':
            kind = 'completion'
        else:
            self.ledger.failed = True
            raise ValueError('Only original authenticated models or task completion endpoint')
        self.ledger.transport[kind + '_attempts'] += 1
        try:
            answer = self.inner.open(request, timeout=timeout)
            self.ledger.transport[kind + '_headers_returned'] += 1
            return answer
        except BaseException as error:
            self.ledger.transport_errors.append(type(error).__name__)
            self.ledger.failed = True
            raise


def construct_original_backend(module, profile, ledger):
    import urllib.request
    ledger._check()
    if ledger.constructor_attempts:
        raise ValueError('One original backend constructor; no replacement')
    ledger.constructor_attempts += 1
    start = time.monotonic()
    try:
        opener = AuditedOpener(urllib.request.build_opener(module._NoRedirect()), ledger, module.DeepSeekBackend.BASE)
        # In-memory original environment ingress; no read of credential files here.
        # Do not set expected_response_model on D: retain its genuine first response
        # usage BEFORE ledger rejects a cross-arm served-model mismatch.
        backend = module.DeepSeekBackend(model=profile['model'], max_calls=100,
            max_tokens=8192, max_total_tokens=900000, opener=opener)
        ledger.constructor_completed += 1
        return backend
    except BaseException:
        ledger.failed = True
        raise
    finally:
        ledger.constructor_wall_s = time.monotonic() - start
