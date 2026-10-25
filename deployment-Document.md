# Azure AKS Deployment Guide - AI Powered Investor Intelligence Platform

## Overview

This document explains how to deploy the AI Powered Investor Intelligence Platform from a local development environment to **Azure Kubernetes Service (AKS)**.

The application uses a completely local AI/RAG stack instead of Azure OpenAI and Azure AI Search.

### Technology Stack

* **FastAPI** — Backend API
* **PyMuPDF4LLM** — PDF to Markdown conversion
* **SemanticChunker** — Semantic document chunking
* **Sentence Transformers (`all-MiniLM-L6-v2`)** — Local text embeddings
* **FAISS** — Local vector database
* **Ollama** — Local LLM runtime
* **Llama 3.2** — Local language model
* **PostgreSQL** — Financial metrics database
* **Docker** — Containerization
* **Azure Container Registry (ACR)** — Docker image registry
* **Azure Kubernetes Service (AKS)** — Container orchestration
* **Azure Database for PostgreSQL** — Managed PostgreSQL database

---

# Deployment Architecture

```text
                         Internet
                            │
                            ▼
                  ┌───────────────────┐
                  │ Azure Load        │
                  │ Balancer          │
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │ FastAPI Pod       │
                  │                   │
                  │ Investor Platform │
                  │                   │
                  │ ┌───────────────┐ │
                  │ │ MiniLM        │ │
                  │ │ Embeddings    │ │
                  │ └───────┬───────┘ │
                  │         │         │
                  │ ┌───────▼───────┐ │
                  │ │ FAISS         │ │
                  │ │ Vector Store  │ │
                  │ └───────┬───────┘ │
                  │         │         │
                  │ ┌───────▼───────┐ │
                  │ │ Ollama        │ │
                  │ │ Llama 3.2     │ │
                  │ └───────────────┘ │
                  └─────────┬─────────┘
                            │
                            ▼
                ┌──────────────────────┐
                │ Azure PostgreSQL     │
                │ financial_metrics    │
                └──────────────────────┘
```

---

# Important Deployment Consideration

The application now uses **local FAISS and Ollama**.

This means these components must exist inside the AKS environment.

A local development machine has:

```text
Mac
 ├── MiniLM
 ├── FAISS
 └── Ollama
      └── Llama 3.2
```

AKS cannot access the Ollama process running on your Mac.

Therefore, when deployed to AKS:

```text
AKS
 ├── FastAPI application
 ├── MiniLM embeddings
 ├── FAISS
 └── Ollama
      └── Llama 3.2
```

Ollama should therefore run as a Kubernetes workload, typically as a separate deployment/service or as a sidecar container.

For a demonstration deployment, this guide uses an **Ollama deployment + Kubernetes service**.

---

# Step 1: Verify the Application Locally

Before deploying to Azure, make sure the local application works.

Start Ollama:

```bash
ollama serve
```

Verify the model:

```bash
ollama list
```

If Llama 3.2 is not installed:

```bash
ollama pull llama3.2
```

Test the model:

```bash
ollama run llama3.2
```

---

# Step 2: Verify the Local RAG Pipeline

The application should successfully perform:

```text
PDF
 ↓
PyMuPDF4LLM
 ↓
Markdown
 ↓
SemanticChunker
 ↓
all-MiniLM-L6-v2
 ↓
FAISS
 ↓
Retriever
 ↓
Ollama
 ↓
Llama 3.2
 ↓
Financial Metrics
 ↓
PostgreSQL
```

Verify:

* Application starts
* Dashboard loads
* PDF upload works
* PDF is converted to Markdown
* Semantic chunks are generated
* Embeddings are generated locally
* FAISS index is created
* Chatbot retrieves relevant chunks
* Ollama generates answers
* Financial metrics are stored in PostgreSQL

---

# Step 3: Build Docker Image

Build the application Docker image.

```bash
docker build -t invint .
```

Verify:

```bash
docker images
```

Expected:

```text
REPOSITORY    TAG
invint        latest
```

---

# Step 4: Run Docker Locally

Run the application container:

```bash
docker run -p 8000:8000 invint
```

Open:

```text
http://localhost:8000
```

However, the application container needs access to Ollama.

If Ollama is running on the host machine, configure:

```text
OLLAMA_HOST=http://host.docker.internal:11434
```

For example:

