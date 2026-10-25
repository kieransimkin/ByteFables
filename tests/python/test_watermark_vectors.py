"""Independent Python parsing/CRC of published PUBLIC test vectors only."""
import json
from pathlib import Path
import unittest
import zlib


class TestWatermarkMessageVectors(unittest.TestCase):
    def test_public_message_header_crc_prefix_independent_decoder(self):
        fixture = json.loads((Path(__file__).resolve().parents[1] / 'vectors' /
            'watermark-message-v1.json').read_text(encoding='utf-8'))
        full = bytes.fromhex(fixture['publicRecordDigestHex'])
        for count in (12, 16, 32):
            data = bytes.fromhex(fixture['messages'][str(count * 8)])
            self.assertEqual(data[:4], b'BFWM')
            self.assertEqual(data[4], 1)
            self.assertEqual(data[5], count)
            self.assertEqual(len(data), count + 10)
            self.assertEqual(data[6:6+count], full[:count])
            self.assertEqual(int.from_bytes(data[-4:], 'big'), zlib.crc32(data[:-4]))


if __name__ == '__main__':
    unittest.main()
