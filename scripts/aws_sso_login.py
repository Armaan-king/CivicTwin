"""Sign in to AWS IAM Identity Center and keep .env supplied with live credentials.

    python scripts/aws_sso_login.py                 # sign in if there is no session
    python scripts/aws_sso_login.py --new-session   # sign in again, restarting the 8h clock
    python scripts/aws_sso_login.py --refresh       # new keys from the existing session

Why this exists rather than `aws configure sso`: that subcommand ships only in AWS CLI
v2, and what pip installs is v1, whose `sso` command can fetch role credentials but cannot
perform the browser sign-in that produces the token they are fetched with. Rather than
require an MSI install mid-session, this does the device-authorization flow directly
against `sso-oidc`, which botocore has had for years.

The point is the two different clocks. The **role credentials** in `.env` last about an
hour, which is shorter than a single generation run and is why this project kept dying
half-finished. The **SSO access token** this obtains lasts around eight hours, and role
credentials can be minted from it as often as needed without a browser and without anyone
pasting a key into a chat window. So a run that outlives its keys can renew them itself.

The token is cached in `.aws-sso-cache.json`, which is gitignored: it is a credential.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import webbrowser

import boto3
import botocore.exceptions

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / ".aws-sso-cache.json"
ENV = ROOT / ".env"

START_URL = "https://identitycenter.amazonaws.com/ssoins-8210ec85e99c7277"
SSO_REGION = "ap-southeast-1"
ACCOUNT_ID = "878093320975"
ROLE_NAME = "hack2026_IsbUsersPS"


def sign_in() -> dict:
    """Device-authorization flow. Prints a URL and a code; the human does the rest."""
    oidc = boto3.client("sso-oidc", region_name=SSO_REGION)
    client = oidc.register_client(clientName="civictwin", clientType="public")
    auth = oidc.start_device_authorization(
        clientId=client["clientId"],
        clientSecret=client["clientSecret"],
        startUrl=START_URL,
    )

    url = auth.get("verificationUriComplete") or auth["verificationUri"]
    print("\n" + "=" * 68)
    print("  Open this in a browser and approve the request:")
    print(f"\n    {url}\n")
    print(f"  If it asks for a code:  {auth['userCode']}")
    print("=" * 68 + "\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    interval = int(auth.get("interval", 5))
    deadline = time.time() + int(auth.get("expiresIn", 600))
    print("waiting for approval", end="", flush=True)
    while time.time() < deadline:
        time.sleep(interval)
        try:
            token = oidc.create_token(
                clientId=client["clientId"],
                clientSecret=client["clientSecret"],
                grantType="urn:ietf:params:oauth:grant-type:device_code",
                deviceCode=auth["deviceCode"],
            )
        except oidc.exceptions.AuthorizationPendingException:
            print(".", end="", flush=True)
            continue
        except oidc.exceptions.SlowDownException:
            interval += 5
            continue
        except oidc.exceptions.ExpiredTokenException:
            break
        print(" approved.")
        payload = {
            "accessToken": token["accessToken"],
            # ~8 hours, against the ~1 hour the role credentials get
            "expiresAt": time.time() + int(token.get("expiresIn", 28800)),
        }
        CACHE.write_text(json.dumps(payload), encoding="utf-8")
        return payload
    raise SystemExit("\nSign-in was not approved in time. Run this again.")


def cached_token() -> dict | None:
    if not CACHE.exists():
        return None
    try:
        payload = json.loads(CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    # a minute of slack, so a token that dies mid-call is renewed before the call
    return payload if payload.get("expiresAt", 0) > time.time() + 60 else None


def write_env(creds: dict) -> None:
    """Put the freshly minted keys where the application reads them."""
    import re

    text = ENV.read_text(encoding="utf-8")
    for key, value in (("AWS_ACCESS_KEY_ID", creds["accessKeyId"]),
                       ("AWS_SECRET_ACCESS_KEY", creds["secretAccessKey"]),
                       ("AWS_SESSION_TOKEN", creds["sessionToken"])):
        text, n = re.subn(rf"^{key}=.*$", lambda _m, v=value: f"{key}={v}",
                          text, count=1, flags=re.M)
        if n != 1:
            raise SystemExit(f"{key} is not in .env; cannot write credentials")
    ENV.write_text(text, encoding="utf-8")


def refresh(quiet: bool = False) -> bool:
    """Mint role credentials from the cached SSO token. No browser, no paste."""
    token = cached_token()
    if token is None:
        if not quiet:
            print("No valid SSO session. Run: python scripts/aws_sso_login.py")
        return False
    sso = boto3.client("sso", region_name=SSO_REGION)
    try:
        creds = sso.get_role_credentials(
            roleName=ROLE_NAME, accountId=ACCOUNT_ID,
            accessToken=token["accessToken"])["roleCredentials"]
    except botocore.exceptions.ClientError as exc:
        if not quiet:
            print(f"Could not mint credentials: {exc.response['Error']['Code']}")
        return False
    write_env(creds)
    if not quiet:
        mins = (creds["expiration"] / 1000 - time.time()) / 60
        left = (token["expiresAt"] - time.time()) / 3600
        print(f"credentials written to .env, good for {mins:.0f} min "
              f"(SSO session has {left:.1f} h left, renew from it any time)")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true",
                    help="mint new keys from the cached session; no browser")
    ap.add_argument("--new-session", "--force", action="store_true", dest="new_session",
                    help="sign in again even if the current session is still valid, to "
                         "start its ~8 hour clock over before a long unattended run")
    args = ap.parse_args()

    # Without --new-session a still-valid session is reused, which renews the one-hour
    # keys but not the eight-hour session behind them. That is the right default for a
    # mid-run top-up and exactly wrong before leaving a long run unattended: it looks
    # like re-authenticating and buys no extra window at all.
    if args.new_session:
        CACHE.unlink(missing_ok=True)
    if not args.refresh and cached_token() is None:
        sign_in()
    if not refresh():
        return 1

    # prove it, rather than assuming the write worked
    import os
    import re
    for m in re.finditer(r"^([A-Z_]+)=(.*)$", ENV.read_text(encoding="utf-8"), re.M):
        os.environ[m.group(1)] = m.group(2).strip()
    ident = boto3.client("sts", region_name=SSO_REGION).get_caller_identity()
    print(f"verified: account {ident['Account']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
