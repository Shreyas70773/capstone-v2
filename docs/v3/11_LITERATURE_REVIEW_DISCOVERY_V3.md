# 📚 Literature Review: Paper Discovery & Research Strategy for Capstone V3

**Document Purpose:** Strategic guide for discovering, evaluating, and organizing peer-reviewed papers for your capstone literature review.

**Target Audience:** Researchers, capstone committee, and anyone needing high-quality papers on:
- Segmentation algorithms (SAM/SAM2)
- Inpainting techniques (LaMa)
- Scene graph generation
- Interactive image editing
- Retrieval-augmented generation (RAG)
- Evaluation metrics (IoU, Dice, LPIPS, FID, CIEDE2000)

---

## 🎯 Three Targeted Prompts for Paper Discovery

### **Prompt 1: Foundation Papers (Core Algorithms)**

Use this prompt with browser-use/Firecrawl to find seminal papers:

```
Search for and extract information about these papers:

1. "Segment Anything" (SAM) - Kirillov et al., Meta AI
   - Find: PDF link, citation count, abstract, key contributions
   - Focus: Zero-shot segmentation, vision transformers

2. "Large Mask Inpainting Model for Content-Aware Image Inpainting" (LaMa)
   - Find: PDF link, Fast Fourier Convolution details, benchmark results
   - Focus: Object removal, inpainting quality metrics (LPIPS, FID)

3. "Scene Graph Generation from Objects, Phrases and Region Captions"
   - Find: Graph relationship inference, spatial relationship types
   - Focus: How spatial relationships are defined and computed

From: arXiv.org, paperswithcode.com, openreview.net, scholar.google.com

Desired output format:
{
  "paper": "Title",
  "authors": "...",
  "year": 2024,
  "link": "https://...",
  "citations": 1234,
  "key_contribution": "...",
  "metrics": ["metric1", "metric2"]
}
```

**Use case:** These are your PRIMARY papers explaining SAM2, LaMa, and graph relationships. They establish your algorithmic foundation.

---

### **Prompt 2: Related Work Papers (Interactive Editing + RAG)**

Use this prompt to contextualize your innovation:

```
Find papers on these topics and extract structured data:

Topic A: Interactive Image Editing Systems
- Keywords: interactive segmentation, user-guided editing, real-time inference
- Papers to find:
  * "Interactive Image Segmentation with Latent Diversity"
  * "Scribbler: Controlling Deep Image Synthesis with Sketch and Color"
  * Real-Time Image Editing via Interactive Segmentation

Topic B: Retrieval-Augmented Generation (RAG) + Knowledge Graphs
- Keywords: graph-augmented generation, semantic relationships, context retrieval
- Papers to find:
  * "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al.)
  * Papers on Knowledge Graph embeddings and spatial reasoning
  * Scene graphs for visual understanding

Topic C: Semantic Scene Understanding
- Keywords: 3D scene understanding, spatial relationships, object interactions
- Papers to find:
  * "Visual Relationship Detection with Language Priors"
  * Scene graph generation and visual reasoning

From: ACM SIGGRAPH, CVPR, ICCV, ECCV, NeurIPS, ICML

Extract for each paper:
- Title, authors, year, link
- Abstract snippet (first 150 chars)
- Key methodology 
- How it relates to image editing or RAG
```

**Use case:** Establish context for why your system combines interactive editing + graph reasoning. Shows innovation positioning.

---

### **Prompt 3: Evaluation & Benchmarking Papers**

Use this prompt to justify your evaluation framework:

