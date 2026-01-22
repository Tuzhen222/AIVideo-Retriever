# KIẾN TRÚC HỆ THỐNG VIDEO RETRIEVAL

## 1. TỔNG QUAN KIẾN TRÚC

Hệ thống được xây dựng theo kiến trúc 3 tầng rõ ràng: giao diện người dùng (Frontend), server xử lý logic (Backend), và các cơ sở dữ liệu chuyên dụng. Mỗi tầng có vai trò riêng biệt, tạo nên một hệ thống hoàn chỉnh và hiệu quả.

### 1.1. Kiến trúc 3 tầng
- **Frontend**: React + Vite (giao diện người dùng)
- **Backend**: FastAPI (xử lý logic tìm kiếm)
- **Infrastructure**: Qdrant (vector DB), Elasticsearch (text search), PostgreSQL (chatbox)

### 1.2. Các phương pháp tìm kiếm

Hệ thống tích hợp 4 phương pháp tìm kiếm chính, mỗi phương pháp có thế mạnh riêng để đảm bảo tìm được kết quả phù hợp nhất:

1. **Multimodal Search**: Kết hợp 3 model CLIP (25%), BEiT-3 (50%) và BIGG (25%) để tận dụng điểm mạnh của từng model trong việc hiểu nội dung đa phương thức
2. **IC Search**: Sử dụng Qwen embedding kết hợp với Cohere reranking để tìm kiếm dựa trên caption của keyframes
3. **ASR Search**: Tìm kiếm trong transcript audio của video, hỗ trợ tìm kiếm tiếng Việt trực tiếp
4. **OCR Search**: Tìm text xuất hiện trong video như subtitle hoặc chữ trên màn hình

---

## 2. PIPELINE HỆ THỐNG

Hệ thống hoạt động theo 3 giai đoạn chính: tiền xử lý dữ liệu, triển khai hệ thống, và quy trình tìm kiếm thời gian thực. Mỗi giai đoạn được thiết kế cẩn thận để đảm bảo hiệu quả và độ chính xác.

### 2.1. Phase 1: Tiền xử lý dữ liệu (Kaggle)

Toàn bộ quá trình tiền xử lý được thực hiện trên nền tảng Kaggle. Đầu tiên, hệ thống sử dụng AutoShot để phát hiện các scene trong video và trích xuất keyframes đại diện. Sau đó, các keyframes này được xử lý bằng nhiều phương pháp khác nhau để tạo ra các loại dữ liệu phục vụ tìm kiếm.

#### Scene Extraction → Keyframes
- **Công cụ**: AutoShot
- **Output**: Keyframes được trích xuất từ scenes

#### Embedding Extraction
- **Multimodal**: CLIP, BEiT-3, BIGG → FAISS .bin files
- **IC**: BLIP-2 (caption) + Qwen3 (embedding) → IC.bin + IC.json
- **OCR**: Gemini 2.5 Flash (ocr.py) → NDJSON format
- **ASR**: Speech-to-text → Elasticsearch index
- **Object**: Object detection → Elasticsearch index

#### Output Files
- `.bin` files (FAISS): clip.bin, beit3.bin, bigg_clip.bin, IC.bin
- JSON files: mapping_kf.json, mapping_scene.json, fps_mapping.json, IC.json
- Elasticsearch indices: asr, ocr, object

### 2.2. Phase 2: Deployment (NGROK + Vector DB)

Để đưa các model embedding lên môi trường production, hệ thống sử dụng NGROK để tạo đường hầm từ Kaggle ra internet công cộng. Các embedding servers chạy trên Kaggle được expose thông qua NGROK, cho phép backend gọi API từ xa một cách ổn định. Các file embedding được tải lên Qdrant (vector database) và các file text được index vào Elasticsearch để phục vụ tìm kiếm.

#### Model Servers (Kaggle → NGROK)
- Kaggle chạy embedding servers (CLIP, BEiT-3, BIGG, Qwen3)
- NGROK tạo public URL → Forward traffic
- Config: `EMBEDDING_SERVER_MULTIMODAL`, `EMBEDDING_SERVER_QWEN` (load balancing)

#### Vector Database Ingestion
- Load FAISS .bin files → Upload vào Qdrant collections
- Collections: clip, beit3, bigg_clip, IC
- Batch processing: 50 vectors/batch (memory-efficient)

### 2.3. Phase 3: Runtime Search Pipeline

Khi người dùng nhập query, hệ thống sẽ thực hiện một loạt các bước xử lý song song để đảm bảo tốc độ và độ chính xác. Đầu tiên, query được dịch sang tiếng Anh (nếu cần) và tạo thêm các biến thể để tăng khả năng tìm thấy kết quả. Sau đó, hệ thống tạo embeddings và tìm kiếm song song trong cả vector database và text database. Kết quả được chuẩn hóa điểm số và kết hợp lại một cách thông minh. Nếu có nhiều giai đoạn tìm kiếm, hệ thống sẽ tổng hợp kết quả theo thời gian để tìm các đoạn video liên tục. Cuối cùng, hệ thống có thể lọc theo đối tượng và sắp xếp để trả về top-K kết quả phù hợp nhất.

