# AI Video Retrieval System

Hệ thống tìm kiếm video thông minh được tối ưu hóa cho thi đấu, kết hợp Vector Search (ngữ nghĩa/đa phương thức) và Text Search (ASR/OCR) với chuẩn hóa điểm số và ensemble để xếp hạng Top-K kết quả.

<!-- TODO: Chèn ảnh giao diện tìm kiếm tại đây -->
![Giao diện tìm kiếm](./images/1.png)
![Giao diện xem keyframes](./images/2.png)
## 📋 Mục lục

- [Mục tiêu hệ thống](#mục-tiêu-hệ-thống)
- [Kiến trúc tổng thể](#kiến-trúc-tổng-thể)
- [Pipeline tìm kiếm](#pipeline-tìm-kiếm)
- [Các phương pháp tìm kiếm](#các-phương-pháp-tìm-kiếm)
- [Query Augmentation](#query-augmentation)
- [Ensemble & Normalization](#ensemble--normalization)
- [Tính năng nâng cao](#tính-năng-nâng-cao)
- [Hệ thống Chatbox & DRES](#hệ-thống-chatbox--dres)
- [Cài đặt & Sử dụng](#cài-đặt--sử-dụng)
- [Tech Stack](#tech-stack)

---

## 🎯 Mục tiêu hệ thống

1. **Truy xuất video theo truy vấn người dùng**: Hệ thống được tối ưu hóa đặc biệt cho môi trường thi đấu, đảm bảo tốc độ và độ chính xác cao.

2. **Kết hợp đa phương thức**: Tích hợp Vector Search (ngữ nghĩa/đa phương thức) + Text Search (ASR/OCR), sau đó chuẩn hóa điểm số và ensemble để xếp hạng Top-K.

3. **Hỗ trợ teamwork và nộp bài**: Tích hợp tính năng Chatbox để làm việc nhóm và hệ thống nộp bài DRES (KIS).

---

## 🏗️ Kiến trúc tổng thể

Hệ thống được xây dựng theo kiến trúc 3 tầng rõ ràng:

### 2.1. Frontend (UI) — React + Vite

Giao diện người dùng cho phép:

- **Nhập query** (tiếng Việt/tiếng Anh) và cấu hình chiến lược tìm kiếm:
  - Bật/tắt các nhánh tìm kiếm (Multimodal / IC / ASR / OCR)
  - Cấu hình Multi-stage search
  - Chọn chế độ Temporal aggregation (ID mode / Tuple mode)
  - Lọc theo đối tượng (Object filter)

- **Hiển thị kết quả**:
  - Top-K kết quả theo keyframe/video
  - Chọn và lưu đáp án vào Chatbox
  - Thao tác nộp bài qua DRES

### 2.2. Backend Orchestrator — FastAPI

Điều phối end-to-end pipeline tìm kiếm:

1. **Preprocessing**: Dịch query (VN → EN khi cần)
2. **Query Augmentation**: Sử dụng Gemini để tạo Q0, Q1, Q2
3. **Embedding Extraction**: Gọi Embedding Services (CLIP/BEiT-3/BIGG/Qwen) qua NGROK
4. **Parallel Search**: 
   - Vector Search (Qdrant): CLIP, BEiT-3, BIGG, IC
   - Text Search (Elasticsearch): ASR, OCR
5. **Score Normalization & Ensemble**: Chuẩn hóa điểm số và kết hợp nhiều cấp
6. **Multi-Stage Processing** (tùy chọn): Xử lý nhiều giai đoạn tìm kiếm
7. **Temporal Aggregation** (tùy chọn): Tổng hợp kết quả theo thời gian
8. **Object Filtering** (tùy chọn): Lọc theo đối tượng đã chọn
9. **Final Ranking**: Mapping ID → keyframe path + timestamp (FPS) → trả Top-K

**Tích hợp**:
- Chatbox/Collab (PostgreSQL): Lưu và chia sẻ đáp án
- DRES submit: Auto-fill thông tin từ mapping + FPS

### 2.3. Data & Infrastructure Layer

- **Qdrant (Vector DB)**: 
  - Collections: `clip`, `beit3`, `bigg_clip`, `ic`
  - Lưu trữ embeddings cho vector search

- **Elasticsearch (Text Search)**: 
  - Indices: `asr` (transcript audio), `ocr` (text trong video), `object` (object detection)
  - Hỗ trợ BM25 search

- **PostgreSQL**: 
  - Chatbox/collab: Lưu đáp án, query, keyframe/video liên quan

---

## 🔄 Pipeline tìm kiếm

### Runtime Search Pipeline

```
User Query (VN/EN)
    ↓
[1] Query Preprocessing
    - Translation (VN → EN khi cần)
    - Query Augmentation (Gemini): Q0, Q1, Q2
    - Method Selection
    ↓
[2] Parallel Embedding Extraction
    - CLIP/BEiT-3/BIGG/Qwen → NGROK Servers
    ↓
[3] Parallel Search
    - Vector Search (Qdrant): CLIP, BEiT-3, BIGG, IC
    - Text Search (Elasticsearch): ASR, OCR
    ↓
[4] Score Normalization & Ensemble
    - Z-score (multimodal), Min-Max (IC), BM25 (ASR/OCR)
    - Weighted ensemble (CLIP:0.25, BEiT3:0.50, BIGG:0.25)
    ↓
[5] Multi-Stage Processing (optional)
    - Stage 1, 2, ... N (mỗi stage có Q0, Q1, Q2)
    - Temporal Aggregation (ID mode / Tuple mode)
    ↓
[6] Object Filtering (optional)
    - Elasticsearch filter by selected objects
    ↓
[7] Final Ranking
    - Sort by score → ID → Keyframe Path mapping
    - Return Top-K results
```

### Offline Data Preparation

#### Phase 1: Tiền xử lý dữ liệu (Kaggle)

- **Scene Extraction → Keyframes**: Sử dụng AutoShot để phát hiện scene và trích xuất keyframes
- **Embedding Extraction**:
  - Multimodal: CLIP, BEiT-3, BIGG → FAISS .bin files
  - IC: BLIP-2 (caption) + Qwen3 (embedding) → IC.bin + IC.json
  - OCR: Gemini 2.5 Flash → NDJSON format
  - ASR: Speech-to-text → Elasticsearch index
  - Object: Object detection → Elasticsearch index
- **Output Files**: 
  - `.bin` files: clip.bin, beit3.bin, bigg_clip.bin, IC.bin
  - JSON files: mapping_kf.json, mapping_scene.json, fps_mapping.json, IC.json
  - Elasticsearch indices: asr, ocr, object

#### Phase 2: Deployment (NGROK + Vector DB)

- **Embedding Services (Kaggle → Internet qua NGROK)**:
  - Server embedding: CLIP, BEiT-3, BIGG, Qwen chạy trên Kaggle
  - NGROK tạo public endpoints với load balancing:
    - `EMBEDDING_SERVER_MULTIMODAL`
    - `EMBEDDING_SERVER_QWEN`

- **Vector Database Ingestion**:
  - Load FAISS .bin files → Upload vào Qdrant collections
  - Batch processing: 50 vectors/batch (memory-efficient)

---

## 🔍 Các phương pháp tìm kiếm

Hệ thống tích hợp 4 phương pháp tìm kiếm chính:

### 1. Multimodal Vector Search (Qdrant)

- **Ensemble 3 model**: CLIP (0.25) + BEiT-3 (0.50) + BIGG (0.25)
- Tận dụng điểm mạnh của từng model trong việc hiểu nội dung đa phương thức
- Vector search trên Qdrant collections: `clip`, `beit3`, `bigg_clip`

### 2. IC Search (Caption-based)

- **Offline**: BLIP-2 tạo caption → Qwen embedding
- **Runtime**: Vector search trên Qdrant collection `ic` + Cohere reranking (tùy chọn)
- Tìm kiếm dựa trên mô tả nội dung của keyframes

### 3. ASR Search (Text)

- **Elasticsearch BM25** trên transcript audio
- Hỗ trợ tìm kiếm tiếng Việt trực tiếp
- Index: `asr`

### 4. OCR Search (Text)

- **Elasticsearch BM25** trên OCR/subtitle/chữ trong khung hình
- Tìm text xuất hiện trong video
- Index: `ocr`

---

## 🚀 Query Augmentation

Hệ thống sử dụng **Gemini 2.0 Flash Lite** để tự động tạo tập truy vấn đa biến thể, nhằm tăng recall và ổn định Top-K:

- **Q0**: Query gốc (hoặc đã dịch VN→EN khi cần)
- **Q1, Q2**: Gemini sinh 2 biến thể tương đương ngữ nghĩa

**Fallback an toàn**: Nếu lỗi/timeout/parse fail → dùng lại Q0 cho Q1/Q2.

Điều này giúp tăng khả năng tìm thấy kết quả phù hợp ngay cả khi cách diễn đạt khác nhau, từ đó nâng cao recall của hệ thống.

---

## 📊 Ensemble & Normalization

Hệ thống thực hiện ensemble và chuẩn hóa điểm số ở 3 cấp độ:

### 8.1. Level 1 — Within Multimodal (theo từng Qi)

- **CLIP/BEiT-3/BIGG**: 
  - Z-score normalization
  - Weighted sum (0.25 / 0.50 / 0.25)
  - Min-Max scaling

### 8.2. Level 2 — Cross-Methods (theo từng Qi)

- Kết hợp **Multimodal + IC + ASR + OCR** (các nhánh được bật)
- **Scaling theo nhánh**:
  - IC: Min-Max
  - ASR/OCR (BM25): Z-score → Sigmoid
- **Ensemble methods**: Weighted average (mặc định đều nhau nếu không cấu hình)

### 8.3. Level 3 — Cross-Queries

- Gộp **Q0/Q1/Q2** → **Q3** bằng average
- Re-rank lấy Top-K cuối cùng

---

## ⚡ Tính năng nâng cao

### Multi-Stage Search

Cho phép thực hiện nhiều giai đoạn tìm kiếm độc lập, mỗi giai đoạn có thể có:
- Query riêng
- Phương pháp riêng
- Điều kiện lọc riêng

Tất cả các giai đoạn được xử lý **song song** để tối ưu thời gian.

### Temporal Aggregation

Hệ thống hỗ trợ hai chế độ tổng hợp thời gian:

- **ID mode**: Gộp kết quả theo video và cộng điểm để tìm video có nhiều keyframe phù hợp nhất
- **Tuple mode**: Tìm các keyframe liên tiếp có thứ tự tăng dần trong cùng một video, phù hợp cho các query yêu cầu tìm đoạn video liên tục

### Object Filtering

- Lọc kết quả theo đối tượng đã phát hiện (person, car, dog, etc.)
- Sử dụng Elasticsearch index `object`

---

## 💬 Hệ thống Chatbox & DRES

### Chatbox (PostgreSQL)

Hệ thống tích hợp tính năng Chatbox để hỗ trợ làm việc nhóm trong thi đấu:

- Khi tìm thấy video phù hợp, thành viên có thể **lưu đáp án** kèm query và keyframe vào database
- Các thành viên khác có thể **xem lại** tất cả các đáp án đã lưu
- **Lọc** theo query hoặc người submit
- Giúp team chia sẻ và tham khảo các đáp án đã tìm được, tránh trùng lặp

### DRES Integration

Hệ thống tích hợp với **DRES** (hệ thống chấm bài thi đấu) để nộp đáp án chính thức:

- Sau khi đăng nhập và chọn evaluation, người dùng có thể nộp đáp án theo 3 chế độ:
  - **KIS**: Nộp đoạn video với thời gian bắt đầu và kết thúc
  - **QA**: Nộp câu trả lời kèm video và timestamp
  - **TRAKE**: Nộp nhiều frame ID trong cùng video

- **Auto-fill**: Hệ thống tự động điền thông tin từ keyframe path đã chọn, chuyển đổi frame index thành thời gian theo FPS

<!-- TODO: Chèn ảnh giao diện nộp bài DRES tại đây -->
![Giao diện nộp bài DRES](./images/2.png)

---

## 🚀 Cài đặt & Sử dụng

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- Qdrant running on port 6333
- Elasticsearch running on port 9200

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -e .

# Create .env file
cp env.example .env
# Edit .env with your API keys (Gemini, NGROK endpoints, etc.)

# Run backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

### Docker Compose (Full Stack)

```bash
# Start all services
docker-compose up -d

# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Qdrant: http://localhost:6333
# Elasticsearch: http://localhost:9200
```

### Cấu hình Embedding Servers

Đảm bảo các embedding servers đang chạy trên Kaggle và được expose qua NGROK:

```env
EMBEDDING_SERVER_MULTIMODAL= server_ngrok
EMBEDDING_SERVER_QWEN= server_ngrok
```

---

## 🛠️ Tech Stack

### Frontend
- **React 18.2** + **Vite 5.4**: Giao diện người dùng
- **TailwindCSS**: Styling
- **Context API**: State management

### Backend
- **FastAPI 0.104**: REST API server
- **Python 3.12**: Backend language
- **Pydantic**: Data validation
- **ThreadPoolExecutor**: Parallel processing (20 workers)

### Infrastructure
- **Qdrant 1.7**: Vector database
- **Elasticsearch 8.x**: Text search engine
- **PostgreSQL**: Chatbox database
- **NGROK**: Tunneling từ Kaggle ra internet

### AI Models & Services
- **CLIP**: Multimodal embedding
- **BEiT-3**: Multimodal embedding
- **BIGG**: Multimodal embedding
- **Qwen3**: Text embedding (IC search)
- **BLIP-2**: Image captioning
- **Gemini 2.0 Flash Lite**: Query augmentation
- **Gemini 2.5 Flash**: OCR extraction
- **Cohere**: Reranking (IC search)

---

## 📈 Vai trò trong thi đấu

Hệ thống được thiết kế để đáp ứng các yêu cầu khắt khe của môi trường thi đấu:

### Tốc độ
- Xử lý song song ở nhiều tầng (query variants, search methods, stages)
- ThreadPoolExecutor với 20 workers
- NGROK với load balancing
- Đảm bảo thời gian phản hồi nhanh ngay cả khi có nhiều người dùng đồng thời

### Độ chính xác
- Query augmentation tăng recall
- Ensemble kết hợp điểm mạnh của nhiều phương pháp
- Reranking bằng Cohere
- Temporal aggregation tìm đoạn video liên tục

### Linh hoạt
- Điều chỉnh chiến lược theo từng giai đoạn
- Bật/tắt phương pháp theo nhu cầu
- Lọc theo đối tượng
- Chọn chế độ tổng hợp thời gian phù hợp

### Collaboration
- Chatbox chia sẻ đáp án
- Tích hợp DRES nộp bài
- Auto-fill tiết kiệm thời gian

---

## 📄 License

CS336 - Information Retrieval Project

## 👥 Contributors

- Team CS336
- AI Video Retrieval System
