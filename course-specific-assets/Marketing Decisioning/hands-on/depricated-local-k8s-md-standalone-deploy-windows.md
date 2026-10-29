# Hands-On: Deploying SAS 360 Marketing Decisioning (Standalone) on Local Kubernetes

> **Purpose of this guide:** This is a learning exercise. You will deploy a complete SAS 360
> Marketing Decisioning execution stack — PostgreSQL, SubjectContact, and a decision
> container — on the Kubernetes cluster built into Docker Desktop. Every command is spelled
> out, and the folder next to this file (`hands-on/`) already contains every YAML manifest,
> SQL script, and sample CSV you need.
>
> Everything here is designed to run entirely on your laptop's local Kubernetes cluster —
> no cloud account, no cluster-specific storage drivers, no object storage. Just Docker
> Desktop, `kubectl`, and `helm`.

---

## 1. What we're building

```
┌─────────────────────────────── Docker Desktop Kubernetes ─────────────────────────────────┐
│                                                                                           │
│  namespace: ci360-shed-hues-pg        namespace: ci360-shed-hues-sub                      │
│  ┌────────────────────────────┐        ┌───────────────────────────────────┐              │
│  │ PostgreSQL (Bitnami chart) │        │ SubjectContact  +  its OWN        │              │
│  │  - TRAINCAT schema         │◄─┐     │ built-in PostgreSQL-HA (Bitnami   │◄─┐           │
│  │  - customer CSV data       │  │     │ subchart, ships with the Helm     │  │           │
│  └────────────────────────────┘  │     │ chart — no separate DB needed!)   │  │           │
│                                  │     └───────────────────────────────────┘  │           │
│                                  │                                            │           │
│                                  │      namespace: ci360-shed-hues            │           │
│                                  │      ┌───────────────────────────────────┐ │           │
│                                  └──────┤ Decision container (2 replicas)   ├─┘           │
│                                         │  - reads customer data from the   │             │
│                                         │    PostgreSQL above               │             │
│                                         │  - reads arbitration scores from  │             │
│                                         │    a mounted ConfigMap            │             │
│                                         └───────────────────────────────────┘             │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

We'll use three dedicated namespaces to keep each piece of the stack tidy and easy to
tear down independently:

| Namespace | Contents |
|---|---|
| `ci360-shed-hues-pg` | PostgreSQL for customer/decision data |
| `ci360-shed-hues-sub` | SubjectContact (+ its own built-in PostgreSQL) |
| `ci360-shed-hues` | Decision container(s) |

> **Naming:** these namespace names are just a convention picked for this guide — 
> you are free to rename them for your own environment — just make sure every command below
> stays consistent with whatever you choose.

## 2. Folder contents

This guide lives in `hands-on/` alongside everything it references:

```
hands-on/
├── local-k8s-md-standalone-deploy.md   <- this file
├── manifests/
│   ├── 00-namespaces.yaml
│   ├── 01-postgres-values.yaml
│   ├── 02-access-point-secret.yaml
│   ├── 03-api-user-secret.yaml
│   ├── 04-subjectcontact-values.yaml
│   ├── 05-db-credentials-secret.yaml
│   ├── 06-decision-deployment.yaml
│   └── 07-decision-service.yaml
├── sql/
│   └── 01_schemas_tables.sql      <- TRAINCAT schema (customer tables)
├── csv/
│   ├── nexus_customer_sample.csv
│   ├── bk_customers_sample.csv
│   └── customer_drf_sample.csv
└── scores/
    └── external_score_customer_id.csv   <- arbitration score file (edit freely)
