from io import BytesIO
from pathlib import Path
import logging
import warnings

from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

MAX_PROOF_BYTES = 5 * 1024 * 1024
DOCUMENT_TYPES = {"business_permit", "tesda_certificate", "other"}

# Parser diagnostics may contain untrusted document fragments. Report only our
# generic validation error, never third-party parser output in application logs.
logging.getLogger("pypdf").addHandler(logging.NullHandler())
logging.getLogger("pypdf").propagate = False


def validate_proof(upload, document_type, document_name):
    """Validate untrusted bytes, independently of the claimed browser MIME type."""
    if document_type not in DOCUMENT_TYPES:
        raise ValueError("Choose a document type.")
    document_name = str(document_name or "").strip()
    if len(document_name) > 120 or (document_type == "other" and not document_name):
        raise ValueError("Enter a document name of up to 120 characters.")
    if upload is None or not 0 < upload.size <= MAX_PROOF_BYTES:
        raise ValueError("Choose one JPG, PNG or PDF up to 5 MB.")
    data = upload.read(MAX_PROOF_BYTES + 1)
    if not data or len(data) > MAX_PROOF_BYTES:
        raise ValueError("Choose one JPG, PNG or PDF up to 5 MB.")
    suffix = Path(upload.name).suffix.lower()
    try:
        if suffix in {".jpg", ".jpeg", ".png"}:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as image:
                    expected = "PNG" if suffix == ".png" else "JPEG"
                    if image.format != expected or image.width * image.height > 20_000_000 or getattr(image, "n_frames", 1) != 1:
                        raise ValueError()
                    image.verify()
                with Image.open(BytesIO(data)) as image:
                    image.load()
            media_type = "image/png" if suffix == ".png" else "image/jpeg"
        elif suffix == ".pdf" and data.startswith(b"%PDF-"):
            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted or not 1 <= len(reader.pages) <= 20:
                raise ValueError()
            # Proofs need no executable actions, embedded files, or interactive forms.
            blocked = {"/JS", "/JavaScript", "/AA", "/OpenAction", "/Launch", "/EmbeddedFiles", "/RichMedia", "/XFA", "/SubmitForm", "/AcroForm"}
            stack, visited, count = [(reader.trailer, 0)], set(), 0
            while stack:
                obj, depth = stack.pop()
                count += 1
                if count > 5000 or depth > 50:
                    raise ValueError()
                if isinstance(obj, IndirectObject):
                    key = (obj.idnum, obj.generation)
                    if key in visited:
                        continue
                    visited.add(key)
                    obj = obj.get_object()
                if isinstance(obj, DictionaryObject):
                    if blocked.intersection(obj.keys()):
                        raise ValueError()
                    stack.extend((value, depth + 1) for value in obj.values())
                elif isinstance(obj, ArrayObject):
                    stack.extend((value, depth + 1) for value in obj)
            media_type = "application/pdf"
        else:
            raise ValueError()
    except Exception:
        # Never return or log parser errors containing private document data.
        raise ValueError("Use a readable JPG, PNG or PDF. PDFs must have 1–20 pages, no password or interactive content.") from None
    return data, media_type, document_name
