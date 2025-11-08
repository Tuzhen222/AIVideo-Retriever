# AI Video Retriever - Frontend

Frontend application built with React and Tailwind CSS.

## Yêu cầu hệ thống

- Node.js (version 16 trở lên)
- npm hoặc yarn

## Cài đặt

Mở terminal và chạy các lệnh sau:

```bash
# Di chuyển vào thư mục frontend
cd frontend

# Cài đặt các dependencies
npm install
```

Hoặc nếu dùng yarn:
```bash
cd frontend
yarn install
```

## Chạy development server

Sau khi cài đặt xong, chạy lệnh:

```bash
npm run dev
```

Hoặc:
```bash
yarn dev
```

Khi server khởi động thành công, bạn sẽ thấy thông báo:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

**Mở trình duyệt và truy cập:** `http://localhost:3000`

## Build cho production

Để build ứng dụng cho production:

```bash
npm run build
```

Files đã build sẽ nằm trong thư mục `dist/`

Để preview build production:

```bash
npm run preview
```

## Cấu trúc

- `src/App.jsx` - Component chính với layout 3 phần
- `src/layouts/Header.jsx` - Header bar màu đỏ với stages và view buttons
- `src/layouts/Sidebar.jsx` - Sidebar với query input và controls
- `src/layouts/MainContent.jsx` - Main content area
- `src/components/ClearButton.jsx` - Clear button component
- `src/components/StageButtons.jsx` - Stage buttons component
- `src/components/ViewControls.jsx` - View controls component (E/A/M mode, Num input, Toggle)

