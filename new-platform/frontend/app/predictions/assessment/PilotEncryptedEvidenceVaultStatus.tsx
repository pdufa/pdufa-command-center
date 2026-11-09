export default function PilotEncryptedEvidenceVaultStatus({nct}:{nct:string}){
  if(nct!=="NCT06081894")return null;
  const frame={border:"1px solid #d1b98c",borderRadius:12,padding:14,
    margin:"12px 0",background:"#fffaf0"} as const;
  return <section aria-label="Encrypted original evidence vault installation status" style={frame}>
    <h3 style={{margin:"0 0 8px"}}>Encrypted original-document vault · staging readiness</h3>
    <p style={{fontSize:13,margin:"5px 0 10px"}}>
      <strong>STAGED IN BACKEND CODE — NOT ACTIVATED.</strong> An isolated PostgreSQL
      encrypted store has been implemented and tested for public, authorized original documents.
      It checks the actual file&apos;s SHA-256 before AES-256-GCM encryption, retains
      unique source versions and linked append-only receipts, and has separate reader/writer
      credential gates. It is <strong>not connected to this browser or storing documents yet</strong>.
    </p>
    <p style={{fontSize:12,margin:"10px 0",padding:9,background:"#fff",border:"1px solid #bdd4c8",borderRadius:8}}>
      <strong>Disposable PostgreSQL 16 acceptance: PASSED.</strong> Actual PostgreSQL
      encryption, original-byte SHA-256, append-only UPDATE/DELETE/TRUNCATE rejection,
      duplicate-version safeguards and an <strong>offline synthetic key-recovery drill</strong>
      passed in a temporary GitHub Actions database.{" "}
      <a href="https://github.com/pdufa/pdufa-command-center/actions/runs/42562929833"
        target="_blank" rel="noopener noreferrer">View audited test run</a>.
      This was not a deployment, offsite key backup, or test against the real Render database.
    </p>
    <details style={{border:"1px solid #ddceb2",background:"#fff",padding:10,borderRadius:9}}>
      <summary style={{cursor:"pointer",fontWeight:750,fontSize:13}}>
        Show storage activation and independent-review requirements
      </summary>
      <ol style={{fontSize:12,paddingLeft:20}}>
        <li>Disposable PostgreSQL 16 tests passed. Still verify the isolated Render backend uses durable PostgreSQL and test the additive vault schema on an authorized separate preview database.</li>
        <li>Provision a separate 256-bit encryption key and two distinct reader/writer access secrets. No keys are stored in the source repository.</li>
        <li>Manually authorize and deploy the isolated Render service. The vault is off by default and has no public dashboard upload proxy.</li>
        <li>Verify the original public source bytes, SHA-256, trial identity, exact document rights, document version and uploader. Public, authorized files only; no patient-level or confidential records.</li>
        <li>The synthetic immutable receipt and offline key-recovery drills passed. Still establish independent real-key backups, tested recovery ownership, document malware controls, and qualified clinical review before scoring.</li>
      </ol>
    </details>
    <p style={{fontSize:12,margin:"9px 0 0"}}>
      <strong>Object storage limitation:</strong> the existing Neon project&apos;s AWS west-2 region
      does not support Neon branchable object storage. The staged alternative is an
      encrypted, size-limited PostgreSQL BYTEA vault, <strong>not a deployed Neon storage bucket</strong>.
    </p>
    <p style={{fontSize:12,margin:"8px 0 0"}}>
      Current vault status: <strong>NOT ACTIVE</strong> · Original documents deposited:
      <strong> 0</strong> · Independently authorized scientific grades:
      <strong> 0/800</strong> · FDA prediction: <strong>ABSTAIN</strong>.
    </p>
  </section>;
}
