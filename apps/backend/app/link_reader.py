import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import httpx

MAX_LINK_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 4
ALLOWED_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.description = ""
        self.site_name = ""
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        values = {key.lower(): value or "" for key, value in attrs}
        if tag in {"script", "style", "noscript", "svg", "nav", "footer"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            key = (values.get("property") or values.get("name")).lower()
            if key in {"description", "og:description", "twitter:description"} and not self.description:
                self.description = values.get("content", "")
            if key == "og:site_name" and not self.site_name:
                self.site_name = values.get("content", "")

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "noscript", "svg", "nav", "footer"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str):
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        if not self._skip_depth:
            self.body_parts.append(text)


def extract_page(data: bytes, content_type: str, include_body: bool = True) -> dict[str, str]:
    text = data.decode("utf-8", errors="ignore")
    if content_type == "text/plain":
        cleaned = re.sub(r"\s+", " ", text).strip()
        return {"title": "", "source": "", "description": cleaned[:500], "text": cleaned[:100000]}
    parser = PageParser()
    parser.feed(text)
    body = re.sub(r"\s+", " ", " ".join(parser.body_parts)).strip()
    return {
        "title": " ".join(parser.title_parts).strip()[:250],
        "source": parser.site_name.strip()[:250],
        "description": re.sub(r"\s+", " ", parser.description).strip()[:1000],
        "text": body[:100000] if include_body else " ".join(filter(None, [parser.description, " ".join(parser.title_parts)]))[:5000],
    }


def ensure_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("El enlace debe usar HTTP o HTTPS")
    if parsed.username or parsed.password:
        raise ValueError("El enlace no puede incluir credenciales")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))}
    except socket.gaierror as exc:
        raise ValueError("No se pudo resolver el sitio") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("El enlace apunta a una red no pública")


def read_link(url: str, include_body: bool = True) -> dict[str, str]:
    current = url
    headers = {"User-Agent": "OLIVA-Intelligence/0.2 (+https://ia.grupooliva.uy)"}
    with httpx.Client(timeout=10, headers=headers, follow_redirects=False) as client:
        for _ in range(MAX_REDIRECTS + 1):
            ensure_public_url(current)
            with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirección sin destino")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if content_type not in ALLOWED_TYPES:
                    raise ValueError("El sitio no devolvió texto legible")
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_LINK_BYTES:
                        raise ValueError("El artículo supera el límite de lectura")
                    chunks.append(chunk)
                result = extract_page(b"".join(chunks), content_type, include_body)
                result["final_url"] = current
                return result
    raise ValueError("El enlace tiene demasiadas redirecciones")