```
Find papers on evaluation metrics and benchmarking:

Topic A: Segmentation Evaluation Metrics
- Find papers explaining: IoU, Dice coefficient, F1 score, Precision/Recall
- Papers: "Metrics for Evaluating 3D Object Detection" and segmentation papers
- Focus: Standard metric definitions, why they matter

Topic B: Inpainting Quality Metrics
- Find: LPIPS (Learned Perceptual Image Patch Similarity)
- Find: FID (Fréchet Inception Distance)
- Find: Papers on perceptual quality evaluation
- Papers: "The Unreasonable Effectiveness of Deep Features as a Perceptual Metric" (Zhang et al.)
- Papers: "An Empirical Evaluation of Generative Adversarial Networks for Learning Distributions"

Topic C: Color Science & Perceptual Metrics
- Find: CIEDE2000 color difference (ΔE00)
- Find: Papers on color matching accuracy
- Find: RGB vs LAB color space conversions

Topic D: Benchmarking Best Practices
- Find: "A survey on evaluation metrics used for NER systems"
- Find: Papers on statistically rigorous ML evaluation

Extract:
- Metric definitions with formulas
- When to use which metric
- Typical value ranges for good/bad performance
- Code implementations if available
```

**Use case:** Justify your evaluation framework. Show you understand metrics deeply. Provide context for your benchmark results.

---

## 📖 Recommended Papers (High Confidence - Research Quality)

### **Tier 1: MUST-READ (Core to Your System)**

