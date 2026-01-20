# Capstone Project Scope
## Simplified Architecture for Academic Demonstration

**Target**: College Capstone Project  
**Scale**: 5-10 concurrent users  
**Budget**: ~$50-100/month  
**Timeline**: 8-10 weeks

---

## Key Simplifications from Production Design

### What We're Keeping (Core Concepts)
- ✅ GraphRAG knowledge representation
- ✅ Multi-agent orchestration pattern
- ✅ Reasoning-augmented generation concept
- ✅ Feedback learning loop
- ✅ Brand consistency validation

### What We're Simplifying

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION → CAPSTONE CHANGES                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  COMPONENT           PRODUCTION                  CAPSTONE                   │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  Infrastructure      AWS EKS + 12 nodes       →  Single VPS (DigitalOcean)│
│                                                   Docker Compose            │
│                                                                              │
│  Graph Database      Neo4j Enterprise         →  Neo4j Community           │
│                      3-node cluster               Single container          │
│                                                                              │
│  Vector Search       PostgreSQL + pgvector    →  Neo4j vector index        │
│                      Separate instances           (built-in)               │
│                                                                              │
│  Image Generation    Self-hosted SDXL         →  Replicate API             │
│                      Custom reasoning head        (SDXL via API)           │
│                      16x A100 GPUs                                          │
│                                                                              │
│  Text Generation     OpenAI GPT-4 Turbo       →  OpenAI GPT-4o-mini       │
│                      + Claude fallback            (cheaper)                │
│                                                                              │
│  Workflow Engine     Temporal.io              →  Python AsyncIO            │
│                      Complex sagas                Simple queues            │
│                                                                              │
│  Message Queue       Apache Kafka (MSK)       →  Redis Pub/Sub             │
│                                                                              │
│  Monitoring          Prometheus + Grafana     →  Basic logs + simple       │
│                      + Jaeger + Loki              dashboard                │
│                                                                              │
│  Storage             S3 + CloudFront          →  Local storage + CDN       │
│                      Multi-region                 (Cloudflare R2)          │
│                                                                              │
│  Multi-tenancy       Full isolation           →  Single tenant             │
│                      50+ enterprises              (demo brands)            │
│                                                                              │
│  LoRA Training       Automated pipeline       →  Pre-trained only          │
│                      Per-brand adapters           Prompt engineering       │
│                                                                              │
│  Auth                Enterprise SSO           →  Simple JWT auth           │
│                      + RBAC + audit                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Simplified Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CAPSTONE ARCHITECTURE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         ┌─────────────────┐                                 │
│                         │   Web App       │                                 │
│                         │   (React SPA)   │                                 │
│                         └────────┬────────┘                                 │
│                                  │                                          │
│                                  ▼                                          │
│                         ┌─────────────────┐                                 │
│                         │   FastAPI       │                                 │
│                         │   Backend       │                                 │
│                         └────────┬────────┘                                 │
│                                  │                                          │
│       ┌──────────────────────────┼──────────────────────────┐              │
│       │                          │                          │              │
│       ▼                          ▼                          ▼              │
│  ┌─────────┐          ┌─────────────────┐         ┌─────────────┐         │
│  │  Brand  │          │  Orchestrator   │         │ Validation  │         │
│  │  Agent  │          │     Agent       │         │   Agent     │         │
│  │ (Python)│          │   (AsyncIO)     │         │  (Python)   │         │
│  └────┬────┘          └────────┬────────┘         └──────┬──────┘         │
│       │                        │                         │                │
│       │              ┌─────────┴─────────┐               │                │
│       │              │                   │               │                │
│       │              ▼                   ▼               │                │
│       │      ┌──────────────┐    ┌──────────────┐        │                │
│       │      │   Image Gen  │    │   Text Gen   │        │                │
│       │      │   (Replicate)│    │  (OpenAI API)│        │                │
│       │      └──────────────┘    └──────────────┘        │                │
│       │                                                   │                │
│       └───────────────────────┬───────────────────────────┘                │
│                               │                                            │
│                               ▼                                            │
│                      ┌─────────────────┐                                   │
│                      │     Neo4j       │                                   │
│                      │   (Community)   │                                   │
│                      │  + Vector Index │                                   │
│                      └─────────────────┘                                   │
│                                                                              │
│  Deployment:  Single DigitalOcean Droplet ($24/month)                      │
│               8GB RAM, 4 vCPUs, 160GB SSD                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack (Simplified)

| Layer | Production | Capstone | Why Changed |
|-------|-----------|----------|-------------|
| **Frontend** | Next.js | React (Vite) | Simpler, no SSR needed |
| **Backend** | Microservices | FastAPI monolith | Easier to develop/deploy |
| **Database** | Neo4j Enterprise + PostgreSQL | Neo4j Community | Single DB, built-in vectors |
| **Cache** | Redis Cluster | Redis single instance | Sufficient for 10 users |
| **Image API** | Self-hosted SDXL | Replicate API | No GPU infrastructure |
| **LLM API** | GPT-4 Turbo | GPT-4o-mini | 15x cheaper |
| **Deployment** | Kubernetes (EKS) | Docker Compose | Simple, reproducible |
| **Hosting** | AWS multi-region | DigitalOcean | Cost-effective |

---

## Cost Breakdown

