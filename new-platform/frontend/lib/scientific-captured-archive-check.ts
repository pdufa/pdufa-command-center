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
  const entries = data.documents as unknown[];
  for (const raw of entries) {
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
    // Guards above establish the concrete string types from untrusted input.
    const documentId = d.documentId as string;
    const digest = d.sha256 as string;
    const gateId = d.gateId as string;
    const sourceType = d.sourceType as string;
    ids.add(documentId);
    hashes.add(digest);
    if (digest === pdfSha256 && d.byteLength === pdfByteLength) {
      matches.push({ documentId, gateId, sourceType });
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


/**
 * The four EXTERNAL scientific-evidence gates (not a completed science grade).
 * A captured PDF merely proves integrity of locally archived bytes and cannot
 * satisfy any independent clinical, statistical, safety, or FDA review gate.
 */
export type CapturedScientificGateCoverage = {
  nctId: "NCT02142738";
  sourceDocumentCount: number;
  gatesWithCapturedPdf: number;
  externallyVerifiedGateCount: 0;
  readyForScientificConclusion: false;
  scientificScore: null;
  fdaApprovalProbability: null;
  gates: {
    gateId: "protocol_sap" | "published_results" | "independent_replication" | "official_regulatory";
    label: string;
    capturedPdfCount: number;
    status: "CAPTURED_UNVERIFIED" | "NO_CAPTURED_PDF";
    independentlyVerified: false;
    nextAction: string;
  }[];
};

const GATE_CATALOG = [
  {
    gateId: "protocol_sap",
    label: "Original protocol and statistical analysis plan",
    nextAction: "Authenticate the dated original protocol/SAP, its amendments, endpoint definitions and multiplicity plan independently.",
  },
  {
    gateId: "published_results",
    label: "Complete results publication or clinical study report",
    nextAction: "Authenticate full source results and independently reconcile populations, endpoint estimates, uncertainty, safety and follow-up.",
  },
  {
    gateId: "independent_replication",
    label: "Biological rationale and independent corroboration",
    nextAction: "Independently assess mechanism, contradictory findings and external replication.",
  },
  {
    gateId: "official_regulatory",
    label: "Original FDA or other official regulatory documents",
    nextAction: "Authenticate the regulatory application, indication, decision records, CMC context and relevant dates.",
  },
] as const;

/**
 * Only use after the authenticated proxy's exact-NCT manifest passes its
 * all-bytes-rehashed contract. Validate AGAIN here to reject forged client
 * input; never transform capture counts into reviewer attestations.
 */
export function summarizeCapturedScientificGates(
  nctId: string, manifest: unknown,
): CapturedScientificGateCoverage {
  const diagnostic = compareLocalPdfWithCapturedArchive(nctId, "0".repeat(64), 32, manifest);
  if (diagnostic.promotionAllowed !== false || diagnostic.clinicalReviewCompleted !== false
      || !manifest || typeof manifest !== "object" || Array.isArray(manifest)) denied();

  const raw = manifest as Record<string, unknown>;
  const list = raw.documents as unknown[];
  const counts = new Map<string, number>();
  for (const row of list) {
    if (!row || typeof row !== "object" || Array.isArray(row)) denied();
    const gateId = (row as Record<string, unknown>).gateId;
    if (typeof gateId !== "string" || !GATE_CATALOG.some(gate => gate.gateId === gateId)) {
      denied();
    }
    // The branch above rejects any non-string or non-catalog gate identifier.
    const validatedGateId = gateId as string;
    counts.set(validatedGateId, (counts.get(validatedGateId) ?? 0) + 1);
  }
  const gates = GATE_CATALOG.map(gate => {
    const count = counts.get(gate.gateId) ?? 0;
    return {
      gateId: gate.gateId,
      label: gate.label,
      capturedPdfCount: count,
      status: count > 0 ? "CAPTURED_UNVERIFIED" as const : "NO_CAPTURED_PDF" as const,
      independentlyVerified: false as const,
      nextAction: gate.nextAction,
    };
  });
  if (gates.reduce((sum, gate) => sum + gate.capturedPdfCount, 0)
      !== diagnostic.capturedSnapshotCount) denied();

  return {
    nctId: "NCT02142738",
    sourceDocumentCount: diagnostic.capturedSnapshotCount,
    gatesWithCapturedPdf: gates.filter(gate => gate.capturedPdfCount > 0).length,
    externallyVerifiedGateCount: 0,
    readyForScientificConclusion: false,
    scientificScore: null,
    fdaApprovalProbability: null,
    gates,
  };
}


/**
 * Downloadable inventory for a future qualified, independent source reviewer.
 * It is not digitally signed and is NEVER a scientific result or approval
 * record. Include only the exact-NCT, server-rehashed archive metadata;
 * do not export curator identifiers, URLs, raw PDFs or reviewer claims.
 */
export function buildScientificSourceReviewHandoff(
  nctId: string, manifest: unknown,
): string {
  const coverage = summarizeCapturedScientificGates(nctId, manifest);
  if (coverage.nctId !== "NCT02142738"
      || coverage.externallyVerifiedGateCount !== 0
      || coverage.readyForScientificConclusion !== false
      || coverage.scientificScore !== null
      || coverage.fdaApprovalProbability !== null
      || !manifest || typeof manifest !== "object" || Array.isArray(manifest)) denied();
  const raw = manifest as Record<string, unknown>;
  const documents = (raw.documents as unknown[]).map(item => {
    if (!item || typeof item !== "object" || Array.isArray(item)) denied();
    const record = item as Record<string, unknown>;
    // summarizeCapturedScientificGates already validated every fixed field.
    const documentId = record.documentId as string;
    const sourceType = record.sourceType as string;
    const gateId = record.gateId as typeof coverage.gates[number]["gateId"];
    const sha256 = record.sha256 as string;
    const byteLength = record.byteLength as number;
    if (!coverage.gates.some(g => g.gateId === gateId)
        || !/^[a-f0-9]{32}$/.test(documentId)
        || !/^[a-f0-9]{64}$/.test(sha256)
        || !Number.isSafeInteger(byteLength) || byteLength < 32) denied();
    return {
      documentId,
      gateId,
      sourceType,
      sha256,
      byteLength,
      capturedByteIntegrity: "REHASHED_AT_AUTHENTICATED_ARCHIVE_READ",
      originalPublisherAuthenticated: false,
      sourceContentClinicallyAdjudicated: false,
    };
  });
  documents.sort((a, b) => a.gateId.localeCompare(b.gateId)
    || a.documentId.localeCompare(b.documentId));
  return JSON.stringify({
    schemaVersion: "isolated-science-source-review-handoff-v1",
    nctId: "NCT02142738",
    classification: "UNSIGNED_UNVERIFIED_SOURCE_INVENTORY",
    sourceDocumentCount: coverage.sourceDocumentCount,
    capturedEvidenceCategories: coverage.gatesWithCapturedPdf,
    independentlyVerifiedCategories: 0,
    gateCoverage: coverage.gates.map(g => ({
      gateId: g.gateId,
      label: g.label,
      capturedPdfCount: g.capturedPdfCount,
      status: g.status,
      independentlyVerified: false,
      requiredNextAction: g.nextAction,
    })),
    capturedPdfFingerprints: documents,
    originalSourceAuthenticated: false,
    independentReviewerCredentialsVerified: false,
    independentSignedAdjudicationComplete: false,
    scientificallyReady: false,
    scientificScore: null,
    fdaApprovalProbability: null,
    promotionAllowed: false,
    documentBytesIncluded: false,
    warning: "UNSIGNED DIAGNOSTIC ONLY: a stored SHA-256/byte-length record is not an original publisher signature or clinical review. Independently retrieve dated originals, verify publisher provenance, reconcile full document contents, obtain qualified independent reviewer attestations and resolve contradictions before any scientific conclusion or FDA probability.",
  }, null, 2) + "\n";
}
