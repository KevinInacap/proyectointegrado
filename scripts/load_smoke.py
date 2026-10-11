"""Carga local acotada sobre una ruta GET autenticada, sin modificar registros."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.cookiejar import CookieJar
import json
import math
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000/')
    parser.add_argument('--path', default='/api/users/')
    parser.add_argument('--identifier', required=True, help='Correo o RUT de una cuenta local de prueba')
    parser.add_argument('--requests', type=int, default=60)
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    if not (1 <= args.requests <= 500 and 1 <= args.workers <= 20):
        parser.error('Límites: 1–500 solicitudes y 1–20 trabajadores.')
    if not args.base_url.startswith('http://127.0.0.1:'):
        parser.error('Solo se permite el servidor local 127.0.0.1.')
    password = os.getenv('SGR_SMOKE_PASSWORD')
    if not password:
        parser.error('Define SGR_SMOKE_PASSWORD en el entorno local.')

    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    root = urljoin(args.base_url, '/')
    opener.open(root, timeout=10).close()
    csrf = next((cookie.value for cookie in jar if cookie.name == 'csrftoken'), None)
    if not csrf:
        raise RuntimeError('No se obtuvo el token CSRF del formulario local.')
    payload = urlencode({
        'username': args.identifier, 'password': password, 'csrfmiddlewaretoken': csrf,
    }).encode()
    opener.open(Request(root, data=payload, headers={'Referer': root}), timeout=10).close()
    if not any(cookie.name == 'sessionid' for cookie in jar):
        raise RuntimeError('No se inició sesión con la cuenta local de prueba.')
    cookie_header = '; '.join(f'{cookie.name}={cookie.value}' for cookie in jar)
    url = urljoin(args.base_url, args.path)

    def one_request(_):
        start = time.perf_counter()
        try:
            with urlopen(Request(url, headers={
                'Cookie': cookie_header, 'Accept': 'application/json',
            }), timeout=15) as response:
                response.read()
                status = response.status
        except HTTPError as exc:
            status = exc.code
        except (URLError, TimeoutError):
            status = 0
        return status, (time.perf_counter() - start) * 1000

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        samples = list(pool.map(one_request, range(args.requests)))
    duration = time.perf_counter() - started
    latencies = sorted(sample[1] for sample in samples)
    statuses = {}
    for status, _ in samples:
        statuses[str(status)] = statuses.get(str(status), 0) + 1
    print(json.dumps({
        'target': args.path, 'requests': args.requests, 'workers': args.workers,
        'duration_seconds': round(duration, 2), 'requests_per_second': round(args.requests / duration, 2),
        'latency_avg_ms': round(sum(latencies) / len(latencies), 1),
        'latency_p95_ms': round(latencies[math.ceil(.95 * len(latencies)) - 1], 1),
        'statuses': statuses,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
