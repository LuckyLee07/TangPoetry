#!/usr/bin/env python3
"""Offline checks for volume-2 preparation, freshness and listening release gates.

All writes and simulated audio stay in temporary directories. No credentials
are loaded, no network is used and no MP3 is synthesized. Run:
python3 -B -m unittest discover -s tests -p 'volume2_audio_test.py'
"""
from concurrent.futures import ThreadPoolExecutor, wait as wait_for_all
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
import builtins
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import generate_azure_audio as shared_pipeline
# The CLI configures shared pipeline globals at import. Restore them so this
# discovered test module cannot change the first-volume tests' defaults.
with patch.object(shared_pipeline, 'STAGE', shared_pipeline.STAGE), \
        patch.object(shared_pipeline, 'RELEASE_DIR', shared_pipeline.RELEASE_DIR):
    import generate_volume2_audio as audio
from narration_recipe import NS, poetry_ssml, poetry_ssml_chunks
from volume2_narration_release import LISTENING_REVIEW_FILE, validate_volume2_release


class Volume2AudioPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='volume2-audio-tests-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.base = self.root / 'data/expansion/tang-second-volume'
        self.base.mkdir(parents=True)
        for name in ['production.json', 'poems.json', 'display-metadata.json',
                     'display-glyphs.json', 'delivery-assets.json']:
            shutil.copy2(ROOT / 'data/expansion/tang-second-volume' / name, self.base / name)
        shutil.copytree(ROOT / 'data/reader-volume-2', self.root / 'data/reader-volume-2')
        self.stage = self.root / 'output/audio-azure-volume-2'
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for target, attr, value in [
            (audio, 'ROOT', self.root),
            (audio, 'CATALOG', self.root / 'data/reader-volume-2/catalog.json'),
            (audio, 'STAGE', self.stage),
            (audio, 'MANIFEST', self.root / 'data/audio-volume-2/manifest.json'),
            (audio.reader_builder, 'BASE', self.base),
            (audio.reader_builder, 'ROOT', self.root),
            (audio.pipeline, 'STAGE', self.stage),
            (audio.pipeline, 'RELEASE_DIR', audio.RELEASE),
        ]:
            self.stack.enter_context(patch.object(target, attr, value))
        self.poems = audio.load()

    def mutate(self, path, change):
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value, ensure_ascii=False) + '\n')

    def records(self):
        """Non-MP3 byte fixtures; never submit these to a decoder or service."""
        (self.stage / 'audio').mkdir(parents=True, exist_ok=True)
        (self.stage / 'ssml').mkdir(exist_ok=True)
        records = {}
        for poem in self.poems:
            path = self.stage / 'audio' / f"{poem['id']}.mp3"
            path.write_bytes(('isolated-non-audio-test-fixture:' + poem['id']).encode())
            (self.stage / 'ssml' / f"{poem['id']}.ssml").write_text(poetry_ssml(poem))
            records[poem['id']] = audio.pipeline.record(poem, path, 200)
        audio.save(self.poems, records)
        return records

    def reviews(self, records):
        review = audio.prepare_listening_review(self.poems, records)
        for identity, row in review['tracks'].items():
            row.update(status='approved-after-listening', reviewedBy='isolated-test-fixture',
                       reviewedAt='2026-10-04T18:00:00+08:00',
                       notes='Simulated test record; never a production listening approval.')
        audio.atomic_json(self.stage / 'listening-review.json', review)
        return review

    @contextmanager
    def generation_cli(self, renderer, poems=None, options=None):
        """Run the actual CLI with only fake bytes, fake credentials and mocked networking."""
        import prepare_recitation_variants as variants
        poems = self.poems[:4] if poems is None else poems
        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, 'argv', [audio.__file__, '--generate', '--jobs', '1', *(options or [])]))
            stack.enter_context(patch.object(audio, 'load', return_value=poems))
            stack.enter_context(patch.object(variants, 'OUT', self.root / 'output/tts-trial/recitation'))
            voice = stack.enter_context(patch.object(variants, 'verify_voice_styles'))
            env = stack.enter_context(patch.object(audio, 'azure_config', return_value=('isolated-no-network-fixture', 'eastasia')))
            prompt = stack.enter_context(patch.object(audio, 'prompt_azure_config', return_value=('isolated-no-network-fixture', 'eastasia')))
            stack.enter_context(patch('prepare_narration_trial.urlopen', side_effect=AssertionError('Network call')))
            stack.enter_context(patch.object(audio.pipeline, 'synthesize_with_retry', side_effect=renderer))
            stack.enter_context(patch.object(audio.pipeline, 'audit', return_value={'tracks': len(poems)}))
            stack.enter_context(redirect_stdout(io.StringIO()))
            yield {'voice': voice, 'env': env, 'prompt': prompt}

    def simulated_audio(self, ssml, target, credentials, pacer):
        target.write_bytes(('isolated-non-audio-test-fixture:' + target.stem).encode())
        return 200

    def test_reader_data_import_and_catalog_build_do_not_require_pillow(self):
        original_import = builtins.__import__
        def no_pillow(name, *args, **kwargs):
            if name == 'PIL' or name.startswith('PIL.'):
                raise AssertionError('Reader data preparation imported Pillow')
            return original_import(name, *args, **kwargs)
        spec = importlib.util.spec_from_file_location('isolated_reader_without_pillow', ROOT / 'scripts/build_volume2_reader.py')
        module = importlib.util.module_from_spec(spec)
        with patch.object(builtins, '__import__', no_pillow):
            spec.loader.exec_module(module)
            module.ROOT, module.BASE = self.root, self.base
            catalog, details = module.reader_entries(
                json.loads((self.base / 'production.json').read_text()),
                json.loads((self.base / 'poems.json').read_text()),
                json.loads((self.base / 'delivery-assets.json').read_text()))
        self.assertEqual((len(catalog['poems']), len(details)), (305, 305))

    def test_prompt_key_requires_generation_without_loading_credentials(self):
        with patch.object(sys, 'argv', [audio.__file__, '--prompt-key']), \
                patch.object(audio, 'load') as load, \
                patch.object(audio, 'azure_config') as env, \
                patch.object(audio, 'prompt_azure_config') as prompt, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as rejected:
                audio.main()
        self.assertEqual(rejected.exception.code, 2)
        for mock in [load, env, prompt]:
            mock.assert_not_called()

    def test_prompt_region_and_env_routes_check_cache_presence(self):
        for options, cache_exists, region in [(['--prompt-key'], False, 'eastasia'),
                                             (['--prompt-key', '--region', 'westus'], False, 'westus'),
                                             ([], True, None)]:
            with self.subTest(options=options):
                shutil.rmtree(self.stage, ignore_errors=True)
                cache = self.root / 'output/tts-trial/recitation/voice-support.json'
                if cache_exists:
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    cache.write_text('{}')
                else:
                    shutil.rmtree(cache.parent, ignore_errors=True)
                with self.generation_cli(self.simulated_audio, poems=self.poems[:2], options=options) as mocks:
                    audio.main()
                self.assertTrue(cache.parent.is_dir())
                mocks['voice'].assert_called_once_with(('isolated-no-network-fixture', 'eastasia'), reuse=cache_exists)
                if region:
                    mocks['prompt'].assert_called_once_with(region)
                    mocks['env'].assert_not_called()
                else:
                    mocks['env'].assert_called_once_with()
                    mocks['prompt'].assert_not_called()

    def test_fatal_http_and_local_failures_stop_unstarted_jobs_and_save_progress(self):
        failures = [audio.AzureHTTPError(401, 'isolated HTTP 401'), audio.AzureHTTPError(403, 'isolated HTTP 403'),
                    subprocess.CalledProcessError(1, ['isolated-ffmpeg']), ValueError('isolated probe failure')]
        for error in failures:
            with self.subTest(error=type(error).__name__, message=str(error)):
                shutil.rmtree(self.stage, ignore_errors=True)
                calls = []
                def failed(ssml, target, credentials, pacer):
                    calls.append(target.stem)
                    raise error
                with self.generation_cli(failed):
                    with self.assertRaises(type(error)) as rejected:
                        audio.main()
                self.assertIs(rejected.exception, error)
                self.assertEqual(calls, [self.poems[0]['id']])
                self.assertEqual(json.loads((self.stage / 'manifest.json').read_text())['tracks'], {})
                self.assertEqual(json.loads((self.stage / 'failures.json').read_text()),
                                 [{'id': self.poems[0]['id'], 'error': str(error)}])
                plan = json.loads((self.stage / 'plan.json').read_text())
                self.assertEqual((plan['readyTracks'], plan['pendingTracks']), (0, 4))

    def test_running_success_after_fatal_is_saved_and_reused_on_resume(self):
        second_started, release_second = threading.Event(), threading.Event()
        calls = []
        error = ValueError('isolated first-track failure')
        first, second = self.poems[:2]
        class ReleaseRunningWorker(ThreadPoolExecutor):
            def shutdown(self, *args, **kwargs):
                release_second.set()
                return super().shutdown(*args, **kwargs)
        def rendered(ssml, target, credentials, pacer):
            calls.append(target.stem)
            if target.stem == first['id']:
                if not second_started.wait(2):
                    raise AssertionError('Second worker did not start')
                raise error
            second_started.set()
            if not release_second.wait(2):
                raise AssertionError('Fatal cleanup did not release the running worker')
            return self.simulated_audio(ssml, target, credentials, pacer)
        with self.generation_cli(rendered, options=['--jobs', '2']), \
                patch.object(audio, 'ThreadPoolExecutor', ReleaseRunningWorker):
            with self.assertRaises(ValueError) as rejected:
                audio.main()
        self.assertIs(rejected.exception, error)
        self.assertEqual(set(calls), {first['id'], second['id']})
        staged = json.loads((self.stage / 'manifest.json').read_text())
        self.assertEqual(set(staged['tracks']), {second['id']})
        self.assertTrue(audio.pipeline.valid_record(second, staged['tracks'][second['id']],
                                                  self.stage / 'audio' / f'{second["id"]}.mp3'))
        self.assertEqual(json.loads((self.stage / 'plan.json').read_text())['readyTracks'], 1)
        resumed = []
        def continued(ssml, target, credentials, pacer):
            resumed.append(target.stem)
            return self.simulated_audio(ssml, target, credentials, pacer)
        with self.generation_cli(continued):
            audio.main()
        self.assertEqual(set(resumed), {p['id'] for p in self.poems[:4]} - {second['id']})
        self.assertEqual(json.loads((self.stage / 'plan.json').read_text())['readyTracks'], 4)

    def test_success_and_fatal_in_same_completed_batch_cannot_refill_queue(self):
        calls = []
        first = self.poems[0]
        def rendered(ssml, target, credentials, pacer):
            calls.append(target.stem)
            if target.stem == first['id']:
                raise ValueError('isolated completed-batch failure')
            return self.simulated_audio(ssml, target, credentials, pacer)
        def success_first(futures, return_when):
            done, pending = wait_for_all(futures)
            return sorted(done, key=lambda future: future.exception() is not None), pending
        with self.generation_cli(rendered, options=['--jobs', '2']), patch.object(audio, 'wait', side_effect=success_first):
            with self.assertRaisesRegex(ValueError, 'completed-batch failure'):
                audio.main()
        self.assertEqual(set(calls), {p['id'] for p in self.poems[:2]})
        self.assertEqual(set(json.loads((self.stage / 'manifest.json').read_text())['tracks']), {self.poems[1]['id']})

    def curl_fixture(self, exit_code=0, http_code=200):
        """Inspect a fake curl invocation; never run a process or send a key."""
        key = 'isolated-secret-fixture-never-a-real-key'
        parent = self.root / 'isolated-curl-tests'
        parent.mkdir(exist_ok=True)
        target = parent / 'fixture.mp3'
        target.write_bytes(b'previous-valid-file-sentinel')
        ssml = poetry_ssml(self.poems[0])
        def run(command, **options):
            self.assertEqual(command[:2], ['/usr/bin/curl', '-q'])
            self.assertNotIn(key, ' '.join(command))
            self.assertIn('--http2', command)
            self.assertIn('--cacert', command)
            self.assertNotIn('--insecure', command)
            self.assertEqual(command[command.index('--max-time') + 1], '120')
            self.assertGreaterEqual(options['timeout'], 120)
            self.assertEqual(options['env'], {'PATH': '/usr/bin:/bin'})
            self.assertEqual(options['input'], f'header = "Ocp-Apim-Subscription-Key: {key}"\n'.encode())
            self.assertEqual(options['stdout'], subprocess.PIPE)
            self.assertEqual(options['stderr'], subprocess.PIPE)
            draft = Path(command[command.index('--data-binary') + 1][1:])
            raw = Path(command[command.index('--output') + 1])
            self.assertEqual(draft.read_text(), ssml)
            self.assertNotIn(key.encode(), draft.read_bytes())
            raw.write_bytes(b'isolated-non-audio-response-or-partial')
            self.assertNotIn(key.encode(), raw.read_bytes())
            return subprocess.CompletedProcess(command, exit_code, stdout=str(http_code).encode(),
                                               stderr=(key + ': malicious diagnostic fixture').encode())
        return key, parent, target, ssml, run

    def test_curl_success_keeps_key_only_on_stdin_and_normalizes_after_http200(self):
        key, parent, target, ssml, run = self.curl_fixture()
        def normalize(raw, final):
            self.assertEqual(raw.read_bytes(), b'isolated-non-audio-response-or-partial')
            final.write_bytes(b'isolated-normalized-audio-fixture')
            return 123.456
        with patch.object(audio.os, 'environ', {'PATH': '/usr/bin:/bin', 'SPEECH_KEY': key, 'SPEECH_REGION': 'eastasia'}), \
                patch.object(audio.subprocess, 'run', side_effect=run) as process, \
                patch.object(audio.pipeline, 'normalize_audio', side_effect=normalize) as normalized:
            duration = audio.synthesize_curl_ssml(ssml, target, (key, 'eastasia'))
        self.assertEqual(duration, 123.456)
        process.assert_called_once()
        normalized.assert_called_once()
        self.assertEqual(target.read_bytes(), b'isolated-normalized-audio-fixture')
        self.assertEqual(list(parent.iterdir()), [target])
        self.assertNotIn(key.encode(), target.read_bytes())

    def test_curl_http401_and_partial_exit18_preserve_target_and_discard_temp(self):
        for exit_code, http_code, error_type in [(0, 401, audio.AzureHTTPError), (18, 200, audio.AzureTransportError)]:
            with self.subTest(exit_code=exit_code, http_code=http_code):
                key, parent, target, ssml, run = self.curl_fixture(exit_code, http_code)
                output = io.StringIO()
                with patch.object(audio.os, 'environ', {'PATH': '/usr/bin:/bin', 'SPEECH_KEY': key, 'SPEECH_REGION': 'eastasia'}), \
                        patch.object(audio.subprocess, 'run', side_effect=run), \
                        patch.object(audio.pipeline, 'normalize_audio') as normalized, \
                        patch.object(audio.pipeline, 'probe') as probe, redirect_stdout(output), redirect_stderr(output):
                    with self.assertRaises(error_type) as rejected:
                        audio.synthesize_curl_ssml(ssml, target, (key, 'eastasia'))
                normalized.assert_not_called()
                probe.assert_not_called()
                if http_code == 401:
                    self.assertEqual(rejected.exception.status, 401)
                self.assertNotIn(key, str(rejected.exception))
                self.assertEqual(output.getvalue(), '')
                self.assertEqual(target.read_bytes(), b'previous-valid-file-sentinel')
                self.assertEqual(list(parent.iterdir()), [target])

    def test_curl_timeout_never_prints_captured_diagnostics_or_replaces_target(self):
        key, parent, target, ssml, _ = self.curl_fixture()
        failure = subprocess.TimeoutExpired(['/usr/bin/curl'], 130, output=key.encode(), stderr=key.encode())
        with patch.object(audio.subprocess, 'run', side_effect=failure), \
                patch.object(audio.pipeline, 'normalize_audio') as normalized:
            with self.assertRaises(audio.AzureTransportError) as rejected:
                audio.synthesize_curl_ssml(ssml, target, (key, 'eastasia'))
        normalized.assert_not_called()
        self.assertNotIn(key, str(rejected.exception))
        self.assertEqual(target.read_bytes(), b'previous-valid-file-sentinel')
        self.assertEqual(list(parent.iterdir()), [target])

    def test_curl_retries_keep_existing_pacer_schedule_and_http401_is_fatal(self):
        pacer = Mock()
        with patch.object(audio, 'synthesize_curl_ssml', side_effect=[audio.AzureTransportError('isolated curl18'), 200]) as transport, \
                patch.object(audio.pipeline.time, 'sleep') as sleep, redirect_stdout(io.StringIO()):
            duration = audio.synthesize_curl_with_retry('isolated ssml', Path('/isolated/target.mp3'), ('fixture', 'eastasia'), pacer)
        self.assertEqual(duration, 200)
        self.assertEqual(pacer.wait.call_count, 2)
        self.assertEqual(transport.call_count, 2)
        sleep.assert_called_once_with(2)
        pacer.reset_mock()
        with patch.object(audio, 'synthesize_curl_ssml', side_effect=audio.AzureHTTPError(401, 'isolated 401')) as transport, \
                patch.object(audio.pipeline.time, 'sleep') as sleep:
            with self.assertRaises(audio.AzureHTTPError):
                audio.synthesize_curl_with_retry('isolated ssml', Path('/isolated/target.mp3'), ('fixture', 'eastasia'), pacer)
        pacer.wait.assert_called_once_with()
        transport.assert_called_once()
        sleep.assert_not_called()

    def test_cli_curl_selects_only_second_volume_transport(self):
        original_shared_transport = audio.pipeline.synthesize_azure_ssml
        original_shared_retry = audio.pipeline.synthesize_with_retry
        with self.generation_cli(self.simulated_audio, poems=self.poems[:2], options=['--transport', 'curl']), \
                patch.object(audio, 'synthesize_curl_with_retry', side_effect=self.simulated_audio) as curl:
            audio.main()
        self.assertEqual(curl.call_count, 2)
        self.assertIs(audio.pipeline.synthesize_azure_ssml, original_shared_transport)
        self.assertIs(audio.pipeline.synthesize_with_retry, original_shared_retry)

    def test_curl_chunked_uses_same_cache_and_normalizes_once(self):
        poem = self.poems[0]
        target = self.root / 'chunked-fixture.mp3'
        def piece(ssml, path, credentials, pacer, normalize):
            self.assertIs(normalize, False)
            path.write_bytes(b'isolated-curl-chunk-fixture')
            return 10
        def join(command, **options):
            Path(command[-1]).write_bytes(b'isolated-joined-chunks-fixture')
        def normalized(raw, final):
            final.write_bytes(b'isolated-normalized-chunks-fixture')
            return 20
        with patch.object(audio, 'synthesize_curl_with_retry', side_effect=piece) as curl, \
                patch.dict(sys.modules, {'imageio_ffmpeg': SimpleNamespace(get_ffmpeg_exe=Mock(return_value='/isolated-nonexecuted-ffmpeg'))}), \
                patch.object(audio.subprocess, 'run', side_effect=join), \
                patch.object(audio.pipeline, 'normalize_audio', side_effect=normalized) as normalize, redirect_stdout(io.StringIO()):
            audio.synthesize_curl_chunked(poem, target, ('fixture', 'eastasia'), Mock())
            self.assertEqual(curl.call_count, len(poetry_ssml_chunks(poem)))
            normalize.assert_called_once()
            curl.reset_mock()
            audio.synthesize_curl_chunked(poem, target, ('fixture', 'eastasia'), Mock())
            curl.assert_not_called()
        self.assertEqual(target.read_bytes(), b'isolated-normalized-chunks-fixture')

    def test_fresh_snapshot_has_all_305_without_reading_pngs(self):
        original = audio.pipeline.digest
        def json_only(path):
            self.assertEqual(Path(path).suffix, '.json')
            return original(path)
        with patch.object(audio.pipeline, 'digest', side_effect=json_only):
            poems = audio.load()
        self.assertEqual(len(poems), 305)
        self.assertEqual(len({p['id'] for p in poems}), 305)

    def test_production_change_rejects_old_snapshot(self):
        self.mutate(self.base / 'production.json', lambda v: v['poems'][0].update(text='Changed source.'))
        with self.assertRaisesRegex(ValueError, 'production.json'):
            audio.load()

    def test_display_mapping_change_rejects_old_snapshot(self):
        self.mutate(self.base / 'display-glyphs.json', lambda v: v.update(reviewedOn='changed'))
        with self.assertRaisesRegex(ValueError, 'display-glyphs.json'):
            audio.load()

    def test_catalog_change_rejects_old_snapshot(self):
        self.mutate(audio.CATALOG, lambda v: v['poems'][0].update(title='Stale title'))
        with self.assertRaisesRegex(ValueError, 'Reader catalog differs'):
            audio.load()

    def test_individual_verse_change_rejects_old_snapshot(self):
        path = audio.CATALOG.parent / 'poems' / f"{self.poems[-1]['id']}.json"
        self.mutate(path, lambda v: v['rubyLines'][0][0].__setitem__(0, '误'))
        with self.assertRaisesRegex(ValueError, 'Reader detail differs'):
            audio.load()

    def test_dry_run_prepares_305_isolated_ssml_without_secrets_or_network(self):
        class EnvironmentNamesOnly:
            def __iter__(self):
                return iter(['SPEECH_KEY', 'SPEECH_REGION'])
            def __getitem__(self, key):
                if key in ['SPEECH_KEY', 'SPEECH_REGION']:
                    raise AssertionError('Dry run attempted to read a secret environment value')
                raise KeyError(key)
            def get(self, key, default=None):
                if key in ['SPEECH_KEY', 'SPEECH_REGION']:
                    raise AssertionError('Dry run attempted to read a secret environment value')
                return default
        first = self.root / 'data/audio/manifest.json'
        first.parent.mkdir(parents=True)
        first.write_bytes(b'first-volume-sentinel')
        env_file = self.root / '.env.azure-speech.local'
        env_file.write_bytes(b'unreadable-by-test credential-file sentinel')
        original_read = Path.read_text
        def guarded_read(path, *args, **kwargs):
            if path == env_file:
                raise AssertionError('Dry run read the credentials file')
            return original_read(path, *args, **kwargs)
        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, 'argv', [audio.__file__]))
            stack.enter_context(patch.object(audio.os, 'environ', EnvironmentNamesOnly()))
            stack.enter_context(patch.object(Path, 'read_text', guarded_read))
            credentials = stack.enter_context(patch.object(audio, 'azure_config', side_effect=AssertionError('Credentials read')))
            prompt = stack.enter_context(patch.object(audio, 'prompt_azure_config', side_effect=AssertionError('Prompt read')))
            network = stack.enter_context(patch('prepare_narration_trial.urlopen', side_effect=AssertionError('Network call')))
            renderer = stack.enter_context(patch.object(audio.pipeline, 'synthesize_with_retry', side_effect=AssertionError('Synthesis call')))
            chunks = stack.enter_context(patch.object(audio.pipeline, 'synthesize_chunked', side_effect=AssertionError('Synthesis call')))
            output = stack.enter_context(redirect_stdout(io.StringIO()))
            audio.main()
        for mock in [credentials, prompt, network, renderer, chunks]:
            mock.assert_not_called()
        plan = json.loads(output.getvalue())
        self.assertEqual((plan['readyTracks'], plan['pendingTracks']), (0, 305))
        self.assertIs(plan['speechCredentialsConfigured'], True)
        self.assertEqual((plan['listeningApprovedTracks'], plan['listeningPendingTracks']), (0, 305))
        expected = {p['id'] for p in self.poems}
        self.assertEqual({p.stem for p in (self.stage / 'ssml').glob('*.ssml')}, expected)
        self.assertEqual(list((self.stage / 'audio').glob('*.mp3')), [])
        self.assertEqual(first.read_bytes(), b'first-volume-sentinel')
        self.assertFalse(audio.MANIFEST.exists())
        self.assertFalse((self.root / audio.RELEASE).exists())
        self.assertEqual(len(json.loads((self.stage / 'listening-review.json').read_text())['tracks']), 305)
        for poem in self.poems:
            draft = ET.fromstring((self.stage / 'ssml' / f"{poem['id']}.ssml").read_text())
            body = draft.find('.//m:express-as', NS)
            self.assertEqual(''.join(''.join(body.itertext()).split()),
                             ''.join(t[0] for line in poem['rubyLines'] for t in line))

    def test_rare_glyphs_use_display_form_in_ssml_and_preserve_logical_source(self):
        source = {p['order']: p for p in json.loads((self.base / 'production.json').read_text())['poems']}
        poems = {p['id']: p for p in self.poems}
        journey = poems[source[28]['id']]
        address = poems[source[183]['id']]
        self.assertIn('𪧘', journey['text'])
        self.assertIn('寠', journey['readingText'])
        self.assertIn('贫寠', poetry_ssml(journey))
        self.assertNotIn('𪧘', poetry_ssml(journey))
        self.assertIn('𥐟', address['sourceTitle'])
        self.assertIn('礒', address['title'])
        self.assertIn('礒', poetry_ssml(address))
        self.assertNotIn('𥐟', poetry_ssml(address))

    def test_all_chunked_drafts_preserve_every_spoken_character(self):
        for poem in self.poems:
            whole = ET.fromstring(poetry_ssml(poem))
            chunks = [ET.fromstring(s) for s in poetry_ssml_chunks(poem)]
            flatten = lambda nodes: ''.join(''.join(''.join(n.itertext()).split()) for n in nodes)
            self.assertEqual(flatten(chunks), flatten([whole]), poem['id'])
            for index, chunk in enumerate(chunks):
                introductions = chunk.find('s:voice', NS).findall('s:prosody', NS)
                self.assertEqual(len(introductions), 1 if index == 0 else 0)

    def test_missing_listening_review_blocks_before_release_or_decode(self):
        records = self.records()
        with patch.object(audio.pipeline, 'audit') as audit:
            with self.assertRaisesRegex(ValueError, '305 首待逐首试听'):
                audio.publish(self.poems)
        audit.assert_not_called()
        self.assertFalse(audio.MANIFEST.exists())
        self.assertFalse((self.root / audio.RELEASE).exists())

    def test_stale_input_or_audio_review_hash_blocks_publish(self):
        records = self.records()
        self.reviews(records)
        identity = self.poems[0]['id']
        for key in ['inputSHA256', 'audioSHA256']:
            review = self.reviews(records)
            review['tracks'][identity][key] = '0' * 64
            audio.atomic_json(self.stage / 'listening-review.json', review)
            with patch.object(audio.pipeline, 'audit') as audit:
                with self.assertRaisesRegex(ValueError, '1 首待逐首试听'):
                    audio.publish(self.poems)
            audit.assert_not_called()
        self.assertFalse(audio.MANIFEST.exists())

    def test_unattributed_or_undated_approval_is_pending(self):
        records = self.records()
        review = self.reviews(records)
        identity = self.poems[0]['id']
        for field, value in [('reviewedBy', ''), ('reviewedAt', ''), ('reviewedAt', '2026-10-04')]:
            row = dict(review['tracks'][identity], **{field: value})
            self.assertFalse(audio.approved_listening_row(row, records[identity]))

    def test_dry_run_does_not_reapprove_changed_tracks(self):
        records = self.records()
        review = self.reviews(records)
        identity = self.poems[0]['id']
        old = dict(review['tracks'][identity])
        records[identity] = {**records[identity], 'sha256': '1' * 64}
        prepared = audio.prepare_listening_review(self.poems, records)
        self.assertEqual(prepared['tracks'][identity], old)
        self.assertEqual(audio.listening_progress(self.poems, records, prepared)['pendingTracks'], 1)

    def test_approved_reviews_cannot_bypass_a_failed_decoding_audit(self):
        records = self.records()
        self.reviews(records)
        with patch.object(audio.pipeline, 'audit', side_effect=ValueError('decoded audio failed')) as audit:
            with self.assertRaisesRegex(ValueError, 'decoded audio failed'):
                audio.publish(self.poems)
        audit.assert_called_once_with(self.poems, stage=self.stage, decode=True)
        self.assertFalse(audio.MANIFEST.exists())
        self.assertFalse((self.root / audio.RELEASE).exists())

    def test_current_reviews_publish_only_the_second_volume_after_audit(self):
        records = self.records()
        self.reviews(records)
        first = self.root / 'data/audio/manifest.json'
        first.parent.mkdir(parents=True)
        first.write_bytes(b'first-volume-sentinel')
        stats = {'tracks': 305, 'seconds': 61000, 'bytes': sum(v['bytes'] for v in records.values()),
                 'recipe': audio.AZURE_RECIPE, 'allFilesDecoded': True}
        with patch.object(audio.pipeline, 'audit', return_value=stats) as audit:
            result = audio.publish(self.poems)
        audit.assert_called_once_with(self.poems, stage=self.stage, decode=True)
        self.assertEqual(result['listeningApprovedTracks'], 305)
        manifest = json.loads(audio.MANIFEST.read_text())
        self.assertEqual(manifest['listeningReviewStatus'], 'complete')
        self.assertEqual(manifest['listeningReviewFile'], LISTENING_REVIEW_FILE)
        self.assertEqual(manifest['listeningReviewSHA256'], audio.pipeline.digest(self.root / LISTENING_REVIEW_FILE))
        self.assertEqual(json.loads((self.root / LISTENING_REVIEW_FILE).read_text()),
                         json.loads((self.stage / 'listening-review.json').read_text()))
        self.assertEqual({p.stem for p in (self.root / audio.RELEASE).glob('*.mp3')}, {p['id'] for p in self.poems})
        self.assertTrue(all(t['file'].startswith('assets/volume-2/audio/') for t in manifest['tracks'].values()))
        self.assertEqual(first.read_bytes(), b'first-volume-sentinel')


    def published_fixture(self):
        records = self.records()
        self.reviews(records)
        stats = {'tracks': 305, 'allFilesDecoded': True}
        with patch.object(audio.pipeline, 'audit', return_value=stats):
            audio.publish(self.poems)
        catalog = json.loads(audio.CATALOG.read_text())
        details = {p['id']: p for p in self.poems}
        return catalog, details, json.loads(audio.MANIFEST.read_text())

    def test_release_missing_manifest_is_unavailable_without_writes(self):
        catalog = json.loads(audio.CATALOG.read_text())
        before = {str(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(validate_volume2_release(self.root, catalog, {p['id']: p for p in self.poems}),
                         {'available': False, 'tracks': 0})
        self.assertEqual(before, {str(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file()})

    def test_release_availability_does_not_bind_old_catalog_flag_or_sha(self):
        catalog, details, manifest = self.published_fixture()
        manifest['catalogSHA256'] = 'provenance-of-the-old-false-catalog'
        audio.atomic_json(audio.MANIFEST, manifest)
        before = copy.deepcopy((catalog, details))
        self.assertEqual(validate_volume2_release(self.root, catalog, details), {'available': True, 'tracks': 305})
        self.assertEqual((catalog, details), before)
        catalog['narrationAvailable'] = True
        self.assertEqual(validate_volume2_release(self.root, catalog, details), {'available': True, 'tracks': 305})

    def test_release_permanent_proof_survives_removal_of_staging(self):
        catalog, details, _ = self.published_fixture()
        shutil.rmtree(self.stage)
        self.assertEqual(validate_volume2_release(self.root, catalog, details), {'available': True, 'tracks': 305})

    def test_release_partial_or_reordered_tracks_are_rejected(self):
        catalog, details, original = self.published_fixture()
        missing = copy.deepcopy(original)
        missing['tracks'].pop(self.poems[0]['id'])
        reordered = copy.deepcopy(original)
        reordered['trackOrder'].reverse()
        for manifest in [missing, reordered]:
            with self.subTest(track_count=len(manifest['tracks'])):
                audio.atomic_json(audio.MANIFEST, manifest)
                with self.assertRaisesRegex(ValueError, 'coverage or order'):
                    validate_volume2_release(self.root, catalog, details)

    def test_release_wrong_recipe_or_volume_or_nonfull_status_is_rejected(self):
        catalog, details, original = self.published_fixture()
        for change in [lambda m: m.update(volume='volume-1'),
                       lambda m: m.update(release='staged'),
                       lambda m: m['recipe'].update(voice='another-voice')]:
            manifest = copy.deepcopy(original)
            change(manifest)
            audio.atomic_json(audio.MANIFEST, manifest)
            with self.assertRaisesRegex(ValueError, 'full volume-2 release.*recipe'):
                validate_volume2_release(self.root, catalog, details)

    def test_release_requires_current_production_hash(self):
        catalog, details, _ = self.published_fixture()
        self.mutate(self.base / 'production.json', lambda v: v.update(name='Updated production'))
        with self.assertRaisesRegex(ValueError, 'productionSHA256'):
            validate_volume2_release(self.root, catalog, details)

    def test_release_requires_current_ssml_input_and_ssml_hash(self):
        catalog, details, manifest = self.published_fixture()
        changed = copy.deepcopy(details)
        identity = self.poems[0]['id']
        changed[identity]['rubyLines'][0][0][0] = '误'
        with self.assertRaisesRegex(ValueError, 'SSML input hash'):
            validate_volume2_release(self.root, catalog, changed)
        manifest['tracks'][identity]['ssmlSHA256'] = '0' * 64
        audio.atomic_json(audio.MANIFEST, manifest)
        with self.assertRaisesRegex(ValueError, 'SSML hash'):
            validate_volume2_release(self.root, catalog, details)

    def test_release_requires_exact_volume2_file_prefix(self):
        catalog, details, manifest = self.published_fixture()
        identity = self.poems[0]['id']
        manifest['tracks'][identity]['file'] = f'assets/audio/{identity}.mp3'
        audio.atomic_json(audio.MANIFEST, manifest)
        with self.assertRaisesRegex(ValueError, 'file prefix or filename'):
            validate_volume2_release(self.root, catalog, details)

    def test_release_changed_file_bytes_or_hash_is_rejected(self):
        catalog, details, manifest = self.published_fixture()
        path = self.root / manifest['tracks'][self.poems[0]['id']]['file']
        original = path.read_bytes()
        path.write_bytes(original + b'x')
        with self.assertRaisesRegex(ValueError, 'audio bytes differ'):
            validate_volume2_release(self.root, catalog, details)
        path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        with self.assertRaisesRegex(ValueError, 'audio file hash differs'):
            validate_volume2_release(self.root, catalog, details)
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'release rejected'):
            validate_volume2_release(self.root, catalog, details)

    def test_release_requires_permanent_proof_path_hash_and_file(self):
        catalog, details, original = self.published_fixture()
        wrong_path = copy.deepcopy(original)
        wrong_path['listeningReviewFile'] = 'output/audio-azure-volume-2/listening-review.json'
        audio.atomic_json(audio.MANIFEST, wrong_path)
        with self.assertRaisesRegex(ValueError, 'permanent.*listening proof'):
            validate_volume2_release(self.root, catalog, details)
        wrong_hash = copy.deepcopy(original)
        wrong_hash['listeningReviewSHA256'] = '0' * 64
        audio.atomic_json(audio.MANIFEST, wrong_hash)
        with self.assertRaisesRegex(ValueError, 'listening proof hash'):
            validate_volume2_release(self.root, catalog, details)
        audio.atomic_json(audio.MANIFEST, original)
        (self.root / LISTENING_REVIEW_FILE).unlink()
        with self.assertRaisesRegex(ValueError, 'release rejected'):
            validate_volume2_release(self.root, catalog, details)

    def test_release_invalid_or_stale_per_track_permanent_approval_is_rejected(self):
        catalog, details, original_manifest = self.published_fixture()
        permanent = self.root / LISTENING_REVIEW_FILE
        original_review = json.loads(permanent.read_text())
        identity = self.poems[0]['id']
        changes = [lambda r: r['tracks'][identity].update(status='pending'),
                   lambda r: r['tracks'][identity].update(inputSHA256='0' * 64),
                   lambda r: r['tracks'][identity].update(audioSHA256='0' * 64),
                   lambda r: r['tracks'][identity].update(reviewedAt='no-date')]
        for change in changes:
            review = copy.deepcopy(original_review)
            change(review)
            audio.atomic_json(permanent, review)
            manifest = copy.deepcopy(original_manifest)
            manifest['listeningReviewSHA256'] = audio.pipeline.digest(permanent)
            audio.atomic_json(audio.MANIFEST, manifest)
            with self.assertRaisesRegex(ValueError, 'listening approval.*invalid or stale'):
                validate_volume2_release(self.root, catalog, details)

    def test_release_wrong_permanent_proof_membership_or_recipe_is_rejected(self):
        catalog, details, original_manifest = self.published_fixture()
        permanent = self.root / LISTENING_REVIEW_FILE
        original_review = json.loads(permanent.read_text())
        for change in [lambda r: r['tracks'].pop(self.poems[0]['id']),
                       lambda r: r.update(volume='volume-1'),
                       lambda r: r['recipe'].update(style='another-style')]:
            review = copy.deepcopy(original_review)
            change(review)
            audio.atomic_json(permanent, review)
            manifest = copy.deepcopy(original_manifest)
            manifest['listeningReviewSHA256'] = audio.pipeline.digest(permanent)
            audio.atomic_json(audio.MANIFEST, manifest)
            with self.assertRaisesRegex(ValueError, 'same 305 identities and recipe'):
                validate_volume2_release(self.root, catalog, details)

    def test_candidate_validation_failure_does_not_switch_published_manifest(self):
        records = self.records()
        self.reviews(records)
        audio.MANIFEST.parent.mkdir(parents=True)
        audio.MANIFEST.write_bytes(b'previous manifest sentinel')
        with patch.object(audio.pipeline, 'audit', return_value={'tracks': 305}), \
                patch.object(audio, 'validate_volume2_manifest', side_effect=ValueError('candidate invalid')):
            with self.assertRaisesRegex(ValueError, 'candidate invalid'):
                audio.publish(self.poems)
        self.assertEqual(audio.MANIFEST.read_bytes(), b'previous manifest sentinel')
        self.assertFalse((self.root / LISTENING_REVIEW_FILE).exists())

    def test_candidate_validation_failure_restores_proof_for_existing_valid_release(self):
        catalog, details, _ = self.published_fixture()
        permanent = self.root / LISTENING_REVIEW_FILE
        old_manifest = audio.MANIFEST.read_bytes()
        old_review = permanent.read_bytes()
        self.assertEqual(validate_volume2_release(self.root, catalog, details),
                         {'available': True, 'tracks': 305})
        identity = self.poems[0]['id']
        self.mutate(self.stage / 'listening-review.json', lambda review: review['tracks'][identity].update(
            reviewedAt='2026-10-05T09:00:00+08:00', notes='Completed a second listening review'))
        self.assertNotEqual((self.stage / 'listening-review.json').read_bytes(), old_review)
        with patch.object(audio.pipeline, 'audit', return_value={'tracks': 305}), \
                patch.object(audio, 'validate_volume2_manifest', side_effect=ValueError('candidate invalid')):
            with self.assertRaisesRegex(ValueError, 'candidate invalid'):
                audio.publish(self.poems)
        self.assertEqual(audio.MANIFEST.read_bytes(), old_manifest)
        self.assertEqual(permanent.read_bytes(), old_review)
        self.assertEqual(validate_volume2_release(self.root, catalog, details),
                         {'available': True, 'tracks': 305})



    def test_complete_release_derives_availability_and_load_accepts_activated_catalog(self):
        _, details, manifest = self.published_fixture()
        catalog, expected_details = audio.reader_builder.reader_entries(
            json.loads((self.base / 'production.json').read_text()),
            json.loads((self.base / 'poems.json').read_text()),
            json.loads((self.base / 'delivery-assets.json').read_text()))
        self.assertTrue(catalog['narrationAvailable'])
        self.assertEqual(expected_details, details)
        # The release remembers the old false catalog. Activation changes its
        # SHA, while the spoken inputs and full catalog order remain valid.
        old_catalog_sha = manifest['catalogSHA256']
        audio.atomic_json(audio.CATALOG, catalog)
        self.assertNotEqual(audio.pipeline.digest(audio.CATALOG), old_catalog_sha)
        self.assertEqual(audio.load(), self.poems)

    def test_reader_and_audio_load_reject_a_present_incomplete_release(self):
        _, _, manifest = self.published_fixture()
        manifest['tracks'].pop(self.poems[0]['id'])
        audio.atomic_json(audio.MANIFEST, manifest)
        with self.assertRaisesRegex(ValueError, 'release rejected.*coverage or order'):
            audio.load()



if __name__ == '__main__':
    unittest.main(verbosity=2)
