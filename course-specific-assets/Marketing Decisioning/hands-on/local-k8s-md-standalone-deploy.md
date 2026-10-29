# Hands-On: Deploying SAS 360 Marketing Decisioning (Standalone) on Local Kubernetes
### Cross-platform edition — Windows (PowerShell) and macOS/Linux (bash/zsh)

> **Purpose of this guide:** Same exercise as the original — deploy PostgreSQL,
> SubjectContact, and a decision container on the Kubernetes cluster built into Docker
> Desktop — but every command block below is given **twice**: once for **Windows
> PowerShell**, once for **macOS/Linux Terminal (bash/zsh)**. Run the block that matches
> your OS and skip the other.
>
> Everything still runs entirely on your laptop's local Kubernetes cluster — no cloud
> account, no cluster-specific storage drivers, no object storage. Just Docker Desktop,
> `kubectl`, and `helm`.

---

## 0. Platform notes (read this first)

| Tool | Windows | macOS/Linux |
|---|---|---|
| Shell | PowerShell 5.1+ or 7+ | bash or zsh (Terminal) |
| Line continuation in multi-line commands | backtick `` ` `` at end of line | backslash `\` at end of line |
| String substitution in manifests | `Get-Content ... -replace` | `sed` (or `envsubst`) |
| Base64 decode | `[Convert]::FromBase64String` | `base64 -D` (macOS/BSD) or `base64 -d` (Linux/GNU) |
| HMAC-SHA256 signing | `System.Security.Cryptography.HMACSHA256` | `openssl dgst -hmac` |
| HTTP calls | `Invoke-RestMethod` / `Invoke-WebRequest` | `curl` |
| JSON parsing | native (`ConvertFrom-Json`) | `jq` (install once: `brew install jq`) |

**macOS/Linux prerequisites to install once**, in addition to Docker Desktop, `kubectl`,
and `helm`:

```bash
# macOS (Homebrew) — openssl and curl already ship with macOS, jq usually does not
brew install jq

# Debian/Ubuntu, if you're on Linux instead of macOS
sudo apt-get install -y jq curl openssl
```

Everywhere below, `hands-on/` paths use backslashes (`manifests\...`) on Windows and
forward slashes (`manifests/...`) on macOS/Linux — same folder, just OS-native path
separators.

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

| Namespace | Contents |
|---|---|
| `ci360-shed-hues-pg` | PostgreSQL for customer/decision data |
| `ci360-shed-hues-sub` | SubjectContact (+ its own built-in PostgreSQL) |
| `ci360-shed-hues` | Decision container(s) |

> **Naming:** these namespace names are just a convention — rename freely, just stay
> consistent with whatever you choose.

## 2. Folder contents

```
hands-on/
├── local-k8s-md-standalone-deploy.md
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
│   └── 01_schemas_tables.sql
├── csv/
│   ├── nexus_customer_sample.csv
│   ├── bk_customers_sample.csv
│   └── customer_drf_sample.csv
└── scores/
    └── external_score_customer_id.csv
```

> **Tip:** run every command in this guide from inside the `hands-on/` folder.

---

## 3. Prerequisites

| # | Requirement | Why you need it |
|---|---|---|
| 1 | **Docker Desktop** with **Kubernetes enabled**. Cluster Type used is **kubeadm** | This *is* the cluster. Same on Windows and Mac. |
| 2 | At least **4 vCPUs / 8 GB RAM** allocated to Docker Desktop | Two PostgreSQL instances + SubjectContact + decision pods run side by side. |
| 3 | `kubectl` pointed at the `docker-desktop` context | `kubectl config use-context docker-desktop` |
| 4 | `helm` v3+ | Installs the PostgreSQL and SubjectContact charts. |
| 5 | **Windows:** PowerShell 5.1+ or 7+. **macOS/Linux:** bash or zsh, plus `jq`, `curl`, `openssl` (see §0) | Shell for running the commands in this guide. |
| 6 | **A real SAS CI360 tenant's credentials** (`TENANT_URL`, `TENANT_ID`, `CLIENT_SECRET`, `API_USERNAME`, `API_PASSWORD`) | Not optional, even locally — see the original guide's explanation. |
| 7 | **Your tenant's Fleets API gateway URL** (`FLEET_API_GW`) | e.g. `https://fleetsapigw-training.ci360.sas.com/` |
| 8 | **A decision container image** — `unique_name` and image URI | The decision you're deploying in Step 3. |