```

Several manifests use `${VAR}` placeholders instead of hardcoded values — you'll substitute
them with PowerShell as you go, using the exact commands shown in each step. This keeps
credentials out of the files on disk and makes the manifests reusable for anyone following
this guide.

> **Tip:** run every command in this guide from inside the `hands-on/` folder, so the
> relative paths (`manifests\...`, `sql\...`, etc.) resolve correctly.

---

## 3. Prerequisites

Confirm the following are in place before you start.

| # | Requirement | Why you need it |
|---|---|---|
| 1 | **Docker Desktop** with **Kubernetes enabled** (Settings → Kubernetes → Enable Kubernetes) | This *is* the cluster we're deploying to. |
| 2 | At least **4 vCPUs / 8 GB RAM** allocated to Docker Desktop | This is only a recommendation, use your best judgment. We're running two PostgreSQL instances, SubjectContact, and decision pods side by side. Skimping here is the #1 cause of pods stuck `Pending`/`CrashLoopBackOff`. |
| 3 | `kubectl` pointed at the `docker-desktop` context | `kubectl config use-context docker-desktop` |
| 4 | `helm` v3+ | Installs the PostgreSQL and SubjectContact charts. |
| 5 | PowerShell (5.1+ or 7+) | All commands below are PowerShell. |
| 6 | **A real SAS CI360 tenant's credentials** (`TENANT_URL`, `TENANT_ID`, `CLIENT_SECRET`, `API_USERNAME`, `API_PASSWORD`) | **Important: not optional, even locally.** SubjectContact and the decision container are proprietary SAS images hosted in a private container registry. The SubjectContact Helm chart runs a pre-install Job that exchanges these credentials for a short-lived registry pull token — Docker Desktop has to reach the internet to do this. There is no "offline demo mode." If you don't have a tenant, you can still complete **Step 1** (PostgreSQL) fully, and read Steps 2–3 to understand the mechanics, but the images won't pull without genuine credentials. |
| 7 | **Your tenant's Fleets API gateway URL** (`FLEET_API_GW`) | SubjectContact's built-in CDC/reporting feature needs this to know which Fleets API gateway to call. Sample: `https://fleetsapigw-training.ci360.sas.com/`. You can find the URL for your environment from our [documentation](https://go.documentation.sas.com/doc/en/cintcdc/production.a/cintqsg/task6-allow-domains.htm) |
| 8 | **A decision container image** — its `unique_name` and image URI, provided by your SAS contact or discovered via the CI360 `marketingContainerImage/images` API or from the user interface of the tenant | This is *the* decision you're deploying in Step 3. |

> **Tip:** keep these values handy in a scratch text file before you start — you'll
> set them as environment variables in the next section, and you'll reuse them across
> Steps 2 and 3.

### 3.1 Point your tools at the local cluster

```powershell
kubectl config use-context docker-desktop
kubectl get nodes                      # should show a single Ready node
kubectl get storageclass               # "hostpath" should be present and (default)
```

> **Important:** Docker Desktop's Kubernetes is a **single-node** cluster. Later, when we
> deploy the decision container "as two nodes," we really mean **two pod replicas** — both
> will be scheduled correctly onto that one node. In a real multi-node cluster the
> scheduler would spread them out; here, we're just proving the Deployment spec supports it.

### 3.2 Clone/open this repo and step into the hands-on folder

```powershell
cd path\to\md-toolkit\hands-on
```

### 3.3 Set your environment variables

Fill in your real CI360 tenant values, then run this in your PowerShell session (every
command below assumes these variables are set):

> **`TENANT_URL` and `FLEET_API_GW` must include the `https://` scheme.** A bare host like
> `extapigwservice-training.ci360.sas.com` (no `https://`) will fail to connect when we call
> its APIs in Steps 5 and 6 — always copy the *full* URL your tenant gave you.

```powershell
$env:TENANT_URL     = "https://extapigwservice-training.ci360.sas.com"    # your tenant's API gateway
$env:TENANT_ID       = "REPLACE_ME"                                    # your tenant ID
$env:CLIENT_SECRET   = "REPLACE_ME"                                    # HS256 signing secret
$env:API_USERNAME    = "REPLACE_ME"                   # CI360 API service account
$env:API_PASSWORD    = "REPLACE_ME"
$env:FLEET_API_GW    = "https://fleetsapigw-training.ci360.sas.com/"   # your tenant's Fleets API gateway

$env:PG_DATABASE     = "ci360db"
$env:PG_USER         = "ci360user"
$env:PG_PASSWORD     = "Orion123"
```

---

## 4. Step 1 — Deploy PostgreSQL and load the customer data

This PostgreSQL instance holds the customer data the **decision** container will query. It's
completely independent from the PostgreSQL that SubjectContact brings with it in Step 2.

### 4.1 Create the namespaces

```powershell
kubectl apply -f manifests\00-namespaces.yaml
```

This creates all three namespaces at once (`ci360-shed-hues-pg`, `ci360-shed-hues-sub`,
`ci360-shed-hues`).

### 4.2 Add the Bitnami Helm repo and install PostgreSQL

```powershell
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update bitnami
```

Notice `manifests\01-postgres-values.yaml` has no special StorageClass override — Docker
Desktop already ships a default `hostpath` StorageClass, so the chart "just works" out of
the box.

```powershell
helm upgrade --install ci360-postgres bitnami/postgresql `
  -n ci360-shed-hues-pg `
  -f manifests\01-postgres-values.yaml `
  --set=auth.database=$env:PG_DATABASE `
  --set=auth.username=$env:PG_USER `
  --set=auth.password=$env:PG_PASSWORD `
  --timeout=300s

kubectl rollout status statefulset/ci360-postgres-postgresql -n ci360-shed-hues-pg --timeout=300s
```

> **Tip:** `manifests\01-postgres-values.yaml` sizes the persistent volume at a modest
> `2Gi` — plenty for a learning exercise, and friendlier to a laptop's disk than a
> production-sized volume.