```
Query Input
    ↓
[1] Query Preprocessing
    - Translation (VN → EN)
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

---

## 3. CƠ CHẾ TÌM KIẾM NÂNG CAO

Hệ thống tích hợp nhiều cơ chế nâng cao để cải thiện hiệu quả tìm kiếm. Các cơ chế này hoạt động cùng nhau để đảm bảo tìm được kết quả chính xác nhất trong thời gian ngắn nhất.

### 3.1. Query Augmentation
Hệ thống sử dụng Gemini 2.0 Flash Lite để tự động tạo thêm 2 biến thể query từ query gốc. Điều này giúp tăng khả năng tìm thấy kết quả phù hợp ngay cả khi cách diễn đạt khác nhau, từ đó nâng cao recall của hệ thống.

### 3.2. Multi-Stage Search
Cho phép thực hiện nhiều giai đoạn tìm kiếm độc lập, mỗi giai đoạn có thể có query riêng, phương pháp riêng và điều kiện lọc riêng. Tất cả các giai đoạn được xử lý song song để tối ưu thời gian, giúp người dùng có thể điều chỉnh chiến lược tìm kiếm linh hoạt.

### 3.3. Temporal Aggregation
Hệ thống hỗ trợ hai chế độ tổng hợp thời gian: **ID mode** gộp kết quả theo video và cộng điểm để tìm video có nhiều keyframe phù hợp nhất, và **Tuple mode** tìm các keyframe liên tiếp có thứ tự tăng dần trong cùng một video, phù hợp cho các query yêu cầu tìm đoạn video liên tục.

### 3.4. Ensemble Strategy
Hệ thống kết hợp kết quả từ nhiều tầng: kết hợp 3 model trong multimodal search, kết hợp các phương pháp tìm kiếm khác nhau, kết hợp các biến thể query, và cuối cùng kết hợp tất cả để đưa ra kết quả cuối cùng có độ chính xác cao nhất. Mỗi tầng ensemble đều được tính toán với trọng số phù hợp.

---

## 4. HỆ THỐNG CHATBOX

Hệ thống tích hợp tính năng Chatbox để hỗ trợ làm việc nhóm trong thi đấu. Khi tìm thấy video phù hợp, thành viên có thể lưu đáp án kèm query và keyframe vào database PostgreSQL. Các thành viên khác có thể xem lại tất cả các đáp án đã lưu, lọc theo query hoặc người submit, giúp team chia sẻ và tham khảo các đáp án đã tìm được, tránh trùng lặp và nâng cao hiệu quả làm việc nhóm.

---

## 5. HỆ THỐNG NỘP BÀI DRES

Hệ thống tích hợp với DRES (hệ thống chấm bài thi đấu) để nộp đáp án chính thức. Sau khi đăng nhập và chọn evaluation, người dùng có thể nộp đáp án theo 3 chế độ: KIS (nộp đoạn video với thời gian bắt đầu và kết thúc), QA (nộp câu trả lời kèm video và timestamp), hoặc TRAKE (nộp nhiều frame ID trong cùng video). Hệ thống tự động điền thông tin từ keyframe path đã chọn, chuyển đổi frame index thành thời gian theo FPS, giúp quá trình nộp bài diễn ra nhanh chóng và chính xác.

---

## 6. VAI TRÒ TRONG THI ĐẤU

Hệ thống được thiết kế để đáp ứng các yêu cầu khắt khe của môi trường thi đấu, tập trung vào ba khía cạnh chính: tốc độ, độ chính xác và tính linh hoạt.

### 6.1. Tốc độ
Hệ thống xử lý song song ở nhiều tầng - từ việc tạo nhiều biến thể query, tìm kiếm bằng nhiều phương pháp, đến xử lý nhiều giai đoạn tìm kiếm cùng lúc. Việc sử dụng ThreadPoolExecutor với 20 workers và NGROK với load balancing giúp phân tải hiệu quả, đảm bảo thời gian phản hồi nhanh ngay cả khi có nhiều người dùng đồng thời.

### 6.2. Độ chính xác
Hệ thống kết hợp nhiều kỹ thuật để nâng cao độ chính xác: query augmentation giúp tăng khả năng tìm thấy kết quả, ensemble kết hợp điểm mạnh của nhiều phương pháp tìm kiếm, reranking bằng Cohere để sắp xếp lại kết quả IC search, và temporal aggregation để tìm các đoạn video liên tục phù hợp với yêu cầu.

### 6.3. Linh hoạt
Hệ thống cho phép điều chỉnh chiến lược theo từng giai đoạn tìm kiếm, bật/tắt các phương pháp theo nhu cầu, lọc theo đối tượng, và chọn chế độ tổng hợp thời gian phù hợp. Điều này giúp người dùng tối ưu hóa quá trình tìm kiếm cho từng loại query cụ thể.

### 6.4. Collaboration
Các tính năng hỗ trợ như Chatbox và tích hợp DRES giúp nâng cao hiệu quả làm việc nhóm và quá trình nộp bài. Tính năng auto-fill tự động điền thông tin từ kết quả tìm kiếm giúp tiết kiệm thời gian nhập liệu, tạo ra một hệ sinh thái hoàn chỉnh phục vụ cho thi đấu video retrieval.

