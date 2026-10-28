"""Prove a stored companion atlas against its original iOS manifest record.

This predicate edits at most one known texture_formats descriptor. It does not
convert pixels, serialize XML, infer hashes, perform network I/O or write assets.
"""
import hashlib

from scripts.trace_asset_transport import verify_stored

DESCRIPTORS = (
    b'.ptc.pvr .atc.dds .dxt.dds .etc.dds',
    b'.atc.dds', b'.etc.dds', b'.etc.pvr',
)


def descriptor_variants(source):
    """Yield unchanged bytes and, if present, one exact known field replacement."""
    yield 'unchanged', source
    if source.count(b'texture_formats=') != 1:
        return
    for descriptor in DESCRIPTORS:
        token = b'texture_formats="' + descriptor + b'"'
        if source.count(token) == 1:
            yield ('texture_formats: ' + descriptor.decode('ascii') + ' -> .ptc.pvr',
                   source.replace(token, b'texture_formats=".ptc.pvr"', 1))


def prove_companion(source, expected):
    """Return exact stored iOS bytes plus proof, or reject every allowed variant.

    A known descriptor is a candidate-generation rule, never acceptance evidence.
    Both stored length and reconstructed FMASZ1 transport length/MD5 must match.
    """
    for transform, stored in descriptor_variants(source):
        try:
            proof = verify_stored(stored, expected)
        except ValueError:
            continue
        return stored, {
            **proof,
            'source_stored_bytes': len(source),
            'source_stored_md5': hashlib.md5(source).hexdigest(),
            'source_stored_sha256': hashlib.sha256(source).hexdigest(),
            'stored_bytes_edited': stored != source,
            'stored_transform': transform,
            'transport_transform': 'FMASZ1 + zlib.compress(stored, 6)',
        }
    raise ValueError('No allowed descriptor variant exactly matches the iOS manifest')