### 4.3 Create the schema (explicit, not "just let it auto-migrate")

The task calls for an **explicitly set schema**, so `sql\01_schemas_tables.sql` defines it
verbatim: the `TRAINCAT` schema and the customer tables the decision container reads.
There's no need to create a `contactresponse` schema here — SubjectContact's own built-in
PostgreSQL (deployed in Step 2) owns that data, so we don't duplicate it in this database.

```powershell
Get-Content sql\01_schemas_tables.sql -Raw | kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- `
    sh -c "PGPASSWORD=$env:PG_PASSWORD psql -h 127.0.0.1 -U $env:PG_USER -d $env:PG_DATABASE"
```

You should see a stream of `CREATE SCHEMA` / `CREATE TABLE` / `CREATE INDEX` messages — no
errors. ✅

### 4.4 (Optional) Set the search_path

This lets the decision container and any tool query `TRAINCAT.*` tables without
schema-qualifying every statement.

```powershell
$pgSuperPassword = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(
    (kubectl get secret ci360-postgres-postgresql -n ci360-shed-hues-pg -o jsonpath="{.data.postgres-password}")
))

"ALTER ROLE $env:PG_USER SET search_path = ""TRAINCAT"", public;" | `
    kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- `
    sh -c "PGPASSWORD=$pgSuperPassword psql -h 127.0.0.1 -U postgres -d $env:PG_DATABASE"
```

### 4.5 Load sample customer data

> **Note on sample size:** production customer files can easily run into thousands of
> rows. For a *learning* exercise we don't need production volumes, so the CSVs in
> `csv/` are trimmed to a small, representative slice (header + 10 rows) — enough to prove
> the pipeline works end-to-end. Swap in your own larger CSVs later using the exact same
> `\copy` pattern once you're comfortable — just drop them in `csv/` and point the commands
> below at your filenames.

```powershell
kubectl cp csv\training_data.csv ci360-shed-hues-pg/ci360-postgres-postgresql-0:/tmp/training_data.csv


$copyCmds = @"
\copy "TRAINCAT".training_data FROM '/tmp/training_data.csv' DELIMITER ',' CSV HEADER;
"@
$copyCmds | kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- `
    sh -c "PGPASSWORD=$env:PG_PASSWORD psql -h 127.0.0.1 -U $env:PG_USER -d $env:PG_DATABASE"
```

> **`kubectl cp` and Windows paths:** if you invoke `kubectl cp` from outside the
> `hands-on/` folder using a full Windows path (e.g. `C:\...\csv\file.csv`), the drive
> letter's colon can confuse `kubectl cp`'s `pod:path` parsing. Running the commands above
> from *inside* `hands-on/` with relative paths (as shown) avoids the problem entirely.

### 4.6 Verify

```powershell
"SELECT count(*) FROM ""TRAINCAT"".training_data;" | `
    kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- `
    sh -c "PGPASSWORD=$env:PG_PASSWORD psql -h 127.0.0.1 -U $env:PG_USER -d $env:PG_DATABASE"
```

You should see `120` come back. PostgreSQL is loaded and ready for use.

---

## 5. Step 2 — Deploy SubjectContact (using its own built-in PostgreSQL)

Here's an important design choice for this local setup: instead of pointing SubjectContact
at an *external* PostgreSQL, we let the `sas-marketing-decisioning` Helm chart deploy **its
own** bundled PostgreSQL-HA subchart (Bitnami `postgresql-ha`, enabled by default — see
`manifests\04-subjectcontact-values.yaml`). That means: no separate database to stand up, no
manual database secret to wire up — just install the chart, and SubjectContact gets a
private PostgreSQL all to itself for contact and response history.

> **This step genuinely needs your CI360 tenant credentials from the Prerequisites
> section.** The chart runs a pre-install Job (`ecr-auth-generator`) that exchanges
> `access-point-secret` + `api-user-secret` for a short-lived registry pull token, because
> SubjectContact's image lives in a private container registry. No valid credentials, no
> pulled image — this isn't something a local cluster can work around.

### 5.1 Add the CI360 Helm repo

```powershell
helm repo add ci360-helm-charts https://sassoftware.github.io/ci360-helm-charts/packages
helm repo update ci360-helm-charts
```

### 5.2 Create the CI360 credential secrets

`manifests\02-access-point-secret.yaml` and `manifests\03-api-user-secret.yaml` use
`${VAR}` placeholders — substitute them with your real values before applying:

```powershell
(Get-Content manifests\02-access-point-secret.yaml -Raw) `
    -replace '\$\{TENANT_ID\}',     $env:TENANT_ID `
    -replace '\$\{CLIENT_SECRET\}', $env:CLIENT_SECRET `
    -replace '\$\{TENANT_URL\}',    $env:TENANT_URL |
    kubectl apply -f -