```bash
docker run \
  -p 8000:8000 \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  invint
```

Verify:

* Application loads
* Dashboard works
* PDF upload works
* FAISS retrieval works
* Chatbot works
* Ollama generates responses

---

# Step 5: Create Azure Resource Group

Login to Azure:

```bash
az login
```

Verify the current subscription:

```bash
az account show
```

Create the resource group if it does not already exist:

```bash
az group create \
  --name rg-inv-intelligence \
  --location centralindia
```

---

# Step 6: Create Azure Container Registry

Create an Azure Container Registry:

```bash
az acr create \
  --resource-group rg-inv-intelligence \
  --name invintelligence \
  --sku Basic
```

Verify:

```bash
az acr list --output table
```

---

# Step 7: Login to Azure Container Registry

Login using Azure CLI:

```bash
az acr login --name invintelligence
```

Expected:

```text
Login Succeeded
```

---

# Step 8: Tag Docker Image

Tag the local application image:

```bash
docker tag \
  invint:latest \
  invintelligence.azurecr.io/invint:v1
```

Verify:

```bash
docker images
```

Expected:

```text
REPOSITORY                              TAG
invintelligence.azurecr.io/invint       v1
```

---

# Step 9: Push Docker Image to ACR

Push the application image:

```bash
docker push invintelligence.azurecr.io/invint:v1
```

Verify:

```bash
az acr repository list \
  --name invintelligence \
  --output table
```

Expected:

```text
Result
----------------
invint
```

---

# Step 10: Create AKS Cluster

If the AKS cluster does not already exist:

```bash
az aks create \
  --resource-group rg-inv-intelligence \
  --name inv-intelligence-aks \
  --node-count 1 \
  --generate-ssh-keys \
  --attach-acr invintelligence
```

For an Ollama workload, the node needs enough CPU/RAM.

A small development cluster may not have enough resources for Llama 3.2.

For demonstration purposes, start with an appropriately sized node and increase the size if the Ollama pod cannot schedule or the model runs too slowly.

---

# Step 11: Connect to AKS

Download cluster credentials:

```bash
az aks get-credentials \
  --resource-group rg-inv-intelligence \
  --name inv-intelligence-aks \
  --overwrite-existing
```

Verify:

```bash
kubectl get nodes
```

Expected:

```text
NAME       STATUS   ROLES
...        Ready    agent
```

---

# Step 12: Verify AKS Can Access ACR

If ACR was not attached during cluster creation:

```bash
az aks update \
  --resource-group rg-inv-intelligence \
  --name inv-intelligence-aks \
  --attach-acr invintelligence
```

Verify:

```bash
az aks check-acr \
  --resource-group rg-inv-intelligence \
  --name inv-intelligence-aks \
  --acr invintelligence
```

---

# Step 13: Create Kubernetes Namespace

Create a dedicated namespace:

```bash
kubectl create namespace invint
```

Verify:

```bash
kubectl get namespaces
```

---

# Step 14: Create PostgreSQL Configuration

The application requires PostgreSQL configuration.

Create a Kubernetes secret:

```bash
kubectl create secret generic postgres-secret \
  --namespace invint \
  --from-literal=POSTGRES_HOST="<postgres-host>" \
  --from-literal=POSTGRES_PORT="5432" \
  --from-literal=POSTGRES_USER="<postgres-user>" \
  --from-literal=POSTGRES_PASSWORD="<postgres-password>" \
  --from-literal=POSTGRES_DATABASE="<postgres-database>"
```

Verify:

```bash
kubectl get secrets -n invint
```

Do not commit PostgreSQL passwords to Git.

---

# Step 15: Create FAISS Persistent Volume

FAISS stores the vector index locally.

A container filesystem is temporary, so the FAISS index should be stored on a Kubernetes Persistent Volume.

Example:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: faiss-pvc
  namespace: invint
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

Save as:

```text
k8s/faiss-pvc.yaml
```

Apply:

```bash
kubectl apply -f k8s/faiss-pvc.yaml
```

Verify:

```bash
kubectl get pvc -n invint
```

Expected:

```text
NAME        STATUS
faiss-pvc   Bound
```

---

# Step 16: Deploy Ollama

Ollama needs to run inside AKS because the FastAPI application cannot use Ollama running on the local development machine.

Create:

```text
k8s/ollama.yaml
```

