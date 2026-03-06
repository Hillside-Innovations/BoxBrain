# Tech Stack (High-Level)

- **Frontend:** Simple mobile-first web app (React + Vite) used to create boxes, upload a short video, and search for items.
- **Backend:** Python FastAPI server that receives videos, manages boxes, and handles search requests.
- **Media Processing:** ffmpeg extracts image frames from uploaded videos.
- **AI Vision:** Multimodal model analyzes frames to identify objects inside the box.
- **Search Intelligence:** Text embeddings generated for each detected object.
- **Vector Database:** ChromaDB stores embeddings and enables semantic search ("allen key" ≈ "hex wrench").
- **Database:** SQLite stores box records and metadata.

All components can run locally on a single machine for the MVP.