(Get-Content manifests\03-api-user-secret.yaml -Raw) `
    -replace '\$\{API_USERNAME\}', $env:API_USERNAME `
    -replace '\$\{API_PASSWORD\}', $env:API_PASSWORD |
    kubectl apply -f -

# The decision container (Step 3) will need its own copy of api-user-secret too,
# in the ci360-shed-hues namespace instead of ci360-shed-hues-sub.
(Get-Content manifests\03-api-user-secret.yaml -Raw) `
    -replace '\$\{API_USERNAME\}', $env:API_USERNAME `
    -replace '\$\{API_PASSWORD\}', $env:API_PASSWORD `
    -replace 'namespace: ci360-shed-hues-sub', 'namespace: ci360-shed-hues' |
    kubectl apply -f -
```

### 5.3 Install — with a values override that keeps the built-in PostgreSQL light for a laptop

```powershell
$tenantHost = ($env:TENANT_URL -replace '^https?://' -replace '/.*$')

(Get-Content manifests\04-subjectcontact-values.yaml -Raw) `
    -replace '\$\{TENANT_HOST\}', $tenantHost `
    -replace '\$\{FLEET_API_GW\}', $env:FLEET_API_GW |
    helm upgrade --install sas-marketing-decisioning ci360-helm-charts/sas-marketing-decisioning `
      -n ci360-shed-hues-sub -f - --timeout=600s

kubectl rollout status deployment/subjectcontact -n ci360-shed-hues-sub --timeout=300s
```

> **Why not disable `postgresql-ha` entirely?** Because requirement #2 of this guide is
> specifically to use the chart's *built-in* PostgreSQL — that's `postgresql-ha.enabled: true`
> (the chart default!). `manifests\04-subjectcontact-values.yaml` only trims replica counts
> and resource requests so three PostgreSQL pods + a Pgpool pod don't need a small data
> center to run.
>
> **Note:** The pre-install registry-auth Job, the built-in PostgreSQL-HA
> cluster forming consensus, and the SubjectContact image pull can together take several
> minutes on a laptop — that's normal, not broken.

### 5.4 Verify

```powershell
kubectl get pods -n ci360-shed-hues-sub
kubectl get svc  -n ci360-shed-hues-sub
```

You should see a `subjectcontact` Deployment pod `Running`, plus the
`sas-marketing-decisioning-postgresql-ha-postgresql-0` pod and a `pgpool` pod alongside it.

---

## 6. Step 3 — Deploy the decision container (as two replicas)

This step deploys the decision image and connects it back to the
PostgreSQL from **Step 1** (not the SubjectContact one — different database, different job).

### 6.1 Prerequisites recap for this step

* The decision's **`unique_name`** (a DNS-safe, lowercase identifier) and its **image URI**.
* If the image lives in a **private registry** (e.g. the same container registry used for
  SubjectContact above), you'll need a pull secret — see §6.4. If it's a **publicly pullable
  image** (or one you've already `docker pull`-ed / `docker load`-ed into the Docker Desktop
  engine, which Kubernetes shares), you can skip the pull secret and rely on
  `imagePullPolicy: IfNotPresent`.
* The `api-user-secret` we already created in `ci360-shed-hues` (§5.2) — the decision
  container uses it at runtime to call back into CI360 contact/response APIs.

```powershell
$decisionName = "my-local-decision"        # <-- your decision's unique_name
# Image URIs look like this in the tenant UI / marketingContainerImage/images API:
#   861073095096.dkr.ecr.us-east-1.amazonaws.com/tenant-images-bctt33:mktdectransactionbasednbasecondary2026081712565650
$imageUri     = "REPLACE_ME/your-image:tag" # <-- your decision image URI
```

### 6.2 Database secret — give the decision access to BOTH PostgreSQL databases

The decision needs to query **two** separate databases at once:

1. The **customer data** PostgreSQL from **Step 1** (`ci360-shed-hues-pg`) — schema
   `TRAINCAT`.
2. SubjectContact's own **built-in** PostgreSQL from **Step 2** (`ci360-shed-hues-sub`) —
   database/schema `contactresponse`, which holds contact/response history. Reach it through
   its **pgpool** Service (`sas-marketing-decisioning-postgresql-ha-pgpool`) rather than a
   single `-postgresql` pod directly — pgpool is the load-balanced, HA-safe entry point the
   `postgresql-ha` subchart sets up for exactly this purpose.

Because both databases live in different namespaces than the decision (`ci360-shed-hues`),
we need each one's full cluster-DNS name. The username/database for SubjectContact's built-in
Postgres are fixed by the chart (`postgres` / `contactresponse`); only the password needs
retrieving, from the `subjectcontact-pg-auth` secret the chart created for you in Step 2:

```powershell
$pgHost = "ci360-postgres-postgresql.ci360-shed-hues-pg.svc.cluster.local"
$pgPort = "5432"

