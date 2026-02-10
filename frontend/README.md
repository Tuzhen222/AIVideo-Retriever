# AI Video Retriever - Frontend

Frontend application built with React and Tailwind CSS.

## Requirements

- Node.js (version 16 or higher)
- npm or yarn

## Installation

Open a terminal and run the following commands:

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install
```

Or if using yarn:
```bash
cd frontend
yarn install
```

## Running the Development Server

After installation, run:

```bash
npm run dev
```

Or:
```bash
yarn dev
```

Once the server starts successfully, you will see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

**Open your browser and navigate to:** `http://localhost:3000`

## Production Build

To build the application for production:

```bash
npm run build
```

The built files will be located in the `dist/` directory.

To preview the production build:

```bash
npm run preview
```

## Project Structure

- `src/App.jsx` — Main component with 3-panel layout
- `src/layouts/Header.jsx` — Red header bar with stages and view buttons
- `src/layouts/Sidebar.jsx` — Sidebar with query input and controls
- `src/layouts/MainContent.jsx` — Main content area
- `src/components/ClearButton.jsx` — Clear button component
- `src/components/StageButtons.jsx` — Stage buttons component
- `src/components/ViewControls.jsx` — View controls component (E/A/M mode, Num input, Toggle)
