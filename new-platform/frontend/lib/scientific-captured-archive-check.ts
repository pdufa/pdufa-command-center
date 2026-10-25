/** Read-only exact-trial captured-byte provenance diagnostic.
 * Matching two SHA-256 values never establishes authorship, FDA decision,
 * valid clinical evidence or independent scientific review.
 */
export type CapturedSourceDigestManifest = {
  nctId: string;
  sourceDocumentCount: number;
  allCapturedBytesRehashed: true;
  independentSourceVerificationCompleted: false;
  scientificScore: null;
  fdaApprovalProbability: null;
  documents: {
    documentId: string;
    gateId: string;
    sourceType: string;
    sha256: string;
    byteLength: number;
    captureStatus: "byte_integrity_checked_unverified";
    scientificVerificationComplete: false;
  }[];
};

export type CapturedArchiveComparison = {
  nctId: "NCT02142738";
  status: "MATCHES_CAPTURED_BYTES_ONLY" | "NO_CAPTURED_BYTE_MATCH" | "NO_ARCHIVED_PDFS";
  capturedSnapshotCount: number;
  matches: { documentId: string; gateId: string; sourceType: string }[];
  sourceAuthorshipIndependentlyAuthenticated: false;
  reviewerIdentitiesAuthenticated: false;
  clinicalReviewCompleted: false;
  scientificScore: null;
  fdaApprovalProbability: null;
  promotionAllowed: false;
};

const denied = (): never => {
  throw new Error("Captured source verification blocked: unsupported or unverified manifest.");
};

/** Never guess or grant independent verification based on SHA equality alone. */
export function compareLocalPdfWithCapturedArchive(
  nctId: string, pdfSha256: string, pdfByteLength: number, input: unknown,
): CapturedArchiveComparison {
  if (nctId !== "NCT02142738" || !/^[a-f0-9]{64}$/.test(pdfSha256)
      || !Number.isSafeInteger(pdfByteLength) || pdfByteLength < 32
      || pdfByteLength > 25 * 1024 * 1024 || !input
      || typeof input !== "object" || Array.isArray(input)) denied();
  const data = input as Record<string, unknown>;
  if (data.nctId !== nctId || data.allCapturedBytesRehashed !== true
      || data.independentSourceVerificationCompleted !== false
      || data.scientificScore !== null || data.fdaApprovalProbability !== null
      || !Number.isSafeInteger(data.sourceDocumentCount)
      || (data.sourceDocumentCount as number) < 0 || (data.sourceDocumentCount as number) > 8
      || !Array.isArray(data.documents)
      || data.documents.length !== data.sourceDocumentCount) denied();
  const ids = new Set<string>();
  const hashes = new Set<string>();
  const matches: CapturedArchiveComparison["matches"] = [];
  for (const raw of data.documents) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) denied();
    const d = raw as Record<string, unknown>;
    if (typeof d.documentId !== "string" || !/^[a-f0-9]{32}$/.test(d.documentId)
        || ids.has(d.documentId) || typeof d.sha256 !== "string"
        || !/^[a-f0-9]{64}$/.test(d.sha256) || hashes.has(d.sha256)
        || typeof d.gateId !== "string" || !/^[a-z_]{3,32}$/.test(d.gateId)
        || typeof d.sourceType !== "string" || !/^[a-z_]{3,64}$/.test(d.sourceType)
        || !Number.isSafeInteger(d.byteLength)
        || (d.byteLength as number) < 32 || (d.byteLength as number) > 5 * 1024 * 1024
        || d.captureStatus !== "byte_integrity_checked_unverified"
        || d.scientificVerificationComplete !== false) denied();
    ids.add(d.documentId);
    hashes.add(d.sha256);
    if (d.sha256 === pdfSha256 && d.byteLength === pdfByteLength) {
      matches.push({
        documentId: d.documentId, gateId: d.gateId, sourceType: d.sourceType,
      });
    }
  }
  return {
    nctId: "NCT02142738",
    status: data.sourceDocumentCount === 0 ? "NO_ARCHIVED_PDFS"
      : matches.length > 0 ? "MATCHES_CAPTURED_BYTES_ONLY" : "NO_CAPTURED_BYTE_MATCH",
    capturedSnapshotCount: data.sourceDocumentCount as number,
    matches,
    sourceAuthorshipIndependentlyAuthenticated: false,
    reviewerIdentitiesAuthenticated: false,
    clinicalReviewCompleted: false,
    scientificScore: null,
    fdaApprovalProbability: null,
    promotionAllowed: false,
  };
}