### 3.1 Point your tools at the local cluster

*(identical on both platforms)*

```bash
kubectl config use-context docker-desktop
kubectl get nodes                      # should show a single Ready node
kubectl get storageclass               # "hostpath" should be present and (default)
```

### 3.2 Step into the hands-on folder

**Windows (PowerShell):**
```powershell
cd path\to\md-toolkit\hands-on
```

**macOS/Linux (bash):**
```bash
cd path/to/md-toolkit/hands-on
```

### 3.3 Set your environment variables

> **`TENANT_URL` and `FLEET_API_GW` must include the `https://` scheme.**

**Windows (PowerShell):**
```powershell
$env:TENANT_URL     = "https://extapigwservice-training.ci360.sas.com"
$env:TENANT_ID       = "REPLACE_ME"
$env:CLIENT_SECRET   = "REPLACE_ME"
$env:API_USERNAME    = "REPLACE_ME"
$env:API_PASSWORD    = "REPLACE_ME"
$env:FLEET_API_GW    = "https://fleetsapigw-training.ci360.sas.com/"

$env:PG_DATABASE     = "ci360db"
$env:PG_USER         = "ci360user"
$env:PG_PASSWORD     = "Orion123"
```

**macOS/Linux (bash):**
```bash
export TENANT_URL="https://extapigwservice-training.ci360.sas.com"
export TENANT_ID="REPLACE_ME"
export CLIENT_SECRET="REPLACE_ME"
export API_USERNAME="REPLACE_ME"
export API_PASSWORD="REPLACE_ME"
export FLEET_API_GW="https://fleetsapigw-training.ci360.sas.com/"

export PG_DATABASE="ci360db"
export PG_USER="ci360user"
export PG_PASSWORD="Orion123"
```

> These `export`s only last for the current terminal session — re-run them (or put them
> in a `.env` file you `source`) if you open a new tab.

---

## 4. Step 1 — Deploy PostgreSQL and load the customer data

### 4.1 Create the namespaces

*(identical on both platforms)*
```bash
kubectl apply -f manifests/00-namespaces.yaml
```
*(Windows: `manifests\00-namespaces.yaml`)*

### 4.2 Add the Bitnami Helm repo and install PostgreSQL

