import functools
import time


def timeit(func):
    """
    어노테이션으로 사용하며 함수의 실행시간을 확인한다.
    - 예시
    ```
    @timeit
    def example_function():
        time.sleep(2) # 2초간 대기
    ```

    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Function {func.__name__} took {end_time - start_time} seconds to run.")
        return result

    return wrapper