Example:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
  namespace: invint
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama
  template:
    metadata:
      labels:
        app: ollama
    spec:
      containers:
        - name: ollama
          image: ollama/ollama:latest
          ports:
            - containerPort: 11434
          resources:
            requests:
              cpu: "1"
              memory: "4Gi"
            limits:
              cpu: "2"
              memory: "8Gi"
---
apiVersion: v1
kind: Service
metadata:
  name: ollama
  namespace: invint
spec:
  selector:
    app: ollama
  ports:
    - port: 11434
      targetPort: 11434
  type: ClusterIP
```

Apply:

```bash
kubectl apply -f k8s/ollama.yaml
```

Verify:

```bash
kubectl get pods -n invint
```

Verify the service:

```bash
kubectl get svc -n invint
```

Expected:

```text
NAME      TYPE        PORT
ollama    ClusterIP   11434
```

---

# Step 17: Download Llama 3.2 in Ollama

After the Ollama pod is running, identify the pod:

```bash
kubectl get pods -n invint
```

Example:

```text
ollama-xxxxxxxxxx-xxxxx
```

Execute the model download:

```bash
kubectl exec -it \
  -n invint \
  <ollama-pod-name> \
  -- ollama pull llama3.2
```

Verify:

```bash
kubectl exec -it \
  -n invint \
  <ollama-pod-name> \
  -- ollama list
```

Expected:

```text
NAME
llama3.2
```

---

# Important Ollama Persistence Note

The example Ollama deployment above is suitable for a basic demonstration.

Without persistent storage, the downloaded model can disappear if the Ollama pod is recreated.

For a more reliable deployment, mount a Persistent Volume at:

```text
/root/.ollama
```

Example:

```yaml
volumeMounts:
  - name: ollama-data
    mountPath: /root/.ollama
```

with a corresponding PersistentVolumeClaim.

This prevents repeatedly downloading the Llama model after pod recreation.

---

# Step 18: Configure the FastAPI Application

The FastAPI application needs to know where Ollama is running.

Inside Kubernetes, the Ollama service can be reached using:

```text
http://ollama:11434
```

Set:

```text
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2
```

The application should NOT use:

```text
http://localhost:11434
```

because inside the FastAPI container, `localhost` refers to the FastAPI container itself.

---

# Step 19: Create Application Deployment

Create:

```text
k8s/invint-deployment.yaml
```

Example:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: invint
  namespace: invint
spec:
  replicas: 1
  selector:
    matchLabels:
      app: invint
  template:
    metadata:
      labels:
        app: invint
    spec:
      containers:
        - name: invint
          image: invintelligence.azurecr.io/invint:v1

          ports:
            - containerPort: 8000

          env:
            - name: OLLAMA_HOST
              value: "http://ollama:11434"

            - name: OLLAMA_MODEL
              value: "llama3.2"

            - name: POSTGRES_HOST
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_HOST

            - name: POSTGRES_PORT
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_PORT

            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_USER

            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_PASSWORD

            - name: POSTGRES_DATABASE
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_DATABASE

          volumeMounts:
            - name: faiss-storage
              mountPath: /app/data/vectorstore

      volumes:
        - name: faiss-storage
          persistentVolumeClaim:
            claimName: faiss-pvc
```

Apply:

```bash
kubectl apply -f k8s/invint-deployment.yaml
```

---

# Step 20: Verify Application Deployment

Check deployment:

```bash
kubectl get deployments -n invint
```

Expected:

```text
NAME      READY
invint    1/1
```

Check pods:

```bash
kubectl get pods -n invint
```

Expected:

```text
NAME                         STATUS
invint-xxxxxxxxxx-xxxxx      Running
ollama-xxxxxxxxxx-xxxxx      Running
```

---

# Step 21: View Application Logs

Get the application pod:

```bash
kubectl get pods -n invint
```

View logs:

```bash
kubectl logs \
  -n invint \
  <invint-pod-name>
```

Follow logs:

```bash
kubectl logs -f \
  -n invint \
  <invint-pod-name>
```

---

# Step 22: View Ollama Logs

```bash
kubectl logs \
  -n invint \
  <ollama-pod-name>
```

Follow:

```bash
kubectl logs -f \
  -n invint \
  <ollama-pod-name>
```

---

# Step 23: Debug Pod Startup

Describe the application pod:

```bash
kubectl describe pod \
  -n invint \
  <invint-pod-name>
```

