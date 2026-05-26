from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from PIL import Image
import os
import shutil
from datetime import datetime
import json

# 1. Gemini API 설정 (본인의 API 키로 변경하세요)
import os
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# 최신 시각 분석 모델인 gemini-1.5-flash 사용 (속도가 빠르고 비용이 저렴함)
model = genai.GenerativeModel('gemini-3.5-flash')

app = FastAPI(
    title="시니어 당뇨 관리 AI 식단 분석 서버",
    description="사진 한 장으로 당뇨 식단을 분석해주는 API",
    version="1.0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/v1/analyze-food", tags=["Diet Analysis"])
async def analyze_food(file: UploadFile = File(...)):
    # 1. 파일 저장 로직 (이전과 동일)
    allowed_extensions = ["jpg", "jpeg", "png", "webp"]
    file_extension = file.filename.split(".")[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="지원하지 않는 이미지 형식입니다.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"food_{timestamp}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Gemini AI에게 전달할 '시니어 맞춤형 프롬프트(지시서)' 작성
    # 프론트엔드에서 색상(초록/노랑/빨강)을 바로 띄울 수 있도록 JSON 형태로 요구합니다.
    prompt = """
    당신은 당뇨와 혈당 관리가 필수적인 시니어(어르신)를 전담하는 친절하고 전문적인 AI 영양사입니다.
    첨부된 음식 사진을 분석하고, 반드시 아래의 순수 JSON 형식으로만 답변해주세요. (마크다운이나 다른 텍스트 금지)
    
    {
      "food_name": "음식 이름 (예: 흰쌀밥과 찌개)",
      "status": "green",  // 혈당에 안전하면 green, 주의가 필요하면 yellow, 위험하면 red
      "message": "어르신을 위한 1~2문장의 다정하고 읽기 쉬운 조언 (존댓말 사용, 글씨를 크게 볼 수 있게 짧고 명확하게)"
    }
    """

    # 3. Gemini API 호출 및 이미지 분석
    try:
        image = Image.open(file_path)
        response = model.generate_content([prompt, image])
        
        # JSON 텍스트 추출 및 파싱
        # (AI가 가끔 ```json 백틱을 붙이는 경우가 있어 이를 제거해주는 안전장치)
        raw_text = response.text.strip().replace("```json", "").replace("```", "")
        analysis_result = json.loads(raw_text)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 분석 중 오류가 발생했습니다: {str(e)}")

    # 4. 최종 결과 반환
    return {
        "success": True,
        "saved_path": file_path,
        "ai_analysis": analysis_result
    }
