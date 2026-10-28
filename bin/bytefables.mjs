#!/usr/bin/env node
/** Public-only reference CLI. Never pass a private key/seed or secret on a command line. */
import {
  ByteValue, PublicRecord, decodeHex, encodeHex, FORMAT_MANIFEST, planPublicFormats,
  executePublicFormat, decodePublicRecord, publicRecordFingerprint,
  createFrameRudimentsIdentityLayer, planPublicWatermark,
  encodeStoryV2, encodeScheduledStory, inspectStoryV2, createFrameRudimentsStoryPreview,
  makeVisualBitPlan, choosePromptBits, composeBaselinePrompt,
  encodeLargeStoryV1, decodeLargeStoryV1, LARGE_LEXICON_COUNTS_V1, decodePublicTextFormat,
  createFrameRudimentsFractalLayer, deriveShortPublicHash, deriveShortPublicHashes,
  createPublicQrCard, encodePublicQrSession, decodePublicQrSession,
  createFrameRudimentsArtworkLayer, planPublicVideoLook, encodeUrBytesMultipartTestOnly,
  decodeUrBytesMultipartTestOnly, createPublicRecoverySheet
} from '../dist/index.js';
import { readFileSync } from 'node:fs';

const help = `ByteFables public-only CLI (no wallet/private-key support)
  bytefables formats [--json]
  bytefables plan --bytes N [--goal recover-typed|recover-any|identify|all] [--planned] [--experimental]
  bytefables demo
  bytefables video-effects [--family grading|spatial|optics|compositing|transform|temporal|transitions|retro|scene-depth|tracking-ai|procedural] [--json]
  bytefables video-look --confirm-public --public-hex HEX --namespace NS --kind KIND
      [--look auto|PRESET_ID] [--intensity 0..1] [--target layer:ID]
      [--purpose public-art|public-video] # frame-wide effects only with public-video purpose
      # FrameRudiments post_effects fragment; public art only; never QR/recovery surface
  bytefables decode-public-text --confirm-public --format FORMAT --text PUBLIC_TEXT [--experimental]
  bytefables story-encode --confirm-public --public-hex HEX --namespace NS --kind KIND
      [--theme nature|technology|music|fantasy|science|humour] [--profile prefix|scheduled] [--stats]
  bytefables story-large-encode --confirm-public --public-hex HEX --namespace NS --kind KIND
      [--locale en-US|en-GB] [--raw] # experimental, PUBLIC data only
  bytefables story-large-decode --confirm-public --story-file FILE # public text file
  bytefables story-large-lexicons # capacities / word counts; not spoken-safe
  bytefables story-preview --confirm-public --public-hex HEX --namespace NS --kind KIND
      [--theme THEME] [--box 0,0,640,120] [--font-size N] [--max-sentences N]
  bytefables short-hashes --confirm-public --public-hex HEX --namespace NS --kind KIND
      [--bytes 3|4|8]    # no --bytes emits all three; long PUBLIC input only
  bytefables visual-features --confirm-public --public-hex HEX --namespace NS --kind KIND
      [--derive-short-bytes 3|4|8] [--prompt-bits N] [--style direct|narrative|structured]
  bytefables fractal-layer --confirm-public --public-hex HEX --namespace NS --kind KIND
      [--family julia|burning-ship|ifs-fern|fbm] [--palette neon|pastel|mono]
      [--quality draft|standard] [--id ID] [--bounds 0,0,128,128]
  bytefables watermark-plan --confirm-public --public-hex HEX --namespace NS --kind KIND
      --carrier image|audio|video|text --mime-type MIME
      [--width N --height N] [--sample-rate N --channels N]
      [--fps N] [--duration-seconds N] [--token-count N]
      [--generation-controlled] [--digest-bytes 12|16|32]
  bytefables encode-public --confirm-public --public-hex HEX --namespace NS --kind KIND
               [--algorithm ALG] [--network NET] [--endian na|big|little]
               [--format FORMAT] [--experimental]
  bytefables artwork-layer --confirm-public --public-hex HEX --namespace NS --kind KIND
      [--artwork sigil|constellation|heraldry|topography|crystal|mandala|cellular|branching|orbital] [--palette neon|pastel|mono]
      [--complexity 1..8] [--id ID] [--bounds 0,0,128,128]
  bytefables qr-public --confirm-public --public-hex HEX --namespace NS --kind KIND
      [--ecc L|M|Q|H] [--qr-mask 0..7] [--max-version N] [--fragment-bytes N] [--no-parity]
      [--include-layers] [--bounds 0,0,512,512] [--layer-prefix ID]
  bytefables qr-recover --confirm-public  # reads JSON array of PUBLIC BFQR1 frame texts from stdin
  bytefables ur-test-encode --confirm-public --public-hex HEX [--fragment-bytes 80] [--mixed-frames N]
  bytefables ur-test-recover --confirm-public  # reads JSON PUBLIC ur:bytes frames from stdin
  bytefables public-print-sheet --confirm-public --public-hex HEX --namespace NS --kind KIND
      [--fragment-bytes N] [--max-version N] [--page-bounds 0,0,1024,1440]
  bytefables decode-public --confirm-public --public-cbor-hex HEX
  bytefables framerudiments-layer --confirm-public --public-hex HEX --namespace NS --kind KIND
               [--algorithm ALG] [--network NET] [--endian na|big|little]
               [--id LAYER_ID] [--bounds 0,0,128,128] [--palette neon|mono|pastel]

WARNING: shell arguments, stdout and terminals may be logged or recorded.
This interface accepts PUBLIC identifiers only. Never input passwords, wallet seeds,
private keys or other secrets. No file, network or clipboard operations are performed.`;