$subjectContactPgHost = "sas-marketing-decisioning-postgresql-ha-pgpool.ci360-shed-hues-sub.svc.cluster.local"
$subjectContactPgPasswordB64 = kubectl get secret subjectcontact-pg-auth -n ci360-shed-hues-sub -o jsonpath='{.data.password}'
$subjectContactPgPassword = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($subjectContactPgPasswordB64))

(Get-Content manifests\05-db-credentials-secret.yaml -Raw) `
    -replace '\$\{PG_HOST\}',                    $pgHost `
    -replace '\$\{PG_DATABASE\}',                $env:PG_DATABASE `
    -replace '\$\{PG_USER\}',                    $env:PG_USER `
    -replace '\$\{PG_PASSWORD\}',                $env:PG_PASSWORD `
    -replace '\$\{PG_PORT\}',                    $pgPort `
    -replace '\$\{SUBJECTCONTACT_PG_HOST\}',     $subjectContactPgHost `
    -replace '\$\{SUBJECTCONTACT_PG_PASSWORD\}', $subjectContactPgPassword |
    kubectl apply -f -
```

> **Why `postgres`/`contactresponse` and not something else?** SubjectContact's chart
> provisions its built-in database with a fixed username (`postgres`) and a fixed database
> name (`contactresponse`) — you can verify this yourself:
> `kubectl exec -n ci360-shed-hues-sub sas-marketing-decisioning-postgresql-ha-postgresql-0 -- env PGPASSWORD=$subjectContactPgPassword psql -h $subjectContactPgHost -U postgres -d contactresponse -p 5432 -c "\dt contactresponse.*"`
> — you should see `contact_history_attributes`, `decision_contact_history`,
> `presented_contact_history`, and `response_history`.
>
> **Already deployed the decision (§6.5) before running this?** Updating a Secret doesn't
> automatically restart pods that already mounted it. Run
> `kubectl rollout restart deployment/$decisionName -n ci360-shed-hues` afterward so both
> replicas pick up the refreshed `db.secrets` file.

### 6.3 Score file — configure it via a ConfigMap

In a full production deployment, the arbitration score file is often mounted from cloud
object storage so it can be refreshed without redeploying anything. Docker Desktop doesn't
have access to that kind of storage, so we'll use the Kubernetes-native equivalent for a
read-only file mount instead: a **ConfigMap**, built from `scores\external_score_customer_id.csv`
and mounted as a volume at the same path the decision container expects
(`/opt/scr/arbitration_score`).

```powershell
kubectl create configmap decision-scores `
  --from-file=external_score_customer_id.csv=scores\external_score_customer_id.csv `
  -n ci360-shed-hues `
  --dry-run=client -o yaml | kubectl apply -f -
```

> **Updating the score file later:** edit `scores\external_score_customer_id.csv`, re-run
> the `kubectl create configmap ... --dry-run ... | kubectl apply -f -` command above, then
> roll the decision pods (`kubectl rollout restart deployment/$decisionName -n
> ci360-shed-hues`) so they pick up the new mount — ConfigMap volumes refresh eventually, but
> a rollout guarantees it immediately.

### 6.4 Image pull secret - exchange your CI360 credentials for a registry token

Decision images live in a private container registry and are only pullable using a
short-lived token issued by CI360 - the same token-exchange process SubjectContact's chart
performed for you automatically in Step 2 (via its `ecr-auth-generator` Job). This time
there's no chart doing it behind the scenes, so we perform the exchange ourselves, in
PowerShell. It is worth reviewing this step carefully, because understanding *why* three HTTP
calls are needed just to pull a container image is the whole point of this step:

1. **Build a static JWT** locally from your `TENANT_ID` + `CLIENT_SECRET` (no network call - just
   HMAC-SHA256 signing).
2. **Exchange that JWT** (plus your `API_USERNAME`/`API_PASSWORD`) for a short-lived CI360
   **access token** by calling `POST {TENANT_URL}/token`.
3. **Use the access token** to call `GET {TENANT_URL}/marketingContainerImage/token`, which
   hands back a registry ("ECR") authorization token - a base64-encoded `username:password`
   pair good for pulling images from your tenant's private registry for a few hours.

```powershell
function ConvertTo-Base64Url([byte[]]$Bytes) {
    [Convert]::ToBase64String($Bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

# CI360's own token-exchange job retries transient failures 3x with a 10s pause -
# mirror that here so a single dropped connection doesn't derail you.
function Invoke-Ci360Request {
    param([string]$Method, [string]$Uri, [hashtable]$Headers, [hashtable]$Body, [string]$ContentType)
    $maxAttempts = 3
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        try {
            if ($Body) {
                return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers -Body $Body -ContentType $ContentType -TimeoutSec 30
            }
            return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers -TimeoutSec 30
        } catch {
            Write-Warning "Attempt $attempt/$maxAttempts to reach $Uri failed: $($_.Exception.Message)"
            if ($attempt -eq $maxAttempts) { throw }
            Start-Sleep -Seconds 10
        }
    }
}

# 1. Build an HS256 JWT from your tenant ID + client secret
$header  = '{"alg":"HS256","typ":"JWT"}'
$payload = "{`"clientID`":`"$env:TENANT_ID`"}"
$headerB64  = ConvertTo-Base64Url ([Text.Encoding]::UTF8.GetBytes($header))
$payloadB64 = ConvertTo-Base64Url ([Text.Encoding]::UTF8.GetBytes($payload))