Describe the Ollama pod:

```bash
kubectl describe pod \
  -n invint \
  <ollama-pod-name>
```

Common problems include:

```text
ImagePullBackOff
CrashLoopBackOff
Pending
OOMKilled
```

If the Ollama pod is:

```text
OOMKilled
```

the node/container does not have enough memory.

Increase the available node resources or use a smaller quantized model.

---

# Step 24: Verify Ollama Connectivity

From inside the FastAPI pod, test the Ollama service.

```bash
kubectl exec -it \
  -n invint \
  <invint-pod-name> \
  -- curl http://ollama:11434/api/tags
```

A successful response confirms that:

```text
FastAPI
   ↓
Kubernetes Service
   ↓
Ollama
```

is working.

---

# Step 25: Expose Application

Create a public LoadBalancer:

```bash
kubectl expose deployment invint \
  --namespace invint \
  --type=LoadBalancer \
  --port=80 \
  --target-port=8000
```

Verify:

```bash
kubectl get svc -n invint
```

Expected:

```text
NAME      TYPE           EXTERNAL-IP
invint    LoadBalancer   20.xxx.xxx.xxx
```

---

# Step 26: Access Application

Get the external IP:

```bash
kubectl get svc invint -n invint
```

Open:

```text
http://<external-ip>
```

Example:

```text
http://20.xxx.xxx.xxx
```

---

# Step 27: Test the Complete Production Flow

The complete deployed flow should now be:

```text
User
 ↓
Public Load Balancer
 ↓
FastAPI
 ↓
PDF Upload
 ↓
PyMuPDF4LLM
 ↓
Markdown
 ↓
SemanticChunker
 ↓
all-MiniLM-L6-v2
 ↓
FAISS
 ↓
Retriever
 ↓
Ollama Service
 ↓
Llama 3.2
 ↓
Financial Metrics
 ↓
Azure PostgreSQL
```

For chatbot requests:

```text
User Question
      ↓
FastAPI /chat
      ↓
MiniLM Embedding
      ↓
FAISS Similarity Search
      ↓
Relevant Financial Report Chunks
      ↓
RAG Prompt
      ↓
Ollama
      ↓
Llama 3.2
      ↓
Answer
```

---

# Common Troubleshooting Commands

## List Nodes

```bash
kubectl get nodes
```

---

## List Pods

```bash
kubectl get pods -n invint
```

---

## List Services

```bash
kubectl get svc -n invint
```

---

## List Deployments

```bash
kubectl get deployments -n invint
```

---

## List Persistent Volume Claims

```bash
kubectl get pvc -n invint
```

---

## Describe Deployment

```bash
kubectl describe deployment invint -n invint
```

---

## Describe Pod

```bash
kubectl describe pod <pod-name> -n invint
```

---

## View Application Logs

```bash
kubectl logs <pod-name> -n invint
```

---

## Follow Application Logs

```bash
kubectl logs -f <pod-name> -n invint
```

---

## View Previous Container Logs

```bash
kubectl logs <pod-name> -n invint --previous
```

---

## Restart Application

```bash
kubectl rollout restart deployment invint -n invint
```

---

## Restart Ollama

```bash
kubectl rollout restart deployment ollama -n invint
```

---

## Check Deployment Status

```bash
kubectl rollout status deployment invint -n invint
```

---

## Delete Application Deployment

```bash
kubectl delete deployment invint -n invint
```

---

## Delete Application Service

```bash
kubectl delete service invint -n invint
```

---

## Delete Namespace

```bash
kubectl delete namespace invint
```

---

# Azure Resource Operations

## List AKS Clusters

```bash
az aks list --output table
```

---

## Get AKS Credentials

```bash
az aks get-credentials \
  --resource-group rg-inv-intelligence \
  --name inv-intelligence-aks \
  --overwrite-existing
```

---

## Show AKS Details

```bash
az aks show \
  --resource-group rg-inv-intelligence \
  --name inv-intelligence-aks
```

---

## Delete AKS Cluster

```bash
az aks delete \
  --resource-group rg-inv-intelligence \
  --name inv-intelligence-aks \
  --yes \
  --no-wait
```

---

# ACR Operations

## List Registries

```bash
az acr list --output table
```

---

## Show Registry

```bash
az acr show \
  --name invintelligence
```

---

## List Repositories

