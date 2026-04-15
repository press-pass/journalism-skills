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

## Step 5: Known provider behavior

Apply what is known about major providers that defeat SMTP verification:

- **Outlook / Hotmail / Live / Office 365** (`outlook.com`, `hotmail.com`, `live.com` and similar): Always return 250 for any address. Mark SMTP result as **Indeterminate (Microsoft catch-all)**.
- **iCloud** (`icloud.com`, `me.com`, `mac.com`): Same behavior. Mark as **Indeterminate (Apple catch-all)**.
- **Yahoo / AOL** (`yahoo.com`, `aol.com`, `yahoo.co.uk`, etc.): Aggressively block SMTP probes. Mark as **Indeterminate (Yahoo blocks verification)**.

For these providers, skip the SMTP check entirely and note that verification is not possible.

## Output

Present a summary table:

| Email | Syntax | MX Record | Disposable | SMTP Result | Verdict |
|-------|--------|-----------|------------|-------------|---------|

Verdicts:
- **Reachable**: Passed all checks, SMTP returned 250, not catch-all
- **Unreachable**: Failed syntax, MX, or SMTP returned 550
- **Risky**: Disposable email provider
- **Indeterminate**: Could not confirm (catch-all, greylisted, blocked, or major provider)

After the table, briefly explain any indeterminate results and suggest next steps (e.g., "send a confirmation email
to verify" for indeterminate addresses).

Email addresses to verify: $ARGUMENTS
