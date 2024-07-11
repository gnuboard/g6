import inspect
from typing import List
from fastapi import Request
from slowapi import *
from slowapi.extension import *
from slowapi.errors import RateLimitExceeded
from pathlib import Path


class CustomConfig(Config):
    """.env 파일을 utf-8로 읽기 위한 CustomConfig 클래스"""
    def _read_file(self, file_name: str | Path) -> dict[str, str]:
        file_values: dict[str, str] = {}
        with open(file_name, encoding="utf-8") as input_file:
            for line in input_file.readlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    file_values[key] = value
        return file_values


class LimiterNoWarning(Limiter):
    """
    Limiter 클래스의 __evaluate_limits 메서드에서
    로깅되는 경고 메시지를 출력하지 않도록 오버라이딩하여 사용하는 Limiter 클래스
    """
    def __init__(
        self,
        key_func: Callable[..., str],
        default_limits: List[StrOrCallableStr] = [],
        application_limits: List[StrOrCallableStr] = [],
        headers_enabled: bool = False,
        strategy: Optional[str] = None,
        storage_uri: Optional[str] = None,
        storage_options: Dict[str, str] = {},
        auto_check: bool = True,
        swallow_errors: bool = False,
        in_memory_fallback: List[StrOrCallableStr] = [],
        in_memory_fallback_enabled: bool = False,
        retry_after: Optional[str] = None,
        key_prefix: str = "",
        enabled: bool = True,
        config_filename: Optional[str] = None,
        key_style: Literal["endpoint", "url"] = "url",
    ) -> None:
        """
        Limiter의 생성자를 오버라이딩 하기 위한 __init__ 메서드
        - .env 파일을 utf-8로 인코딩하기 위해 CustomConfig 클래스를 사용
        """
        self.logger = logging.getLogger("slowapi")

        dotenv_file_exists = os.path.isfile(".env")
        self.app_config = CustomConfig(
            ".env"
            if dotenv_file_exists and config_filename is None
            else config_filename
        )

        self.enabled = enabled
        self._default_limits = []
        self._application_limits = []
        self._in_memory_fallback: List[LimitGroup] = []
        self._in_memory_fallback_enabled = (
            in_memory_fallback_enabled or len(in_memory_fallback) > 0
        )
        self._exempt_routes: Set[str] = set()
        self._request_filters: List[Callable[..., bool]] = []
        self._headers_enabled = headers_enabled
        self._header_mapping: Dict[int, str] = {}
        self._retry_after: Optional[str] = retry_after
        self._strategy = strategy
        self._storage_uri = storage_uri
        self._storage_options = storage_options
        self._auto_check = auto_check
        self._swallow_errors = swallow_errors

        self._key_func = key_func
        self._key_prefix = key_prefix
        self._key_style = key_style

        for limit in set(default_limits):
            self._default_limits.extend(
                [
                    LimitGroup(
                        limit, self._key_func, None, False, None, None, None, 1, False
                    )
                ]
            )
        for limit in application_limits:
            self._application_limits.extend(
                [
                    LimitGroup(
                        limit,
                        self._key_func,
                        "global",
                        False,
                        None,
                        None,
                        None,
                        1,
                        False,
                    )
                ]
            )
        for limit in in_memory_fallback:
            self._in_memory_fallback.extend(
                [
                    LimitGroup(
                        limit, self._key_func, None, False, None, None, None, 1, False
                    )
                ]
            )
        self._route_limits: Dict[str, List[Limit]] = {}
        self._dynamic_route_limits: Dict[str, List[LimitGroup]] = {}
        # a flag to note if the storage backend is dead (not available)
        self._storage_dead: bool = False
        self._fallback_limiter = None
        self._Limiter__check_backend_count = 0
        self._Limiter__last_check_backend = time.time()
        self._Limiter__marked_for_limiting: Dict[str, List[Callable]] = {}

        class BlackHoleHandler(logging.StreamHandler):
            def emit(*_):
                return

        self.logger.addHandler(BlackHoleHandler())

        self.enabled = self.get_app_config(C.ENABLED, self.enabled)
        self._swallow_errors = self.get_app_config(
            C.SWALLOW_ERRORS, self._swallow_errors
        )
        self._headers_enabled = self._headers_enabled or self.get_app_config(
            C.HEADERS_ENABLED, False
        )
        self._storage_options.update(self.get_app_config(C.STORAGE_OPTIONS, {}))
        self._storage = storage_from_string(
            self._storage_uri or self.get_app_config(C.STORAGE_URL, "memory://"),
            **self._storage_options,
        )
        strategy = self._strategy or self.get_app_config(C.STRATEGY, "fixed-window")
        if strategy not in STRATEGIES:
            raise ConfigurationError("Invalid rate limiting strategy %s" % strategy)
        self._limiter: RateLimiter = STRATEGIES[strategy](self._storage)
        self._header_mapping.update(
            {
                HEADERS.RESET: self._header_mapping.get(
                    HEADERS.RESET,
                    self.get_app_config(C.HEADER_RESET, "X-RateLimit-Reset"),
                ),
                HEADERS.REMAINING: self._header_mapping.get(
                    HEADERS.REMAINING,
                    self.get_app_config(C.HEADER_REMAINING, "X-RateLimit-Remaining"),
                ),
                HEADERS.LIMIT: self._header_mapping.get(
                    HEADERS.LIMIT,
                    self.get_app_config(C.HEADER_LIMIT, "X-RateLimit-Limit"),
                ),
                HEADERS.RETRY_AFTER: self._header_mapping.get(
                    HEADERS.RETRY_AFTER,
                    self.get_app_config(C.HEADER_RETRY_AFTER, "Retry-After"),
                ),
            }
        )
        self._retry_after = self._retry_after or self.get_app_config(
            C.HEADER_RETRY_AFTER_VALUE
        )
        self._key_prefix = self._key_prefix or self.get_app_config(C.KEY_PREFIX)
        app_limits: Optional[StrOrCallableStr] = self.get_app_config(
            C.APPLICATION_LIMITS, None
        )
        if not self._application_limits and app_limits:
            self._application_limits = [
                LimitGroup(
                    app_limits,
                    self._key_func,
                    "global",
                    False,
                    None,
                    None,
                    None,
                    1,
                    False,
                )
            ]

        conf_limits: Optional[StrOrCallableStr] = self.get_app_config(
            C.DEFAULT_LIMITS, None
        )
        if not self._default_limits and conf_limits:
            self._default_limits = [
                LimitGroup(
                    conf_limits, self._key_func, None, False, None, None, None, 1, False
                )
            ]
        fallback_enabled = self.get_app_config(C.IN_MEMORY_FALLBACK_ENABLED, False)
        fallback_limits: Optional[StrOrCallableStr] = self.get_app_config(
            C.IN_MEMORY_FALLBACK, None
        )
        if not self._in_memory_fallback and fallback_limits:
            self._in_memory_fallback = [
                LimitGroup(
                    fallback_limits,
                    self._key_func,
                    None,
                    False,
                    None,
                    None,
                    None,
                    1,
                    False,
                )
            ]
        if not self._in_memory_fallback_enabled:
            self._in_memory_fallback_enabled = (
                fallback_enabled or len(self._in_memory_fallback) > 0
            )

        if self._in_memory_fallback_enabled:
            self._fallback_storage = MemoryStorage()
            self._fallback_limiter = STRATEGIES[strategy](self._fallback_storage)


    def _Limiter__evaluate_limits(
        self, request: Request, endpoint: str, limits: List[Limit]
    ) -> None:
        failed_limit = None
        limit_for_header = None
        for lim in limits:
            limit_scope = lim.scope or endpoint
            if lim.is_exempt:
                continue
            if lim.methods is not None and request.method.lower() not in lim.methods:
                continue
            if lim.per_method:
                limit_scope += ":%s" % request.method

            if "request" in inspect.signature(lim.key_func).parameters.keys():
                limit_key = lim.key_func(request)
            else:
                limit_key = lim.key_func()

            args = [limit_key, limit_scope]
            if all(args):
                if self._key_prefix:
                    args = [self._key_prefix] + args
                if not limit_for_header or lim.limit < limit_for_header[0]:
                    limit_for_header = (lim.limit, args)

                cost = lim.cost(request) if callable(lim.cost) else lim.cost
                if not self.limiter.hit(lim.limit, *args, cost=cost):
                    failed_limit = lim
                    limit_for_header = (lim.limit, args)
                    break
            else:
                self.logger.error(
                    "Skipping limit: %s. Empty value found in parameters.", lim.limit
                )
                continue
        # keep track of which limit was hit, to be picked up for the response header
        request.state.view_rate_limit = limit_for_header

        if failed_limit:
            raise RateLimitExceeded(failed_limit)