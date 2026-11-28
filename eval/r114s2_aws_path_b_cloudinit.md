# AWS Path B — the owner-side persistent host (R114 dir 5)

**Why this document exists:** the sandbox reprovisions on every context
boundary (5+ events measured). Local patch bundles and login bridges die
with each sandbox — the remote push is the only durable evidence home
(Art. 18), and native AWS credentials cannot survive the treadmill. The
permanent fix is a persistent host the OWNER controls: an EC2 instance
with an **instance role** (credentials never leave AWS), launched from
the owner's own console/device. Everything below is copy-pasteable.

**What the host unblocks:** (a) the engine−bare fresh run if the HF-429
persists (AGNES legs can run from the host's egress), (b) Score-8
(Bedrock ≥3 non-generator families + agreement ≥0.7), (c) Score-9 (the
rediscovery instrument recovery ≥0.40), (d) F30 (novelty-vs-feasibility
on the acceptance set) — all currently gated on a persistent, natively
credentialed machine.

---

## Step 1 — the instance role (owner console, ~3 minutes)

In the AWS console → IAM → Roles → Create role → **AWS service** →
**EC2**, attach this inline policy (least-privilege for the lanes):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:Converse"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    },
    {
      "Sid": "HealthRead",
      "Effect": "Allow",
      "Action": ["bedrock:ListFoundationModels", "bedrock:GetFoundationModel"],
      "Resource": "*"
    }
  ]
}
```

Name it `discovery-fabric-batch-role`. (No S3, no EC2 write, no IAM
write — the host only needs Bedrock invoke + list.)

## Step 2 — launch the instance (owner console)

- Region: your existing profile region (`ap-southeast-2` is the
  standing profile default).
- AMI: **Ubuntu 24.04 LTS** (or Amazon Linux 2023).
- Instance type: `t3.medium` is enough for the batch instruments
  (2 vCPU / 4 GB); `t3.small` works if the corpus fits in ~2 GB.
- **Advanced → IAM instance profile**: select `discovery-fabric-batch-role`.
- **Advanced → User data** (cloud-init — paste verbatim):

```yaml
#cloud-config
package_update: true
packages: [git, python3.12, python3-pip, python3-venv, awscli]
runcmd:
  - [systemctl, enable, --now, amazon-ssm-agent || true]
  - aws --version
  - aws bedrock list-foundation-models --region ap-southeast-2 --query 'modelSummaries[?starts_with(modelId, `anthropic.`)].modelId' --output text | head -1
  - git clone https://github.com/prateekm1007/discovery-evidence-fabric /opt/fabric
  - cd /opt/fabric && python3 -m venv .venv && . .venv/bin/activate
  - pip install pytest py pygments pint cantera mapie huggingface-hub
  - echo 'CLOUD-INIT DONE — instance is ready for the batch lanes'
```

The `runcmd` #3 line is the smoke test: it returns an Anthropic model id
iff the instance role + Bedrock are live (`native creds, zero logins`).

## Step 3 — hand the host to the loop

Paste the instance's **Session Manager URL** (or public IP + your key)
in-channel. The loop then runs, from the host:

1. **Score-8** — `python3 scripts/<score8_panel>.py` (the ≥3-family
   Bedrock agreement panel; families to cover: Anthropic Claude, Amazon
   Nova/Titan, Meta Llama, Mistral — pick 3 non-generator families,
   ≥10 invoke-200s each, agreement ≥0.7 measured, never normalized).
2. **Score-9** — the post-cutoff rediscovery instrument
   (recovery ≥0.40, or the typed pre-registered re-calibration filed).
3. **F30** — the acceptance-set novelty-vs-feasibility gate
   (feasibility gap ≤0.25 AND novelty +0.5, Art. 14).
4. Results push to `queue/dev12_r7` under claim-before-work (Art. 29),
   from the host, with the host's run log committed.

**Unattended batch** = the whole step 3 runs in one `tmux`/`systemd`
session with no interactive logins (that is the "0 intervention"
acceptance clause).

---

## Login-bridge retirement (Art. 16 — filed in the same change)

The R113 bridge (`mini-services/aws-login-service`, port 3021 + the
temporary `/api/aws-login-spawn` route) is RETIRED:

- the bridge service directory already died with sandbox reprovision #5
  (work that dies with the sandbox is not evidence — the treadmill
  lesson measured twice);
- the spawn route is deleted from the Next.js app this window;
- **successor:** this document's owner-side instance-role host (native
  credentials, no logins, no sandbox dependence);
- the ledger entry rides this commit: `eval/retirement_ledger.json`.

**Art. 28 note:** the owner-action counters for this item are at 2/3
rounds (R113 dir 8, R114 dir 5). This document + the in-channel message
are the escalation artifacts; the loop's offline work meanwhile = every
lane this window (F92/F91 push, F93, custody) + the staged runbooks
above.
