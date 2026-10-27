from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from typing import List, Dict
from app.services.pdf_parser import PDFParser, QuizGenerator
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User

router = APIRouter(prefix="/pdf", tags=["PDF Upload"])

@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin)
):
    """رفع ملف PDF واستخراج الأسئلة"""
    
    # ✅ التحقق من نوع الملف
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="⚠️ يرجى رفع ملف PDF فقط"
        )
    
    try:
        # ✅ استخراج النص من PDF
        text = await PDFParser.extract_text_from_pdf(file)
        
        if not text:
            raise HTTPException(
                status_code=400,
                detail="⚠️ لم يتم العثور على نص في ملف PDF"
            )
        
        # ✅ استخراج الأسئلة
        questions = PDFParser.extract_questions_from_text(text)
        
        if not questions:
            raise HTTPException(
                status_code=400,
                detail="⚠️ لم يتم العثور على أسئلة في ملف PDF"
            )
        
        # ✅ تصنيف الأسئلة
        classified_questions = PDFParser.classify_questions(questions)
        
        return {
            "success": True,
            "message": f"✅ تم استخراج {len(classified_questions)} سؤال",
            "questions": classified_questions,
            "total": len(classified_questions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"❌ حدث خطأ: {str(e)}"
        )

@router.post("/generate-quiz")
async def generate_quiz(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin)
):
    """رفع PDF وتوليد كويز HTML مباشر"""
    
    # ✅ التحقق من نوع الملف
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="⚠️ يرجى رفع ملف PDF فقط"
        )
    
    try:
        # ✅ استخراج النص من PDF
        text = await PDFParser.extract_text_from_pdf(file)
        
        if not text:
            raise HTTPException(
                status_code=400,
                detail="⚠️ لم يتم العثور على نص في ملف PDF"
            )
        
        # ✅ استخراج الأسئلة
        questions = PDFParser.extract_questions_from_text(text)
        
        if not questions:
            raise HTTPException(
                status_code=400,
                detail="⚠️ لم يتم العثور على أسئلة في ملف PDF"
            )
        
        # ✅ تصنيف الأسئلة
        classified_questions = PDFParser.classify_questions(questions)
        
        # ✅ توليد HTML
        title = file.filename.replace('.pdf', '').replace('_', ' ').title()
        html = QuizGenerator.generate_quiz_html(classified_questions, title)
        
        # ✅ إرجاع HTML
        return Response(
            content=html,
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename={title}_quiz.html"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"❌ حدث خطأ: {str(e)}"
        )