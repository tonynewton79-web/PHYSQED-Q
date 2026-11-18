"""Gate 7: strict external QASMBench circuit admission and frozen upstream source.

The pinned small/ QASMBench files were authored by PNNL, not PHYSQED-Q.
No benchmark-file text is vendored into this repository. On hosted CI,
download each pinned source and verify its *actual Git blob SHA1*.
Eligibility is strict and FAILS CLOSED: 2-4 qubits, final all-qubit
identity-index measurement, and only ten native PHYSQED-Q logical gate
operations. Unsupported files and reasons are preserved in the report,
and NEVER replaced by hand-written synthetic approximations.

Original: https://github.com/pnnl/QASMBench
Ang Li et al., QASMBench, ACM TQC 2022; doi:10.1145/3550488.
NOTE: upstream GitHub API license metadata is NOASSERTION; do not
redistribute corpus sources without auditing the upstream permissions.
"""
from collections import Counter
import hashlib
from pathlib import Path
import urllib.request

UPSTREAM="pnnl/QASMBench"
COMMIT="357b942396d5c2b7cbc1c229c585a6ef5ccaebac"
# Frozen before any benchmark results. Each QASM path is inside
# the independently published QASMBench 'small' benchmark directory.
SOURCE_BLOBS=(
    ("adder_n4", "895cf110c11cc822c7db74110336f88159ca3298"),
    ("basis_change_n3", "5a5e5971efc88ff932d4a47a0b69507c1efd2d04"),
    ("basis_trotter_n4", "fcef28931c452a95988efa7007657ecc7ee574a3"),
    ("bell_n4", "de3f32d4c21145c3efb65d230199a9e326aab8fd"),
    ("cat_state_n4", "394ba7e47b74a8d95f7de27170004220859a4e49"),
    ("deutsch_n2", "dc0ff30f107fa83c7b62e1b1fe01b347193e3741"),
    ("dnn_n2", "31310dcbef5c48cb48b015b65331d8f6cf2644b9"),
    ("fredkin_n3", "e86da24181b826470b4563362d66435909f22d0c"),
    ("grover_n2", "d52ad89fa94aecd0c40357907a4d569e4bbfa40d"),
    ("hs4_n4", "e39b6b1a46ecbb98ebf2766f660f43b75f7d2318"),
    ("inverseqft_n4", "98812f5fed3ea1cad0301dff7346dffbe6b309b8"),
    ("iswap_n2", "653d13a25dc227afd830b79fd08ef329ab65ffaa"),
    ("linearsolver_n3", "f6fae89860cf24e314d3e494a2b48858e2d5280a"),
    ("qaoa_n3", "2c3e0367d459088c6e80e651988960bc56e70f29"),
    ("qft_n4", "c6e6f124eff46718d66669afa55155bc61a6eebc"),
    ("qrng_n4", "684e110174a82ad59786ffdc469cb83edd60a302"),
    ("quantumwalks_n2", "fc8e264b5952b808946715802def7f7a51e54c00"),
    ("teleportation_n3", "b88c71b51cecd5da74dcca4417605469ac4d983f"),
    ("toffoli_n3", "0e77669d15541e66560e1592ce49a67b8546f99f"),
)
SUPPORTED={
    "h":"H","x":"X","z":"Z","s":"S","sdg":"SDG",
    "t":"T","tdg":"TDG","cx":"CNOT","cz":"CZ","swap":"SWAP",
}
MAX_LOGICAL_OPS=200
MAX_SOURCE_BYTES=40000
EXPECTED_N=19


def path_for(name):
    if name not in dict(SOURCE_BLOBS):
        raise ValueError("unlisted upstream QASMBench benchmark")
    return f"small/{name}/{name}.qasm"


def raw_url(name):
    return f"https://raw.githubusercontent.com/{UPSTREAM}/{COMMIT}/{path_for(name)}"


def git_blob_sha(payload):
    return hashlib.sha1(b"blob "+str(len(payload)).encode()+b"\x00"+payload).hexdigest()


def read_source(name, cache):
    path=Path(cache)/f"{name}.qasm"
    if not path.is_file():
        raise RuntimeError(f"frozen upstream QASM not downloaded: {path}")
    payload=path.read_bytes()
    if not payload or len(payload)>MAX_SOURCE_BYTES:
        raise RuntimeError(f"invalid source bytes for {name}")
    expected=dict(SOURCE_BLOBS)[name]
    observed=git_blob_sha(payload)
    if observed!=expected:
        raise RuntimeError(f"external source revision altered: {name} "
                           f"expected {expected}, got {observed}")
    return payload.decode("utf-8-sig")