```
Monthly Costs:
────────────────────────────────────────
Infrastructure:
  • DigitalOcean Droplet (8GB)      $24
  • Domain + SSL (Cloudflare)       $10
  • Cloudflare R2 Storage           $5
                                    ────
  Subtotal:                         $39

API Costs (assuming 500 generations/month):
  • Replicate (SDXL):
    500 × $0.0055 = $2.75
  
  • OpenAI GPT-4o-mini:
    500 × 1000 tokens × $0.15/1M ≈ $0.08
                                    ────
  Subtotal:                         $3

TOTAL: ~$42/month
────────────────────────────────────────

Production comparison: $62,100/month 😱
Savings: 99.93%
```

---

## Feature Comparison

| Feature | Production | Capstone | Implementation |
|---------|-----------|----------|----------------|
| **Graph Knowledge Base** | ✅ Multi-hop, 10M nodes | ✅ Single-hop, 10K nodes | Neo4j with 5 node types |
| **Vector Search** | ✅ Hybrid (graph + vector) | ✅ Basic vector search | Neo4j vector index |
| **Image Generation** | ✅ Custom SDXL + reasoning | ✅ SDXL via API | Replicate API |
| **Text Generation** | ✅ GPT-4 + Claude fallback | ✅ GPT-4o-mini | OpenAI API |
| **Multi-Agent** | ✅ MCP + A2A protocol | ✅ Python async tasks | AsyncIO queues |
| **Feedback Loop** | ✅ Real-time + batch | ✅ Batch (daily) | Python scripts |
| **Brand Consistency** | ✅ LoRA adapters | ✅ Prompt engineering | Structured prompts |
| **Validation** | ✅ Multi-stage pipeline | ✅ Basic checks | Color + logo detection |
| **Multi-tenancy** | ✅ 50 enterprises | ❌ Single tenant | Demo brands only |
| **Auto-scaling** | ✅ 1000 concurrent | ❌ Fixed capacity | 10 users max |
| **SSO** | ✅ SAML/OIDC | ❌ Simple auth | JWT tokens |
| **Monitoring** | ✅ Full observability | ⚠️ Basic logging | Python logging + dashboard |

---

## Capstone Learning Objectives

This simplified architecture still demonstrates:

### 1. **Graph Database Concepts** ✓
- Knowledge representation
- Relationship modeling
- Cypher queries
- Vector embeddings

### 2. **AI/ML Integration** ✓
- Prompt engineering
- LLM API usage
- Image generation APIs
- Quality validation

### 3. **Multi-Agent Systems** ✓
- Agent communication patterns
- Task orchestration
- Async programming
- Event-driven architecture

### 4. **Full-Stack Development** ✓
- React frontend
- Python backend (FastAPI)
- REST API design
- Database integration

### 5. **System Design** ✓
- Architecture documentation
- Data flow diagrams
- API design
- Deployment strategy

### 6. **Software Engineering** ✓
- Docker containerization
- CI/CD (GitHub Actions)
- Version control
- Documentation

---

## What Professors Will See

### Technical Depth
- Novel GraphRAG approach for brand knowledge
- Multi-agent orchestration pattern
- Reasoning-augmented generation concept
- Feedback learning loop

### Practical Demonstration
- Working web application
- Real-time content generation
- Visual brand consistency
- User feedback collection

### Academic Rigor
- Comprehensive documentation (6 documents)
- Architecture diagrams
- Performance analysis
- Cost optimization

---

## Deployment Guide (Simplified)

```bash
# 1. Clone repository
git clone https://github.com/Shreyas70773/system-design-capstone.git
cd system-design-capstone

# 2. Configure environment
cp .env.example .env
# Edit .env with API keys

# 3. Start with Docker Compose
docker-compose up -d

# 4. Initialize database
docker exec -it neo4j-container bash
# Run Cypher schema scripts

# 5. Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Neo4j Browser: http://localhost:7474
```

---

## Demo Script for Professors

### 1. Architecture Overview (5 min)
- Show system architecture diagram
- Explain GraphRAG concept
- Demonstrate multi-agent flow

### 2. Knowledge Graph (5 min)
- Open Neo4j Browser
- Show brand nodes and relationships
- Execute sample Cypher queries
- Explain vector embeddings

### 3. Live Generation (10 min)
- Open web application
- Select a brand (e.g., "Nike")
- Request: "Athletic shoe ad for summer campaign"
- Show real-time agent activity
- Display generated image + text
- Explain brand consistency validation

### 4. Feedback Loop (3 min)
- Provide feedback (thumbs up/down)
- Show how graph updates
- Explain continuous learning

### 5. Code Walkthrough (5 min)
- Show agent implementation
- Explain orchestration logic
- Demonstrate API integration

### 6. Q&A (7 min)

**Total: 35 minutes**

---

## Success Metrics (Capstone)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Generation Success Rate | > 95% | API logs |
| Average Latency | < 45s | Request timing |
| Brand Consistency Score | > 0.85 | Validation metrics |
| System Uptime | > 95% | Monitoring logs |
| Demo Brands Supported | 5 | Database count |
| Concurrent Users | 10 | Load testing |
| API Cost per Generation | < $0.01 | Usage tracking |

---

## Next Steps

See [07-capstone-implementation.md](./07-capstone-implementation.md) for the simplified 8-week implementation plan.
