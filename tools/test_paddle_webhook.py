#!/usr/bin/env python3
"""
Simple test script to POST a simulated Paddle webhook to the local server.

Usage:
  python tools/test_paddle_webhook.py --host http://127.0.0.1:3456

This will POST form-encoded data to `/paddle/webhook`. By default the
script does not include a valid `p_signature` (so signature verification
will fail if a public key is configured). Adjust `--include-signature`
to test signature handling when you have a valid signature.
"""
import argparse
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='http://127.0.0.1:3456', help='Server base URL')
    parser.add_argument('--passthrough', default='sap_test_user_1', help='passthrough / device id')
    parser.add_argument('--include-signature', action='store_true', help='Include dummy p_signature')
    args = parser.parse_args()

    url = args.host.rstrip('/') + '/paddle/webhook'

    data = {
        'alert_name': 'checkout_complete',
        'checkout_id': 'chk_123456',
        'alert_id': '1',
        'passthrough': args.passthrough,
        'email': 'buyer@example.com',
        'amount': '9.99',
        'currency': 'USD',
    }

    if args.include_signature:
        # placeholder: not a valid signature — only used to test path when present
        data['p_signature'] = 'INVALID_SIGNATURE_BASE64'

    print(f"POSTing to {url} with passthrough={args.passthrough} (include_signature={args.include_signature})")
    r = requests.post(url, data=data, timeout=10)
    print(f"Status: {r.status_code}")
    try:
        print(r.json())
    except Exception:
        print(r.text)


if __name__ == '__main__':
    main()
