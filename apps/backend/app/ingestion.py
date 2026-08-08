from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from io import BytesIO
import re
from openai import OpenAI
from .config import get_settings

AUDIO_TYPES = {
    "audio/mpeg", "audio/mp4", "audio/x-m4a", "audio/wav", "audio/x-wav",
    "audio/webm", "audio/mpga", "video/mp4",
}
AUDIO_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}
AUDIO_MAX_SIZE = 25 * 1024 * 1024
EMAIL_MAX_SIZE = 15 * 1024 * 1024


class TextOnlyParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs):
        if tag in {"script", "style", "svg"}: self.skip += 1

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "svg"} and self.skip: self.skip -= 1

    def handle_data(self, data: str):
        if not self.skip and data.strip(): self.parts.append(data.strip())


def html_to_text(value: str) -> str:
    parser = TextOnlyParser(); parser.feed(value)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def extract_email(data: bytes) -> str:
    message = BytesParser(policy=policy.default).parsebytes(data)
    plain_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[str] = []
    for part in message.walk():
        if part.is_multipart(): continue
        filename = part.get_filename()
        if filename:
            attachments.append(filename); continue
        try:
            value = part.get_content()
        except Exception:
            continue
        if part.get_content_type() == "text/plain": plain_parts.append(str(value))
        elif part.get_content_type() == "text/html": html_parts.append(html_to_text(str(value)))
    body = "\n\n".join(plain_parts or html_parts).strip()
    headers = [
        f"ASUNTO: {message.get('subject', '(sin asunto)')}",
        f"DE: {message.get('from', '(no indicado)')}",
        f"PARA: {message.get('to', '(no indicado)')}",
        f"FECHA: {message.get('date', '(no indicada)')}",
    ]
    if attachments: headers.append(f"ADJUNTOS: {', '.join(attachments)}")
    return "\n".join(headers) + f"\n\nCUERPO:\n{body}"


def format_email(subject: str, from_address: str, to_address: str, date: str, content: str) -> str:
    return f"ASUNTO: {subject}\nDE: {from_address or '(no indicado)'}\nPARA: {to_address or '(no indicado)'}\nFECHA: {date or '(no indicada)'}\n\nCUERPO:\n{content.strip()}"


def transcribe_audio(data: bytes, filename: str, content_type: str, context: str = "") -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        return ""
    transcription = OpenAI(api_key=settings.openai_api_key).audio.transcriptions.create(
        model=settings.openai_transcription_model,
        file=(filename, BytesIO(data), content_type),
        prompt=(context.strip() or "Reunión o entrevista de investigación estratégica para OLIVA Publicidad.")[:1000],
    )
    return transcription.text.strip()