# Key = base64(client_secret) - the bytes of the base64 text, not the decoded secret
$keyBytes = [Text.Encoding]::UTF8.GetBytes(
    [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($env:CLIENT_SECRET)))
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = $keyBytes
$sigBytes = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes("$headerB64.$payloadB64"))
$jwt = "$headerB64.$payloadB64.$(ConvertTo-Base64Url $sigBytes)"

# 2. Exchange the JWT + your API user credentials for a CI360 access token
# (normalize TENANT_URL in case it was set without a scheme, e.g. "extapigwservice-training.ci360.sas.com")
$tenantBase = $env:TENANT_URL
if ($tenantBase -notmatch '^https?://') { $tenantBase = "https://$tenantBase" }
$tokenUrl = $tenantBase.TrimEnd('/') + "/token"
$body = @{ grant_type = "password"; username = $env:API_USERNAME; password = $env:API_PASSWORD }
$resp = Invoke-Ci360Request -Method Post -Uri $tokenUrl `
    -Headers @{ Authorization = "Bearer $jwt" } -Body $body -ContentType "application/x-www-form-urlencoded"
$accessToken = $resp.access_token
if (-not $accessToken) { throw "No access_token in CI360 response - check TENANT_ID/CLIENT_SECRET/API_USERNAME/API_PASSWORD." }

# 3. Use the access token to fetch a registry ("ECR") authorization token
$imageTokenUrl = $tenantBase.TrimEnd('/') + "/marketingContainerImage/token"
$imgTokenResp = Invoke-Ci360Request -Method Get -Uri $imageTokenUrl -Headers @{ Authorization = "Bearer $accessToken" }
$authToken = ($imgTokenResp.tokenDetails | Where-Object { $_.authorizationToken })[0].authorizationToken
if (-not $authToken) { throw "No authorizationToken in marketingContainerImage/token response." }

# 4. Decode it (it's base64 "username:password") and derive the registry from $imageUri
$decoded = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($authToken))
$registryUser, $registryPass = $decoded.Split(':', 2)
$registryHost = $imageUri.Split('/')[0]   # e.g. 861073095096.dkr.ecr.us-east-1.amazonaws.com

kubectl create secret docker-registry decision-pull-secret `
    --docker-server="$registryHost" `
    --docker-username="$registryUser" `
    --docker-password="$registryPass" `
    -n ci360-shed-hues `
    --dry-run=client -o yaml | kubectl apply -f -
```

> **Important:** these registry tokens are short-lived (they typically expire within hours). If
> pods later fail to pull with `401`/`403`, just re-run this whole block to mint a fresh
> token and re-apply the secret.
>
> **Getting `Unable to connect to the remote server` on step 2 or 3?** The #1 cause is
> `$env:TENANT_URL` missing its `https://` scheme (e.g. it was set to just
> `extapigwservice-training.ci360.sas.com` instead of `https://extapigwservice-training.ci360.sas.com`)
> — a schemeless URL fails to connect outright. The script above normalizes this into
> `$tenantBase` automatically, so as long as `$env:TENANT_URL` is set to *some* form of the
> right host you're covered. If it still fails after 3 retries: confirm there's no trailing
> path beyond the host, confirm you have outbound internet access (no VPN/proxy blocking it),
> and try running just the `Invoke-RestMethod` call on its own a minute later.
>
> **Don't have a decision image yet?** List what's available in your tenant with:
> `Invoke-RestMethod -Method Get -Uri "$($tenantBase.TrimEnd('/'))/marketingContainerImage/images?limit=1000" -Headers @{ Authorization = "Bearer $accessToken" }`
> - each entry's `imageUris` gives you the full image URI (registry/repo:tag) shown in the
> tenant UI, e.g. `861073095096.dkr.ecr.us-east-1.amazonaws.com/tenant-images-bctt33:mktdectransactionbasednbasecondary2026081712565650`.
>
> **Testing with a publicly pullable image instead?** You can skip this whole section -
> just delete the `imagePullSecrets:` block from `manifests\06-decision-deployment.yaml`
> before applying it in the next step (otherwise Kubernetes will complain about a missing
> secret reference).
### 6.5 Deployment and Service — two replicas, `SAS_SCR_APP_PATH` configured

