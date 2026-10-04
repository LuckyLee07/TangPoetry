"""Read-only verification of a complete, listened-to volume-2 narration release.

This module has no synthesis, credential or staging dependencies. Availability
is derived from the published files and current expected reader inputs, never
from a stored catalog flag or its pre-activation catalog SHA.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

try:
    from .narration_recipe import AZURE_RECIPE, input_hash, poetry_ssml
except ImportError:
    from narration_recipe import AZURE_RECIPE, input_hash, poetry_ssml

RELEASE_DIR = 'assets/volume-2/audio/xiaoxiao-poetry-v1'
MANIFEST_FILE = 'data/audio-volume-2/manifest.json'
LISTENING_REVIEW_FILE = 'data/audio-volume-2/listening-review.json'
PRODUCTION_FILE = 'data/expansion/tang-second-volume/production.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def approved_listening_row(row, track):
    if not isinstance(row, dict) or not isinstance(track, dict):
        return False
    if (row.get('status') != 'approved-after-listening'
            or not isinstance(row.get('reviewedBy'), str) or not row['reviewedBy'].strip()
            or not isinstance(row.get('reviewedAt'), str)):
        return False
    try:
        when = datetime.fromisoformat(row['reviewedAt'].replace('Z', '+00:00'))
    except ValueError:
        return False
    if when.tzinfo is None:
        return False
    for field, track_field in [('inputSHA256', 'inputSHA256'), ('audioSHA256', 'sha256')]:
        fingerprint = track.get(track_field)
        if not isinstance(fingerprint, str) or not re.fullmatch(r'[0-9a-f]{64}', fingerprint):
            return False
        if row.get(field) != fingerprint:
            return False
    return True


def validate_volume2_manifest(root, catalog, details, manifest):
    """Validate a candidate manifest before publishing its atomic pointer."""
    root = Path(root)
    try:
        if not isinstance(catalog, dict) or not isinstance(manifest, dict):
            raise ValueError('Expected catalog and published manifest must be objects')
        entries = catalog['poems']
        identities = [p['id'] for p in entries]
        expected = set(identities)
        if (catalog.get('volume') != 'volume-2' or len(identities) != 305 or len(expected) != 305
                or not all(re.fullmatch(r'[a-z0-9][a-z0-9-]*', identity) for identity in identities)
                or not all(type(p.get('order')) is int for p in entries)
                or {p['order'] for p in entries} != set(range(1, 306))
                or not isinstance(details, dict) or set(details) != expected):
            raise ValueError('Expected catalog/details do not cover the 305 distinct volume-2 identities and orders')
        if (manifest.get('schemaVersion') != 1 or manifest.get('volume') != 'volume-2'
                or manifest.get('release') != 'full' or manifest.get('recipe') != AZURE_RECIPE):
            raise ValueError('Published manifest must declare a full volume-2 release with the supported recipe')
        if (not isinstance(manifest.get('tracks'), dict) or set(manifest['tracks']) != expected
                or manifest.get('trackOrder') != identities):
            raise ValueError('Published track coverage or order differs from the 305-poem catalog')
        if manifest.get('productionSHA256') != digest(root / PRODUCTION_FILE):
            raise ValueError('Published productionSHA256 no longer matches the current production')
        if (manifest.get('listeningReviewStatus') != 'complete'
                or manifest.get('listeningReviewFile') != LISTENING_REVIEW_FILE):
            raise ValueError('A complete permanent volume-2 listening proof is required')
        review_path = root / LISTENING_REVIEW_FILE
        if manifest.get('listeningReviewSHA256') != digest(review_path):
            raise ValueError('Permanent listening proof hash differs from the published manifest')
        review = json.loads(review_path.read_text())
        if (not isinstance(review, dict) or review.get('schemaVersion') != 1 or review.get('volume') != 'volume-2'
                or review.get('recipe') != AZURE_RECIPE or not isinstance(review.get('tracks'), dict)
                or set(review['tracks']) != expected):
            raise ValueError('Permanent listening proof does not cover the same 305 identities and recipe')
        for summary in entries:
            identity = summary['id']
            poem = details[identity]
            track = manifest['tracks'][identity]
            if (not isinstance(poem, dict) or not isinstance(track, dict) or poem.get('id') != identity
                    or track.get('id') != identity or track.get('title') != poem['title']
                    or track.get('author') != poem['author'] or track.get('section') != summary['section']):
                raise ValueError(f'Published track identity/title/author/section differs: {identity}')
            if track.get('file') != f'{RELEASE_DIR}/{identity}.mp3':
                raise ValueError(f'Published audio file prefix or filename is not isolated to volume 2: {identity}')
            if track.get('inputSHA256') != input_hash(poem, AZURE_RECIPE):
                raise ValueError(f'Published SSML input hash differs from the current poem: {identity}')
            if track.get('ssmlSHA256') != hashlib.sha256(poetry_ssml(poem).encode()).hexdigest():
                raise ValueError(f'Published SSML hash differs from the current poem: {identity}')
            path = root / track['file']
            if type(track.get('bytes')) is not int or track['bytes'] <= 0 or path.stat().st_size != track['bytes']:
                raise ValueError(f'Published audio bytes differ: {identity}')
            if track.get('sha256') != digest(path):
                raise ValueError(f'Published audio file hash differs: {identity}')
            if not approved_listening_row(review['tracks'][identity], track):
                raise ValueError(f'Permanent listening approval is pending, invalid or stale: {identity}')
        return {'available': True, 'tracks': 305}
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f'Second-volume narration release rejected: {error}') from None


def validate_volume2_release(root, catalog, details):
    """Return unavailable only when no manifest exists; reject invalid releases."""
    path = Path(root) / MANIFEST_FILE
    if not path.exists() and not path.is_symlink():
        return {'available': False, 'tracks': 0}
    try:
        manifest = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise ValueError(f'Second-volume narration release rejected: {error}') from None
    return validate_volume2_manifest(root, catalog, details, manifest)
