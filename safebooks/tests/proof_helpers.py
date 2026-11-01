from hashlib import sha256
from io import BytesIO

from PIL import Image

from safebooks.models import BookkeeperProof


def proof_image():
    stream = BytesIO()
    Image.new("RGB", (8, 8), "white").save(stream, "PNG")
    return stream.getvalue()


def create_test_proof(account):
    data = proof_image()
    proof, _ = BookkeeperProof.objects.get_or_create(bookkeeper=account, defaults={
        "document_type": "business_permit", "content": data, "media_type": "image/png",
        "size": len(data), "sha256": sha256(data).hexdigest(),
    })
    return proof
