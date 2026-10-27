import re
import json
from typing import List, Dict, Any
import PyPDF2
import io
from fastapi import UploadFile

class PDFParser:
    """استخراج النص من ملفات PDF"""
    
    @staticmethod
    async def extract_text_from_pdf(file: UploadFile) -> str:
        """استخراج النص من ملف PDF"""
        try:
            content = await file.read()
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text
        except Exception as e:
            raise Exception(f"خطأ في قراءة PDF: {str(e)}")
    
    @staticmethod
    def extract_questions_from_text(text: str) -> List[Dict]:
        """استخراج الأسئلة من النص"""
        
        questions = []
        current_question = {}
        current_options = []
        current_correct = None
        
        # ✅ تنظيف النص
        lines = text.split('\n')
        
        # ✅ أنماط البحث
        question_pattern = r'^(?:Q|سؤال|Question)[\s]*[\.:]*[\s]*(\d+)[\s]*[\.:]*[\s]*(.*?)(?=\n|$)'
        option_pattern = r'^([A-Da-d])[\)\.\:]\s*(.*?)(?=\n|$)'
        correct_pattern = r'(?:الإجابة|Answer|Correct|الصحيح)[\s]*[\.:]*[\s]*(?:[\(]?)([A-Da-d])(?:[\)]?)?'
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # ✅ البحث عن رقم السؤال
            match_question = re.match(question_pattern, line, re.IGNORECASE)
            if match_question:
                # حفظ السؤال السابق
                if current_question and current_options:
                    current_question['options'] = current_options
                    current_question['correct'] = current_correct
                    questions.append(current_question)
                
                # بدء سؤال جديد
                current_question = {
                    'number': int(match_question.group(1)),
                    'text': match_question.group(2).strip()
                }
                current_options = []
                current_correct = None
                continue
            
            # ✅ البحث عن الخيارات
            match_option = re.match(option_pattern, line, re.IGNORECASE)
            if match_option and current_question:
                letter = match_option.group(1).upper()
                option_text = match_option.group(2).strip()
                current_options.append({
                    'letter': letter,
                    'text': option_text
                })
                continue
            
            # ✅ البحث عن الإجابة الصحيحة
            match_correct = re.search(correct_pattern, line, re.IGNORECASE)
            if match_correct and current_question:
                current_correct = match_correct.group(1).upper()
                continue
        
        # ✅ إضافة آخر سؤال
        if current_question and current_options:
            current_question['options'] = current_options
            current_question['correct'] = current_correct
            questions.append(current_question)
        
        return questions
    
    @staticmethod
    def classify_questions(questions: List[Dict]) -> List[Dict]:
        """تصنيف الأسئلة حسب الموضوع"""
        
        categories = {
            'physics': ['physics', 'فيزياء', 'applied physics', 'force', 'energy', 'motion'],
            'mechanics': ['mechanics', 'ميكانيكا', 'stress', 'strain', 'elasticity'],
            'fluids': ['fluid', 'مائع', 'liquid', 'gas', 'pressure', 'flow'],
            'units': ['unit', 'وحدة', 'dimension', 'measurement', 'prefix'],
            'afo': ['afo', 'ankle', 'foot', 'orthosis'],
            'kafo': ['kafo', 'knee', 'thigh', 'orthosis'],
            'prosthetics': ['prosthetic', 'prosthesis', 'limb', 'socket'],
            'orthotics': ['orthotic', 'orthosis', 'brace', 'support'],
            'tf': ['true', 'false', 'صح', 'خطأ']
        }
        
        classified = []
        
        for q in questions:
            # ✅ تحديد الفئة
            category = 'general'
            q_text = q.get('text', '').lower()
            
            for cat, keywords in categories.items():
                if any(keyword in q_text for keyword in keywords):
                    category = cat
                    break
            
            # ✅ تحديد نوع السؤال (True/False)
            is_tf = 'true' in q_text or 'false' in q_text or 'صح' in q_text or 'خطأ' in q_text
            if is_tf and len(q.get('options', [])) <= 2:
                category = 'tf'
            
            # ✅ معالجة خيارات الأسئلة
            options = q.get('options', [])
            if not options:
                # إذا لم تكن هناك خيارات، اجعلها True/False
                options = [
                    {'letter': 'A', 'text': 'True'},
                    {'letter': 'B', 'text': 'False'}
                ]
                category = 'tf'
            
            classified.append({
                'number': q.get('number', len(classified) + 1),
                'text': q.get('text', ''),
                'options': options,
                'correct': q.get('correct', 'A'),
                'category': category,
                'explanation': q.get('explanation', '')
            })
        
        return classified


