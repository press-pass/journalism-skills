---
description: Verify whether email addresses are reachable without sending an email. Checks syntax, DNS/MX records, disposable domains, and SMTP mailbox existence.
---

You will be given one or more email addresses (comma-separated). For each email address, run the verification pipeline
below. Report results in a summary table at the end.

## Step 1: Syntax check

Verify the email matches a valid format: one `@`, valid local part (no leading/trailing dots, no consecutive dots),
and a valid domain (valid hostname characters, at least one dot).

If the syntax is invalid, mark the email as **Invalid (bad syntax)** and skip remaining steps.

## Step 2: DNS/MX record check

Run `dig +short <domain> MX` via Bash. Inspect the results:

- If no MX records are returned, try `dig +short <domain> A` as a fallback (some domains accept mail on their A record).
- If neither returns results, mark as **Invalid (no mail server)** and skip remaining steps.
- If MX records exist, note the lowest-preference (primary) MX server for Step 4.

## Step 3: Disposable email check

Check whether the domain is a known disposable/temporary email provider. Search the web for
"is <domain> a disposable email" or check against well-known disposable domains (mailinator.com, guerrillamail.com,
tempmail.com, throwaway.email, yopmail.com, sharklasers.com, 10minutemail.com, trashmail.com, etc.).

If disposable, flag it as **Warning: disposable email provider** but continue to Step 4.

## Step 4: SMTP RCPT TO verification

This step connects to the mail server and asks if the mailbox exists without sending an email.

Run this Bash script, substituting the email and MX server:

```bash
{
  exec 3<>/dev/tcp/<mx_server>/25
  timeout=5

  # Read greeting
  read -t $timeout -u 3 greeting
  echo "GREETING: $greeting"

  # HELO
  echo -e "HELO verify.local\r" >&3
  read -t $timeout -u 3 helo_resp
  echo "HELO: $helo_resp"

  # MAIL FROM
  echo -e "MAIL FROM:<verify@verify.local>\r" >&3
  read -t $timeout -u 3 mail_resp
  echo "MAIL FROM: $mail_resp"

  # RCPT TO - the actual verification
  echo -e "RCPT TO:<EMAIL_ADDRESS>\r" >&3
  read -t $timeout -u 3 rcpt_resp
  echo "RCPT TO: $rcpt_resp"

  # QUIT
  echo -e "QUIT\r" >&3

  exec 3<&-
  exec 3>&-
} 2>&1
```

Interpret the RCPT TO response:

- **250**: Mailbox exists (or domain is catch-all — see below)
- **550/551/553**: Mailbox does not exist — mark as **Invalid (mailbox not found)**
- **450/451/452**: Temporary rejection (greylisting) — mark as **Indeterminate (greylisted)**
- **Connection refused/timeout**: Server blocked the check — mark as **Indeterminate (server unreachable)**
- **Any other error**: Note the code and mark as **Indeterminate**

### Catch-all detection

After the RCPT TO check, if the result was 250, test whether the domain is catch-all by checking a clearly fake
address: `does-not-exist-xyz-99@<domain>`. If that also returns 250, the domain accepts all addresses and the result
is **Indeterminate (catch-all domain)**.

## Step 5: Provider-specific headless browser verification

For providers that defeat SMTP verification, use Playwright to check account existence via their password recovery
flows. Skip the SMTP check (Step 4) for these providers and use this step instead.

### Microsoft (outlook.com, hotmail.com, live.com, msn.com)

1. Call `browser_navigate` to `https://account.live.com/password/reset`
2. Call `browser_snapshot` to find the email input field.
3. Call `browser_fill_form` to enter the email address into the email input.
4. Call `browser_click` on the "Next" button.
5. Wait 3 seconds, then call `browser_snapshot` and check:
   - If the page contains text like "that Microsoft account doesn't exist" or "No account found with that email" → **Unreachable (account not found)**
   - If the page shows identity verification options ("verify your identity", "send a code", "authenticator app") → **Reachable (account exists)**
   - If a CAPTCHA appears, note it and mark as **Indeterminate (CAPTCHA blocked)**

### Yahoo (yahoo.com, ymail.com, aol.com, yahoo.co.uk, yahoo.ca, etc.)

1. Call `browser_navigate` to `https://login.yahoo.com/forgot`
2. Call `browser_snapshot` to find the email/phone input field.
3. Call `browser_fill_form` to enter the email address.
4. Call `browser_click` on "Continue".
5. Wait 3 seconds, then call `browser_snapshot` and check:
   - If the page shows an error message like "Sorry, we don't recognize that email" → **Unreachable (account not found)**
   - If the page shows verification options (send a code, security key, etc.) → **Reachable (account exists)**
   - If a CAPTCHA appears, note it and mark as **Indeterminate (CAPTCHA blocked)**

### Microsoft 365 (business domains with MX pointing to outlook.com or *.mail.protection.outlook.com)

Before using the headless browser, try the faster API check:

Run via Bash:
```bash
curl -s -X POST 'https://login.microsoftonline.com/common/GetCredentialType' \
  -H 'Content-Type: application/json' \
  -d '{"Username": "EMAIL_ADDRESS"}' | python3 -c "import sys,json; r=json.load(sys.stdin); print('EXISTS' if r.get('IfExistsResult')==0 else 'NOT_FOUND' if r.get('IfExistsResult')==1 else f'UNKNOWN({r.get(\"IfExistsResult\")})')"
```

- `EXISTS` → **Reachable (Microsoft 365 account exists)**
- `NOT_FOUND` → **Unreachable (account not found)**
- `UNKNOWN` → Fall back to the Microsoft headless browser check above

### iCloud (icloud.com, me.com, mac.com)

Apple does not expose account enumeration in password recovery flows. For iCloud addresses, SMTP verification is
unreliable (catch-all behavior) and no headless workaround exists. Mark as **Indeterminate (Apple — cannot verify)**.

### All other providers

Use the SMTP RCPT TO check from Step 4.

## Output

Present a summary table:

| Email | Syntax | MX Record | Disposable | Verification Method | Result | Verdict |
|-------|--------|-----------|------------|---------------------|--------|---------|

Verification Method should indicate what was used: SMTP, Headless (Microsoft), Headless (Yahoo), API (M365), or N/A.

Verdicts:
- **Reachable**: Account confirmed to exist via SMTP 250 (non-catch-all) or headless browser / API check
- **Unreachable**: Failed syntax, MX, SMTP returned 550, or headless browser confirmed account does not exist
- **Risky**: Disposable email provider (may still be reachable)
- **Indeterminate**: Could not confirm (catch-all, greylisted, CAPTCHA blocked, or Apple iCloud)

After the table, briefly explain any indeterminate results and suggest next steps (e.g., "send a confirmation email
to verify" for indeterminate addresses).

Email addresses to verify: $ARGUMENTS