def acquire_sources(cache):
    """Hosted CI only; explicit hash-pinned public upstream GETs."""
    if len(SOURCE_BLOBS)!=EXPECTED_N or len(set(dict(SOURCE_BLOBS)))!=EXPECTED_N:
        raise RuntimeError("corpus changed")
    folder=Path(cache)
    folder.mkdir(parents=True,exist_ok=True)
    for name,_ in SOURCE_BLOBS:
        url=raw_url(name)
        req=urllib.request.Request(url,headers={
            "User-Agent":"PHYSQED-Q-gate7-external-audit/1"})
        with urllib.request.urlopen(req,timeout=20) as response:
            payload=response.read(MAX_SOURCE_BYTES+1)
        if len(payload)>MAX_SOURCE_BYTES:
            raise RuntimeError("upstream file exceeds bounded source size")
        if git_blob_sha(payload)!=dict(SOURCE_BLOBS)[name]:
            raise RuntimeError("upstream source hash changed: "+name)
        (folder/f"{name}.qasm").write_bytes(payload)


def inspect(name, text, qasm2):
    """Admit unmodified QASMBench instructions only, with explicit refusals."""
    try:
        qc=qasm2.loads(text,strict=True)
    except Exception as exc:
        return {"name":name, "admitted":False,
                "reason":"QASM_PARSE_OR_CLASSICAL_UNSUPPORTED",
                "detail":type(exc).__name__}
    n=qc.num_qubits
    if n<2 or n>4:
        return {"name":name,"admitted":False,"reason":"WIDTH_OUT_OF_SCOPE",
                "qubits":n}
    if len(qc.clbits)!=n:
        return {"name":name,"admitted":False,"reason":"NONFULL_CLASSICAL_REGISTER",
                "qubits":n, "classical_bits":len(qc.clbits)}
    gates=[];measurements={};nonfinal=False;seen_measure=False
    refused=Counter()
    for instruction in qc.data:
        op=instruction.operation.name.lower()
        if op=="barrier":
            continue
        if op=="measure":
            if len(instruction.qubits)!=1 or len(instruction.clbits)!=1:
                refused["MALFORMED_MEASUREMENT"]+=1
                continue
            q=qc.find_bit(instruction.qubits[0]).index
            c=qc.find_bit(instruction.clbits[0]).index
            if c in measurements or q in measurements.values():
                refused["DUPLICATE_MEASUREMENT"]+=1
            else:
                measurements[c]=q
            seen_measure=True
            continue
        if seen_measure:
            nonfinal=True
        if op not in SUPPORTED:
            refused["UNSUPPORTED_GATE:"+op]+=1
            continue
        if len(instruction.clbits):
            refused["CLASSICAL_CONDITION"]+=1
            continue
        gate={"gate":SUPPORTED[op],
              "qubits":[qc.find_bit(q).index for q in instruction.qubits]}
        gates.append(gate)
    if not measurements or len(measurements)!=n:
        refused["MISSING_ALL_QUBIT_MEASUREMENT"]+=1
    if measurements and any(measurements.get(i)!=i for i in range(n)):
        refused["OUTPUT_CLASSICAL_ORDER_NOT_IDENTITY"]+=1
    if nonfinal:
        refused["MIDCIRCUIT_MEASUREMENT"]+=1
    if len(gates)>MAX_LOGICAL_OPS:
        refused["MAX_GATE_BUDGET"]+=1
    if refused:
        return {"name":name,"admitted":False,
                "reason":"STRICT_SCOPE_REFUSED",
                "qubits":n,
                "raw_instruction_count":len(qc.data),
                "supported_gate_count":len(gates),
                "refusals":dict(sorted(refused.items()))}
    return {"name":name,"admitted":True,"qubits":n,
            "raw_instruction_count":len(qc.data),
            "logical":{"name":"external-"+name,
                       "qubits":n, "gates":gates}}


def manifest():
    return {"source":"PNNL QASMBench independent published corpus",
            "source_repository":UPSTREAM,"upstream_commit":COMMIT,
            "declared_19_files":[{"path":path_for(name),"git_blob_sha1":sha}
                                 for name,sha in SOURCE_BLOBS],
            "source_file_count":EXPECTED_N,
            "repo_corpus_relicensed_or_redistributed":False,
            "max_qubits":4,"gate_budget":MAX_LOGICAL_OPS,
            "supported_input_gate_names":sorted(SUPPORTED),
            "model_evidence_not_real_hardware":True}