class QuizGenerator:
    """توليد كويز من الأسئلة المستخرجة"""
    
    @staticmethod
    def generate_quiz_html(questions: List[Dict], title: str = "Quiz") -> str:
        """توليد HTML للكويز"""
        
        # ✅ توليد HTML لكل سؤال
        questions_html = ""
        for i, q in enumerate(questions):
            options_html = ""
            for opt in q.get('options', []):
                options_html += f"""
                    <div class="option" data-letter="{opt.get('letter', '')}" data-opt="{opt.get('letter', '')}" onclick="selectAnswer({i}, '{opt.get('letter', '')}')">
                        {opt.get('text', '')}
                    </div>
                """
            
            questions_html += f"""
                <div class="question-card" id="q-{i}" data-index="{i}">
                    <div class="q-header">
                        <div class="q-num">{q.get('number', i+1)}</div>
                        <div class="q-cat">{q.get('category', 'General')}</div>
                    </div>
                    <div class="q-text">{q.get('text', '')}</div>
                    <div class="options" id="opts-{i}">
                        {options_html}
                    </div>
                    <div class="feedback" id="fb-{i}"></div>
                </div>
            """
        
        # ✅ HTML كامل
        html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | A.D.Gad-platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        /* جميع الأنماط من الملف الذي أرسلته */
        :root {{
            --primary: #2d6a4f;
            --primary-light: #52b788;
            --primary-dark: #1b4332;
            --secondary: #1e7a7a;
            --secondary-light: #3d9e9e;
            --dark: #1a2a2a;
            --card-bg: rgba(255,255,255,0.85);
            --card-bg-hover: rgba(255,255,255,0.95);
            --light: #e8f0ee;
            --gray: #7a9a92;
            --gray-light: #b5cdc5;
            --white: #f5faf8;
            --success: #52b788;
            --success-light: #74c69d;
            --error: #d97777;
            --error-light: #e8a8a8;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Cairo', sans-serif;
            background: linear-gradient(145deg, #e8f0ee 0%, #d4e4df 40%, #c5d9d3 100%);
            color: #1a2a2a;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: rgba(255,255,255,0.88);
            backdrop-filter: blur(15px);
            border-radius: 32px;
            padding: 30px 25px;
            border: 1px solid rgba(45,106,79,0.10);
            box-shadow: 0 8px 40px rgba(0,0,0,0.03);
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 25px;
        }}
        
        .header h1 {{
            font-size: 1.8rem;
            font-weight: 800;
            color: var(--primary);
        }}
        
        .header p {{
            color: var(--gray);
        }}
        
        .progress-stats {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
            margin: 15px 0;
        }}
        
        .stat-badge {{
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            background: rgba(255,255,255,0.6);
            border: 1px solid rgba(45,106,79,0.10);
            color: var(--dark);
        }}
        
        .stat-correct {{ background: rgba(82,183,136,0.08); border-color: var(--success); color: var(--primary); }}
        .stat-wrong {{ background: rgba(217,119,119,0.06); border-color: var(--error); color: #8b5555; }}
        .stat-percent {{ background: rgba(45,106,79,0.06); border-color: var(--primary); color: var(--primary); }}
        
        .progress-bar-container {{
            width: 100%;
            height: 6px;
            background: rgba(45,106,79,0.10);
            border-radius: 3px;
            overflow: hidden;
            margin: 10px 0 20px;
        }}
        
        .progress-bar {{
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            border-radius: 3px;
            transition: width 0.3s;
            width: 0%;
        }}
        
        .question-card {{
            background: rgba(255,255,255,0.85);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 22px 24px;
            margin-bottom: 16px;
            border: 1px solid rgba(45,106,79,0.06);
            transition: all 0.3s;
            box-shadow: 0 2px 12px rgba(0,0,0,0.02);
        }}
        
        .question-card:hover {{
            transform: translateX(-4px);
            border-color: var(--secondary);
            background: rgba(255,255,255,0.92);
            box-shadow: 0 4px 20px rgba(0,0,0,0.04);
        }}
        
        .question-card.correct {{ border-right: 4px solid var(--success); background: rgba(82,183,136,0.03); }}
        .question-card.wrong {{ border-right: 4px solid var(--error); background: rgba(217,119,119,0.03); }}
        
        .q-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 14px;
        }}
        
        .q-num {{
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            width: 34px;
            height: 34px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: white;
            font-size: 0.9rem;
        }}
        
        .q-cat {{
            background: rgba(30,122,122,0.06);
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.65rem;
            font-weight: 600;
            color: var(--secondary);
        }}
        
        .q-text {{
            font-size: 1rem;
            font-weight: 500;
            line-height: 1.7;
            margin-bottom: 16px;
            color: #1a2a2a;
        }}
        
        .options {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .option {{
            padding: 10px 16px;
            background: rgba(255,255,255,0.4);
            border: 1px solid rgba(45,106,79,0.06);
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s;
            font-family: 'Cairo', sans-serif;
            font-size: 0.9rem;
            color: #1a2a2a;
            text-align: right;
        }}
        
        .option:hover:not(:disabled) {{
            background: rgba(45,106,79,0.03);
            border-color: var(--primary);
            transform: translateX(-4px);
        }}
        
        .option.correct {{
            background: rgba(82,183,136,0.06);
            border-color: var(--success);
            color: var(--primary);
        }}
        
        .option.wrong {{
            background: rgba(217,119,119,0.06);
            border-color: var(--error);
            color: #8b5555;
        }}
        
        .option:disabled {{
            cursor: default;
        }}
        
        .feedback {{
            margin-top: 12px;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 0.8rem;
            display: none;
            animation: slideDown 0.3s ease;
        }}
        
        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .feedback.correct {{
            background: rgba(82,183,136,0.04);
            border-right: 3px solid var(--success);
            color: var(--primary);
        }}
        
        .feedback.wrong {{
            background: rgba(217,119,119,0.04);
            border-right: 3px solid var(--error);
            color: #8b5555;
        }}
        
        .submit-area {{
            text-align: center;
            margin: 25px 0;
        }}
        
        .btn-submit {{
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            border: none;
            padding: 12px 45px;
            border-radius: 40px;
            color: white;
            font-size: 0.95rem;
            font-weight: 700;
            font-family: 'Cairo', sans-serif;
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .btn-submit:hover:not(:disabled) {{
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(45,106,79,0.2);
        }}
        
        .btn-submit:disabled {{
            opacity: 0.4;
            cursor: not-allowed;
        }}
        
        .results-screen {{
            display: none;
            text-align: center;
            padding: 20px;
        }}
        
        .results-screen h2 {{
            color: var(--primary);
            font-size: 1.8rem;
            margin-bottom: 8px;
        }}
        
        .results-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin: 20px 0;
        }}
        
        .result-stat {{
            padding: 12px;
            border-radius: 14px;
        }}
        
        .result-stat.c {{ background: rgba(82,183,136,0.04); border: 1px solid var(--success); }}
        .result-stat.w {{ background: rgba(217,119,119,0.04); border: 1px solid var(--error); }}
        .result-stat.p {{ background: rgba(30,122,122,0.04); border: 1px solid var(--secondary); }}
        
        .result-stat .num {{
            font-size: 1.6rem;
            font-weight: 800;
        }}
        .result-stat.c .num {{ color: var(--primary); }}
        .result-stat.w .num {{ color: #8b5555; }}
        .result-stat.p .num {{ color: var(--secondary); }}
        .result-stat .label {{ font-size: 0.8rem; color: var(--gray); }}
        
        .review-area {{
            text-align: right;
            margin-top: 25px;
            max-height: 280px;
            overflow-y: auto;
        }}
        
        .review-item {{
            background: rgba(217,119,119,0.03);
            border-right: 3px solid var(--error);
            padding: 10px 14px;
            border-radius: 10px;
            margin-bottom: 8px;
            text-align: right;
            font-size: 0.8rem;
        }}
        
        .btn-restart {{
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            border: none;
            padding: 10px 28px;
            border-radius: 40px;
            color: white;
            font-weight: 700;
            font-family: 'Cairo', sans-serif;
            cursor: pointer;
            margin: 8px 4px;
            transition: all 0.3s;
            font-size: 0.9rem;
        }}
        
        .btn-home {{
            background: rgba(255,255,255,0.4);
            border: 1px solid rgba(45,106,79,0.10);
            padding: 10px 28px;
            border-radius: 40px;
            color: var(--gray);
            font-weight: 700;
            font-family: 'Cairo', sans-serif;
            cursor: pointer;
            margin: 8px 4px;
            transition: all 0.3s;
            font-size: 0.9rem;
        }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 15px; }}
            .question-card {{ padding: 16px; }}
            .results-stats {{ gap: 6px; }}
            .result-stat .num {{ font-size: 1.2rem; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📚 {title}</h1>
        <p>تم إنشاؤه بواسطة A.D.Gad-platform</p>
        <div class="progress-stats">
            <span class="stat-badge stat-correct" id="statCorrect">✅ 0</span>
            <span class="stat-badge stat-wrong" id="statWrong">❌ 0</span>
            <span class="stat-badge stat-percent" id="statPercent">📊 0%</span>
        </div>
        <div class="progress-bar-container">
            <div class="progress-bar" id="progressFill"></div>
        </div>
    </div>
    
    <div id="questionsContainer">
        {questions_html}
    </div>
    
    <div class="submit-area">
        <button class="btn-submit" id="submitBtn" disabled>🎯 Show Results</button>
    </div>
    
    <div class="results-screen" id="resultsScreen">
        <h2>🏆 Quiz Completed!</h2>
        <div class="results-stats">
            <div class="result-stat c"><div class="num" id="resultCorrect">0</div><div class="label">✅ Correct</div></div>
            <div class="result-stat w"><div class="num" id="resultWrong">0</div><div class="label">❌ Wrong</div></div>
            <div class="result-stat p"><div class="num" id="resultPercent">0%</div><div class="label">📊 Percentage</div></div>
        </div>
        <button class="btn-restart" onclick="restartQuiz()">🔄 Retake Quiz</button>
        <button class="btn-home" onclick="window.location.reload()">🏠 Home</button>
        <div class="review-area" id="reviewArea"></div>
    </div>
</div>

<script>
// ✅ بيانات الأسئلة من Backend
const QUESTIONS = {json.dumps(questions, ensure_ascii=False)};

let currentQuestions = QUESTIONS;
let answeredCount = 0;
let correctCount = 0;
let wrongCount = 0;
let quizActive = true;

function selectAnswer(qIdx, optLetter) {{
    if (!quizActive) return;
    const q = currentQuestions[qIdx];
    const optsDiv = document.getElementById(`opts-${{qIdx}}`);
    if (optsDiv.querySelector('.correct,.wrong')) return;

    const isCorrect = optLetter === q.correct;
    const allOpts = optsDiv.querySelectorAll('.option');

    allOpts.forEach(opt => {{
        opt.style.pointerEvents = 'none';
        if (opt.dataset.opt === q.correct) {{
            opt.classList.add('correct');
        }} else if (opt.dataset.opt === optLetter && !isCorrect) {{
            opt.classList.add('wrong');
        }}
    }});

    const fb = document.getElementById(`fb-${{qIdx}}`);
    fb.style.display = 'block';
    fb.className = `feedback ${{isCorrect ? 'correct' : 'wrong'}}`;
    fb.innerHTML = isCorrect ? `✅ Correct!` : `❌ Wrong! The correct answer: ${{q.correct}}`;

    document.getElementById(`q-${{qIdx}}`).classList.add(isCorrect ? 'correct' : 'wrong');

    if (isCorrect) correctCount++;
    else wrongCount++;
    answeredCount++;

    updateStats();

    if (answeredCount === currentQuestions.length) {{
        document.getElementById('submitBtn').disabled = false;
    }}
}}

function updateStats() {{
    const total = currentQuestions.length;
    const percent = answeredCount > 0 ? Math.round(correctCount / answeredCount * 100) : 0;
    document.getElementById('statCorrect').textContent = `✅ ${{correctCount}}`;
    document.getElementById('statWrong').textContent = `❌ ${{wrongCount}}`;
    document.getElementById('statPercent').textContent = `📊 ${{percent}}%`;
    const progress = total > 0 ? (answeredCount / total * 100) : 0;
    document.getElementById('progressFill').style.width = `${{progress}}%`;
}}

function showResults() {{
    quizActive = false;
    const total = currentQuestions.length;
    const percent = Math.round(correctCount / total * 100);

    document.getElementById('resultCorrect').textContent = correctCount;
    document.getElementById('resultWrong').textContent = wrongCount;
    document.getElementById('resultPercent').textContent = `${{percent}}%`;

    let msg = '';
    if (percent >= 90) msg = '🌟 Excellent! Outstanding performance!';
    else if (percent >= 75) msg = '👏 Very Good! Keep up the great work!';
    else if (percent >= 60) msg = '👍 Good! Review the incorrect answers.';
    else msg = '📚 Needs more revision — You can do better!';
    document.getElementById('resultMessage').innerHTML = msg;

    const reviewDiv = document.getElementById('reviewArea');
    reviewDiv.innerHTML = '<h3>📋 Review Incorrect Answers</h3>';
    let hasWrong = false;

    currentQuestions.forEach((q, idx) => {{
        const card = document.getElementById(`q-${{idx}}`);
        if (card && card.classList.contains('wrong')) {{
            hasWrong = true;
            reviewDiv.innerHTML += `
                <div class="review-item">
                    <strong>❌ Question ${{q.number}}:</strong> ${{q.text}}<br>
                    <strong>✅ Correct Answer:</strong> ${{q.correct}}<br>
                </div>
            `;
        }}
    }});

    if (!hasWrong) {{
        reviewDiv.innerHTML = '<div style="text-align:center;color:#2d6a4f;padding:20px;">🎉 All answers correct! Excellent work!</div>';
    }}

    document.getElementById('questionsContainer').style.display = 'none';
    document.getElementById('submitBtn').style.display = 'none';
    document.getElementById('resultsScreen').style.display = 'block';
}}

function restartQuiz() {{
    location.reload();
}}

document.getElementById('submitBtn').addEventListener('click', showResults);
</script>
</body>
</html>"""
        
        return html