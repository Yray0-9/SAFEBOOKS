import uuid

from django.db import models

from .user_model import BookkeeperAccount


class ProofMetadataManager(models.Manager):
    def get_queryset(self):
        # Queue, status, and approval reads must never load document contents.
        return super().get_queryset().defer("content")


class BookkeeperProof(models.Model):
    bookkeeper = models.OneToOneField(BookkeeperAccount, on_delete=models.CASCADE, related_name="verification_proof")
    revision = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    document_type = models.CharField(max_length=24, choices=[
        ("business_permit", "Business Permit"), ("tesda_certificate", "TESDA Certificate"), ("other", "Other"),
    ])
    document_name = models.CharField(max_length=120, blank=True, default="")
    media_type = models.CharField(max_length=32)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    # Private database storage: no media URL, public file, or filesystem orphan on rollback.
    content = models.BinaryField(editable=False)
    submitted_at = models.DateTimeField(auto_now=True)

    objects = ProofMetadataManager()

    class Meta:
        db_table = "bookkeeper_verification_proofs"
        constraints = [models.CheckConstraint(condition=models.Q(size__gt=0, size__lte=5 * 1024 * 1024), name="bk_proof_size_limit")]