*(identical on both platforms — helm/kubectl syntax doesn't change)*

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update bitnami
```

**Windows (PowerShell):**
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

**macOS/Linux (bash):**
```bash
helm upgrade --install ci360-postgres bitnami/postgresql \
  -n ci360-shed-hues-pg \
  -f manifests/01-postgres-values.yaml \
  --set=auth.database="$PG_DATABASE" \
  --set=auth.username="$PG_USER" \
  --set=auth.password="$PG_PASSWORD" \
  --timeout=300s

kubectl rollout status statefulset/ci360-postgres-postgresql -n ci360-shed-hues-pg --timeout=300s
```

### 4.3 Create the schema

**Windows (PowerShell):**
```powershell
Get-Content sql\01_schemas_tables.sql -Raw | kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- `
    sh -c "PGPASSWORD=$env:PG_PASSWORD psql -h 127.0.0.1 -U $env:PG_USER -d $env:PG_DATABASE"
```

**macOS/Linux (bash):**
```bash
cat sql/01_schemas_tables.sql | kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- \
    sh -c "PGPASSWORD=$PG_PASSWORD psql -h 127.0.0.1 -U $PG_USER -d $PG_DATABASE"
```

You should see a stream of `CREATE SCHEMA` / `CREATE TABLE` / `CREATE INDEX` messages. ✅

### 4.4 (Optional) Set the search_path

**Windows (PowerShell):**
```powershell
$pgSuperPassword = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(
    (kubectl get secret ci360-postgres-postgresql -n ci360-shed-hues-pg -o jsonpath="{.data.postgres-password}")
))

"ALTER ROLE $env:PG_USER SET search_path = ""TRAINCAT"", public;" | `
    kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- `
    sh -c "PGPASSWORD=$pgSuperPassword psql -h 127.0.0.1 -U postgres -d $env:PG_DATABASE"
```

**macOS/Linux (bash):**
```bash
pgSuperPassword=$(kubectl get secret ci360-postgres-postgresql -n ci360-shed-hues-pg \
    -o jsonpath="{.data.postgres-password}" | base64 -D)
# On Linux (GNU base64), use: | base64 -d

echo "ALTER ROLE $PG_USER SET search_path = \"TRAINCAT\", public;" | \
    kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- \
    sh -c "PGPASSWORD=$pgSuperPassword psql -h 127.0.0.1 -U postgres -d $PG_DATABASE"
```

### 4.5 Load sample customer data

**Windows (PowerShell):**
```powershell
kubectl cp csv\training_data.csv ci360-shed-hues-pg/ci360-postgres-postgresql-0:/tmp/training_data.csv

$copyCmds = @"
\copy "TRAINCAT".training_data FROM '/tmp/training_data.csv' DELIMITER ',' CSV HEADER;
"@
$copyCmds | kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- `
    sh -c "PGPASSWORD=$env:PG_PASSWORD psql -h 127.0.0.1 -U $env:PG_USER -d $env:PG_DATABASE"
```

**macOS/Linux (bash):**
```bash
kubectl cp csv/training_data.csv ci360-shed-hues-pg/ci360-postgres-postgresql-0:/tmp/training_data.csv

copyCmds='\copy "TRAINCAT".training_data FROM '"'"'/tmp/training_data.csv'"'"' DELIMITER '"'"','"'"' CSV HEADER;'
echo "$copyCmds" | kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- \
    sh -c "PGPASSWORD=$PG_PASSWORD psql -h 127.0.0.1 -U $PG_USER -d $PG_DATABASE"
```

> Quoting tip for macOS/Linux: it's often easier to write the `\copy` command to a small
> local file and pipe that in instead of fighting nested quotes:
> ```bash
> printf '%s\n' '\copy "TRAINCAT".training_data FROM '"'"'/tmp/training_data.csv'"'"' DELIMITER '"'"','"'"' CSV HEADER;' > /tmp/copy.sql
> cat /tmp/copy.sql | kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- \
>     sh -c "PGPASSWORD=$PG_PASSWORD psql -h 127.0.0.1 -U $PG_USER -d $PG_DATABASE"
> ```

> **`kubectl cp` path note:** on Windows, a full drive-letter path (`C:\...`) can confuse
> `kubectl cp`'s `pod:path` parsing — run from inside `hands-on/` with relative paths. On
> macOS/Linux this isn't an issue (no drive letters), but relative paths from `hands-on/`
> are still the simplest.

### 4.6 Verify

**Windows (PowerShell):**
```powershell
"SELECT count(*) FROM ""TRAINCAT"".training_data;" | `
    kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- `
    sh -c "PGPASSWORD=$env:PG_PASSWORD psql -h 127.0.0.1 -U $env:PG_USER -d $env:PG_DATABASE"
```

**macOS/Linux (bash):**
```bash
echo 'SELECT count(*) FROM "TRAINCAT".training_data;' | \
    kubectl exec -i -n ci360-shed-hues-pg ci360-postgres-postgresql-0 -- \
    sh -c "PGPASSWORD=$PG_PASSWORD psql -h 127.0.0.1 -U $PG_USER -d $PG_DATABASE"
```

You should see `120` come back.

---

## 5. Step 2 — Deploy SubjectContact (using its own built-in PostgreSQL)

### 5.1 Add the CI360 Helm repo

*(identical on both platforms)*
```bash
helm repo add ci360-helm-charts https://sassoftware.github.io/ci360-helm-charts/packages
helm repo update ci360-helm-charts
```

### 5.2 Create the CI360 credential secrets

**Windows (PowerShell):**
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

(Get-Content manifests\03-api-user-secret.yaml -Raw) `
    -replace '\$\{API_USERNAME\}', $env:API_USERNAME `
    -replace '\$\{API_PASSWORD\}', $env:API_PASSWORD `
    -replace 'namespace: ci360-shed-hues-sub', 'namespace: ci360-shed-hues' |
    kubectl apply -f -
```

**macOS/Linux (bash):**
```bash
sed -e "s|\${TENANT_ID}|$TENANT_ID|g" \
    -e "s|\${CLIENT_SECRET}|$CLIENT_SECRET|g" \
    -e "s|\${TENANT_URL}|$TENANT_URL|g" \
    manifests/02-access-point-secret.yaml | kubectl apply -f -

sed -e "s|\${API_USERNAME}|$API_USERNAME|g" \
    -e "s|\${API_PASSWORD}|$API_PASSWORD|g" \
    manifests/03-api-user-secret.yaml | kubectl apply -f -

# The decision container (Step 3) needs its own copy in ci360-shed-hues too
sed -e "s|\${API_USERNAME}|$API_USERNAME|g" \
    -e "s|\${API_PASSWORD}|$API_PASSWORD|g" \
    -e "s|namespace: ci360-shed-hues-sub|namespace: ci360-shed-hues|g" \
    manifests/03-api-user-secret.yaml | kubectl apply -f -
```

> `sed` note: the examples use `|` as the `sed` delimiter instead of `/` because
> `TENANT_URL` itself contains slashes — this avoids escaping them.

### 5.3 Install SubjectContact

**Windows (PowerShell):**
```powershell
$tenantHost = ($env:TENANT_URL -replace '^https?://' -replace '/.*$')

(Get-Content manifests\04-subjectcontact-values.yaml -Raw) `
    -replace '\$\{TENANT_HOST\}', $tenantHost `
    -replace '\$\{FLEET_API_GW\}', $env:FLEET_API_GW |
    helm upgrade --install sas-marketing-decisioning ci360-helm-charts/sas-marketing-decisioning `
      -n ci360-shed-hues-sub -f - --timeout=600s

kubectl rollout status deployment/subjectcontact -n ci360-shed-hues-sub --timeout=300s
```

**macOS/Linux (bash):**
```bash
tenantHost=$(echo "$TENANT_URL" | sed -E 's|^https?://||; s|/.*$||')

sed -e "s|\${TENANT_HOST}|$tenantHost|g" \
    -e "s|\${FLEET_API_GW}|$FLEET_API_GW|g" \
    manifests/04-subjectcontact-values.yaml | \
  helm upgrade --install sas-marketing-decisioning ci360-helm-charts/sas-marketing-decisioning \
    -n ci360-shed-hues-sub -f - --timeout=600s

kubectl rollout status deployment/subjectcontact -n ci360-shed-hues-sub --timeout=300s
```

> This can take several minutes (registry-auth Job + PostgreSQL-HA consensus + image
> pull) — that's normal on both platforms.

### 5.4 Verify

*(identical on both platforms)*
```bash
kubectl get pods -n ci360-shed-hues-sub
kubectl get svc  -n ci360-shed-hues-sub
```

---

## 6. Step 3 — Deploy the decision container (as two replicas)

### 6.1 Prerequisites recap

Same as the original guide: the decision's `unique_name`, its image URI, and (if private)
a pull secret set up in §6.4.

**Windows (PowerShell):**
```powershell
$decisionName = "my-local-decision"
$imageUri     = "REPLACE_ME/your-image:tag"
```

**macOS/Linux (bash):**
```bash
decisionName="my-local-decision"
imageUri="REPLACE_ME/your-image:tag"
```

### 6.2 Database secret — access to both PostgreSQL databases

**Windows (PowerShell):**
```powershell
$pgHost = "ci360-postgres-postgresql.ci360-shed-hues-pg.svc.cluster.local"
$pgPort = "5432"

$subjectContactPgHost = "sas-marketing-decisioning-cnpg-rw.ci360-shed-hues-sub.svc.cluster.local"
$subjectContactPgPasswordB64 = kubectl get secret subjectcontact-cnpg-auth -n ci360-shed-hues-sub -o jsonpath='{.data.password}'
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

**macOS/Linux (bash):**
```bash
pgHost="ci360-postgres-postgresql.ci360-shed-hues-pg.svc.cluster.local"
pgPort="5432"

subjectContactPgHost="sas-marketing-decisioning-postgresql-ha-pgpool.ci360-shed-hues-sub.svc.cluster.local"
subjectContactPgPasswordB64=$(kubectl get secret subjectcontact-pg-auth -n ci360-shed-hues-sub -o jsonpath='{.data.password}')
subjectContactPgPassword=$(echo "$subjectContactPgPasswordB64" | base64 -D)
# Linux (GNU base64): | base64 -d

sed -e "s|\${PG_HOST}|$pgHost|g" \
    -e "s|\${PG_DATABASE}|$PG_DATABASE|g" \
    -e "s|\${PG_USER}|$PG_USER|g" \
    -e "s|\${PG_PASSWORD}|$PG_PASSWORD|g" \
    -e "s|\${PG_PORT}|$pgPort|g" \
    -e "s|\${SUBJECTCONTACT_PG_HOST}|$subjectContactPgHost|g" \
    -e "s|\${SUBJECTCONTACT_PG_PASSWORD}|$subjectContactPgPassword|g" \
    manifests/05-db-credentials-secret.yaml | kubectl apply -f -
```

> If you already deployed the decision before running this, remember to run
> `kubectl rollout restart deployment/$decisionName -n ci360-shed-hues` afterward
> (`$decisionName` on macOS/Linux, `$env:decisionName`-style variable isn't needed since
> `$decisionName` works directly in both PowerShell and bash once set as above).

### 6.3 Score file — ConfigMap

*(identical on both platforms — just watch the path separator)*

**Windows (PowerShell):**
```powershell
kubectl create configmap decision-scores `
  --from-file=external_score_customer_id.csv=scores\external_score_customer_id.csv `
  -n ci360-shed-hues `
  --dry-run=client -o yaml | kubectl apply -f -
```

**macOS/Linux (bash):**
```bash
kubectl create configmap decision-scores \
  --from-file=external_score_customer_id.csv=scores/external_score_customer_id.csv \
  -n ci360-shed-hues \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 6.4 Image pull secret — exchange CI360 credentials for a registry token

Same three-call flow: build a JWT locally, exchange it for an access token, then exchange
that for a registry auth token.

**Windows (PowerShell):**
```powershell
function ConvertTo-Base64Url([byte[]]$Bytes) {
    [Convert]::ToBase64String($Bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

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

$header  = '{"alg":"HS256","typ":"JWT"}'
$payload = "{`"clientID`":`"$env:TENANT_ID`"}"
$headerB64  = ConvertTo-Base64Url ([Text.Encoding]::UTF8.GetBytes($header))
$payloadB64 = ConvertTo-Base64Url ([Text.Encoding]::UTF8.GetBytes($payload))

$keyBytes = [Text.Encoding]::UTF8.GetBytes(
    [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($env:CLIENT_SECRET)))
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = $keyBytes
$sigBytes = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes("$headerB64.$payloadB64"))
$jwt = "$headerB64.$payloadB64.$(ConvertTo-Base64Url $sigBytes)"

$tenantBase = $env:TENANT_URL
if ($tenantBase -notmatch '^https?://') { $tenantBase = "https://$tenantBase" }
$tokenUrl = $tenantBase.TrimEnd('/') + "/token"
$body = @{ grant_type = "password"; username = $env:API_USERNAME; password = $env:API_PASSWORD }
$resp = Invoke-Ci360Request -Method Post -Uri $tokenUrl `
    -Headers @{ Authorization = "Bearer $jwt" } -Body $body -ContentType "application/x-www-form-urlencoded"
$accessToken = $resp.access_token
if (-not $accessToken) { throw "No access_token in CI360 response - check TENANT_ID/CLIENT_SECRET/API_USERNAME/API_PASSWORD." }

$imageTokenUrl = $tenantBase.TrimEnd('/') + "/marketingContainerImage/token"
$imgTokenResp = Invoke-Ci360Request -Method Get -Uri $imageTokenUrl -Headers @{ Authorization = "Bearer $accessToken" }
$authToken = ($imgTokenResp.tokenDetails | Where-Object { $_.authorizationToken })[0].authorizationToken
if (-not $authToken) { throw "No authorizationToken in marketingContainerImage/token response." }

$decoded = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($authToken))
$registryUser, $registryPass = $decoded.Split(':', 2)
$registryHost = $imageUri.Split('/')[0]

kubectl create secret docker-registry decision-pull-secret `
    --docker-server="$registryHost" `
    --docker-username="$registryUser" `
    --docker-password="$registryPass" `
    -n ci360-shed-hues `
    --dry-run=client -o yaml | kubectl apply -f -
```

**macOS/Linux (bash)** — uses `openssl` for HMAC/base64url and `jq`/`curl` in place of
`Invoke-RestMethod`:

```bash
# --- helpers ---------------------------------------------------------------

b64url() {
  # reads raw bytes on stdin, writes URL-safe base64 without padding
  openssl base64 -A | tr '+/' '-_' | tr -d '='
}

ci360_curl() {
  # retries like the PowerShell version: 3 attempts, 10s apart
  local max_attempts=3 attempt=1
  while [ $attempt -le $max_attempts ]; do
    if resp=$(curl -sS -f "$@"); then
      echo "$resp"
      return 0
    fi
    echo "Attempt $attempt/$max_attempts failed" >&2
    attempt=$((attempt+1))
    [ $attempt -le $max_attempts ] && sleep 10
  done
  return 1
}

# --- 1. Build an HS256 JWT from TENANT_ID + CLIENT_SECRET -------------------

header='{"alg":"HS256","typ":"JWT"}'
payload="{\"clientID\":\"$TENANT_ID\"}"
headerB64=$(printf '%s' "$header"  | b64url)
payloadB64=$(printf '%s' "$payload" | b64url)

# Key = base64(client_secret) — the bytes of the base64 TEXT, not the decoded secret
keyB64text=$(printf '%s' "$CLIENT_SECRET" | openssl base64 -A)

sigB64=$(printf '%s.%s' "$headerB64" "$payloadB64" | \
    openssl dgst -sha256 -hmac "$keyB64text" -binary | b64url)

jwt="$headerB64.$payloadB64.$sigB64"

# --- 2. Exchange the JWT + API user credentials for a CI360 access token ---

tenantBase="$TENANT_URL"
case "$tenantBase" in
  http://*|https://*) ;;
  *) tenantBase="https://$tenantBase" ;;