`manifests\06-decision-deployment.yaml` and `manifests\07-decision-service.yaml` use
`decision-placeholder` and `${IMAGE_URI}` as placeholders — substitute them:

```powershell
(Get-Content manifests\06-decision-deployment.yaml -Raw) `
    -replace 'decision-placeholder', $decisionName `
    -replace '\$\{IMAGE_URI\}',      $imageUri |
    kubectl apply -f -

(Get-Content manifests\07-decision-service.yaml -Raw) `
    -replace 'decision-placeholder', $decisionName |
    kubectl apply -f -

kubectl rollout status deployment/$decisionName -n ci360-shed-hues --timeout=300s
```

> **Recreated or fixed `decision-pull-secret` *after* the pods already existed?** Existing
> `ImagePullBackOff` pods don't automatically retry with a freshly (re)created secret if
> `kubectl apply` reports the Deployment as `unchanged` (no rollout gets triggered). Force it
> with `kubectl delete pod -n ci360-shed-hues -l app=$decisionName` — the ReplicaSet
> immediately recreates them, and this time they'll pick up the current secret.

> **`SAS_SCR_APP_PATH` explained:** this environment variable (already set inside
> `manifests\06-decision-deployment.yaml`, following the `decision-placeholder` substitution
> above) tells the decision container which URL path to expose its REST API under (e.g.
> `/my-local-decision`). It must match the path segment you'll call in Step 4. If you're
> deploying in **batch mode** instead of realtime, add `SAS_SCR_REST_API_TYPE: "BATCH"` right
> after `SAS_SCR_APP_PATH` in the manifest's `env` list, and suffix the resource name with
> `-b` (e.g. `$decisionName-b`) so realtime and batch variants can run side by side.

### 6.6 Verify

```powershell
kubectl get pods -n ci360-shed-hues -l app=$decisionName
```

You should see **two** pods for `$decisionName`, both `Running` and `1/1 Ready` — proof that
"two nodes" made it into the spec, even though Docker Desktop schedules both onto the same
physical node.

---

## 7. Step 4 — Execute the decision via its API

Decision Services are `ClusterIP`, so we reach them from our laptop with `kubectl
port-forward`.

```powershell
# Leave this running in its own PowerShell window / tab
kubectl port-forward svc/$decisionName 8080:8080 -n ci360-shed-hues
```

In a second PowerShell window:

```powershell
# Adjust the payload for your decision's actual expected schema —
# this is a representative example for a "score by customer id" style decision.
$response = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8080/$decisionName" `
    -Method POST `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body '{
        "data": {
            "page": "",
            "customer_id": "33",
            "channel_id": "web",
            "intent": "help",
            "search_term": "",
            "savings_calculator": 0,
            "loan_applicant": 0,
            "payment_issue": 0
        }
    }'

$response.data | ConvertTo-Json -Depth 100
```

> **No response, or a 404?** Double-check `SAS_SCR_APP_PATH` matches the URL path you're
> calling, and check the pod logs: `kubectl logs -n ci360-shed-hues deployment/$decisionName`.

---

## 8. Step 5 — Execute the SubjectContact API

Same drill, different namespace and port:

```powershell
# Leave this running in its own PowerShell window / tab
kubectl port-forward svc/subjectcontact 8081:8080 -n ci360-shed-hues-sub
```

```powershell
# Example health/status check — replace with your actual SubjectContact endpoint & payload.
$headers=@{}
$headers.Add("Content-Type", "application/json")
$headers.Add("User-Agent", "insomnia/12.3.1")
$response = Invoke-WebRequest -Uri 'http://localhost:8081/marketingDecisioningSubjectContact/responses' -Method POST -Headers $headers -ContentType 'application/json' -Body '{
    "items": [
        {
            "responseTxt": "Reject",
            "responseTypeTxt": "reject",
            "responseTypeCode": "REJECT",
            "responseChannel": "crm",
            "responseTrackingCode": "123",
            "responseDateTime": "2026-04-24T09:03:19.697Z",
            "identityValue": "1111",
            "identityType": "customer_id",
            "subjectLevel": "customer",
            "actionCode": "ext-code-123", 
            "actionCategory": "cross sell",
            "actionType": "offer"
        },{
            "responseTxt": "Reject",
            "responseTypeTxt": "reject",
            "responseTypeCode": "REJECT",
            "responseChannel": "crm",
            "responseTrackingCode": "123",
            "responseDateTime": "2026-04-24T09:03:19.697Z",
            "identityValue": "1111",
            "identityType": "customer_id",
            "subjectLevel": "customer",
            "actionCode": "ext-code-123", 
            "actionCategory": "cross sell",
            "actionType": "offer"
        }
    ]
}'

$response
```

