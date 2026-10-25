#!/usr/bin/env node
/** Public-only reference CLI. Never pass a private key/seed or secret on a command line. */
import {
  ByteValue, PublicRecord, decodeHex, encodeHex, FORMAT_MANIFEST, planPublicFormats,
  executePublicFormat, decodePublicRecord, publicRecordFingerprint,
  createFrameRudimentsIdentityLayer, planPublicWatermark,
  encodeStoryV2, encodeScheduledStory, inspectStoryV2, createFrameRudimentsStoryPreview,
  makeVisualBitPlan, choosePromptBits, composeBaselinePrompt,
  createFrameRudimentsFractalLayer, deriveShortPublicHash, deriveShortPublicHashes
} from '../dist/index.js';

const help = `ByteFables public-only CLI (no wallet/private-key support)
  bytefables formats [--json]
  bytefables plan --bytes N [--goal recover-typed|recover-any|identify|all] [--planned] [--experimental]
  bytefables demo
  bytefables story-encode --confirm-public --public-hex HEX --namespace NS --kind KIND
      [--theme nature|technology|music|fantasy|science|humour] [--profile prefix|scheduled] [--stats]
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
    if (['--json', '--planned', '--experimental', '--confirm-public', '--generation-controlled', '--stats'].includes(flag)) {
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
