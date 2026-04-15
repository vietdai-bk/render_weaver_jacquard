from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
import uuid
import json
from convert_json import convert_hsv_to_matrix, save_library
from weaver_render import SmartWeaver3D

app = FastAPI(title="Weaving AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
RENDER_DIR = "renders"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RENDER_DIR, exist_ok=True)

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "API is running"}

@app.post("/api/patterns/render")
async def render_pattern(request: Request, file: UploadFile = File(...)):
    print(f"--- NHẬN ĐƯỢC YÊU CẦU UPLOAD ---")
    print(f"File name: {file.filename}")
    file_id = str(uuid.uuid4())[:8]
    input_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        matrix = convert_hsv_to_matrix(input_path)
        if matrix is None:
            raise HTTPException(status_code=400, detail="Không thể xử lý ảnh. Vui lòng thử ảnh khác.")
        
        pattern_key = f"pattern_{file_id}"
        save_library(pattern_key, matrix, filename="pattern_library.json")
        
        weaver = SmartWeaver3D(pattern_key, library_file="pattern_library.json")
        rendered_img = weaver.render()
        
        output_filename = f"render_{file_id}.png"
        output_path = os.path.join(RENDER_DIR, output_filename)
        rendered_img.save(output_path)

        base_url = str(request.base_url)
        return {
            "image_url": f"{base_url}renders/{output_filename}",
            "pattern": {
                "name": pattern_key,
                "matrix": matrix
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

@app.get("/renders/{filename}")
async def get_render(filename: str):
    file_path = os.path.join(RENDER_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)

class AIPromptReq(BaseModel):
    prompt: str
    auto_mode: bool = False

@app.post("/api/ai/generate")
async def generate_from_prompt(req: AIPromptReq):
    dummy_matrix = [[1, 2, 1, 2], [2, 1, 2, 1]]
    return {
        "pattern_name": "ai_generated_1",
        "matrix": dummy_matrix,
        "levers": [11, 13, 15] if req.auto_mode else [1, 3, 5],
        "color_map": {"1": [180, 40, 50], "2": [45, 110, 75]},
        "message": f"Đã tạo mẫu thành công cho yêu cầu: '{req.prompt}'"
    }

@app.get("/api/patterns")
async def get_all_patterns():
    if not os.path.exists("pattern_library.json"):
        return {"patterns": []}
    with open("pattern_library.json", "r") as f:
        data = json.load(f)
    return {"patterns": [{"name": k} for k in data.keys()]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)