> **Tip:** `kubectl get svc -n ci360-shed-hues-sub` will confirm the exact Service name and
> port if it differs from the defaults shown here (both are `subjectcontact` / `8080` as
> deployed by the chart's default values).

---

## 9. Step 6 — Remove the decision

```powershell
kubectl delete deployment,service $decisionName -n ci360-shed-hues
kubectl delete secret db-credentials -n ci360-shed-hues
kubectl delete configmap decision-scores -n ci360-shed-hues
# Only if you created one in §6.4:
kubectl delete secret decision-pull-secret -n ci360-shed-hues --ignore-not-found
```

---

## 10. Step 7 — Remove SubjectContact

```powershell
helm uninstall sas-marketing-decisioning -n ci360-shed-hues-sub
```

> **Note:** the built-in PostgreSQL-HA's PersistentVolumeClaims carry the
> `helm.sh/resource-policy: keep` annotation by default, so they'll survive the uninstall.
> Clean them up explicitly if you want a truly fresh start:
> `kubectl delete pvc -n ci360-shed-hues-sub --all`

---

## 11. Step 8 — Remove PostgreSQL

```powershell
helm uninstall ci360-postgres -n ci360-shed-hues-pg
kubectl delete pvc -n ci360-shed-hues-pg --all
```

---

## 12. Bonus: nuke everything in one go

```powershell
helm uninstall sas-marketing-decisioning -n ci360-shed-hues-sub --ignore-not-found 2>$null
helm uninstall ci360-postgres -n ci360-shed-hues-pg --ignore-not-found 2>$null
kubectl delete namespace ci360-shed-hues ci360-shed-hues-sub ci360-shed-hues-pg --ignore-not-found
```

Deleting the namespaces cleans up every Deployment, Service, Secret, ConfigMap, and PVC
inside them — the fastest possible reset button. (The files in `hands-on/` are untouched —
they're just manifests, safe to keep around for the next time you want to run through this.)

---

## 13. Troubleshooting & tips for the local (Docker Desktop) environment

| Symptom | Likely cause | Fix |
|---|---|---|
| PostgreSQL pod stuck `Pending` | Docker Desktop's `hostpath` StorageClass isn't the default, or resources are too tight | `kubectl get storageclass` — confirm `(default)` next to `hostpath`; bump Docker Desktop's CPU/RAM allocation |
| SubjectContact's `ecr-auth-generator` Job fails | Invalid/expired CI360 credentials, or Docker Desktop has no internet access | Re-check `$env:TENANT_URL/TENANT_ID/CLIENT_SECRET/API_USERNAME/API_PASSWORD`; `kubectl logs job/sas-marketing-decisioning-ecr-auth-generator -n ci360-shed-hues-sub` |
| `ImagePullBackOff` on the decision pods | Missing/expired pull secret, wrong image URI, or the pods predate the secret's (re)creation | `kubectl describe pod -n ci360-shed-hues -l app=$decisionName` for the exact error (e.g. `no basic auth credentials` means the pod isn't picking up the secret at all — delete the pods to force a retry); short-lived registry tokens can expire in hours — regenerate per §6.4 |
| Decision pod `Running` but not `Ready` | `SAS_SCR_APP_PATH` mismatch, or the DB secret/ConfigMap wasn't mounted | `kubectl logs deployment/$decisionName -n ci360-shed-hues`; `kubectl describe pod ...` to check volume mount events |
| Everything is sluggish / pods slowly cycling `CrashLoopBackOff` | Docker Desktop is under-resourced for 2× PostgreSQL + SubjectContact + 2 decision replicas | Bump Docker Desktop to more CPUs/RAM (Settings → Resources), or scale `postgresql.replicaCount`/resources down further in `manifests\04-subjectcontact-values.yaml`, or drop the decision `replicas` to `1` while iterating |
| `kubectl cp` says `one of src or dest must be a local file specification` | A Windows drive letter (`C:\...`) in the path is being parsed as a `pod:path` separator | Run the command from inside `hands-on/` using the relative paths shown in this guide (e.g. `csv\file.csv`) instead of a full Windows path |

> **Summary:** You have now deployed, exercised, and torn down a complete SAS 360 Marketing
> Decisioning stack entirely on your own laptop — PostgreSQL with an explicitly defined
> schema, SubjectContact running with its own built-in database, and a two-replica decision
> container connecting to both. This exercise demonstrates how these components fit together
> in any environment, cloud or otherwise.