function parseFlags(args, allowed) {
  const opts = Object.create(null);
  for (let i = 0; i < args.length; i++) {
    const flag = args[i];
    if (!flag.startsWith('--') || !allowed.includes(flag) || flag in opts) {
      throw new TypeError(`Unknown or repeated flag: ${flag}`);
    }
    if (['--json', '--planned', '--experimental', '--confirm-public', '--generation-controlled', '--stats', '--no-parity', '--include-layers','--raw'].includes(flag)) {
      opts[flag] = true;
    } else {
      if (i + 1 >= args.length || args[i + 1].startsWith('--')) {
        throw new TypeError(`Missing value for ${flag}`);
      }
      opts[flag] = args[++i];
    }
  }
  return opts;
}

function requirePublic(opts) {
  if (opts['--confirm-public'] !== true) {
    throw new TypeError('Must pass --confirm-public: input MUST NOT be a secret');
  }
}

async function main(args) {
  const [command, ...rest] = args;
  switch (command) {
    case '--help':
    case '-h':
    case 'help':
    case undefined:
      console.log(help); return;
    case 'formats': {
      const opt = parseFlags(rest, ['--json']);
      if (opt['--json']) console.log(JSON.stringify(FORMAT_MANIFEST, null, 2));
      else for (const e of FORMAT_MANIFEST) {
        console.log(`${e.formatId}@${e.version} [${e.maturity}] ${e.guarantee}`);
      }
      return;
    }
    case 'plan': {
      const opt = parseFlags(rest, ['--bytes', '--goal', '--planned', '--experimental']);
      if (opt['--bytes'] === undefined) throw new TypeError('Missing --bytes');
      if (!/^\d+$/.test(opt['--bytes'])) throw new TypeError('Invalid byte count');
      const results = planPublicFormats({ byteLength: Number(opt['--bytes']),
        goal: opt['--goal'] ?? 'all', includePlanned: !!opt['--planned'],
        includeExperimental: !!opt['--experimental'] });
      console.log(JSON.stringify(results, null, 2)); return;
    }
    case 'decode-public-text': {
      const opt = parseFlags(rest, ['--confirm-public', '--format', '--text', '--experimental']);
      requirePublic(opt);
      if (!opt['--format'] || opt['--text'] === undefined) {
        throw new TypeError('Requires --format and --text for PUBLIC fixtures only');
      }
      const data = await decodePublicTextFormat(opt['--format'], opt['--text'],
        { allowExperimental: !!opt['--experimental'] });
      console.log(JSON.stringify({ formatId: opt['--format'], bytesHex: encodeHex(data),
        byteLength: data.length, contextRecovered: false,
        warning: 'Raw bytes only; no network, owner, wallet or key type is recovered.' }, null, 2));
      return;
    }
    case 'video-effects': {
      const opt = parseFlags(rest, ['--family', '--json']);
      const url = new URL('../manifests/video-effects-v1.json', import.meta.url);
      const catalogue = JSON.parse(readFileSync(url, 'utf8'));
      const allowedFamilies = new Set(catalogue.entries.map(e => e.family));
      if (opt['--family'] && !allowedFamilies.has(opt['--family'])) throw new TypeError('Unknown video effect family');
      const entries = catalogue.entries.filter(e => !opt['--family'] || e.family === opt['--family']);
      if (opt['--json']) console.log(JSON.stringify({ ...catalogue, entries }, null, 2));
      else for (const entry of entries) {
        console.log(`${entry.id} [${entry.family}] ${entry.implementation}: ${entry.algorithm}`);
      }
      return;
    }
    case 'video-look': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-hex', '--namespace', '--kind',
        '--look', '--intensity', '--target', '--purpose']);
      requirePublic(opt);
      if (!opt['--public-hex'] || !opt['--namespace'] || !opt['--kind']) {
        throw new TypeError('Missing public data for video look');
      }
      if (opt['--intensity'] !== undefined && !/^(?:0(?:\.\d+)?|1(?:\.0+)?)$/.test(opt['--intensity'])) {
        throw new TypeError('Video look intensity must be a decimal 0..1');
      }
      const record = new PublicRecord(ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace: opt['--namespace'], kind: opt['--kind']
      }));
      const plan = await planPublicVideoLook(record, {
        look: opt['--look'] ?? 'auto',
        intensity: opt['--intensity'] === undefined ? 1 : Number(opt['--intensity']),
        target: opt['--target'] ?? 'layer:bytefables-identity', purpose: opt['--purpose'] ?? 'public-art'
      });
      console.log(JSON.stringify(plan, null, 2)); return;
    }
    case 'demo': {
      if (rest.length) throw new TypeError('demo takes no arguments');
      const record = new PublicRecord(ByteValue.public(Uint8Array.of(0, 1, 2, 255), {
        namespace: 'danceflow', kind: 'node-id'
      }));
      const artifact = await executePublicFormat('archive/public-cbor-v1', record);
      console.log(JSON.stringify({ example: 'PUBLIC test vector only',
        fingerprint: await publicRecordFingerprint(record),
        encodedCborHex: encodeHex(artifact.data),
        bytesHex: encodeHex(record.toBytes()) }, null, 2));
      return;
    }
    case 'encode-public': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-hex', '--namespace',
        '--kind', '--algorithm', '--network', '--endian', '--format', '--experimental']);
      requirePublic(opt);
      if (!opt['--public-hex'] || !opt['--namespace'] || !opt['--kind']) {
        throw new TypeError('Required: --public-hex, --namespace, --kind');
      }
      const record = new PublicRecord(ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace: opt['--namespace'], kind: opt['--kind']
      }), { algorithm: opt['--algorithm'] ?? 'opaque', network: opt['--network'] ?? '',
        endian: opt['--endian'] ?? 'na' });
      const artifact = await executePublicFormat(opt['--format'] ?? 'archive/public-cbor-v1',
        record, { allowExperimental: !!opt['--experimental'] });
      console.log(JSON.stringify({ formatId: artifact.formatId, mediaType: artifact.mediaType,
        guarantee: artifact.guarantee,
        ...(typeof artifact.data === 'string' ? { text: artifact.data } : { dataHex: encodeHex(artifact.data) }) }, null, 2));
      return;
    }
    case 'framerudiments-layer': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-hex', '--namespace',
        '--kind', '--algorithm', '--network', '--endian', '--id', '--bounds', '--palette']);
      requirePublic(opt);
      if (!opt['--public-hex'] || !opt['--namespace'] || !opt['--kind']) {
        throw new TypeError('Required: --public-hex, --namespace, --kind');
      }
      const rawBounds = opt['--bounds'] ?? '0,0,128,128';
      if (!/^\d+,\d+,\d+,\d+$/.test(rawBounds)) throw new TypeError('Invalid layer bounds');
      const bounds = rawBounds.split(',').map(Number);
      const record = new PublicRecord(ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace: opt['--namespace'], kind: opt['--kind']
      }), { algorithm: opt['--algorithm'] ?? 'opaque', network: opt['--network'] ?? '',
        endian: opt['--endian'] ?? 'na' });
      const layer = await createFrameRudimentsIdentityLayer(record, {
        id: opt['--id'] ?? 'bytefables-identity', bounds,
        palette: opt['--palette'] ?? 'neon'
      });
      console.log(JSON.stringify(layer, null, 2)); return;
    }
    case 'fractal-layer': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-hex', '--namespace', '--kind',
        '--id', '--bounds', '--family', '--palette', '--quality']);
      requirePublic(opt);
      if (!opt['--public-hex'] || !opt['--namespace'] || !opt['--kind']) {
        throw new TypeError('Fractal layer requires public hex, namespace and kind');
      }
      const rawBounds = opt['--bounds'] ?? '0,0,128,128';
      if (!/^\d+,\d+,\d+,\d+$/.test(rawBounds)) throw new TypeError('Invalid layer bounds');
      const record = new PublicRecord(ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace: opt['--namespace'], kind: opt['--kind']
      }));
      console.log(JSON.stringify(await createFrameRudimentsFractalLayer(record, {
        id: opt['--id'] ?? 'bytefables-fractal', bounds: rawBounds.split(',').map(Number),
        family: opt['--family'] ?? 'julia', palette: opt['--palette'] ?? 'neon',
        quality: opt['--quality'] ?? 'draft'
      }), null, 2));
      return;
    }
    case 'story-encode': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-hex', '--namespace', '--kind',
        '--theme', '--profile', '--stats']);
      requirePublic(opt);
      if (opt['--public-hex'] === undefined || !opt['--namespace'] || !opt['--kind']) {
        throw new TypeError('Missing public story input');
      }
      const source = ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace: opt['--namespace'], kind: opt['--kind']
      });
      const theme = opt['--theme'] ?? 'nature';
      const profile = opt['--profile'] ?? 'prefix';
      if (!['prefix', 'scheduled'].includes(profile)) throw new TypeError('Invalid story profile');
      const story = profile === 'prefix' ? await encodeStoryV2(source, theme) :
        await encodeScheduledStory(source, theme);
      console.log(JSON.stringify({ format: profile === 'prefix' ? 'codec/story-v2-prefix' :
        'codec/story-v2-scheduled', experimental: true, publicOnly: true, story,
        ...(opt['--stats'] && profile === 'prefix' ? { stats: await inspectStoryV2(source, theme) } : {})
      }, null, 2)); return;
    }
    case 'story-large-lexicons': {
      if (rest.length) throw new TypeError('No flags supported');
      console.log(JSON.stringify({ format: 'bytefables.large-lexicons.v1',
        counts: LARGE_LEXICON_COUNTS_V1, roles: ['adjectives','nouns','verbs'],
        locales: ['en-US','en-GB'], sentenceBits: 68, rawPayloadBits: 66,
        warning: 'Experimental public-written codebooks; visual/spoken mnemonic and private-key recovery not certified.' }, null, 2));
      return;
    }
    case 'story-large-encode': {
      const opt = parseFlags(rest, ['--confirm-public','--public-hex','--namespace','--kind','--locale','--raw']);
      requirePublic(opt);
      if (opt['--public-hex'] === undefined || !opt['--namespace'] || !opt['--kind']) {
        throw new TypeError('Expected PUBLIC hex, namespace and kind');
      }
      const value = ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace: opt['--namespace'], kind: opt['--kind']
      });
      const result = await encodeLargeStoryV1(value, opt['--locale'] ?? 'en-GB');
      if (opt['--raw']) console.log(result);
      else console.log(JSON.stringify({ experimental: true, publicOnly: true,
        format: 'bytefables-large-story-v1', text: result }, null, 2));
      return;
    }
    case 'story-large-decode': {
      const opt = parseFlags(rest, ['--confirm-public','--story-file']);
      requirePublic(opt);
      if (!opt['--story-file']) throw new TypeError('Required --story-file (PUBLIC text only)');
      const source = readFileSync(opt['--story-file'], 'utf8').replace(/\n$/, '');
      const decoded = await decodeLargeStoryV1(source);
      console.log(JSON.stringify({ experimental: true, publicOnly: true,
        format: decoded.format, locale: decoded.locale, publicHex: encodeHex(decoded.bytes),
        warning: 'Raw bytes only; original namespace/kind not preserved, no secret processing.' }, null, 2));
      return;
    }
    case 'story-preview': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-hex', '--namespace', '--kind',
        '--theme', '--box', '--font-size', '--max-sentences']);
      requirePublic(opt);
      if (opt['--public-hex'] === undefined || !opt['--namespace'] || !opt['--kind']) {
        throw new TypeError('Missing public story input');
      }
      const bytes = ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace: opt['--namespace'], kind: opt['--kind']
      });
      const raw = opt['--box'] ?? '0,0,640,120';
      if (!/^\d+,\d+,\d+,\d+$/.test(raw)) throw new TypeError('Invalid story preview box');
      const numberOpt = (x, fallback) => {
        const v = opt[x];
        if (v === undefined) return fallback;
        if (!/^\d+$/.test(v)) throw new TypeError('Invalid numeric option');
        return Number(v);
      };
      console.log(JSON.stringify(await createFrameRudimentsStoryPreview(bytes,
        opt['--theme'] ?? 'nature', { box: raw.split(',').map(Number),
          fontSize: numberOpt('--font-size', 24),
          maxSentences: numberOpt('--max-sentences', 2) }), null, 2)); return;
    }
    case 'short-hashes': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-hex', '--namespace', '--kind', '--bytes']);
      requirePublic(opt);
      if (opt['--public-hex'] === undefined || !opt['--namespace'] || !opt['--kind']) {
        throw new TypeError('Missing public short-hash input');
      }
      const source = ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace: opt['--namespace'], kind: opt['--kind']
      });
      let hashes;
      if (opt['--bytes'] === undefined) {
        hashes = await deriveShortPublicHashes(source);
      } else {
        if (!/^(3|4|8)$/.test(opt['--bytes'])) throw new TypeError('Choose 3, 4 or 8 bytes');
        hashes = [await deriveShortPublicHash(source, Number(opt['--bytes']))];
      }
      console.log(JSON.stringify({ hashes, warning: 'DISPLAY ONLY; preserve full public identity for lookup and verification' }, null, 2));
      return;
    }
    case 'visual-features': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-hex', '--namespace',
        '--kind', '--prompt-bits', '--style', '--derive-short-bytes']);
      requirePublic(opt);
      if (opt['--public-hex'] === undefined || !opt['--namespace'] || !opt['--kind']) {
        throw new TypeError('Missing public visual-feature input');
      }
      const source = ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace: opt['--namespace'], kind: opt['--kind']
      });
      let derived = null;
      if (opt['--derive-short-bytes'] !== undefined) {
        if (!/^(3|4|8)$/.test(opt['--derive-short-bytes'])) {
          throw new TypeError('Choose 3, 4 or 8 derived bytes');
        }
        derived = await deriveShortPublicHash(source, Number(opt['--derive-short-bytes']));
      }
      const selectedValue = derived ? ByteValue.public(decodeHex(derived.hex), {
        namespace: source.namespace, kind: source.kind
      }) : source;
      const plan = await makeVisualBitPlan(selectedValue);
      const rawBudget = opt['--prompt-bits'] ?? String(Math.min(12, plan.bitCount));
      if (!/^\d+$/.test(rawBudget)) throw new TypeError('Invalid prompt bit budget');
      const budget = Number(rawBudget);
      const style = opt['--style'] ?? 'direct';
      console.log(JSON.stringify({ ...plan,
        ...(derived ? { shortDerivation: derived } : {}),
        promptBitBudget: budget,
        selectedFeatures: choosePromptBits(plan, budget),
        baselinePrompt: composeBaselinePrompt(plan, budget, style),
        baselineStyle: style,
        claimsBitExactImage: false }, null, 2));
      return;
    }
    case 'watermark-plan': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-hex', '--namespace', '--kind',
        '--algorithm', '--network', '--endian', '--carrier', '--mime-type', '--width', '--height',
        '--sample-rate', '--channels', '--duration-seconds', '--fps', '--token-count',
        '--generation-controlled', '--digest-bytes']);
      requirePublic(opt);
      if (!opt['--public-hex'] || !opt['--namespace'] || !opt['--kind'] ||
          !opt['--carrier'] || !opt['--mime-type']) {
        throw new TypeError('Watermark planning requires --public-hex, --namespace, --kind, --carrier, --mime-type');
      }
      const record = new PublicRecord(ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace: opt['--namespace'], kind: opt['--kind']
      }), { algorithm: opt['--algorithm'] ?? 'opaque', network: opt['--network'] ?? '',
        endian: opt['--endian'] ?? 'na' });
      // No file or media bytes are read; only strict carrier metadata is inspected.
      const numberFlag = (name) => {
        const v = opt[`--${name}`];
        if (v === undefined || !/^\d+(?:\.\d+)?$/.test(v)) {
          throw new TypeError(`Expected numeric --${name}`);
        }
        return Number(v);
      };
      const kind = opt['--carrier'];
      const mimeType = opt['--mime-type'];
      let carrier;
      switch (kind) {
        case 'image': carrier = { kind, mimeType, width: numberFlag('width'),
          height: numberFlag('height') }; break;
        case 'audio': carrier = { kind, mimeType, sampleRate: numberFlag('sample-rate'),
          channels: numberFlag('channels'), durationSeconds: numberFlag('duration-seconds') }; break;
        case 'video': carrier = { kind, mimeType, width: numberFlag('width'),
          height: numberFlag('height'), fps: numberFlag('fps'),
          durationSeconds: numberFlag('duration-seconds') }; break;
        case 'text': carrier = { kind, mimeType, tokenCount: numberFlag('token-count'),
          generationControlled: !!opt['--generation-controlled'] }; break;
        default: throw new TypeError('Unsupported watermark carrier');
      }
      const length = opt['--digest-bytes'] === undefined ? 12 : numberFlag('digest-bytes');
      const plan = await planPublicWatermark(record, carrier, { digestBytes: length });
      console.log(JSON.stringify(plan, null, 2)); return;
    }
    case 'artwork-layer': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-hex', '--namespace', '--kind',
        '--artwork', '--palette', '--complexity', '--id', '--bounds']);
      requirePublic(opt);
      if (!opt['--public-hex'] || !opt['--namespace'] || !opt['--kind']) {
        throw new TypeError('Missing PUBLIC identity data for artwork layer');
      }
      const rawBounds = opt['--bounds'] ?? '0,0,128,128';
      if (!/^\d+,\d+,\d+,\d+$/.test(rawBounds)) throw new TypeError('Invalid artwork bounds');
      const complexity = opt['--complexity'] ?? '4';
      if (!/^[1-8]$/.test(complexity)) throw new TypeError('Artwork complexity must be 1..8');
      const record = new PublicRecord(ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace: opt['--namespace'], kind: opt['--kind']
      }));
      const layer = await createFrameRudimentsArtworkLayer(record, {
        id: opt['--id'] ?? 'bytefables-artwork', bounds: rawBounds.split(',').map(Number),
        artwork: opt['--artwork'] ?? 'sigil', palette: opt['--palette'] ?? 'neon',
        complexity: Number(complexity)
      });
      console.log(JSON.stringify({ layer, fullFingerprint: await publicRecordFingerprint(record, 32),
        caveat: 'This is a deterministic avatar, NOT a reversible key or identity proof.' }, null, 2));
      return;
    }
    case 'qr-public': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-hex', '--namespace', '--kind',
        '--algorithm', '--network', '--endian', '--ecc', '--max-version', '--fragment-bytes',
        '--no-parity', '--include-layers', '--qr-mask', '--bounds', '--layer-prefix']);
      requirePublic(opt);
      if (opt['--public-hex'] === undefined || !opt['--namespace'] || !opt['--kind']) {
        throw new TypeError('Missing required QR public record fields');
      }
      const record = new PublicRecord(ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace: opt['--namespace'], kind: opt['--kind']
      }), { algorithm: opt['--algorithm'] ?? 'opaque', network: opt['--network'] ?? '',
        endian: opt['--endian'] ?? 'na' });
      const integer = (name, fallback) => {
        if (opt[name] === undefined) return fallback;
        if (!/^\d+$/.test(opt[name])) throw new TypeError(`Invalid ${name}`);
        return Number(opt[name]);
      };
      const options = {
        ecc: opt['--ecc'] ?? 'Q', qrMask: integer('--qr-mask', 0), maxVersion: integer('--max-version', 12),
        fragmentBytes: integer('--fragment-bytes', undefined), parity: !opt['--no-parity']
      };
      if (opt['--include-layers']) {
        const rawBounds = opt['--bounds'] ?? '0,0,512,512';
        if (!/^\d+,\d+,\d+,\d+$/.test(rawBounds)) throw new TypeError('Invalid QR bounds');
        const card = await createPublicQrCard(record, { ...options, bounds: rawBounds.split(',').map(Number),
          layerIdPrefix: opt['--layer-prefix'] ?? 'bytefables-qr' });
        console.log(JSON.stringify(card, null, 2));
      } else {
        const session = await encodePublicQrSession(record, options);
        console.log(JSON.stringify({ schema: session.schema, sessionId: session.sessionId,
          qrErrorCorrection: session.qrErrorCorrection, qrMaxVersion: session.qrMaxVersion,
          fragmentBytes: session.fragmentBytes, dataFrames: session.dataFrames,
          parityFrames: session.parityFrames, frames: session.frames.map(f => f.text),
          warning: 'PUBLIC data ONLY; BFQR1 is NOT URv2, SeedQR, secret archival, or proof of identity' }, null, 2));
      }
      return;
    }
    case 'ur-test-encode': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-hex', '--fragment-bytes', '--mixed-frames']);
      requirePublic(opt);
      if (opt['--public-hex'] === undefined) throw new TypeError('Missing --public-hex');
      const number = (name, fallback) => {
        if (opt[name] === undefined) return fallback;
        if (!/^\d+$/.test(opt[name])) throw new TypeError('Invalid '+name);
        return Number(opt[name]);
      };
      const sequence = await encodeUrBytesMultipartTestOnly(decodeHex(opt['--public-hex']), {
        fragmentBytes: number('--fragment-bytes', 80), extraMixedFrames: number('--mixed-frames', 0)
      });
      console.log(JSON.stringify(sequence, null, 2)); return;
    }
    case 'ur-test-recover': {
      const opt = parseFlags(rest, ['--confirm-public']);
      requirePublic(opt);
      const input = readFileSync(0, 'utf8');
      if (input.length > 8000000) throw new RangeError('Too much UR test input');
      let frames;
      try { const json=JSON.parse(input); frames=Array.isArray(json)?json:json.frames; }
      catch { throw new TypeError('Expected JSON array of PUBLIC ur:bytes test frames'); }
      const bytes=await decodeUrBytesMultipartTestOnly(frames);
      console.log(JSON.stringify({bytesHex:encodeHex(bytes),testOnly:true,
        warning:'PUBLIC ur:bytes test fixtures only; not a wallet backup'},null,2)); return;
    }
    case 'public-print-sheet': {
      const opt = parseFlags(rest, ['--confirm-public','--public-hex','--namespace','--kind',
        '--fragment-bytes','--max-version','--page-bounds']);
      requirePublic(opt);
      if (opt['--public-hex'] === undefined || !opt['--namespace'] || !opt['--kind']) {
        throw new TypeError('Missing PUBLIC print-sheet identity fields');
      }
      const bounds = opt['--page-bounds'] ?? '0,0,1024,1440';
      if (!/^\d+,\d+,\d+,\d+$/.test(bounds)) throw new TypeError('Invalid print bounds');
      const num = (key, defaultValue) => {
        if (opt[key] === undefined) return defaultValue;
        if (!/^\d+$/.test(opt[key])) throw new TypeError('Invalid '+key);
        return Number(opt[key]);
      };
      const record = new PublicRecord(ByteValue.public(decodeHex(opt['--public-hex']), {
        namespace:opt['--namespace'],kind:opt['--kind']
      }));
      const sheet = await createPublicRecoverySheet(record, {
        fragmentBytes:num('--fragment-bytes',64),maxVersion:num('--max-version',12),
        pageBounds:bounds.split(',').map(Number)
      });
      console.log(JSON.stringify(sheet,null,2)); return;
    }
    case 'qr-recover': {
      const opt = parseFlags(rest, ['--confirm-public']);
      requirePublic(opt);
      const input = readFileSync(0, 'utf8');
      if (input.length > 8000000) throw new RangeError('Too much PUBLIC QR input');
      let texts;
      try { const data = JSON.parse(input); texts = Array.isArray(data) ? data : data.frames; }
      catch { throw new TypeError('Expected JSON array of BFQR1 PUBLIC frame strings on stdin'); }
      const record = await decodePublicQrSession(texts);
      console.log(JSON.stringify({ namespace: record.namespace, kind: record.kind,
        algorithm: record.algorithm, network: record.network, endian: record.endian,
        schemaVersion: record.schemaVersion, bytesHex: encodeHex(record.toBytes()),
        fingerprint: await publicRecordFingerprint(record) }, null, 2));
      return;
    }
    case 'decode-public': {
      const opt = parseFlags(rest, ['--confirm-public', '--public-cbor-hex']);
      requirePublic(opt);
      if (opt['--public-cbor-hex'] === undefined) throw new TypeError('Missing --public-cbor-hex');
      const record = await decodePublicRecord(decodeHex(opt['--public-cbor-hex']));
      console.log(JSON.stringify({ namespace: record.namespace, kind: record.kind,
        algorithm: record.algorithm, network: record.network,
        endian: record.endian, schemaVersion: record.schemaVersion,
        bytesHex: encodeHex(record.toBytes()),
        fingerprint: await publicRecordFingerprint(record) }, null, 2)); return;
    }
    default: throw new TypeError(`Unknown command: ${command}`);
  }
}

main(process.argv.slice(2)).catch(err => {
  // Errors never embed rejected bytes, arguments or payloads.
  console.error(`ByteFables: ${err.message}`);
  process.exitCode = 1;
});
