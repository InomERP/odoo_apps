# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Prepare applicant documents for the one-document-per-type rule.

    Runs before the new unique(applicant_id, doc_type) constraint is applied:
      1. Map the retired 'pending' status to the new 'submitted' status.
      2. Remove duplicate documents, keeping the most recent record
         (highest id) per applicant + document type, so the unique
         constraint can be created without error.
    """
    if not version:
        return

    # 1) Migrate retired status value.
    cr.execute(
        "UPDATE univ_applicant_document SET state = 'submitted' "
        "WHERE state = 'pending'"
    )

    # 2) De-duplicate: keep the newest row per (applicant_id, doc_type).
    cr.execute(
        """
        DELETE FROM univ_applicant_document a
        USING univ_applicant_document b
        WHERE a.applicant_id = b.applicant_id
          AND a.doc_type = b.doc_type
          AND a.id < b.id
        """
    )
    _logger.info(
        "inom_university_admission: applicant documents normalised for the "
        "one-document-per-type constraint."
    )