esac
tenantBase="${tenantBase%/}"
tokenUrl="$tenantBase/token"

tokenResp=$(ci360_curl -X POST "$tokenUrl" \
    -H "Authorization: Bearer $jwt" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=password" \
    --data-urlencode "username=$API_USERNAME" \
    --data-urlencode "password=$API_PASSWORD") || { echo "Failed to reach $tokenUrl after retries" >&2; exit 1; }

accessToken=$(echo "$tokenResp" | jq -r '.access_token // empty')
if [ -z "$accessToken" ]; then
  echo "No access_token in CI360 response - check TENANT_ID/CLIENT_SECRET/API_USERNAME/API_PASSWORD." >&2
  exit 1
fi

# --- 3. Use the access token to fetch a registry ("ECR") auth token --------

imageTokenUrl="$tenantBase/marketingContainerImage/token"
imgTokenResp=$(ci360_curl "$imageTokenUrl" -H "Authorization: Bearer $accessToken") || \
    { echo "Failed to reach $imageTokenUrl after retries" >&2; exit 1; }

authToken=$(echo "$imgTokenResp" | jq -r '[.tokenDetails[] | select(.authorizationToken != null)][0].authorizationToken // empty')
if [ -z "$authToken" ]; then
  echo "No authorizationToken in marketingContainerImage/token response." >&2
  exit 1
fi

# --- 4. Decode "username:password" and derive the registry host ------------

decoded=$(echo "$authToken" | base64 -D)   # Linux (GNU base64): base64 -d
registryUser="${decoded%%:*}"
registryPass="${decoded#*:}"
registryHost="${imageUri%%/*}"

kubectl create secret docker-registry decision-pull-secret \
    --docker-server="$registryHost" \
    --docker-username="$registryUser" \
    --docker-password="$registryPass" \
    -n ci360-shed-hues \
    --dry-run=client -o yaml | kubectl apply -f -
```

> **Listing available decision images (macOS/Linux):**
> ```bash
> curl -sS "$tenantBase/marketingContainerImage/images?limit=1000" \
>     -H "Authorization: Bearer $accessToken" | jq .
> ```
> **Windows equivalent:**
> ```powershell
> Invoke-RestMethod -Method Get -Uri "$($tenantBase.TrimEnd('/'))/marketingContainerImage/images?limit=1000" -Headers @{ Authorization = "Bearer $accessToken" }
> ```
>
> **Testing with a publicly pullable image instead?** Skip this whole section on either
> platform — just delete the `imagePullSecrets:` block from
> `manifests/06-decision-deployment.yaml` before applying it.
>
> **Tokens are short-lived** (hours). If pods later fail to pull with `401`/`403`, re-run
> the whole §6.4 block for your platform to mint a fresh token.

### 6.5 Deployment and Service

**Windows (PowerShell):**
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

**macOS/Linux (bash):**
```bash
sed -e "s|decision-placeholder|$decisionName|g" \
    -e "s|\${IMAGE_URI}|$imageUri|g" \
    manifests/06-decision-deployment.yaml | kubectl apply -f -

sed -e "s|decision-placeholder|$decisionName|g" \
    manifests/07-decision-service.yaml | kubectl apply -f -

kubectl rollout status deployment/$decisionName -n ci360-shed-hues --timeout=300s
```

> **Recreated the pull secret after pods already existed?** Force a retry on either
> platform:
> ```bash
> kubectl delete pod -n ci360-shed-hues -l app=$decisionName
> ```

### 6.6 Verify

*(identical on both platforms)*
```bash
kubectl get pods -n ci360-shed-hues -l app=$decisionName
```

---

## 7. Step 4 — Execute the decision via its API

*(port-forward is identical on both platforms)*
```bash
kubectl port-forward svc/$decisionName 8080:8080 -n ci360-shed-hues
```

**Windows (PowerShell)**, in a second window:
```powershell
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

**macOS/Linux (bash)**, in a second terminal tab:
```bash
curl -sS -X POST "http://127.0.0.1:8080/$decisionName" \
    -H "Content-Type: application/json" \
    -d '{
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
    }' | jq '.data'
```

> **No response, or a 404?** Check `SAS_SCR_APP_PATH` matches the URL path, and check
> logs: `kubectl logs -n ci360-shed-hues deployment/$decisionName` (same on both
> platforms).

---

## 8. Step 5 — Execute the SubjectContact API

*(port-forward identical)*
```bash
kubectl port-forward svc/subjectcontact 8081:8080 -n ci360-shed-hues-sub
```

**Windows (PowerShell):**
```powershell
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
        }
    ]
}'

$response
```

**macOS/Linux (bash):**
```bash
curl -sS -X POST "http://localhost:8081/marketingDecisioningSubjectContact/responses" \
    -H "Content-Type: application/json" \
    -H "User-Agent: insomnia/12.3.1" \
    -d '{
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
        }
    ]
}'
```

> `kubectl get svc -n ci360-shed-hues-sub` confirms the exact Service name/port on either
> platform.

---

## 9. Step 6 — Remove the decision

*(identical on both platforms)*
```bash
kubectl delete deployment,service $decisionName -n ci360-shed-hues
kubectl delete secret db-credentials -n ci360-shed-hues
kubectl delete configmap decision-scores -n ci360-shed-hues
kubectl delete secret decision-pull-secret -n ci360-shed-hues --ignore-not-found
```

## 10. Step 7 — Remove SubjectContact

*(identical on both platforms)*
```bash
helm uninstall sas-marketing-decisioning -n ci360-shed-hues-sub
helm uninstall sas-marketing-decisioning-cloudnative-pg -n cnpg-system --ignore-not-found
# Optional full reset:
kubectl delete pvc -n ci360-shed-hues-sub --all
```

## 11. Step 8 — Remove PostgreSQL

*(identical on both platforms)*
```bash
helm uninstall ci360-postgres -n ci360-shed-hues-pg
kubectl delete pvc -n ci360-shed-hues-pg --all
```

## 12. Bonus: nuke everything in one go

*(identical on both platforms)*
```bash
helm uninstall sas-marketing-decisioning -n ci360-shed-hues-sub --ignore-not-found 
helm uninstall ci360-postgres -n ci360-shed-hues-pg --ignore-not-found 

helm uninstall sas-marketing-decisioning-cloudnative-pg -n cnpg-system --ignore-not-found

kubectl delete namespace ci360-shed-hues ci360-shed-hues-sub ci360-shed-hues-pg cnpg-system --ignore-not-found


```
*(Windows PowerShell uses `2>$null` instead of `2>/dev/null` — everything else is the same.)*

---

## 13. Troubleshooting & tips

| Symptom | Likely cause | Fix |
|---|---|---|
| PostgreSQL pod stuck `Pending` | `hostpath` StorageClass isn't default, or resources too tight | `kubectl get storageclass`; bump Docker Desktop CPU/RAM |
| SubjectContact's `ecr-auth-generator` Job fails | Invalid/expired CI360 credentials, or no internet access | Re-check env vars; `kubectl logs job/sas-marketing-decisioning-ecr-auth-generator -n ci360-shed-hues-sub` |
| `ImagePullBackOff` on decision pods | Missing/expired pull secret, wrong image URI, or pods predate the secret | `kubectl describe pod -n ci360-shed-hues -l app=$decisionName`; delete pods to force retry; regenerate token per §6.4 |
| Decision pod `Running` but not `Ready` | `SAS_SCR_APP_PATH` mismatch, or DB secret/ConfigMap not mounted | `kubectl logs deployment/$decisionName -n ci360-shed-hues`; `kubectl describe pod ...` |
| Everything sluggish / `CrashLoopBackOff` | Docker Desktop under-resourced | Bump CPU/RAM in Docker Desktop settings, or scale replicas/resources down |
| **Windows:** `kubectl cp` says `one of src or dest must be a local file specification` | Drive letter (`C:\...`) parsed as `pod:path` separator | Run from inside `hands-on/` using relative paths |
| **macOS/Linux:** `base64: invalid option -- 'D'` | Using GNU coreutils `base64` (from Homebrew) instead of the BSD one | Use `base64 -d` instead of `-D`, or drop the `coreutils` alias for this command |
| **macOS/Linux:** `curl: command not found` for `--data-urlencode` behavior differs | Old curl version | `brew install curl` and use the Homebrew version, or `curl --version` to confirm ≥7.60 |
| **macOS/Linux:** `jq: command not found` | `jq` not installed | `brew install jq` (macOS) or `sudo apt-get install jq` (Linux) |

> **Summary:** Same end state on either OS — PostgreSQL with an explicitly defined
> schema, SubjectContact with its own built-in database, and a two-replica decision
> container connecting to both. Only the *scripting* around `kubectl`/`helm` differs;
> `kubectl` and `helm` themselves behave identically on Windows and macOS/Linux.