| Paper | Authors | Year | Why | Where to Find |
|-------|---------|------|-----|---|
| **Segment Anything** | Kirillov et al. | 2023 | SAM foundation | [arXiv:2304.02643](https://arxiv.org/abs/2304.02643) |
| **Segment Anything in High Quality** | Ke et al. | 2024 | SAM2 improvements | [arXiv:2408.00714](https://arxiv.org/abs/2408.00714) |
| **Resolution-robust Large Mask Inpainting with Fourier Convolution** | Suvorov et al. | 2022 | LaMa architecture | [arXiv:2109.07161](https://arxiv.org/abs/2109.07161) |
| **Scene Graph Generation by Iterative Message Passing** | Li et al. | 2019 | Graph relationships | [CVPR 2019](https://arxiv.org/abs/1903.10135) |

### **Tier 2: IMPORTANT (Context & Positioning)**

| Paper | Focus | Year | Why | Where to Find |
|-------|-------|------|-----|---|
| **The Unreasonable Effectiveness of Deep Features as a Perceptual Metric** | LPIPS metric | 2018 | Your inpainting evaluation | [CVPR 2018](https://arxiv.org/abs/1801.03924) |
| **Generative Adversarial Networks** | GAN baseline | 2016 | Compare inpainting approaches | [arXiv:1406.2661](https://arxiv.org/abs/1406.2661) |
| **Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks** | RAG framework | 2020 | Graph-RAG integration | [Facebook Research](https://arxiv.org/abs/2005.11401) |
| **Knowledge Graph Embedding by Translating on Hyperplanes** | Graph embeddings | 2014 | Node relationship learning | [AAAI 2014](https://arxiv.org/abs/1312.5419) |
| **An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale** | ViT architecture | 2020 | SAM backbone | [ICLR 2021](https://arxiv.org/abs/2010.11929) |

### **Tier 3: SUPPLEMENTARY (Validation & Metrics)**

| Paper | Focus | Year | Why | Where to Find |
|-------|-------|------|-----|---|
| **Fréchet Inception Distance** (in GAN paper) | FID metric | 2017 | Inpainting quality | [arXiv:1706.08500](https://arxiv.org/abs/1706.08500) |
| **The CIEDE2000 Color-Difference Formula** | Color metrics | 2001 | Color matching accuracy | [Luo et al., JOSA](https://www.researchgate.net/publication/279349267) |
| **Content-Aware Fill** | Inpainting baseline | 2005 | Compare with traditional methods | [Criminisi et al.](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/criminisi_siggraph2003.pdf) |
| **Interactive Video Object Segmentation** | Interactive segmentation | 2018 | User interaction patterns | [CVPR 2018](https://arxiv.org/abs/1809.04954) |

---

## 🛠️ How to Get the Best Papers

### **Step 1: Identify Paper Repositories**

Use browser-use to search these sites (ranked by quality):

```
Priority 1 (Best Quality):
- arXiv.org - Pre-prints with citing info
- Papers with Code (paperswithcode.com) - Code + benchmarks
- OpenReview.net - Peer-reviewed conference submissions

Priority 2 (Peer Reviewed):
- ACM Digital Library (acm.org)
- IEEE Xplore (ieee.org)
- CVPR/ICCV/ECCV (conference proceedings)

Priority 3 (Supplementary):
- Google Scholar (scholar.google.com)
- Semantic Scholar (semanticscholar.org)
- ResearchGate (researchgate.net)
```

### **Step 2: Extract Key Information**

For each paper, use browser-use to capture:

```json
{
  "title": "Paper Title",
  "authors": ["Author1", "Author2"],
  "year": 2024,
  "conference": "CVPR 2024",
  "arxiv_id": "2404.xxxxx",
  "links": {
    "arxiv": "https://arxiv.org/abs/...",
    "pdf": "https://arxiv.org/pdf/...",
    "code": "https://github.com/...",
    "demo": "https://..."
  },
  "abstract": "...",
  "citations": 1234,
  "key_contributions": ["...", "..."],
  "evaluation_metrics": ["IoU", "LPIPS"],
  "implementation_language": "Python/PyTorch",
  "relevance_to_your_system": "High/Medium/Low"
}
```

### **Step 3: Quality Scoring (Sort by Relevance)**

Prioritize papers by this scoring formula:

```
Score = (Relevance × 0.4) + (Citations / 100 × 0.3) + (Recency × 0.2) + (Code Available × 0.1)

Where:
- Relevance: How directly related (0-10)
- Citations: Academic impact (divide by 100 for normalization)
- Recency: Year - 2015 (normalize 0-10)
- Code Available: Binary (1 if yes, 0 if no)
```

### **Step 4: Build Your Literature Matrix**

Create this organizational structure:

```markdown
## Literature Review Matrix

### Segmentation & Masking (3-5 papers)
- SAM/SAM2
- Competing methods
- Benchmarks

### Inpainting & Content-Aware Editing (3-5 papers)
- LaMa
- Competing approaches
- Generative methods

### Scene Understanding & Graphs (2-3 papers)
- Scene graphs
- Spatial relationships
- Visual reasoning

### Interactive Systems (2-3 papers)
- User interaction patterns
- Real-time inference
- GUI design patterns

### Evaluation Metrics (2-3 papers)
- Perceptual metrics
- Benchmarking standards
- Statistical methods

### RAG & Knowledge Graphs (2-3 papers)
- Retrieval-augmented generation
- Knowledge graphs
- Context retrieval

Total: 15-22 key papers for comprehensive literature review
```

---

## 🎯 Browser-Use / Firecrawl Search Strategy

### **Optimal Search Query Templates**

For maximum paper discovery effectiveness:

**Template 1 - Algorithm Focus:**
```
"[Paper Title] PDF site:arxiv.org OR site:openreview.net"
"[Algorithm] segmentation [Year] site:arxiv.org"
```

**Template 2 - Metric Focus:**
```
"[Metric name] evaluation benchmark site:arxiv.org"
"perceptual quality inpainting metrics"
```

**Template 3 - Application Focus:**
```
"interactive image editing segmentation 2023 2024"
"scene understanding spatial relationships graphs"
"graph-augmented image generation"
```

**Template 4 - Benchmark Focus:**
```
"[Dataset name] benchmark results inpainting"
"[Metric] comparison state-of-the-art"
```

### **Optimal Search Order**

1. **Start with arXiv** - Most comprehensive, has citations
2. **Cross-reference on Papers with Code** - Verify with implementations
3. **Check Google Scholar** - See citation counts and related work
4. **Search OpenReview** - Latest conference submissions

### **Extract Full PDFs**

For each paper found:
- Get direct PDF link (usually `arxiv.org/pdf/xxxx.xxxxx.pdf`)
- Capture code repository if available
- Note any supplementary materials
- Record citation count for relevance weighting

---

## 📋 Quick Reference: Paper Finding Commands

Use these search strings directly in browser-use:

```
1. "Segment Anything Model 2024 site:arxiv.org"
2. "LaMa inpainting fast fourier convolution"
3. "Scene graph generation visual relationships"
4. "LPIPS perceptual metric image quality"
5. "CIEDE2000 color difference metric"
6. "Retrieval augmented generation knowledge graph"
7. "Interactive segmentation user guidance"
8. "FID Fréchet inception distance GAN"
```

---

## ✅ Recommended Reading Order for Your Capstone

### **Week 1: Foundation (Algorithms)**
- SAM2 paper (Ke et al., 2024)
- LaMa paper (Suvorov et al., 2022)
- Original SAM (Kirillov et al., 2023)

**Outcome:** Deep understanding of core algorithms + mathematical foundations

### **Week 2: Scene Understanding (Graphs)**
- Scene Graph Generation (Li et al., 2019)
- Visual Relationship Detection
- Knowledge Graph Embeddings

**Outcome:** Understand how spatial relationships are formalized and computed

### **Week 3: Evaluation & Metrics**
- LPIPS paper (Zhang et al., 2018)
- FID metric papers
- CIEDE2000 color science
- Segmentation metrics literature

**Outcome:** Justify your evaluation framework with peer-reviewed standards

### **Week 4: Related Work (Context)**
- Retrieval-Augmented Generation (Lewis et al., 2020)
- Interactive Image Editing systems
- Vision Transformers (Dosovitskiy et al., 2020)

**Outcome:** Position your work within broader research landscape

### **Week 5: Synthesis & Comparison**
- Benchmark papers and comparisons
- State-of-the-art comparisons
- Implementation details from Papers with Code

**Outcome:** Ready to write your literature review with proper context

---

## 📊 Expected Coverage from These Papers

| Topic | Papers | Coverage |
|-------|--------|----------|
| Segmentation (SAM/SAM2) | 2-3 | ✅ Comprehensive |
| Inpainting (LaMa) | 2-3 | ✅ Comprehensive |
| Scene Graphs | 2-3 | ✅ Complete |
| Evaluation Metrics | 3-4 | ✅ In-depth |
| Interactive Systems | 2 | ✅ Good |
| RAG + Knowledge Graphs | 2 | ✅ Sufficient |
| Vision Transformers | 1 | ✅ Foundation |
| **Total** | **15-22** | **✅ Excellent** |

---

## 🎓 Literature Review Organization Tips

### **Suggested Sections for Your Literature Review**

```markdown
# Literature Review

## 1. Semantic Segmentation & Masking
   1.1 Traditional Segmentation Methods
   1.2 Deep Learning Approaches
   1.3 Vision Transformers & SAM
   1.4 Multi-scale Segmentation (SAM2)

## 2. Content-Aware Image Inpainting
   2.1 Traditional Inpainting Techniques
   2.2 Deep Learning-Based Inpainting
   2.3 GAN-Based Approaches
   2.4 Fourier-Based Methods (LaMa)

## 3. Scene Understanding & Knowledge Graphs
   3.1 Scene Graph Generation
   3.2 Spatial Relationship Detection
   3.3 Knowledge Graph Embeddings
   3.4 Visual Reasoning

## 4. Interactive Image Editing Systems
   4.1 User-Guided Segmentation
   4.2 Real-time Inference Requirements
   4.3 Multi-component Workflows

## 5. Retrieval-Augmented Generation
   5.1 RAG Framework Overview
   5.2 Graph-Augmented Generation
   5.3 Context Retrieval Patterns

## 6. Evaluation Metrics & Benchmarking
   6.1 Segmentation Metrics (IoU, Dice)
   6.2 Perceptual Quality Metrics (LPIPS, FID)
   6.3 Color Science (CIEDE2000)
   6.4 Benchmarking Best Practices

## 7. Research Gaps & Contributions
   7.1 Limited Work on Graph-Augmented Interactive Editing
   7.2 Need for Comprehensive Evaluation
   7.3 Our Capstone Contributions
```

---

## 🔗 Useful Research Databases & Tools

| Tool | Best For | URL |
|------|----------|-----|
| **arXiv** | Pre-prints, latest research | https://arxiv.org |
| **Papers with Code** | Code + benchmarks | https://paperswithcode.com |
| **Google Scholar** | Citations, impact | https://scholar.google.com |
| **OpenReview** | Conference submissions | https://openreview.net |
| **Semantic Scholar** | AI-powered search | https://www.semanticscholar.org |
| **ResearchGate** | Author profiles | https://www.researchgate.net |
| **Connected Papers** | Citation visualization | https://www.connectedpapers.com |
| **Elicit** | AI research assistant | https://elicit.org |

---

## 💡 Pro Tips for Literature Review

### **Finding Hidden Gems**

1. **Citation Chains:** Start with a key paper, look at papers it cites (backward citations) and papers that cite it (forward citations)
2. **Author Search:** Find prolific authors in your field and browse their work
3. **Connected Papers:** Use tools like Connected Papers to visualize relationships between papers
4. **Conference Proceedings:** Browse CVPR, ICCV, ECCV for recent work
5. **Preprint Servers:** Check arXiv weekly for latest submissions in your topics

### **Evaluating Paper Quality**

- ✅ **High quality:** CVPR, ICCV, ECCV, NeurIPS, ICML (top-tier venues)
- ✅ **Good quality:** SIGGRAPH, AAAI, IEEE Transactions
- ⚠️ **Variable quality:** arXiv (pre-prints, check conference status)
- ⚠️ **Use cautiously:** ResearchGate (unvetted), Medium blogs

### **Reading Strategy**

1. **First pass:** Abstract + introduction → Understand motivation
2. **Second pass:** Methodology + figures → Understand approach
3. **Third pass:** Experiments + results → Understand performance
4. **Final pass:** Conclusion + references → Understand impact

---

## 🚀 Implementation Workflow

### **Step-by-Step Execution**

1. **Week 1: Discovery**
   - Use the 3 prompts with browser-use
   - Execute searches from quick reference section
   - Collect 20-25 candidate papers
   - Score using the quality formula

2. **Week 2: Analysis**
   - Download top 15-22 papers
   - Extract key information into JSON
   - Build literature matrix
   - Identify patterns and gaps

3. **Week 3: Organization**
   - Group papers by category
   - Create literature review outline
   - Map papers to outline sections
   - Identify paper synthesis opportunities

4. **Week 4: Writing**
   - Write one section per day
   - Integrate citations naturally
   - Compare/contrast approaches
   - Highlight novel contributions

5. **Week 5: Refinement**
   - Ensure comprehensive coverage
   - Check citation accuracy
   - Refine connections between papers
   - Polish final version

---

## ✅ Completion Checklist

- [ ] Executed 3 search prompts with browser-use
- [ ] Found 15-22 core papers
- [ ] Downloaded PDFs for all papers
- [ ] Created structured metadata (JSON) for each
- [ ] Built literature matrix
- [ ] Organized by 6-7 categories
- [ ] Written literature review draft
- [ ] Cross-referenced with capstone work
- [ ] Identified research gaps your system addresses
- [ ] Refined final literature review

---

## 📞 Quick Reference

**Need papers on:** → **Search these terms:**
- Segmentation → "SAM segment anything"
- Inpainting → "LaMa inpainting fourier"
- Graphs → "scene graph generation"
- Metrics → "LPIPS FID evaluation"
- Interactive → "interactive segmentation user"
- RAG → "retrieval augmented generation"

---

**Document Status:** Complete & Ready to Use  
**Last Updated:** April 19, 2026  
**Related Docs:** [09_ML_MATHEMATICS_AND_EVALUATION_V3.md](./09_ML_MATHEMATICS_AND_EVALUATION_V3.md) | [10_ML_RESEARCH_SUMMARY.md](./10_ML_RESEARCH_SUMMARY.md)