```bash
az acr repository list \
  --name invintelligence \
  --output table
```

---

## Show Repository Tags

```bash
az acr repository show-tags \
  --name invintelligence \
  --repository invint \
  --output table
```

---

## Delete Registry

```bash
az acr delete \
  --name invintelligence \
  --resource-group rg-inv-intelligence \
  --yes
```

---

# Docker Operations

## Build Image

```bash
docker build -t invint .
```

---

## Run Image

```bash
docker run -p 8000:8000 invint
```

---

## Tag Image

```bash
docker tag \
  invint:latest \
  invintelligence.azurecr.io/invint:v1
```

---

## Push Image

```bash
docker push \
  invintelligence.azurecr.io/invint:v1
```

---

# Important Differences From the Previous Azure Architecture

The previous architecture used:

```text
FastAPI
   ↓
Azure AI Search
   ↓
Azure OpenAI
   ↓
Azure PostgreSQL
```

The new architecture uses:

```text
FastAPI
   ↓
FAISS
   ↓
Ollama
   ↓
Llama 3.2
   ↓
Azure PostgreSQL
```

Therefore the following Azure components are no longer required:

```text
❌ Azure OpenAI
❌ Azure AI Search
❌ Azure Search Index
❌ Azure Search API Key
❌ Azure OpenAI API Key
❌ Azure OpenAI Embedding Deployment
❌ create_index.py
```

The following remain useful:

```text
✅ Azure Container Registry
✅ Azure Kubernetes Service
✅ Azure Database for PostgreSQL
```

---

# Environment Variables

The local application should use:

```text
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

POSTGRES_HOST=<postgres-host>
POSTGRES_PORT=5432
POSTGRES_USER=<postgres-user>
POSTGRES_PASSWORD=<postgres-password>
POSTGRES_DATABASE=<postgres-database>
```

Inside Kubernetes:

```text
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2
```

PostgreSQL credentials should be supplied through Kubernetes Secrets.

Do not commit `.env` files containing passwords or API keys to GitHub.

---

# Production Enhancements

The current deployment is suitable for demonstrations and development.

For a production deployment, consider:

* GitHub Actions CI/CD
* Azure Key Vault
* Kubernetes Secrets
* HTTPS / SSL certificates
* Custom domain
* NGINX Ingress Controller
* Azure Application Gateway
* Monitoring and logging
* Horizontal Pod Autoscaling
* Authentication and authorization
* Private networking
* Network policies
* Azure Container Registry vulnerability scanning
* Persistent storage for FAISS
* Persistent storage for Ollama models
* GPU-enabled AKS nodes for faster LLM inference
* Model quantization
* Resource limits and requests
* Health probes
* Readiness probes
* Liveness probes
* Backup strategy for PostgreSQL
* Centralized application logging

---

# Final Deployment Architecture

```text
                         USER
                           │
                           ▼
                 ┌──────────────────┐
                 │ Azure Load       │
                 │ Balancer         │
                 └────────┬─────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │         AKS            │
              │                        │
              │   ┌────────────────┐   │
              │   │ FastAPI        │   │
              │   │ Application    │   │
              │   └───────┬────────┘   │
              │           │            │
              │     ┌─────▼─────┐      │
              │     │  MiniLM   │      │
              │     │ Embeddings│      │
              │     └─────┬─────┘      │
              │           │            │
              │     ┌─────▼─────┐      │
              │     │   FAISS   │      │
              │     └─────┬─────┘      │
              │           │            │
              │     ┌─────▼─────┐      │
              │     │  Ollama   │      │
              │     │ Llama 3.2 │      │
              │     └───────────┘      │
              │                        │
              │  Persistent Storage    │
              │  ├── FAISS Index       │
              │  └── Ollama Models     │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │ Azure PostgreSQL       │
              │                        │
              │ financial_metrics      │
              └────────────────────────┘
```

## Final Result

The deployed system provides a complete AI-powered financial intelligence platform using:

```text
PDF Processing
      +
Semantic Chunking
      +
Local Embeddings
      +
FAISS Vector Retrieval
      +
RAG
      +
Ollama / Llama 3.2
      +
PostgreSQL
      +
FastAPI
      +
Docker
      +
AKS
```

This architecture removes the dependency on Azure OpenAI and Azure AI Search while still allowing the application to use Azure infrastructure for container orchestration, image storage, networking, and managed PostgreSQL.
