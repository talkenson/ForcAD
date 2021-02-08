import time
from typing import Callable, Optional, Iterable, Any, Dict

import redis

ArgsType = Optional[Iterable[Any]]
KwargsType = Optional[Dict[str, Any]]


def cache_helper(
        pipeline: redis.client.Pipeline,
        cache_key: str,
        cache_func: Callable[..., Any],
        cache_args: ArgsType = None,
        cache_kwargs: KwargsType = None,
):
    if cache_args is None:
        cache_args = tuple()
    if cache_kwargs is None:
        cache_kwargs = dict()

    was_changed = False
    while True:
        try:
            pipeline.watch(cache_key)
            cached = pipeline.exists(cache_key)
            current_round = pipeline.get('round')

            pipeline.multi()

            if not cached:
                was_changed = True
                cache_func(*cache_args, **cache_kwargs)

            pipeline.execute()
        except redis.WatchError:
            time.sleep(0.05)
        else:
            break

    return was_changed
